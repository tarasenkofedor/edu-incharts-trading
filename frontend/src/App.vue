<template>
  <div id="app">
    <nav class="main-nav">
      <!-- <router-link to="/">Home</router-link>
      <template v-if="isLoggedIn">
        <span class="user-info"
          >Welcome, {{ currentUserNickname || "User" }}!</span
        >
        <a href="#" @click.prevent="handleLogout" class="nav-link">Logout</a>
      </template>
      <template v-else>
        <router-link to="/login" class="nav-link">Login</router-link>
        <router-link to="/register">Register</router-link>
      </template> -->
      <!-- <router-link to="/about">About</router-link> -->
      <router-view />
    </nav>
  </div>
</template>

<script>
import { mapGetters, mapActions, mapState } from "vuex";

export default {
  name: "App",
  computed: {
    ...mapGetters("auth", ["isLoggedIn"]),
    ...mapState("auth", {
      user: (state) => state.user,
    }),
    currentUserNickname() {
      return this.user ? this.user.nickname : "";
    },
  },
  methods: {
    ...mapActions("auth", ["logout"]),
    async handleLogout() {
      await this.logout();
      this.$router.push("/login"); // Redirect to login after logout
    },
  },
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* text-align: center; */ /* Let components decide text alignment */
  color: #2c3e50;
}

.main-nav {
  padding: 15px 30px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e7e7e7;
  display: flex;
  justify-content: space-between; /* Distributes space */
  align-items: center;
}

.main-nav a.nav-link,
.main-nav a[href="#"] {
  font-weight: bold;
  color: #2c3e50;
  text-decoration: none;
  margin-left: 15px;
}

/* .main-nav a.router-link-exact-active {
  color: #42b983;
} */

.main-nav .user-info {
  margin-left: auto; /* Pushes user info and logout to the right */
  margin-right: 15px;
  color: #555;
}

/* Keeping original nav styles commented for reference if needed */
/* nav {
  padding: 30px;
}

nav a {
  font-weight: bold;
  color: #2c3e50;
}

nav a.router-link-exact-active {
  color: #42b983;
} */
</style>
