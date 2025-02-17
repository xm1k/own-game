<template>
  <div class="home-page">
    <div class="panel-block">
      <div class="user">
        <div class="profile">
          <img src="../assets/user.webp" alt="" style="height: 45px; margin-right: 10px;">
          <h1>{{ username }}</h1>
        </div>
      </div>
      <hr>
      <div class="container">
        <div v-if="!inLobby" class="actions">
          <button @click="showCreateLobbyModal = true">Создать лобби</button>
          <button @click="showJoinLobbyModal = true">Присоединиться к лобби</button>
          <button @click="logout" class="red-but">Выход</button>
        </div>

        <LobbyPage v-if="inLobby" :lobbyCode="lobbyCode" :playerName="username" :email="email" @leave-lobby="leaveLobby" />

        <!-- Модальное окно для создания лобби -->
        <div v-if="showCreateLobbyModal" class="modal">
          <div class="modal-content">
            <h2>Создание лобби</h2>
            <input v-model="newLobbyName" placeholder="Название лобби" />
            <button @click="confirmCreateLobby">Создать</button>
            <button @click="closeModal" class="red-but">Отмена</button>
          </div>
        </div>

        <!-- Модальное окно для присоединения к лобби -->
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
    <button v-if="inLobby" @click="sendClickTimestamp" class="big-but"></button>
  </div>
</template>

<script>
import LobbyPage from './LobbyPage.vue';

export default {
  components: { LobbyPage },
  props: ['username', 'email'],  // Принимаем email тоже
  data() {
    return {
      inLobby: false,
      lobbyCode: '',
      showCreateLobbyModal: false,
      showJoinLobbyModal: false,
      newLobbyName: '',
      lobbyCodeInput: ''
    };
  },
  created() {
    const userData = localStorage.getItem('lobby');
    if (userData) {
        const lobby = JSON.parse(userData);
        this.lobbyCodeInput = lobby.code
        this.confirmJoinLobby();
    }
  },
  methods: {
    async sendClickTimestamp() {
      const timestamp = Date.now(); // Точное время в миллисекундах
      try {
        const response = await fetch('http://localhost:5000/click-timestamp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timestamp,
            email: this.email  // Отправляем email
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
          body: JSON.stringify({ lobby_name: this.newLobbyName, email: this.email, player_name: this.username })
        });
        const data = await response.json();
        if (data.status === 'success') {
          document.getElementsByClassName('profile')[0].style.marginLeft = "0px";
          localStorage.setItem('lobby', JSON.stringify({
              code: data.lobby_code
            }));
          this.lobbyCode = data.lobby_code;
          this.inLobby = true;
        } else {
          alert(data.message);
        }
      } catch (error) {
        console.error('Ошибка при создании лобби:', error);
      }
      this.closeModal();
    },
    async confirmJoinLobby() {
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
          localStorage.setItem('lobby', JSON.stringify({
              code: data.lobby_code
            }));
          this.lobbyCode = this.lobbyCodeInput;
          this.inLobby = true;
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
    }
  }
};
</script>

<style>
  
body{
  padding: 0px;
  margin: 0px;
  font-family: Arial;
}

</style>

<style scoped>

button{
  background-color: white;
  border-radius: 5px;
  border: 2px solid gray;
  transition-duration: 0.3s;
}

button:hover{
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

.big-but:hover{
  top: 41%;
  background-color: red;
  border-radius: 50%;
  border: none;
  outline: none;
  cursor: pointer;
  box-shadow: 0px 10px 0px darkred;
}

.big-but:active{
  top: 43%;
  box-shadow: 0px 0px 0px darkred;
}

.red-but:hover{
  background-color: #d95252;
}


.actions{
  display: flex;
  flex-direction: column;
}
  
.panel-block{
  background-color: white;
  display: flex;
  flex-direction: column;
  align-items: start;
  padding: 0px;
  width: 20%;
  border-radius: 25px;
  margin: 15px;
  padding-bottom: 20px;
  padding-top: 0px;
  
}

.container{
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.user{
  background-color: #164a9e;
  padding: 0px;
  margin: 0px;
  font-family: Arial;
  color: white;
  display: flex;
  height: 50px;
  justify-content: start;
  align-items: center;
  transition-duration: 0.3s;
  width: 100%;
  height: 100%;
  border-radius: 25px 0px;
}

.user img{
  border-radius: 50%;
  outline: solid 3px white;
  outline-offset: -3px;
}
.profile{
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
</style>