<!-- HomePage.vue -->
<template>
  <div class="home-page">
    <h1>Добро пожаловать, {{ username }}!</h1>
    <button @click="logout">Выход</button>
  </div>
</template>

<script>
export default {
  props: ['username'],
  methods: {
    logout() {
      this.$emit('logout');  // Отправляем событие на выход
    }
  }
}
</script>

<style scoped>
.home-page {
  text-align: center;
  margin-top: 50px;
}

button {
  font-size: 16px;
  cursor: pointer;
  margin-top: 20px;
}
</style>
