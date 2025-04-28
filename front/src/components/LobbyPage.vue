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
      scores: [],
      players: [],
      pollingInterval: null,
      copied: false,
      socket: null,
      localStream: null,
      peers: {},
      isMuted: false,
      owner: '',
      respondent: '',
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
      return this.processedPlayers
        .filter(p => p.email !== this.owner)
        .sort((a, b) => b.score - a.score);
    }
  },
  async created() {
    await this.fetchLobbyInfo();
    this.setupPolling();
  },
  beforeUnmount() {
    this.stopPolling();
    this.cleanupWebRTC();
  },
  watch: {
    owner(newOwner) {
      console.log(newOwner)
      if (!this.isOwner && this.localStream) {
        this.muteLocal();
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
          this.lobbyName = data.lobby_name;
          this.players = data.players;
          this.scores = data.scores;
          this.owner = data.owner;
          this.respondent = data.respondent;
          this.$emit('update-lobby-info', {
            owner: this.owner,
            respondent: this.respondent,
            question_number: data.question_number,
            question_nominal: data.question_nominal
          });
          if (!this.players.includes(this.email)) this.leaveLobby();
        } else {
          this.stopPolling();
          this.$emit('leave-lobby');
        }
      } catch {
        this.leaveLobby();
      }
    },
    async handleIceCandidate({ sender_id, candidate }) {
      const peer = this.peers[sender_id];
      if (peer && candidate) {
        try {
          await peer.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
          console.error('Ошибка при добавлении ICE-кандидата:', err);
        }
      }
    },

    // Обработка отключения пользователя
    handleUserDisconnect({ user_id }) {
      const peer = this.peers[user_id];
      if (peer) {
        peer.close();
        delete this.peers[user_id];
      }
    },
    async initMediaAndSocket() {
      // 1. Получаем локальный аудио-поток
      try {
        this.localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        console.error('Failed to getUserMedia:', err);
        return;
      }
      // 2. Если не владелец, сразу мьютим
      this.muteLocal();
      // 3. Настраиваем socket и присоединяемся после получения потока
      this.socket = io('http://localhost:5000', {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000
      });
      this.socket.on('connect', () => {
        this.socket.emit('join_lobby', {
          lobby_code: this.lobbyCode,
          user_id: this.email
        });
      });
      // 4. Обработка событий
      this.socket.on('user_joined', this.handleNewUser);
      this.socket.on('webrtc_offer', this.handleOffer);
      this.socket.on('webrtc_answer', this.handleAnswer);
      this.socket.on('ice_candidate', this.handleIceCandidate);
      this.socket.on('user_left', this.handleUserDisconnect);

    },
    muteLocal() {
      this.isMuted = true;
      this.localStream.getAudioTracks().forEach(t => t.enabled = false);
    },
    async leaveLobby() {
      try {
        this.cleanupWebRTC();
        await fetch('http://localhost:5000/leave-lobby', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lobby_code: this.lobbyCode, email: this.email, player_name: this.playerName })
        });
        this.stopPolling();
        this.$emit('leave-lobby');
      } catch {
        this.stopPolling();
        this.$emit('leave-lobby');
      }
    },
    setupPolling() {
      this.pollingInterval = setInterval(this.fetchLobbyInfo, 1000);
    },
    stopPolling() {
      if (this.pollingInterval) clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    },
    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.lobbyCode);
        this.copied = true;
        setTimeout(() => (this.copied = false), 1000);
      } catch (error) {
        console.error('Ошибка при копировании:', error);
      }
    },
    createPeerConnection(targetId) {
      const peer = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
      this.localStream.getTracks().forEach(track => peer.addTrack(track, this.localStream));
      peer.onicecandidate = ({ candidate }) => {
        if (candidate) this.socket.emit('ice_candidate', { sender_id: this.email, lobby_code: this.lobbyCode, target_id: targetId, candidate });
      };
      peer.ontrack = ({ streams: [remoteStream] }) => {
        const audio = document.createElement('audio');
        audio.srcObject = remoteStream;
        audio.autoplay = true;
        document.body.appendChild(audio);
      };
      return peer;
    },
    async handleNewUser({ user_id }) {
      if (user_id === this.email) return;
      // создаём и сразу шлём offer
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
      if (sender_id === this.email) return;

      let peer = this.peers[sender_id];
      if (!peer) {
        peer = this.createPeerConnection(sender_id);
        this.peers[sender_id] = peer;
      }

      // ИЗМЕНЕНО: только если мы в stable, иначе дублируем
      if (peer.signalingState !== 'stable') {
        console.warn(`Ignoring duplicate offer from ${sender_id}, state=${peer.signalingState}`);
        return;
      }

      try {
        await peer.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await peer.createAnswer();
        await peer.setLocalDescription(answer);
        this.socket.emit('webrtc_answer', {
          sender_id: this.email,
          lobby_code: this.lobbyCode,
          target_id: sender_id,
          answer: peer.localDescription
        });
      } catch (err) {
        console.error('Ошибка в handleOffer:', err);
      }
    },
    async handleAnswer({ answer, sender_id }) {
      const peer = this.peers[sender_id];
      if (!peer) return;

      // ИЗМЕНЕНО: только если мы реально отправляли offer (have-local-offer)
      if (peer.signalingState !== 'have-local-offer') {
        console.warn(`Ignoring unexpected answer from ${sender_id}, state=${peer.signalingState}`);
        return;
      }

      try {
        await peer.setRemoteDescription(new RTCSessionDescription(answer));
      } catch (err) {
        console.error('Ошибка в handleAnswer:', err);
      }
    },
    toggleMicrophone() {
      this.isMuted = !this.isMuted;
      this.localStream.getAudioTracks().forEach(t => (t.enabled = !this.isMuted));
    },
    cleanupWebRTC() {
      Object.values(this.peers).forEach(p => p.close());
      this.peers = {};
      if (this.localStream) this.localStream.getTracks().forEach(t => t.stop());
      if (this.socket) {
        this.socket.emit('leave_lobby', { lobby_code: this.lobbyCode, user_id: this.email });
        this.socket.disconnect();
      }
      this.localStream = null;
      this.socket = null;
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
