from flask import Flask, request, jsonify
from flask_cors import CORS
import random
from sqlalchemy import create_engine, text

def hashp(password) :
    h=0
    for l in password:
        h=h * 257+int(l)
    return h
def expected_score(rating_a, rating_b):
    """
    Рассчитывает ожидаемый результат для игрока A против игрока B.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def update_elo_ratings(ratings, results, k=32):
    """
    Обновляет рейтинги игроков на основе результатов матча.

    :param ratings: Список текущих рейтингов игроков.
    :param results: Список результатов, где 1 — победа, 0 — поражение, 0.5 — ничья.
    :param k: Коэффициент K для системы Эло (по умолчанию 32).
    :return: Список обновленных рейтингов.
    """
    n = len(ratings)
    new_ratings = ratings.copy()

    for i in range(n):
        actual_score = results[i]
        expected_score_total = 0

        # Рассчитываем общий ожидаемый результат для игрока i
        for j in range(n):
            if i != j:
                expected_score_total += expected_score(ratings[i], ratings[j])

        # Обновляем рейтинг игрока i
        new_ratings[i] += k * (actual_score - expected_score_total)

    return new_ratings
app = Flask(__name__)
CORS(app)
def anti_sqlin(text):
    #так как у пользователея мало свободного ввода (только ввод того где точно не может быть сочетания '};' то с помощью replace я просто удалю часть возможных попыток sql инъекции)
    text=text.replace('};','')
    text=text.replace(';','')
    return text
auth = {
    'user' : 'postgres',
    'password': '777',
    'host':'localhost/ssi'
}
engine = create_engine(
    'postgresql+psycopg2://{}:{}@{}'.format(auth['user'], auth['password'],auth['host']),
    echo=True,
    isolation_level='SERIALIZABLE',
)

# Временное хранилище для лобби (в реальном приложении используйте базу данных)
lobbies = {}

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
    print('Received data:', data)

    email = data.get('email')
    password = data.get('password')

    print('Email:', email, 'Password:', password)
    q="select * from authorization('{}',{})".format(email,hashp(password)%1000000007)
    with engine.connect() as connect:
        res=connect.execute(text(q))
        connect.commit()
    for x in res:
        f=x[0]
        print(x[0])
        if f:
            return jsonify({'status': 'success', 'message': 'Вход успешен', 'name': x[2]}), 200
        return jsonify({'status': 'error', 'message': 'Неверный email или пароль'}), 400


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    print(f"Регистрация: {email}, {password}, {name}")
    q=f"select add_user('{name}','{email}',{hashp(password)%1000000007})"
    with engine.connect() as connect:
        connect.execute(text(q))
        connect.commit()
    if email and password and name:
        return jsonify({'status': 'success', 'message': 'Регистрация успешна', 'name': name}), 201
    return jsonify({'status': 'error', 'message': 'Ошибка регистрации'}), 400


@app.route('/create-lobby', methods=['POST'])
def create_lobby():
    print("CREATE")
    data = request.get_json()
    print(data)
    lobby_name = data.get('lobby_name')
    player_name = data.get('email')  # Получаем имя создателя

    if not lobby_name or not player_name:
        return jsonify({'status': 'error', 'message': 'Название лобби или имя игрока не указано'}), 400

    q=f"select * from get_info_p('{player_name}')"
    with engine.connect() as connect:
        res=connect.execute(text(q))
        connect.commit()
    temp=()
    for x in res:
        temp=x
    id=temp[0]
    #p_name=res[0][1]
    q=f"select * from add_lobby('{lobby_name}',0,{id})"
    with engine.connect() as connect:
        res=connect.execute(text(q))
        connect.commit()
    # Генерация уникального кода лобби
    lobby_code=0
    for x in res:
        lobby_code=int(x[0])
    # Создание лобби с добавлением владельца отдельно
    lobbies[int(lobby_code)] = {
        'name': lobby_name,
        'owner': player_name,  # Сохранение владельца отдельно
        'players': [player_name]  # Добавляем владельца в список игроков
    }

    return jsonify({
        'status': 'success',
        'message': 'Лобби создано',
        'lobby_code': lobby_code,
        'lobby_name': lobby_name,
        'owner': player_name,  # Отправляем владельца клиенту
        'players': lobbies[lobby_code]['players']
    }), 201



@app.route('/join-lobby', methods=['POST'])
def join_lobby():
    print("JOIN")
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))
    player_name = data.get('email')

    print(data)
    print(lobbies)
    print(lobby_code, lobbies[(lobby_code)])
    print(lobby_code not in lobbies)
    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if int(lobby_code) not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Добавление игрока в лобби
    if(player_name not in lobbies[int(lobby_code)]['players']):
        lobbies[lobby_code]['players'].append(player_name)
    q=f"select * from get_info_p('{player_name}')"
    with engine.connect() as connect:
        r=connect.execute(text(q))
        connect.commit()
    for x in r:
        res=x
    id=res[0]
    q=f"select add_user_in_lobby({id},{lobby_code})"
    with engine.connect() as connect:
        connect.execute(text(q))
        connect.commit()  
    print("да не выходи ты нахуй")
    return jsonify({
        'status': 'success',
        'message': 'Вы присоединились к лобби',
        'lobby_code': lobby_code,
        'lobby_name': lobbies[int(lobby_code)]['name'],
        # СДЕЛАТЬ В БД ЧТОБЫ ПРИСЫЛАЛИСЬ НЕ ПОЧТЫ А ИМЕНА ПО ПОЧТАМ
        'players': lobbies[int(lobby_code)]['players']
    }), 200


@app.route('/get-lobby-info', methods=['POST'])
def get_lobby_info():
    print("GET INFO")
    data = request.get_json()
    lobby_code = data.get('lobby_code')
    print(lobby_code, lobby_code not in lobbies)
    if not lobby_code:
        return jsonify({'status': 'error', 'message': 'Код лобби не указан'}), 400

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    return jsonify({
        'status': 'success',
        'lobby_name': lobbies[lobby_code]['name'],
        'players': lobbies[lobby_code]['players']
    }), 200


@app.route('/leave-lobby', methods=['POST'])
def leave_lobby():
    print("LEAVE")
    data = request.get_json()
    lobby_code = data.get('lobby_code')
    player_name = data.get('email')

    print(data)
    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if (lobby_code) not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Удаление игрока из лобби
    if player_name in lobbies[(lobby_code)]['players']:
        lobbies[(lobby_code)]['players'].remove(player_name)

    return jsonify({
        'status': 'success',
        'message': 'Вы покинули лобби',
        'lobby_name': lobbies[(lobby_code)]['name'],
        'players': lobbies[(lobby_code)]['players']
    }), 200


if __name__ == '__main__':
    app.run(debug=True)