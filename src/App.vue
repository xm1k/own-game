<template>
  <div id="app">
    <StartPage v-if="currentPage === 'start'" @update-page="goToHomePage" />
    <HomePage v-if="currentPage === 'home'" :username="username" @logout="logout" />
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
      username: ''
    }
  },
  methods: {
    goToHomePage(username) {
      this.username = username;
      this.currentPage = 'home'; // Переключаем страницу на home
    },
    logout() {
      this.username = '';
      this.currentPage = 'start'; // При выходе возвращаем на стартовую страницу
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
