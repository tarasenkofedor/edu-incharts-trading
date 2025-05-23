<template>
  <div class="login-view">
    <h2>Login</h2>
    <form @submit.prevent="handleLogin" class="login-form">
      <div class="form-group">
        <label for="identifier">Nickname or Email:</label>
        <input type="text" id="identifier" v-model="identifier" required />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input type="password" id="password" v-model="password" required />
      </div>
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Logging in..." : "Login" }}
      </button>
      <p v-if="error" class="error-message">{{ error }}</p>
      <p class="register-link">
        Don't have an account?
        <router-link to="/register">Register here</router-link>
      </p>
    </form>
  </div>
</template>

<script>
import { mapActions } from "vuex";

export default {
  name: "LoginView",
  data() {
    return {
      identifier: "",
      password: "",
      isLoading: false,
      error: "",
    };
  },
  methods: {
    ...mapActions("auth", ["login"]),
    async handleLogin() {
      this.isLoading = true;
      this.error = "";
      try {
        await this.login({
          username: this.identifier,
          password: this.password,
        });
        this.$router.push("/");
      } catch (err) {
        // The error is already set in the Vuex action (AUTH_ERROR mutation)
        // We can access it via a getter or mapState if needed, or just display a generic one.
        // For now, let's assume the Vuex module updates the error state which can be shown.
        // this.error = err.message || "An error occurred during login.";
        // console.error("Login error in component:", err);
        // Let's rely on the auth module's error state for now, and ensure it's displayed.
        // If auth module sets a specific error message in its state, we could map it.
        // For now, if the login action throws, it means it failed.
        this.error =
          this.$store.state.auth.status ||
          "Login failed. Please check your credentials.";
      } finally {
        this.isLoading = false;
      }
    },
  },
  computed: {
    // Add computed property to get error from store
    authError() {
      return this.$store.state.auth.status; // Assuming status holds error messages on failure
    },
  },
  watch: {
    // Watch for authError changes to update local error prop
    authError(newValue) {
      if (newValue && newValue.startsWith("Error:")) {
        // Or however your auth module signals an error
        this.error = newValue;
      }
    },
  },
};
</script>

<style scoped>
.login-view {
  max-width: 400px;
  margin: 50px auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.login-form .form-group {
  margin-bottom: 15px;
}

.login-form label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.login-form input[type="text"],
.login-form input[type="password"] {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.login-form button {
  width: 100%;
  padding: 10px;
  background-color: #5cb85c; /* Green */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.login-form button:disabled {
  background-color: #ccc;
}

.error-message {
  color: red;
  margin-top: 10px;
}

.register-link {
  margin-top: 15px;
  text-align: center;
}
</style>
