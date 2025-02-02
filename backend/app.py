from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text
import bcrypt

def hashp(password) :
    h=0
    for l in password:
        h=h * 257+int(l)
    return h



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

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
    print('Received data:', data)

    email = data.get('email')
    password = data.get('password')

    print('Email:', email, 'Password:', password)
    q="select authorization('{}',{})".format(email,hashp(password)%1000000007)
    with engine.connect() as connect:
        res=connect.execute(text(q))
        f=res.scalar()
        connect.commit()
    print('pizdec nahui bluyat',f,hashp(password) % 1000000007)
    if f:
        return jsonify({'status': 'success', 'message': 'Вход успешен', 'name': "name"}), 200
    return jsonify({'status': 'error', 'message': 'Неверный email или пароль'}), 400


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    print("goida")
    print(f"Регистрация: {email}, {password}, {name}")
    q=f"select add_user('{name}','{email}',{hashp(password)%1000000007})"
    with engine.connect() as connect:
        connect.execute(text(q))
        connect.commit()
    if email and password and name:
        return jsonify({'status': 'success', 'message': 'Регистрация успешна', 'name': name}), 201
    return jsonify({'status': 'error', 'message': 'Ошибка регистрации'}), 400


if __name__ == '__main__':
    app.run(debug=True)
