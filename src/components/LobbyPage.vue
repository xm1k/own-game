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
  </div>
</template>

<script>
export default {
  props: ['lobbyCode', 'playerName'],
  data() {
    return {
      lobbyName: '',
      players: [],
      pollingInterval: null,
      copied: false // Состояние для уведомления о копировании
    };
  },
  created() {
    this.fetchLobbyInfo();
    this.setupPolling();
  },
  beforeUnmount() {
    this.stopPolling();
  },
  methods: {
    // Получение информации о лобби
    async fetchLobbyInfo() {
      try {
        console.log("Отправка запроса на сервер get-lobby-info с кодом:", this.lobbyCode);
        const response = await fetch('http://localhost:5000/get-lobby-info', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            lobby_code: this.lobbyCode
          })
        });
        const data = await response.json();
        console.log("Ответ от сервера:", data);
        if (data.status === 'success') {
          this.lobbyName = data.lobby_name;
          this.players = data.players;
        } else {
          alert(data.message);
          this.leaveLobby(true); // Если лобби не найдено, выйти
        }
      } catch (error) {
        console.error('Ошибка при получении информации о лобби:', error);
      }
    },
    // Покинуть лобби
    async leaveLobby() {
      try {
        console.log("Покидаем лобби...");

        const response = await fetch('http://localhost:5000/leave-lobby', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            lobby_code: this.lobbyCode,
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
  color: #49824b;
  padding: 2px 5px;
  transition-duration: 0.3s;
  font-size: 25px;
  font-weight: bold;
}

.code:hover {
  background-color: #49824b;
  color: white;
}

.copied-message {
  position: absolute;
  font-size: 15px;
  color: #49824b;
  margin-left: 10px;
  text-align: center;
  background-color: rgba(0,0,0,0.1);
  padding: 8px;
}

.players {
  width: 100%;
  text-align: left;
  font-size: 20px;
  margin-top: 15px;
}

</style>
