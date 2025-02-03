<template>
  <div class="forma">
    <div class="buttons">
      <button
        @click="currentForm = 'login'"
        :class="{'active': currentForm === 'login'}"
       style = "font-size: 25px;">
        Вход
      </button>
      <button
        @click="currentForm = 'register'"
        :class="{'active': currentForm === 'register'}"
       style = "font-size: 25px;">
        Регистрация
      </button>
    </div>

    <div v-if="currentForm === 'login'" class="block">
      <!-- Слушаем правильное событие от компонента UserLogin -->
      <UserLogin @enter-success="goToHomePage" />
    </div>
    <div v-if="currentForm === 'register'" class="block">
      <UserRegistration @enter-success="goToHomePage" />
    </div>
  </div>
</template>

<script>
import UserLogin from './UserLogin.vue'
import UserRegistration from './UserRegistration.vue'

export default {
  components: {
    UserLogin,
    UserRegistration
  },
  data() {
    return {
      currentForm: 'login'
    }
  },
  methods: {
    goToHomePage(username) {
      this.$emit('update-page', username);
    }
  }
}
</script>

<style scoped>
button {
  font-size: 16px;
  cursor: pointer;
}

button:hover {
  background-color: #f0f0f0;
}

div {
  text-align: center;
}

.block{
  width: 40%;
}

.buttons {
  border: none;
}

.buttons button{
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 10px 20px;
  border: none;
  transition: background-color 0.3s;
}

.buttons button.active {
  background-color: #007bff;
  color: white;
}

.forma {
  display: flex;
  flex-direction: column;
  padding-top: 0px;
  justify-content: center;
  align-items: center;
  width: 50%;
  margin-top: 25vh;
  background-color: white;
  margin-left: auto;
  margin-right: auto;
  height: 45vh;
  border-radius: 25px;
}
</style>
