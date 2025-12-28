from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
# Ключ для работы сессий
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Список всех созданных каналов (хранится в памяти сервера)
rooms_db = []

HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Voice Discord Clone</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://unpkg.com/peerjs@1.4.7/dist/peerjs.min.js"></script>
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #36393f; color: #dcddde; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #2f3136; padding: 20px; border-radius: 8px; width: 400px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); text-align: center; }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 4px; border: none; background: #40444b; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; border: none; border-radius: 4px; background: #5865f2; color: white; cursor: pointer; font-weight: bold; margin-top: 10px; }
        button:hover { background: #4752c4; }
        .room-list { margin-top: 20px; text-align: left; max-height: 200px; overflow-y: auto; background: #202225; padding: 10px; border-radius: 4px; }
        .room-item { display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #2f3136; }
        .room-item:last-child { border-bottom: none; }
        .hidden { display: none; }
        .status-on { color: #3ba55d; font-weight: bold; margin: 15px 0; }
    </style>
</head>
<body>

    <div id="step-login" class="card">
        <h2>Введите имя</h2>
        <input type="text" id="username" placeholder="Твое имя в сети...">
        <button onclick="login()">Войти в поиск</button>
    </div>

    <div id="step-lobby" class="card hidden">
        <h2>Поиск каналов</h2>
        <div id="display-my-name" style="color: #8e9297; margin-bottom: 10px;"></div>
        
        <div class="room-list" id="room-list-container">
            </div>

        <div style="margin-top: 20px;">
            <input type="text" id="new-room-name" placeholder="Название нового канала...">
            <button onclick="createNewRoom()" style="background: #3ba55d;">Создать канал</button>
        </div>
    </div>

    <div id="step-voice" class="card hidden">
        <h2 id="active-room-title"># Канал</h2>
        <div class="status-on">● Прямой эфир</div>
        <div id="participant-list" style="text-align: left; margin-bottom: 20px;"></div>
        <button onclick="location.reload()" style="background: #ed4245;">Выйти из канала</button>
    </div>

    <script>
        const socket = io();
        let myName, myPeer, myStream;
        let activeCalls = {};

        // 1. Авторизация
        function login() {
            myName = document.getElementById('username').value;
            if(!myName) return alert("Имя введи!");
            document.getElementById('step-login').classList.add('hidden');
            document.getElementById('step-lobby').classList.remove('hidden');
            document.getElementById('display-my-name').innerText = "Ты зашел как: " + myName;
            
            // Запрашиваем список комнат сразу после логина
            socket.emit('request_rooms');
        }

        // 2. Обновление списка каналов (ПОИСК)
        socket.on('update_rooms', (rooms) => {
            const container = document.getElementById('room-list-container');
            if (rooms.length === 0) {
                container.innerHTML = '<div style="text-align:center; color:#72767d;">Каналов пока нет. Создай первый!</div>';
                return;
            }
            container.innerHTML = '';
            rooms.forEach(room => {
                const item = document.createElement('div');
                item.className = 'room-item';
                item.innerHTML = `<span># ${room}</span> <button onclick="joinRoom('${room}')" style="width:auto; padding: 5px 12px; margin:0;">Подключиться</button>`;
                container.appendChild(item);
            });
        });

        // 3. Создание канала
        function createNewRoom() {
            const rName = document.getElementById('new-room-name').value;
            if(!rName) return alert("Название канала?");
            socket.emit('create_room', rName);
            joinRoom(rName); // Сразу входим в него
        }

        // 4. Подключение к голосу
        async function joinRoom(roomName) {
            document.getElementById('step-lobby').classList.add('hidden');
            document.getElementById('step-voice').classList.remove('hidden');
            document.getElementById('active-room-title').innerText = "# " + roomName;

            try {
                myStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                // Генерируем ID для WebRTC
                const peerId = 'peer_' + myName + '_' + Math.random().toString(36).substr(2, 5);
                myPeer = new Peer(peerId);

                myPeer.on('open', (id) => {
                    socket.emit('join_voice', { room: roomName, peerId: id });
                });

                // Принимаем входящие голоса
                myPeer.on('call', (call) => {
                    call.answer(myStream);
                    handleCall(call);
                });

                // Если кто-то уже есть в комнате, сервер скажет нам их ID, и мы им позвоним
                socket.on('connect_to_peer', (otherPeerId) => {
                    const call = myPeer.call(otherPeerId, myStream);
                    handleCall(call);
                });

            } catch(e) {
                alert("Микрофон включи в браузере!");
                location.reload();
            }
        }

        function handleCall(call) {
            call.on('stream', (stream) => {
                if(!activeCalls[call.peer]) {
                    const audio = document.createElement('audio');
                    audio.srcObject = stream;
                    audio.play();
                    activeCalls[call.peer] = call;
                    
                    const p = document.createElement('p');
                    p.innerText = "🎙 " + call.peer.replace('peer_', '').split('_')[0];
                    document.getElementById('participant-list').appendChild(p);
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@socketio.on('request_rooms')
def send_rooms():
    emit('update_rooms', rooms_db)

@socketio.on('create_room')
def on_create(name):
    if name not in rooms_db:
        rooms_db.append(name)
    emit('update_rooms', rooms_db, broadcast=True)

@socketio.on('join_voice')
def on_join(data):
    room = data['room']
    p_id = data['peerId']
    join_room(room)
    # Сообщаем всем остальным в этой комнате, что надо позвонить новичку
    emit('connect_to_peer', p_id, to=room, include_self=False)

if __name__ == '__main__':
    # Запуск на порту 5000
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)