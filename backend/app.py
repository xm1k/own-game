from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
import os 
import threading
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Подключение к БД: читаем из переменной окружения или используем сервис db
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:777@db/ssi'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


def get_player_id_by_login(login: str) -> int | None:
    player = Player.query.filter_by(login=login).first()
    return player.id if player else None

def get_owner_login_by_lobby_id(lobby_code: int) -> str | None:
    l = Lobby.query.filter_by(lobby_id=lobby_code).first()
    owner_id=l.admin_id
    player = Player.query.filter_by(id=owner_id).first()
    return player.login if player else None

def get_lobby_name_by_id(lobby_code: int) -> str | str:
    l = Lobby.query.filter_by(lobby_id=lobby_code).first()
    return l.lobby_name if l else "просто лобби"

def hashp(password):
    h = 0
    for char in password:
        h = h * 257 + ord(char)
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
    :param results: Список результатов в очках ([10 20 30])
    :param k: Коэффициент K для системы Эло (по умолчанию 32).
    :return: Список обновленных рейтингов.
    """
    n = len(ratings)
    new_ratings = [0]*len(ratings)

    for i in range(n):
        actual_score = results[i]
        expected_score_total = 0

        # Рассчитываем общий ожидаемый результат для игрока i
        for j in range(n):
            if i != j:
                expected_score_total += expected_score(ratings[i], ratings[j])

        # Обновляем рейтинг игрока i
        new_ratings[i] = round(k * (actual_score - expected_score_total))

    return new_ratings

# Модель Player
class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    login = db.Column(db.Text, unique=True)
    password = db.Column(db.BigInteger)
    nickname = db.Column(db.Text)
    rating = db.Column(db.Integer)
    lobby_memberships = db.relationship('LobbyMembers', back_populates='player')

# Модель LobbyMembers
class LobbyMembers(db.Model):
    __tablename__ = 'lobbymembers'
    player_id = db.Column(db.BigInteger, db.ForeignKey('players.id'), primary_key=True)
    lobby_id = db.Column(db.BigInteger, db.ForeignKey('lobbies.lobby_id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.now())
    place = db.Column(db.Integer)
    points = db.Column(db.Integer)
    change_rating = db.Column(db.Integer)
    player = db.relationship('Player', back_populates='lobby_memberships')
    lobby = db.relationship('Lobby', back_populates='members')

# Модель Lobby
class Lobby(db.Model):
    __tablename__ = 'lobbies'
    lobby_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    lobby_name = db.Column(db.Text)
    capacity = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.now())
    admin_id = db.Column(db.BigInteger, db.ForeignKey('players.id'))
    active = db.Column(db.Boolean)
    admin = db.relationship('Player', foreign_keys=[admin_id])
    members = db.relationship('LobbyMembers', back_populates='lobby')
# Временное хранилище для лобби (в реальном приложении используйте базу данных)
#вместо надо будет подключить redis
lobbiestmp={}
clicks_per_lobby={}
processing_lobbies = set()

def update_lobby_members(lobby_code):
    s_players,s_scores=get_sorted_players_and_scores(lobby_code)
    rat=[]
    print(s_players)
    print(s_scores)
    lob = Lobby.query.filter_by(lobby_id=lobby_code).first()
    for i in range(len(s_players)):
            pi_id=get_player_id_by_login(s_players[i])
            player = db.session.get(Player, pi_id)
            if (pi_id!=lob.admin_id):
                rat.append(player.rating)
            else:
                rat.append(0)
    changes_raiting=update_elo_ratings(rat,s_scores)
    print(rat)
    print(changes_raiting)
    try:
        print(s_players)
        for i in range(len(s_players)):
            #print(s_players[i])
            p_id=get_player_id_by_login(s_players[i])
            #print(p_id)
            member = LobbyMembers.query.filter_by(lobby_id=lobby_code,player_id=p_id).first()
            if not member:
                continue
            member.points=s_scores[i]
            member.change_rating=changes_raiting[i]
            member.place=i+1
            member.points=s_scores[i]
            db.session.commit()
            player = db.session.get(Player, p_id)
            if player:
                player.rating += changes_raiting[i]
                db.session.commit()
            else:
                return jsonify({"message": "В лобби нет участникa"}), 200

    except Exception as e:
        print("jopa")
        db.session.rollback()
        return jsonify({"error": f"Ошибка базы данных: {str(e)}"}), 500
def get_sorted_players_and_scores(lobby_code):
    """Возвращает два списка: игроки и их очки, отсортированные по убыванию"""
    lobby = lobbiestmp[lobby_code]

    # Собираем пары (email, score) для онлайн-игроков
    players_with_scores = []
    for email in lobby['online']:
        try:
            idx = lobby['online'].index(email)
            players_with_scores.append((email, lobby['score'][idx]))
        except (ValueError, IndexError):
            continue

    # Сортируем по убыванию очков
    sorted_data = sorted(players_with_scores, key=lambda x: x[1], reverse=True)

    # Разделяем на отдельные списки
    return [item[0] for item in sorted_data], [item[1] for item in sorted_data]

def get_sorted_players(lobby_code):
    """Возвращает отсортированный список игроков с очками"""
    lobby = lobbiestmp[int(lobby_code)]
    online_players = lobby['online']

    # Создаем список пар (очки, игрок) для онлайн игроков
    players_with_scores = []
    for player in online_players:
        try:
            index = lobby['online'].index(player)
            players_with_scores.append({
                'player': player,
                'score': lobby['score'][index]
            })
        except ValueError:
            continue

    # Сортируем по убыванию очков
    sorted_players = sorted(players_with_scores,
                            key=lambda x: x['score'],
                            reverse=True)

    # Форматируем результат
    return [{
        'player': item['player'],
        'score': item['score']
    } for item in sorted_players]

@app.route('/players', methods=['GET'])
def get_all_players():
    # Получаем всех игроков, сортируем по рейтингу по убыванию
    players = Player.query.order_by(Player.rating.desc()).all()

    # Формируем ответ: порядок, имя и рейтинг
    result = []
    for index, p in enumerate(players, start=1):
        result.append({
            'place': index,
            'name': p.nickname,
            'rating': p.rating
        })
    return jsonify({'status': 'success', 'players': result}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    print('Received data:', data, flush=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

    email = data.get('email')
    password = data.get('password')

    print('Email:', email, 'Password:', password)
    player = Player.query.filter_by(login=email).first()
    print(player.password)
    if (password) == player.password:
        print('sucess', player.login)
        return jsonify({'status': 'success', 'message': 'Вход успешен', 'name': player.nickname}), 200
    return jsonify({'status': 'error', 'message': 'Неверный email или пароль'}), 400

@app.route('/responsestatus', methods=['POST'])
def responsestatus():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

    l_code = int(data.get('lobby_code'))
    status = data.get('status')
    nominal = data.get('nominal', 1)  # По умолчанию 1, если номинал не передан

    if l_code not in lobbiestmp:
        return jsonify({'status': 'error', 'message': 'Lobby not found'}), 404

    lobby = lobbiestmp[l_code]
    respondent = lobby['respondent']

    if respondent in lobby['online']:
        try:
            index = lobby['online'].index(respondent)
            if status == 'correct':
                lobby['score'][index] += nominal
            else:
                lobby['score'][index] -= nominal
        except (ValueError, IndexError) as e:
            print(f"Error updating score: {e}")

    lobby['respondent'] = ''
    return jsonify({'status': 'success'}), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    Password = data.get('password')
    name = data.get('name')

    print(f"Регистрация: {email}, {Password}, {name}")

    if email and Password and name:
        new_player = Player(
            login=email,
            password=(Password),
            nickname=name,
            rating=1500
        )
        db.session.add(new_player)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Регистрация успешна', 'name': name}), 201
    return jsonify({'status': 'error', 'message': 'Ошибка регистрации'}), 400

@app.route('/next-question', methods=['POST'])
def next_question():
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))

    if lobby_code not in lobbiestmp:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    lobby = lobbiestmp[lobby_code]
    lobby['question_number'] = lobby.get('question_number', 1) + 1
    question_number = lobby['question_number']
    # Циклический номинал: 10,20,30,40,50,10,20...
    question_nominal = 10 * (((question_number - 1) % 5) + 1)
    lobby['question_nominal'] = question_nominal

    # Отправляем событие всем игрокам в лобби
    socketio.emit('next_question', {
        'lobby_code': lobby_code,
        'question_number': question_number,
        'question_nominal': question_nominal
    }, room=lobby_code)

    return jsonify({
        'status': 'success',
        'question_number': question_number,
        'question_nominal': question_nominal
    }), 200


@app.route('/delete-lobby', methods=['POST'])
def delete_lobby():
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))

    if not lobby_code:
        return jsonify({'status': 'error', 'message': 'Код лобби не указан'}), 400
    L=Lobby.query.filter_by(lobby_id=lobby_code).first()
    if not L:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404
    update_lobby_members(lobby_code)
    L.active=False
    print("все обновили")
    db.session.commit()
    # Эмитим событие, чтобы уведомить всех участников, что лобби закрыто
    socketio.emit('lobby_deleted', {'lobby_code': lobby_code}, room=lobby_code)

    # Удаляем лобби из временного хранилища
    del lobbiestmp[int(lobby_code)]

    return jsonify({'status': 'success', 'message': 'Лобби успешно удалено'}), 200


@app.route('/create-lobby', methods=['POST'])
def create_lobby():
    data = request.get_json()
    l_name = data.get('lobby_name')
    player_name = data.get('email')  # Получаем email создателя как имя

    if not l_name or not player_name:
        return jsonify({'status': 'error', 'message': 'Название лобби или имя игрока не указано'}), 400
    a_id=get_player_id_by_login(player_name)
    new_lobby = Lobby(
        lobby_name=l_name,
        capacity=12,
        admin_id=a_id,
        active=True
    )
    db.session.add(new_lobby)
    db.session.commit()
    lobby_code = int(new_lobby.lobby_id)
    
    print(lobbiestmp)
    lobbiestmp[lobby_code] = {
        'online': [player_name],
        'score': [0],
        'respondent': '',
        'question_number': 1,
        'question_nominal': 10
    }
    print(lobbiestmp)
    socketio.emit('lobby_created', {
        'lobby_code': lobby_code,
        'player_name': player_name,   
        'question_number': 1,
        'question_nominal': 10
    })

    return jsonify({
        'status': 'success',
        'message': 'Лобби создано',
        'lobby_code': lobby_code,
        'lobby_name': l_name,
        'owner': player_name,
        'players': lobbiestmp[lobby_code]['online'],
        'question_number': 1,
        'question_nominal': 10
    }), 201


@app.route('/join-lobby', methods=['POST'])
def join_lobby():
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))
    player_name = data.get('email')
    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400
    L=Lobby.query.filter_by(lobby_id=lobby_code).first()
    if not L or not L.active:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Добавление игрока в лобби
    a_id=get_player_id_by_login(player_name)
    print(a_id, player_name, lobby_code, flush=True)
    if not is_player_in_lobby(lobby_code,a_id):
        new_l_m=LobbyMembers(
            player_id=a_id,
            lobby_id=lobby_code
        )
        db.session.add(new_l_m)
        db.session.commit()

    if player_name not in lobbiestmp[lobby_code]['online']:
        lobbiestmp[lobby_code]['online'].append(player_name)
        lobbiestmp[lobby_code]['score'].append(0)
    print("bipki")
    return jsonify({
        'status': 'success',
        'message': 'Вы присоединились к лобби',
        'lobby_code': lobby_code,
        'lobby_name': get_lobby_name_by_id(lobby_code),
        'players': get_sorted_players(lobby_code),
        'question_number': lobbiestmp[lobby_code].get('question_number', 1),
        'question_nominal': lobbiestmp[lobby_code].get('question_nominal', 10)
    }), 200
def is_player_in_lobby(lobby_id: int, player_id: int):
    """
    Проверяет, состоит ли игрок в указанном лобби
    :param lobby_id: ID лобби
    :param player_id: ID игрока
    :return: True если связь существует, False если нет
    """
    membership = LobbyMembers.query.filter_by(
        lobby_id=lobby_id,
        player_id=player_id
    ).first()

    return membership is not None

def process_lobby_clicks(lobby_code):
    """
    Ждём 1 секунду с момента первого клика, 
    затем выбираем победителя (самый маленький timestamp) 
    и рассылаем всем в лобби.
    """
    # Ожидаем сбора всех кликов в течение секунды
    time.sleep(1)

    # Достанем и очистим накопленные клики
    clicks = clicks_per_lobby.pop(lobby_code, [])

    if clicks:
        # Сортируем по timestamp и берём первый
        winner = min(clicks, key=lambda x: x['timestamp'])

        # Сохраняем результат в лобби
        lobbiestmp[lobby_code]['respondent'] = winner['email']

        # Эмитим событие победителя
        socketio.emit('click_winner', {
            'lobby_code': lobby_code,
            'winner_email': winner['email'],
            'winner_timestamp': winner['timestamp']
        }, room=lobby_code)

    # Убираем флаг обработки, чтобы на следующий клик можно было снова запустить поток
    processing_lobbies.discard(lobby_code)

@app.route('/get-lobby-info', methods=['POST'])
def get_lobby_info():
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))

    if not lobby_code:
        return jsonify({'status': 'error', 'message': 'Код лобби не указан'}), 400

    if lobby_code not in lobbiestmp:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Получаем отсортированные данные
    sorted_players, sorted_scores = get_sorted_players_and_scores(lobby_code)
    return jsonify({
        'status': 'success',
        'lobby_name': get_lobby_name_by_id(lobby_code),
        'players': sorted_players,  # список игроков с их очками
        'scores': sorted_scores,
        'owner': get_owner_login_by_lobby_id(lobby_code),
        'respondent': lobbiestmp[lobby_code]['respondent'],
        'question_number': lobbiestmp[lobby_code].get('question_number', 1),
        'question_nominal': lobbiestmp[lobby_code].get('question_nominal', 10)
    }), 200


@app.route('/leave-lobby', methods=['POST'])
def leave_lobby():
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))
    player_name = data.get('email')
    
    print(data)

    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if lobby_code not in lobbiestmp:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    return jsonify({
        'status': 'success',
        'message': 'Вы покинули лобби',
        'lobby_name': get_lobby_name_by_id(lobby_code),
        'players': lobbiestmp[lobby_code]['online']
    }), 200


@app.route('/click-timestamp', methods=['POST'])
def receive_click_timestamp():
    data = request.get_json()
    timestamp = data.get('timestamp')
    email = data.get('email', 'Не указан')
    lobby_code = int(data.get('lobby_code', 0))

    if not timestamp or not lobby_code:
        return jsonify({'status': 'error', 'message': 'Нет данных о клике'}), 400

    # Инициализируем список кликов, если первый раз
    if lobby_code not in clicks_per_lobby:
        clicks_per_lobby[lobby_code] = []

    # Добавляем текущий клик
    clicks_per_lobby[lobby_code].append({
        'email': email,
        'timestamp': timestamp
    })

    # Запускаем обработчик только один раз за «раунд»
    if lobby_code not in processing_lobbies:
        processing_lobbies.add(lobby_code)
        thread = threading.Thread(
            target=process_lobby_clicks,
            args=(lobby_code,),
            daemon=True
        )
        thread.start()

    return jsonify({
        'status': 'success',
        'received_timestamp': timestamp,
        'email': email
    }), 200


@socketio.on('connect')
def handle_connect():
    print('Клиент подключился:', request.sid)

@socketio.on('leave_lobby')
def handle_leave_lobby(data):
    lobby_code = data['lobby_code']
    user_id = data['user_id']
    leave_room(lobby_code)
    leave_room(user_id)
    emit('user_left', {'user_id': user_id}, room=lobby_code)

@socketio.on('disconnect')
def handle_disconnect():
    print('Клиент отключился:', request.sid)

@socketio.on('join_lobby')
def handle_join_lobby(data):
    lobby_code = data['lobby_code']
    user_id = data['user_id']
    join_room(lobby_code)  # Комната лобби для широковещательных сообщений
    join_room(user_id)     # Персональная комната для прямых сообщений
    print(f"User {user_id} joined lobby {lobby_code}")
    emit('user_joined', {'user_id': user_id}, room=lobby_code)


@socketio.on('webrtc_answer')
def handle_answer(data):
    if not all(k in data for k in ['answer', 'sender_id', 'target_id']):
        print("Ошибка: отсутствуют необходимые данные в webrtc_answer", data)
        return

    emit('webrtc_answer', {
        'answer': data['answer'],
        'sender_id': data['sender_id']
    }, to=data['target_id'])


@socketio.on('webrtc_offer')
def handle_offer(data):
    sender_id = data.get('sender_id')
    if not sender_id:
        print("Ошибка: отсутствует sender_id в webrtc_offer", data)
        return  # Пропускаем обработку, если sender_id нет

    emit('webrtc_offer', {
        'offer': data['offer'],
        'sender_id': sender_id
    }, to=data['target_id'])

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    sender_id = data.get('sender_id')
    if not sender_id:
        print("Ошибка: отсутствует sender_id в ice_candidate", data)
        return  # Пропускаем обработку

    emit('ice_candidate', {
        'candidate': data['candidate'],
        'sender_id': sender_id
    }, to=data['target_id'])



if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)

####