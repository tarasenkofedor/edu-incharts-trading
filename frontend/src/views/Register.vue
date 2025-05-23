<template>
  <div class="register-view">
    <h2>Register</h2>
    <form @submit.prevent="handleRegister" class="register-form">
      <div class="form-group">
        <label for="nickname">Nickname:</label>
        <input type="text" id="nickname" v-model="form.nickname" required />
      </div>
      <div class="form-group">
        <label for="email">Email:</label>
        <input type="email" id="email" v-model="form.email" required />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input type="password" id="password" v-model="form.password" required />
      </div>
      <div class="form-group">
        <label for="confirmPassword">Confirm Password:</label>
        <input
          type="password"
          id="confirmPassword"
          v-model="form.confirmPassword"
          required
        />
      </div>
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Registering..." : "Register" }}
      </button>
      <p v-if="error" class="error-message">{{ error }}</p>
      <p class="login-link">
        Already have an account?
        <router-link to="/login">Login here</router-link>
      </p>
    </form>
  </div>
</template>

<script>
import { mapActions } from "vuex";

export default {
  name: "RegisterView",
  data() {
    return {
      form: {
        nickname: "",
        email: "",
        password: "",
        confirmPassword: "",
      },
      isLoading: false,
      error: "",
    };
  },
  methods: {
    ...mapActions("auth", ["register", "login"]), // Assuming a 'register' action will be created
    async handleRegister() {
      if (this.form.password !== this.form.confirmPassword) {
        this.error = "Passwords do not match.";
        return;
      }
      this.isLoading = true;
      this.error = "";
      try {
        // Dispatch Vuex register action
        await this.register({
          nickname: this.form.nickname,
          email: this.form.email,
          password: this.form.password,
        });

        // After successful registration, automatically log in the user
        // The backend register endpoint might return a user object but not a token by default
        // So we call the login action explicitly.
        await this.login({
          username: this.form.nickname,
          password: this.form.password,
        });
        this.$router.push("/"); // Redirect to home after successful registration and login
      } catch (err) {
        this.error =
          this.$store.state.auth.error ||
          "An error occurred during registration.";
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>

<style scoped>
.register-view {
  max-width: 400px;
  margin: 50px auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.register-form .form-group {
  margin-bottom: 15px;
}

.register-form label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.register-form input[type="text"],
.register-form input[type="email"],
.register-form input[type="password"] {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.register-form button {
  width: 100%;
  padding: 10px;
  background-color: #5cb85c; /* Green */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.register-form button:disabled {
  background-color: #ccc;
}

.error-message {
  color: red;
  margin-top: 10px;
}

.login-link {
  margin-top: 15px;
  text-align: center;
}
</style>
