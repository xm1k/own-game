from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import threading
from flask_sqlalchemy import SQLAlchemy
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:777@localhost/ssi'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def get_player_id_by_login(login: str) -> int | None:
    player = Player.query.filter_by(login=login).first()
    return player.id if player else None
def hashp(password):
    h = 0
    for char in password:
        h = h * 257 + ord(char)  # Используем ASCII-код символа
    return h


def expected_score(rating_a, rating_b):
    """
    Рассчитывает ожидаемый результат для игрока A против игрока B.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 100))

def update_elo_ratings(ratings, results, players, k):
    """
    Обновляет рейтинги игроков на основе результатов матча.

    :param ratings: Список текущих рейтингов игроков.
    :param results: Список результатов
    :param k: Коэффициент K для системы Эло (по умолчанию 32).
    :return: Список обновленных рейтингов.
    """
    n = len(players)
    new_ratings = ratings.copy()
    for i in range(n):
        actual_score = 0
        for j in range(len(results)):
            if i != j:
                if results[i]>results[j]:
                    actual_score += 1
                elif results[i]>results[j]:
                    actual_score += 0.5

        # Рассчитываем общий ожидаемый результат для игрока i
        expected_score_total = 0
        for j in range(n):
            if i != j:
                expected_score_total += expected_score(ratings[i], ratings[j])

        # Обновляем рейтинг игрока i
        new_ratings[i] += int(round(k * (actual_score - expected_score_total),0))

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
    plase = db.Column(db.Integer)
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
lobbies = {}
#вместо надо будет подключить redis
lobbiestmp={}
clicks_per_lobby={}

def update_lobby_members(lobby_code):
    s_players,s_scores=get_sorted_players_and_scores(lobby_code)
    changes_raiting=[1]*len(s_players)
    print(s_players,s_scores)
    try:
        for i in range(len(s_players)):
            p_id=get_player_id_by_login(s_players[i])
            member = LobbyMembers.query.filter_by(lobby_id=lobby_code,player_id=p_id).first()
            if not member:
                return jsonify({"message": "В лобби нет участникa"}), 200
            member.points=s_scores[i]
            member.change_rating=changes_raiting[i]
            member.plase=i+1
            member.points=s_scores[i]
            db.session.commit()
            player = db.session.get(Player, p_id)
            print(p_id)
            print(player)
            if player:
                print(changes_raiting[i])
                player.rating += changes_raiting[i]
                db.session.commit()
                return jsonify({'status': 'success', 'message': 'Все данные обновлены'}), 200
            return jsonify({"message": "В лобби нет участникa"}), 200

    except Exception as e:
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

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
    print('Received data:', data)

    email = data.get('email')
    password = data.get('password')

    print('Email:', email, 'Password:', password)
    player = Player.query.filter_by(login=email).first()
    print(player.password)
    if hashp(password) == player.password:
        return jsonify({'status': 'success', 'message': 'Вход успешен', 'name': "name"}), 200
    return jsonify({'status': 'error', 'message': 'Неверный email или пароль'}), 400

@app.route('/responsestatus', methods=['POST'])
def responsestatus():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

    l_code = int(data.get('lobby_code'))
    status = data.get('status')
    nominal = data.get('nominal', 1)  # По умолчанию 1, если номинал не передан

    if l_code not in lobbies:
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
            password=hashp(Password),
            nickname=name,
            rating=0
        )
        db.session.add(new_player)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Регистрация успешна', 'name': name}), 201
    return jsonify({'status': 'error', 'message': 'Ошибка регистрации'}), 400

@app.route('/next-question', methods=['POST'])
def next_question():
    data = request.get_json()
    lobby_code = int(data.get('lobby_code'))

    if lobby_code not in lobbies:
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
    
    """while lobby_code in lobbies:
        lobby_code = str(random.randint(1000, 9999))"""

    # Инициализация лобби с вопросом
    lobbies[lobby_code] = {
        'name': l_name,
        'owner': player_name,
        'players': [player_name]
    }
    print(lobbiestmp)
    print("DWDWDWDW", lobbies[lobby_code])
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
    if not L:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Добавление игрока в лобби
    a_id=get_player_id_by_login(player_name)
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
        'lobby_name': lobbies[lobby_code]['name'],
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
    """ Ждет секунду после первого клика и определяет победителя. """
    time.sleep(1)  # Ждем секунду после первого клика

    if lobby_code in clicks_per_lobby and clicks_per_lobby[lobby_code]:
        # Сортируем клики по времени
        sorted_clicks = sorted(clicks_per_lobby[lobby_code], key=lambda x: x['timestamp'])
        winner = sorted_clicks[0]  # Первый клик — победитель

        print(f"Победитель в лобби {lobby_code}: {winner['email']} нажал в {winner['timestamp']} мс")

        lobbiestmp[lobby_code]['respondent'] = winner['email']

        # Отправляем результат в лобби через WebSocket
        socketio.emit('click_winner', {
            'lobby_code': lobby_code,
            'winner_email': winner['email'],
            'winner_timestamp': winner['timestamp']
        }, room=lobby_code)

        # Очищаем список кликов для этого лобби
        clicks_per_lobby.pop(lobby_code, None)

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
        'lobby_name': lobbies[lobby_code]['name'],
        'players': sorted_players,  # список игроков с их очками
        'scores': sorted_scores,
        'owner': lobbies[lobby_code]['owner'],
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

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Удаление игрока из лобби
    if player_name in lobbiestmp[int(lobby_code)]['online']:
        lobbiestmp[int(lobby_code)]['online'].remove(player_name)

    return jsonify({
        'status': 'success',
        'message': 'Вы покинули лобби',
        'lobby_name': lobbies[lobby_code]['name'],
        'players': lobbiestmp[lobby_code]['online']
    }), 200


@app.route('/click-timestamp', methods=['POST'])
def receive_click_timestamp():
    data = request.json
    timestamp = data.get('timestamp')
    email = data.get('email', 'Не указан')
    lobby_code = int(data.get('lobby_code'))

    if not timestamp or not lobby_code:
        return jsonify({'status': 'error', 'message': 'Нет данных о клике'}), 400

    print(f"Пользователь {email} нажал кнопку в {timestamp} мс, в лобби: {lobby_code}")

    # Добавляем клик в хранилище
    if lobby_code not in clicks_per_lobby:
        clicks_per_lobby[lobby_code] = []
        # Запускаем поток для обработки кликов в этом лобби
        thread = threading.Thread(target=process_lobby_clicks, args=(lobby_code,))
        thread.start()

    clicks_per_lobby[lobby_code].append({'email': email, 'timestamp': timestamp})

    return jsonify({'status': 'success', 'received_timestamp': timestamp, 'email': email})


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