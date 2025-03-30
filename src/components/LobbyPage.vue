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
        <li v-if="owner">
          {{ owner }} 👑
        </li>
        <li v-for="player in sortedPlayers" :key="player.email">
          {{ player.email }} <span class="score">{{ player.score }}</span>
        </li>
      </ul>
    </div>
    <button @click="leaveLobby">Покинуть лобби</button>
    <!-- Кнопка управления аудио отображается только для владельца -->
    <div class="audio-controls" v-if="isOwner || respondent == email">
      <button @click="toggleMicrophone" v_if = "isMuted">
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
      scores: [],
      players: [],
      pollingInterval: null,
      copied: false,
      socket: null,
      localStream: null,
      peers: {},
      isMuted: false, // для владельца по умолчанию микрофон включен, а для не-владельцев мы принудительно замучиваем
      owner: '',
      respondent: ''
    };
  },
  computed: {
    isOwner() {
      return this.email === this.owner;
    },
    processedPlayers() {
      return this.players.map((email, index) => ({
        email,
        score: this.scores[index] || 0
      }));
    },
    sortedPlayers() {
      // Исключаем владельца и сортируем по убыванию
      return this.processedPlayers
        .filter(p => p.email !== this.owner)
        .sort((a, b) => b.score - a.score);
    }
  },
  async created() {
    // Сначала получаем информацию о лобби, чтобы знать, кто владелец
    await this.fetchLobbyInfo();
    // После этого запускаем WebRTC
    this.setupWebRTC();
    this.setupPolling();
  },
  beforeUnmount() {
    this.stopPolling();
    this.cleanupWebRTC();
  },
  watch: {
    // Как только получим владельца, если пользователь не владелец – гарантируем, что микрофон выключен
    owner(newOwner) {
      console.log(newOwner)
      if (!this.isOwner && this.localStream) {
        this.isMuted = true;
        this.localStream.getAudioTracks().forEach(track => {
          track.enabled = false;
        });
      }
    }
  },
  methods: {
    async fetchLobbyInfo() {
      try {
        const response = await fetch('http://localhost:5000/get-lobby-info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lobby_code: this.lobbyCode })
        });
        const data = await response.json();
        if (data.status === 'success') {
          console.log(data);
          this.lobbyName = data.lobby_name;
          this.players = data.players;
          this.scores = data.scores;
          this.owner = data.owner;
          this.respondent = data.respondent;
          // Если сервер возвращает question_number и question_nominal,
          // передаём их в родительский компонент для обновления home-page
          this.$emit('update-lobby-info', {
            owner: this.owner,
            respondent: this.respondent,
            question_number: data.question_number,
            question_nominal: data.question_nominal
          });
          // Дополнительно можно проверять, что игрок есть в лобби и выполнять прочие действия
          const isPlayerInLobby = this.players.includes(this.email);
          if (!isPlayerInLobby) {
            console.log('Игрок не найден в лобби, выполняем выход');
            this.leaveLobby();
          }
        } else {
          this.stopPolling();
          this.$emit('leave-lobby');
        }
      } catch (error) {
        this.leaveLobby();
      }
    },
    
    async leaveLobby() {
      try {
        console.log("Покидаем лобби...");
        this.cleanupWebRTC();
        const response = await fetch('http://localhost:5000/leave-lobby', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lobby_code: this.lobbyCode,
            email: this.email,
            player_name: this.playerName
          })
        });
        const data = await response.json();
        console.log("Ответ от сервера:", data);
        if (data.status !== 'success') {
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
    setupPolling() {
      this.pollingInterval = setInterval(() => {
        this.fetchLobbyInfo();
      }, 1000);
    },
    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval);
        this.pollingInterval = null;
      }
    },
    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.lobbyCode);
        this.copied = true;
        setTimeout(() => { this.copied = false; }, 1000);
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
        // Если пользователь не владелец – сразу мьютим аудио
        if (this.owner && !this.isOwner) {
          this.isMuted = true;
          this.localStream.getAudioTracks().forEach(track => {
            track.enabled = false;
          });
        }
        // Обработчики событий WebRTC
        this.socket.on('user_joined', this.handleNewUser);
        this.socket.on('webrtc_offer', this.handleOffer);
        this.socket.on('webrtc_answer', this.handleAnswer);
        this.socket.on('ice_candidate', this.handleIceCandidate);
        this.socket.on('user_left', this.handleUserDisconnect);
      } catch (error) {
        console.error('Ошибка настройки WebRTC:', error);
      }
    },
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
        ]
      });
      // Добавляем локальные треки перед созданием предложения
      this.localStream.getTracks().forEach(track => {
        peer.addTrack(track, this.localStream);
      });
      // Обработчик ICE-кандидатов
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
        sender_id: this.email,
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
      Object.entries(this.peers).forEach(([userId, peer]) => {
        peer.close();
        delete this.peers[userId];
      });
      if (this.localStream) {
        this.localStream.getTracks().forEach(track => track.stop());
        this.localStream = null;
      }
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
  outline-offset: -2px;
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
