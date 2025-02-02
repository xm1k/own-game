<template>
  <div class="home-page">
    <div class="user">
      <img src="../assets/user.webp" alt="" style="width: 80px;">
      <h1>{{ username }}</h1>
    </div>
    <div v-if="!inLobby" class="actions">
      <button @click="showCreateLobbyModal = true">Создать лобби</button>
      <button @click="showJoinLobbyModal = true">Присоединиться к лобби</button>
      <button @click="logout" class="red-but">Выход</button>
    </div>

    <LobbyPage v-if="inLobby" :lobbyCode="lobbyCode" :playerName="username" @leave-lobby="leaveLobby" />

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
</template>

<script>
import LobbyPage from './LobbyPage.vue';

export default {
  components: { LobbyPage },
  props: ['username'],
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
  methods: {
    async confirmCreateLobby() {
      if (!this.newLobbyName.trim()) {
        alert('Введите название лобби');
        return;
      }
      try {
        const response = await fetch('http://localhost:5000/create-lobby', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lobby_name: this.newLobbyName, player_name: this.username })
        });
        const data = await response.json();
        if (data.status === 'success') {
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
          body: JSON.stringify({ lobby_code: this.lobbyCodeInput, player_name: this.username })
        });
        const data = await response.json();
        if (data.status === 'success') {
          this.lobbyCode = this.lobbyCodeInput;
          this.inLobby = true;
        } else {
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
      this.inLobby = false;
      this.lobbyCode = '';
    },
    logout() {
      this.$emit('logout');
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

.red-but:hover{
  background-color: #d95252;
}


.actions{
  display: flex;
  flex-direction: column;
}
  
.home-page{
  background-color: white;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 0px;
  width: 20%;
  border-radius: 25px;
  margin: 15px;
  padding-bottom: 20px;
  padding-top: 10px;

}

.user{
  font-family: Arial;
  color: #446ead;
  display: flex;
  height: 50px;
  justify-content: center;
  align-items: center;
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
