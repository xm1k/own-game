<template>
  <div class="login-form">
    <form @submit.prevent="register" style="margin-top: 20px;">
      <div class="form-group">
        <input v-model="name" type="text" placeholder="Имя" required />
      </div>
      <div class="form-group">
        <input v-model="email" type="email" placeholder="Email" required />
      </div>
      <div class="form-group">
        <input 
          v-model="password" 
          type="password" 
          placeholder="Пароль" 
          required 
          :class="{ 'error-border': showPasswordError }"
        />
      </div>
      <div class="form-group">
        <input 
          v-model="confirmPassword" 
          type="password" 
          placeholder="Подтвердите пароль" 
          required 
          :class="{ 'error-border': showPasswordError }"
          @input="checkPasswords"
        />
      </div>
      <div  v-if="showPasswordError" class="error-message">
        Пароли не совпадают!
      </div>
      <button type="submit">Зарегистрироваться</button>
    </form>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      email: '',
      password: '',
      confirmPassword: '',
      name: '',
      showPasswordError: false
    }
  },
  methods: {
    checkPasswords() {
      this.showPasswordError = this.password !== this.confirmPassword;
    },
    async register() {
      // Проверка совпадения паролей перед отправкой
      if (this.password !== this.confirmPassword) {
        this.showPasswordError = true;
        alert('Пароли не совпадают');
        return;
      }

      try {
        const response = await axios.post('http://localhost:5000/register', {
          email: this.email,
          password: this.password,
          name: this.name
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
          
          // Очистка полей после успешной регистрации
          this.email = '';
          this.password = '';
          this.confirmPassword = '';
          this.name = '';
          this.showPasswordError = false;
        }
      } catch (error) {
        console.error('Ошибка при регистрации:', error);
        alert(error.response?.data?.message || 'Ошибка при регистрации');
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
    padding-bottom: 15px;
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
    font-size: 18px;
    border: solid 2px #707070;
    transition: 0.3s;
  }

  button:hover{
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 0px;
  }

  .error-message {
    width: 10%;
    left: 45%;
    bottom: 20%;
    position: absolute;
    background-color: white;
    color: black;
    margin-bottom: 10px;
    font-size: 16px;
    border: solid #ff4444 4px;
    border-radius: 15px;
    padding: 20px 0px;
  }


  </style>
