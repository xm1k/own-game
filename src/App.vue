<template>
  <div id="app">
    <StartPage v-if="currentPage === 'start'" @update-page="goToHomePage" />
    <HomePage v-if="currentPage === 'home'" :username="username" :email="email" @logout="logout" />
  </div>
</template>

<script>
import StartPage from './components/StartPage.vue'
import HomePage from './components/HomePage.vue'

export default {
  components: {
    StartPage,
    HomePage
  },
  data() {
    return {
      currentPage: 'start',
      username: '',
      email: ''  // Добавляем email в data
    }
  },
  created() {
    // Проверяем наличие данных при загрузке
    const userData = localStorage.getItem('user');
    if (userData) {
        const user = JSON.parse(userData);
        this.goToHomePage({ 
            username: user.name,  // Правильное имя свойства
            email: user.email     // и синтаксис объекта
        });
    }
  },
  methods: {
    // Обновляем метод для работы с объектом, который содержит и username, и email
    goToHomePage({ username, email }) {
      this.username = username;
      this.email = email;  // Присваиваем email
      this.currentPage = 'home'; // Переключаем страницу на home
    },
    logout() {
      this.username = '';
      this.email = '';  // Сбрасываем email
      this.currentPage = 'start'; // При выходе возвращаем на стартовую страницу
      localStorage.removeItem('user');
    }
  }
}
</script>



<style>
body {
  padding: 0;
  background-color: #5e87c4;
}
</style>
