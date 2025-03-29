from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import threading
import time

clicks_per_lobby = {}

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
# Временное хранилище для лобби (в реальном приложении используйте базу данных)
lobbies = {}

def get_sorted_players(lobby_code):
    """Возвращает отсортированный список игроков с очками"""
    lobby = lobbies[lobby_code]
    online_players = lobby['online']

    # Создаем список пар (очки, игрок) для онлайн игроков
    players_with_scores = []
    for player in online_players:
        try:
            index = lobby['players'].index(player)
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


def get_sorted_players_and_scores(lobby_code):
    """Возвращает два списка: игроки и их очки, отсортированные по убыванию"""
    lobby = lobbies[lobby_code]

    # Собираем пары (email, score) для онлайн-игроков
    players_with_scores = []
    for email in lobby['online']:
        try:
            idx = lobby['players'].index(email)
            players_with_scores.append((email, lobby['score'][idx]))
        except (ValueError, IndexError):
            continue

    # Сортируем по убыванию очков
    sorted_data = sorted(players_with_scores, key=lambda x: x[1], reverse=True)

    # Разделяем на отдельные списки
    return [item[0] for item in sorted_data], [item[1] for item in sorted_data]

def get_sorted_players(lobby_code):
    """Возвращает отсортированный список игроков с очками"""
    lobby = lobbies[lobby_code]
    online_players = lobby['online']

    # Создаем список пар (очки, игрок) для онлайн игроков
    players_with_scores = []
    for player in online_players:
        try:
            index = lobby['players'].index(player)
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

    if email == 'a@b' and password == 'c':
        return jsonify({'status': 'success', 'message': 'Вход успешен', 'name': "name"}), 200
    return jsonify({'status': 'error', 'message': 'Неверный email или пароль'}), 400

@app.route('/responsestatus', methods=['POST'])
def responsestatus():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

    l_code = data.get('lobby_code')
    status = data.get('status')
    nominal = data.get('nominal', 1)  # По умолчанию 1, если номинал не передан

    if l_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Lobby not found'}), 404

    lobby = lobbies[l_code]
    respondent = lobby['respondent']

    if respondent in lobby['players']:
        try:
            index = lobby['players'].index(respondent)
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
    password = data.get('password')
    name = data.get('name')

    print(f"Регистрация: {email}, {password}, {name}")

    if email and password and name:
        return jsonify({'status': 'success', 'message': 'Регистрация успешна', 'name': name}), 201
    return jsonify({'status': 'error', 'message': 'Ошибка регистрации'}), 400

@app.route('/next-question', methods=['POST'])
def next_question():
    data = request.get_json()
    lobby_code = data.get('lobby_code')

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    lobby = lobbies[lobby_code]
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
    lobby_code = data.get('lobby_code')

    if not lobby_code:
        return jsonify({'status': 'error', 'message': 'Код лобби не указан'}), 400
    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Эмитим событие, чтобы уведомить всех участников, что лобби закрыто
    socketio.emit('lobby_deleted', {'lobby_code': lobby_code}, room=lobby_code)

    # Удаляем лобби из временного хранилища
    del lobbies[lobby_code]

    return jsonify({'status': 'success', 'message': 'Лобби успешно удалено'}), 200


@app.route('/create-lobby', methods=['POST'])
def create_lobby():
    data = request.get_json()
    lobby_name = data.get('lobby_name')
    player_name = data.get('email')  # Получаем email создателя как имя

    if not lobby_name or not player_name:
        return jsonify({'status': 'error', 'message': 'Название лобби или имя игрока не указано'}), 400

    lobby_code = str(random.randint(1000, 9999))
    while lobby_code in lobbies:
        lobby_code = str(random.randint(1000, 9999))

    # Инициализация лобби с вопросом
    lobbies[lobby_code] = {
        'name': lobby_name,
        'owner': player_name,
        'players': [player_name],
        'online': [player_name],
        'score': [0],
        'respondent': '',
        'question_number': 1,
        'question_nominal': 10
    }

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
        'lobby_name': lobby_name,
        'owner': player_name,
        'players': lobbies[lobby_code]['online'],
        'question_number': 1,
        'question_nominal': 10
    }), 201


@app.route('/join-lobby', methods=['POST'])
def join_lobby():
    data = request.get_json()
    lobby_code = data.get('lobby_code')
    player_name = data.get('email')

    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Добавление игрока в лобби
    if player_name not in lobbies[lobby_code]['players']:
        lobbies[lobby_code]['players'].append(player_name)
        lobbies[lobby_code]['score'].append(0)  # Добавляем начальный счет

    if player_name not in lobbies[lobby_code]['online']:
        lobbies[lobby_code]['online'].append(player_name)

    return jsonify({
        'status': 'success',
        'message': 'Вы присоединились к лобби',
        'lobby_code': lobby_code,
        'lobby_name': lobbies[lobby_code]['name'],
        'players': get_sorted_players(lobby_code),
        'question_number': lobbies[lobby_code].get('question_number', 1),
        'question_nominal': lobbies[lobby_code].get('question_nominal', 10)
    }), 200

def process_lobby_clicks(lobby_code):
    """ Ждет секунду после первого клика и определяет победителя. """
    time.sleep(1)  # Ждем секунду после первого клика

    if lobby_code in clicks_per_lobby and clicks_per_lobby[lobby_code]:
        # Сортируем клики по времени
        sorted_clicks = sorted(clicks_per_lobby[lobby_code], key=lambda x: x['timestamp'])
        winner = sorted_clicks[0]  # Первый клик — победитель

        print(f"Победитель в лобби {lobby_code}: {winner['email']} нажал в {winner['timestamp']} мс")

        lobbies[lobby_code]['respondent'] = winner['email']

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
    lobby_code = data.get('lobby_code')

    if not lobby_code:
        return jsonify({'status': 'error', 'message': 'Код лобби не указан'}), 400

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Получаем отсортированные данные
    sorted_players, sorted_scores = get_sorted_players_and_scores(lobby_code)

    return jsonify({
        'status': 'success',
        'lobby_name': lobbies[lobby_code]['name'],
        'players': sorted_players,  # список игроков с их очками
        'scores': sorted_scores,
        'owner': lobbies[lobby_code]['owner'],
        'respondent': lobbies[lobby_code]['respondent'],
        'question_number': lobbies[lobby_code].get('question_number', 1),
        'question_nominal': lobbies[lobby_code].get('question_nominal', 10)
    }), 200


@app.route('/leave-lobby', methods=['POST'])
def leave_lobby():
    data = request.get_json()
    lobby_code = data.get('lobby_code')
    player_name = data.get('email')

    print(data)

    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Удаление игрока из лобби
    if player_name in lobbies[lobby_code]['online']:
        lobbies[lobby_code]['online'].remove(player_name)

    return jsonify({
        'status': 'success',
        'message': 'Вы покинули лобби',
        'lobby_name': lobbies[lobby_code]['name'],
        'players': lobbies[lobby_code]['online']
    }), 200


@app.route('/click-timestamp', methods=['POST'])
def receive_click_timestamp():
    data = request.json
    timestamp = data.get('timestamp')
    email = data.get('email', 'Не указан')
    lobby_code = data.get('lobby_code')

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