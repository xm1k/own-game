  <template>
    <div class="lobby-page">
      <div style="text-align: center; margin-top: 15px;">
        <span style="font-size: 28px; font-weight: bold">{{ lobbyName }} </span>
        <span class="code" @click="copyToClipboard">{{ lobbyCode }}</span>
        <span v-if="copied" class="copied-message">Скопировано!</span>
      </div>
      <div class="players">
        Игроки:
        <ul style="margin: 10px 0px 0px 0px;">
          <li v-for="player in players" :key="player">{{ player }}</li>
        </ul>
      </div>
      <button @click="leaveLobby">Покинуть лобби</button>
      <div class="audio-controls">
        <button @click="toggleMicrophone">
          {{ isMuted ? 'Включить микрофон' : 'Выключить микрофон' }}
        </button>
      </div>
    </div>
  </template>

  <script>
  import { io } from 'socket.io-client';
  export default {
    props: ['lobbyCode', 'playerName', 'email'],
    data() {
      return {
        lobbyName: '',
        players: [],
        pollingInterval: null,
        copied: false,
        socket: null,
        localStream: null,
        peers: {},
        isMuted: false
      };
    },
    created() {
      this.setupWebRTC();
      this.fetchLobbyInfo();
      this.setupPolling();
    },
    beforeUnmount() {
      this.stopPolling();
      this.cleanupWebRTC();
    },
    methods: {
      // Получение информации о лобби
      async fetchLobbyInfo() {
        try {
            const response = await fetch('http://localhost:5000/get-lobby-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lobby_code: this.lobbyCode })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.lobbyName = data.lobby_name;
                this.players = data.players;
                
                // Проверяем наличие текущего игрока в списке
                const isPlayerInLobby = this.players.includes(this.email); // Или this.playerName
                if (!isPlayerInLobby) {
                    console.log('Игрок не найден в лобби, выполняем выход');
                    this.leaveLobby();
                }
                
            } else {
                this.stopPolling();
                this.$emit('leave-lobby');
            }
        }
        catch (error) {
            this.leaveLobby();
        }
      },
      // Покинуть лобби
      async leaveLobby() {
        try {
          console.log("Покидаем лобби...");
          this.cleanupWebRTC();

          const response = await fetch('http://localhost:5000/leave-lobby', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              lobby_code: this.lobbyCode,
              email: this.email,
              player_name: this.playerName
            })
          });

          const data = await response.json();
          console.log("Ответ от сервера:", data);

          if (data.status !== 'success') {
            alert(data.message);
            return;
          }

          this.stopPolling();
          this.$emit('leave-lobby');
        } catch (error) {
          this.stopPolling();
          localStorage.removeItem('lobby');
          this.$emit('leave-lobby');
          console.error("Ошибка при выходе из лобби:", error);
        }
      },
      // Запуск polling для обновления информации о лобби
      setupPolling() {
        this.pollingInterval = setInterval(() => {
          this.fetchLobbyInfo();
        }, 3000); // Обновление каждые 5 секунд
      },
      // Остановка polling
      stopPolling() {
        if (this.pollingInterval) {
          clearInterval(this.pollingInterval);
          this.pollingInterval = null;
        }
      },
      // Копирование кода лобби
      async copyToClipboard() {
        try {
          await navigator.clipboard.writeText(this.lobbyCode);
          this.copied = true;
          setTimeout(() => {
            this.copied = false;
          }, 1000); // Убираем надпись через 2 секунды
        } catch (error) {
          console.error('Ошибка при копировании:', error);
        }
      },
      async setupWebRTC() {
        try {
          // Настройка Socket.IO
          this.socket = io('http://localhost:5000');
          this.socket.emit('join_lobby', { 
            lobby_code: this.lobbyCode,
            user_id: this.email
          });

          // Получение аудио потока
          this.localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          
          // Обработчики событий WebRTC
          this.socket.on('user_joined', this.handleNewUser);
          this.socket.on('webrtc_offer', this.handleOffer);
          this.socket.on('webrtc_answer', this.handleAnswer);
          this.socket.on('ice_candidate', this.handleIceCandidate);
          this.socket.on('user_left', this.handleUserDisconnect);
        } catch (error) {
          console.error('Ошибка настройки WebRTC:', error);
        }
      }
      ,

      handleUserDisconnect({ user_id }) {
          if (this.peers[user_id]) {
              this.peers[user_id].close();
              delete this.peers[user_id];
              console.log(`Пользователь ${user_id} отключен`);
          }
      },

      createPeerConnection(targetId) {
          const peer = new RTCPeerConnection({
              iceServers: [
                  { urls: 'stun:stun.l.google.com:19302' },
                  // Добавьте реальные TURN-сервера при необходимости
              ]
          });

          // Добавляем локальные треки перед созданием предложения
          this.localStream.getTracks().forEach(track => {
              peer.addTrack(track, this.localStream);
          });

          // Обработчики ICE-кандидатов
          peer.onicecandidate = (event) => {
              if (event.candidate) {
                  this.socket.emit('ice_candidate', {
                      sender_id: this.email,
                      lobby_code: this.lobbyCode,
                      target_id: targetId,
                      candidate: event.candidate
                  });
              }
          };

          // Обработка удаленного потока
          peer.ontrack = (event) => {
              const remoteStream = event.streams[0];
              // Добавьте логику отображения удаленного аудио
              const audioElement = document.createElement('audio');
              audioElement.srcObject = remoteStream;
              audioElement.autoplay = true;
              document.body.appendChild(audioElement);
          };

          return peer;
      },

      async handleNewUser({ user_id }) {
        if (user_id === this.email) return;
        
        const peer = this.createPeerConnection(user_id);
        this.peers[user_id] = peer;

        const offer = await peer.createOffer();
        await peer.setLocalDescription(offer);
        
        this.socket.emit('webrtc_offer', {
          sender_id: this.email, // Теперь передаём sender_id
          lobby_code: this.lobbyCode,
          target_id: user_id,
          offer: peer.localDescription
        });
      },

      async handleOffer({ offer, sender_id }) {
        console.log(`Получено WebRTC-предложение от ${sender_id}`);
        
        const peer = this.createPeerConnection(sender_id);
        this.peers[sender_id] = peer;

        await peer.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await peer.createAnswer();
        await peer.setLocalDescription(answer);
        
        console.log(`Отправка WebRTC-ответа ${sender_id}`);
        this.socket.emit('webrtc_answer', {
          sender_id: this.email,
          lobby_code: this.lobbyCode,
          target_id: sender_id,
          answer: peer.localDescription
        });
      },

      async handleAnswer({ answer, sender_id }) {
        console.log(`Получен WebRTC-ответ от ${sender_id}`);
        const peer = this.peers[sender_id];
        if (!peer) {
          console.error('Peer connection не найден');
          return;
        }
        
        // Проверяем состояние peer connection
        if (peer.signalingState !== 'have-local-offer') {
          console.warn('Неправильное состояние peer connection:', peer.signalingState);
          return;
        }

        try {
          await peer.setRemoteDescription(new RTCSessionDescription(answer));
        } catch (error) {
          console.error('Ошибка установки удаленного описания:', error);
        }
      },

      async handleIceCandidate({ candidate, sender_id }) {
        const peer = this.peers[sender_id];
        if (!peer || peer.connectionState === 'closed') {
          console.warn('Peer connection закрыт или не существует');
          return;
        }

        try {
          if (candidate) {
            await peer.addIceCandidate(new RTCIceCandidate(candidate));
          }
        } catch (error) {
          console.error(`Ошибка при добавлении ICE-кандидата:`, error);
        }
      },

      toggleMicrophone() {
        this.isMuted = !this.isMuted;
        this.localStream.getAudioTracks().forEach(track => {
          track.enabled = !this.isMuted;
        });
      },

      cleanupWebRTC() {
        // Закрываем все peer соединения
        Object.entries(this.peers).forEach(([userId, peer]) => {
          peer.close();
          delete this.peers[userId];
        });
        
        // Останавливаем локальный поток
        if (this.localStream) {
          this.localStream.getTracks().forEach(track => track.stop());
          this.localStream = null;
        }
        
        // Отключаем сокет
        if (this.socket) {
          this.socket.emit('leave_lobby', {
            lobby_code: this.lobbyCode,
            user_id: this.email
          });
          this.socket.disconnect();
          this.socket = null;
        }
      }
    }
  };
  </script>

  <style scoped>

  button {
    padding: 10px 20px;
    font-size: 16px;
    margin-top: 20px;
    cursor: pointer;
    background-color: white;
    border-radius: 5px;
    border: 2px solid gray;
    transition-duration: 0.3s;
  }

  button:hover {
    background-color: #d95252;
    border-radius: 0px;
    border: 2px solid rgba(256,256,256,0);
    color: white;
  }

  .lobby-page {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  ul {
    list-style-type: none;
    padding: 0;
  }

  .code {
    cursor: pointer;
    padding: 2px 5px;
    transition-duration: 0.3s;
    font-size: 25px;
    font-weight: bold;
    color: white;
    background-color: #49824b;
    outline: 2px dashed #49824b;
    outline-offset:-2px;

  }

  .code:hover {
    background-color: white;
    color: #49824b;
  }

  .copied-message {
    position: absolute;
    font-size: 15px;
    color: #49824b;
    margin-left: 10px;
    text-align: center;
    background-color: rgba(235,235,235,1);
    padding: 8px;
  }

  .players {
    width: 100%;
    text-align: left;
    font-size: 20px;
    margin-top: 15px;
  }

  </style>