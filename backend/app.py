from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
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

    if email == 'a@b' and password == 'c':
        return jsonify({'status': 'success', 'message': 'Вход успешен', 'name': "name"}), 200
    return jsonify({'status': 'error', 'message': 'Неверный email или пароль'}), 400


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


@app.route('/create-lobby', methods=['POST'])
def create_lobby():
    data = request.get_json()
    print(data)
    lobby_name = data.get('lobby_name')
    player_name = data.get('email')  # Получаем имя создателя

    if not lobby_name or not player_name:
        return jsonify({'status': 'error', 'message': 'Название лобби или имя игрока не указано'}), 400

    # Генерация уникального кода лобби
    lobby_code = str(random.randint(1000, 9999))
    while lobby_code in lobbies:
        lobby_code = str(random.randint(1000, 9999))

    # Создание лобби с добавлением владельца отдельно
    lobbies[lobby_code] = {
        'name': lobby_name,
        'owner': player_name,  # Сохранение владельца отдельно
        'players': [player_name]  # Добавляем владельца в список игроков
    }

    socketio.emit('lobby_created', {
        'lobby_code': lobby_code,
        'player_name': player_name
    })

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
    data = request.get_json()
    lobby_code = data.get('lobby_code')
    player_name = data.get('email')

    print(data)

    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Добавление игрока в лобби
    if(player_name not in lobbies[lobby_code]['players']):
        lobbies[lobby_code]['players'].append(player_name)

    return jsonify({
        'status': 'success',
        'message': 'Вы присоединились к лобби',
        'lobby_code': lobby_code,
        'lobby_name': lobbies[lobby_code]['name'],
        # СДЕЛАТЬ В БД ЧТОБЫ ПРИСЫЛАЛИСЬ НЕ ПОЧТЫ А ИМЕНА ПО ПОЧТАМ
        'players': lobbies[lobby_code]['players']
    }), 200


@app.route('/get-lobby-info', methods=['POST'])
def get_lobby_info():
    data = request.get_json()
    lobby_code = data.get('lobby_code')

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
    data = request.get_json()
    lobby_code = data.get('lobby_code')
    player_name = data.get('email')

    print(data)

    if not lobby_code or not player_name:
        return jsonify({'status': 'error', 'message': 'Не указан код лобби или имя игрока'}), 400

    if lobby_code not in lobbies:
        return jsonify({'status': 'error', 'message': 'Лобби не найдено'}), 404

    # Удаление игрока из лобби
    if player_name in lobbies[lobby_code]['players']:
        lobbies[lobby_code]['players'].remove(player_name)

    return jsonify({
        'status': 'success',
        'message': 'Вы покинули лобби',
        'lobby_name': lobbies[lobby_code]['name'],
        'players': lobbies[lobby_code]['players']
    }), 200


@app.route('/click-timestamp', methods=['POST'])
def receive_click_timestamp():
    data = request.json
    timestamp = data.get('timestamp', '')
    email = data.get('email', 'Не указан')  # Получаем email
    lobby_code = data.get('lobby_code')

    print(f"Пользователь {email} нажал кнопку в {timestamp} мс, в лобби: {lobby_code}")

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