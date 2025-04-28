  <template>
    <div class="home-page">
      <!-- Блок вопроса и таймера (синхронизирован для всех) -->
      <!-- Боковая панель с информацией о пользователе и действиями -->
      <div class="panel-block">
        <div class="user" style="border-radius: 25px 25px 0px 0px; padding: 10px 0px;">
          <div class="profile">
            <img src="../assets/user.webp" alt="" style="height: 45px; margin-right: 10px;">
            <h1>{{ username }}</h1>
          </div>
        </div>
        <div class="user-stats" v-if="email">
          <p><strong>Почта:</strong> {{ email }}</p>
          <p><strong>Место:</strong> {{ userStats.place || '—' }}</p>
          <p><strong>Рейтинг:</strong> {{ userStats.rating || '—' }}</p>
        </div>
        <div class="container">
          <div v-if="!inLobby" class="actions">
            <button @click="showCreateLobbyModal = true">Создать лобби</button>
            <button @click="showJoinLobbyModal = true">Присоединиться к лобби</button>
            <button @click="logout" class="red-but">Выход</button>
          </div>
          
          <LobbyPage
           v-if="inLobby"
           ref="lobby"
           :lobbyCode="lobbyCode"
           :playerName="username"
           :email="email"
           @leave-lobby="leaveLobby"
           @update-lobby-info="updateLobbyInfo"
         />

          <!-- Модальные окна -->
          <div v-if="showCreateLobbyModal" class="modal">
            <div class="modal-content">
              <h2>Создание лобби</h2>
              <input v-model="newLobbyName" placeholder="Название лобби" />
              <button @click="confirmCreateLobby">Создать</button>
              <button @click="closeModal" class="red-but">Отмена</button>
            </div>
          </div>
          <div v-if="showJoinLobbyModal" class="modal">
            <div class="modal-content">
              <h2>Присоединение к лобби</h2>
              <input v-model="lobbyCodeInput" placeholder="Код лобби" />
              <button @click="confirmJoinLobby">Присоединиться</button>
              <button @click="closeModal" class="red-but">Отмена</button>
            </div>
          </div>
        </div>
      </div>

      <div class="question-container" v-if="inLobby">
        <h2 class="question-label">{{ questionLabel }}</h2>
        <div v-if="timerVisible" class="timer-display">
          {{ timerValue }}
        </div>
        <!-- Кнопка для владельца, чтобы запустить отсчёт (видна, если никто ещё не отвечает и таймер не активен) -->
        <div style="display: flex; padding: 30px 30px; justify-content: center; align-items: center;">
          <div v-if="isOwner && !respondent && !timerVisible" class="owner-controls" style="margin-right: 30px;">
            <button @click="startTimer" class="finish-btn">Закончить вопрос</button>
          </div>
          <!-- Новая кнопка для владельца: Завершить игру, видна только когда кто-то отвечает -->
          <div v-if="isOwner" class="owner-controls">
            <button @click="endGame" class="end-game-btn">Завершить игру</button>
          </div>
        </div>
      </div>


      <div class="central-blocks" v-if="!inLobby">
        <!-- Блок списка игроков -->
        <div class="players-panel" style="overflow: clip; margin-bottom: 20px;" >
          <h3>Таблица рейтинга</h3>
          <ul>
            <li v-for="player in players" :key="player.place">
              <span style="background-color: #2d2959; color: white; padding: 10px 15px; border-radius: 15px; margin-right: 20px;">{{ player.place }}</span>{{ player.name }}<span style="margin-left: 20px;">{{ player.rating }}</span>
            </li>
          </ul>
        </div>
        <!-- Пустой блок лобби -->
        <div class="lobby-panel">
          <h3>Список лобби ( to be continued )</h3>
          <!-- Пока только фон -->
        </div>
      </div>

      <!-- Красная кнопка для участников, останавливающая таймер -->
      <button v-if="inLobby && shouldShowBigBut" @click="sendClickTimestamp" class="big-but"></button>
      <!-- Информация об отвечающем -->
      <div class="respondent" v-if="respondent !== '' && inLobby">
        <h1 v-if="respondent !== '' && inLobby" class="respondent-label">
          Отвечает {{ respondent }}
        </h1>
        <!-- Кнопки владельца для проверки ответа -->
        <div v-if="respondent !== '' && isOwner && inLobby" class="response-buttons">
          <button @click="handleResponse('correct')" class="correct-but">Верно</button>
          <button @click="handleResponse('incorrect')" class="incorrect-but">Не верно</button>
        </div>
      </div>
    </div>
  </template>

  <script>
  import io from "socket.io-client";
  import LobbyPage from './LobbyPage.vue';

  export default {
    components: { LobbyPage },
    props: ['username', 'email'],
    data() {
      return {
        inLobby: false,
        lobbyCode: '',
        showCreateLobbyModal: false,
        showJoinLobbyModal: false,
        newLobbyName: '',
        lobbyCodeInput: '',
        owner: '',
        respondent: '',
        shouldShowBigBut: false,
        // Данные для синхронизации таймера и вопроса
        timerVisible: false,
        timerValue: 7,
        timerInterval: null,
        questionNumber: 1,
        questionNominal: 10,
        socket: null,
        players: []
      };
    },
    computed: {
      questionLabel() {
        return `Вопрос ${this.questionNumber} (${this.questionNominal})`;
      },
      isOwner() {
        return this.email === this.owner;
      },
      userStats(){
        const me = this.players.find(p => p.name === this.username);
        return me || {};
      }
    },
    created() {
      const userData = localStorage.getItem('lobby');
      if (userData) {
        const lobby = JSON.parse(userData);
        this.lobbyCodeInput = lobby.code;
        this.confirmJoinLobby();
      }
    },
    mounted() {
      // Инициализируем Socket.IO и подписываемся на событие обновления вопроса
      this.socket = io('http://localhost:5000');
      this.socket.on('next_question', data => {
        if (data.lobby_code === this.lobbyCode) {
          this.questionNumber = data.question_number;
          this.questionNominal = data.question_nominal;
          this.respondent = ''; // сброс информации об отвечающем
          this.stopTimer();
        }
      });
      // Если сервер инициирует остановку таймера, останавливаем локальный отсчёт
      this.socket.on('stop_timer', () => {
        this.stopTimer();
      });
      this.fetchPlayers();
    },
    methods: {
      async handleResponse(status) {
        // Останавливаем таймер у всех участников
        this.socket.emit('stop_timer', { lobby_code: this.lobbyCode });
        this.stopTimer();
        try {
          const response = await fetch('http://localhost:5000/responsestatus', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              status: status,
              lobby_code: this.lobbyCode,
              nominal: this.questionNominal
            })
          });
          const data = await response.json();
          console.log("Ответ от сервера:", data);
          if (status === 'correct') {
            this.nextQuestion();
          }
          else{
            this.startTimer();
          }
        } catch (error) {
          console.error("Ошибка при отправке статуса ответа:", error);
        }
      },
      async fetchPlayers() {
            try {
              const response = await fetch('http://localhost:5000/players');
              const data = await response.json();
              if (data.status === 'success') {
                this.players = data.players;
              }
            } catch (error) {
              console.error('Ошибка при получении списка игроков:', error);
            }
          },
      updateLobbyInfo({ owner, respondent, question_number, question_nominal }) {
        this.owner = owner;
        this.respondent = respondent;
        if (respondent) {this.stopTimer();}
        if (typeof question_number !== 'undefined') {
          this.questionNumber = question_number;
        }
        if (typeof question_nominal !== 'undefined') {
          this.questionNominal = question_nominal;
        }
        this.shouldShowBigBut = this.respondent === "" && this.email !== this.owner;
      },
      async sendClickTimestamp() {
        // Останавливаем таймер у всех участников
        this.socket.emit('stop_timer', { lobby_code: this.lobbyCode });
        this.stopTimer();
        const timestamp = Date.now();
        try {
          const response = await fetch('http://localhost:5000/click-timestamp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              timestamp,
              email: this.email,
              lobby_code: this.lobbyCode
            })
          });
          const data = await response.json();
          console.log("Ответ от сервера:", data);
        } catch (error) {
          console.error("Ошибка при отправке времени:", error);
        }
      },
      async confirmCreateLobby() {
        if (!this.newLobbyName.trim()) {
          alert('Введите название лобби');
          return;
        }
        try {
          const response = await fetch('http://localhost:5000/create-lobby', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              lobby_name: this.newLobbyName,
              email: this.email,
              player_name: this.username
            })
          });
          const data = await response.json();

          if (data.status === 'success') {
            // Получили код, сохраняем в поле и очищаем форму
            this.lobbyCodeInput = String(data.lobby_code);
            this.newLobbyName = ''; 
            this.showCreateLobbyModal = false;

            // Сразу вызываем присоединение по тому же коду
            await this.confirmJoinLobby();

          } else {
            alert(data.message);
          }
        } catch (error) {
          console.error('Ошибка при создании лобби:', error);
        }
      },
      async confirmJoinLobby() {
        this.lobbyCodeInput = String(this.lobbyCodeInput);
        if (!this.lobbyCodeInput.trim()) {
          alert('Введите код лобби');
          return;
        }
        try {
          const response = await fetch('http://localhost:5000/join-lobby', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lobby_code: this.lobbyCodeInput, email: this.email, player_name: this.username })
          });
          const data = await response.json();
          if (data.status === 'success') {
            document.getElementsByClassName('profile')[0].style.marginLeft = "0px";
            localStorage.setItem('lobby', JSON.stringify({ code: data.lobby_code }));
            this.lobbyCode = this.lobbyCodeInput;
            this.questionNumber = data.question_number || 1;
            this.questionNominal = data.question_nominal || 10;
            this.inLobby = true;
            this.$nextTick(() => {this.$refs.lobby.initMediaAndSocket();});
          } else {
            localStorage.removeItem('lobby');
            alert('Лобби не найдено');
          }
        } catch (error) {
          console.error('Ошибка при подключении к лобби:', error);
        }
        this.closeModal();
      },
      closeModal() {
        this.showCreateLobbyModal = false;
        this.showJoinLobbyModal = false;
        this.newLobbyName = '';
        this.lobbyCodeInput = '';
      },
      leaveLobby() {
        document.getElementsByClassName('profile')[0].style.marginLeft = "25%";
        this.inLobby = false;
        this.lobbyCode = '';
        localStorage.removeItem('lobby');
      },
      logout() {
        this.$emit('logout');
        localStorage.removeItem('lobby');
      },
      startTimer() {
        this.timerVisible = true;
        this.timerValue = 7;
        this.timerInterval = setInterval(() => {
          this.timerValue--;
          if (this.timerValue <= 0) {
            this.stopTimer();
            this.nextQuestion();
          }
        }, 1000);
      },
      stopTimer() {
        this.timerVisible = false;
        clearInterval(this.timerInterval);
      },
      nextQuestion() {
        // Обновляем локальные значения и отправляем запрос на сервер для синхронизации
        this.questionNumber++;
        this.questionNominal = 10 * (((this.questionNumber - 1) % 5) + 1);
        fetch('http://localhost:5000/next-question', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lobby_code: this.lobbyCode })
        }).then(response => response.json())
          .then(data => {
            this.questionNumber = data.question_number;
            this.questionNominal = data.question_nominal;
          }).catch(error => {
            console.error('Ошибка при обновлении вопроса:', error);
          });
      },
      async endGame() {
        // Метод для владельца, который завершает игру (удаляет лобби)
        try {
          const response = await fetch('http://localhost:5000/delete-lobby', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lobby_code: this.lobbyCode })
          });
          const data = await response.json();
          if (data.status === 'success') {
            alert('Игра завершена, лобби удалено');
            // Удаляем данные лобби и выходим из лобби
            this.inLobby = false;
            localStorage.removeItem('lobby');
            this.$emit('leave-lobby');
          } else {
            alert('Ошибка при завершении игры');
          }
        } catch (error) {
          console.error('Ошибка при завершении игры:', error);
        }
      }
    }
  };
  </script>



<style>

.user-stats{
  background-color: rgba(0,0,0,0.1);
  width: 100%;
  text-align: center;
  margin-left: auto;
  margin-right: auto;
  font-size: 18px;

}

.central-blocks {
  width: 50%;
  display: flex;
  justify-content: space-around;
  flex-direction: column;
  margin: 20px;
}
.players-panel, .lobby-panel {
  width: auto;
  height: 300px;
  background-color: #164a9e;
  border-radius: 10px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.players-panel h3, .lobby-panel h3 {
  color: white;
  margin-top: 0;
}

.players-panel ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(48%, 1fr));
  /* auto-fill подберёт по ширине, minmax — минимальная ширина колонки */
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.players-panel li {
  background-color: white;
  border-radius: 15px;
  padding: 15px;
  font-weight: bold;
  font-family: 'Arial';
  text-align: left;

  margin: 5px 0;
  font-size: 16px;
}
.lobby-panel {
  /* Пока только фон -- можно менять позже */
  background-size: cover;
  background-position: center;
}

.home-page {
  display: flex;
  width: 100%;
}

  body {
    padding: 0;
    margin: 0;
    font-family: Arial, sans-serif;
  }

  /* Блок вопроса и таймера */
  .question-container {
    background: linear-gradient(135deg, #446ead, #3b5998);
    color: #fff;
    text-align: center;
    padding: 40px;
    border-radius: 10px;
    margin: 15px;
    width: 50%;
    height: 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .question-label {
    font-size: 24px;
  }

  .timer-display {
    font-size: 32px;
    font-weight: bold;
    margin-bottom: 10px;
    margin-left: 30px;
  }

  .owner-controls {
    margin-top: 10px;
  }

  /* Стили для остальных блоков остаются без изменений */
  .panel-block {
    background-color: #fff;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 0px;
    width: 20%;
    border-radius: 25px;
    margin: 15px;
    padding-bottom: 20px;
    padding-top: 0;
  }

  .container {
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .user {
    background-color: #164a9e;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    width: 100%;
    border-radius: 25px 0 25px 0px;
  }

  .profile {
    width: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-left: 25%;
  }

  .actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 20px;
  }

  .big-but {
    position: absolute;
    left: 45%;
    width: 10%;
    height: 100px;
    background-color: red;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    box-shadow: 0px 15px 0px darkred;
    transition: all 0.2s ease-in-out;
    top: 40%;
  }

  .big-but:hover {
    top: 41%;
    box-shadow: 0px 10px 0px darkred;
  }

  .respondent{
    border-radius: 15px;
    position: fixed;
    padding: 50px 0;
    top: 20%;
    left: 40%;
    width: 20%;
    display: flex;
    justify-content: center;
    flex-direction: column;
    align-items: center;
    height: auto;
    background-color: rgba(0,0,0,0.1);
  }

  .respondent-label {
    margin-bottom: 20px;
    color: #fff;
    margin: 0;
  }

  /* Остальные стили для модальных окон, кнопок и прочего можно оставить без изменений */
  </style>

  <style scoped>
  /* Стили, уже присутствующие в компоненте */
  button {
    background-color: white;
    border-radius: 5px;
    border: 2px solid gray;
    transition-duration: 0.3s;
  }

  button:hover {
    background-color: #446ead;
    border-radius: 0px;
    border: 2px solid rgba(256,256,256,0);
    color: white;
  }

  .big-but {
    position: absolute;
    left: 45%;
    width: 10%;
    height: 100px;
    background-color: red;
    border-radius: 50%;
    border: none;
    outline: none;
    cursor: pointer;
    box-shadow: 0px 15px 0px darkred;
    transition: all 0.2s ease-in-out;
    top: 40%;
  }

  .big-but:hover {
    top: 41%;
    background-color: red;
    border-radius: 50%;
    border: none;
    outline: none;
    cursor: pointer;
    box-shadow: 0px 10px 0px darkred;
  }

  .big-but:active {
    top: 43%;
    box-shadow: 0px 0px 0px darkred;
  }

  .red-but:hover {
    background-color: #d95252;
  }

  .actions {
    display: flex;
    flex-direction: column;
  }

  .panel-block {
    background-color: white;
    display: flex;
    flex-direction: column;
    align-items: start;
    padding: 0;
    width: 20%;
    border-radius: 25px;
    margin: 15px;
    padding-bottom: 20px;
    padding-top: 0;
  }

  .container {
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .user {
    background-color: #164a9e;
    padding: 0;
    margin: 0;
    font-family: Arial;
    color: white;
    display: flex;
    height: 50px;
    justify-content: start;
    align-items: center;
    transition-duration: 0.3s;
    width: 100%;
    border-radius: 25px 0 0 25px;
  }

  .user img {
    border-radius: 50%;
    outline: solid 3px white;
    outline-offset: -3px;
  }

  .profile {
    width: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-left: 25%;
    transition-duration: 0.3s;
  }

  .actions {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-top: 20px;
  }

  button {
    font-size: 16px;
    cursor: pointer;
    padding: 10px 20px;
  }

  .modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .modal-content {
    background-color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
  }

  .modal-content input {
    margin: 10px 0;
    padding: 10px;
    width: 80%;
    font-size: 16px;
  }

  .modal-content button {
    margin: 5px;
  }

  .response-buttons {
    margin-top: 40px;
    display: flex;
    gap: 10px;
  }

  .correct-but,
  .incorrect-but {
    background-color: white;
    border-radius: 5px;
    border: 0;
    transition-duration: 0.3s;
    font-size: 16px;
    cursor: pointer;
    padding: 10px 20px;
  }

  .correct-but:hover {
    background-color: #49824b;
    color: white;
    padding: 10px 20px;
    border: 0;
    border-radius: 5px;
  }

  .incorrect-but:hover {
    background-color: #d95252;
    color: white;
    padding: 10px 20px;
    border: 0;
    border-radius: 5px;
  }

  .finish-btn, .end-game-btn {
    background-color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s;
  }

  .finish-btn:hover, .end-game-btn:hover {
    background-color: #d95252;
  }

  </style>