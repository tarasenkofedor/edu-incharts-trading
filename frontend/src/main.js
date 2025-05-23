import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import store from "./store"; // Import the store

Vue.config.productionTip = false;

// Attempt to log in automatically if a token exists
store
  .dispatch("auth/tryAutoLogin")
  .then(() => {
    new Vue({
      router,
      store, // Add store to the Vue instance
      render: (h) => h(App),
    }).$mount("#app");
  })
  .catch((error) => {
    // Handle potential errors from tryAutoLogin if necessary, though it should handle its own errors gracefully
    console.error("Auto-login error:", error);
    // Still mount the app even if auto-login fails
    new Vue({
      router,
      store,
      render: (h) => h(App),
    }).$mount("#app");
  });
