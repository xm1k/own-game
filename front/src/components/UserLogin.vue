<template>
  <div class="login-form">
    <form @submit.prevent="login" style="margin-top: 20px;">
      <div class="form-group">
        <input v-model="email" type="email" placeholder="Email" required />
      </div>
      <div class="form-group">
        <input v-model="password" type="password" placeholder="Пароль" required />
      </div>
      <button type="submit">Войти</button>
    </form>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      email: '',
      password: ''
    }
  },
  methods: {
      async login() {
        try {
          const response = await axios.post('http://localhost:5000/login', {
            email: this.email,
            password: this.password
          });
 
          if (response.data.status === 'success') {
            localStorage.setItem('user', JSON.stringify({
              email: this.email,
              name: response.data.name
            }));
            this.$emit('enter-success', {
              username: response.data.name,
              email: this.email
            });
          }
        } catch (error) {
          console.error('Ошибка:', error);
          alert('Ошибка авторизации');
        }
      }
  }
}
</script>

<style scoped>

  .login-form{
    width: 100%;
  }

  .form-group{
    padding-bottom: 10px;
    display: flex;
  }
  .form-group input{
    width: 100%;
    height: 40px;
    border-radius: 15px;
    border: solid 2px #707070;
    padding-left: 15px;
    font-size: 20px;
    font-family: Arial;
    background-color: #ededed;
  }

  button{
    height: 40px;
    width: auto;
    padding: 0 50px;
    border-radius: 10px;
    cursor: pointer;
    font-family: Arial;
    font-size: 20px;
    border: solid 2px #707070;
    transition: 0.3s;
  }

  button:hover{
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 0px;
  }

  </style>