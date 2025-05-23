import axios from "axios";

// Helper to get token, could be more sophisticated (e.g., cookies)
const getToken = () => localStorage.getItem("user-token");
const setToken = (token) => localStorage.setItem("user-token", token);
const removeToken = () => localStorage.removeItem("user-token");

const state = {
  user: null, // Could store user profile info here
  token: getToken() || null,
  status: "", // e.g., 'loading', 'success', 'error'
};

const mutations = {
  AUTH_REQUEST(state) {
    state.status = "loading";
    state.error = null;
  },
  AUTH_SUCCESS(state, { token, user }) {
    state.status = "success";
    state.token = token;
    state.user = user; // Optionally store user profile
    state.error = null;
  },
  AUTH_ERROR(state, error) {
    state.status = "error";
    state.token = null;
    state.user = null;
    state.error = error;
  },
  LOGOUT(state) {
    state.status = "";
    state.token = null;
    state.user = null;
    state.error = null;
  },
  SET_USER(state, user) {
    state.user = user;
  },
};

const actions = {
  async login({ commit, dispatch }, credentials) {
    commit("AUTH_REQUEST");
    try {
      const formData = new URLSearchParams();
      formData.append("username", credentials.username);
      formData.append("password", credentials.password);

      const response = await axios.post(
        "http://localhost:8000/auth/login",
        formData,
        {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        }
      );

      const token = response.data.access_token;
      setToken(token);
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;

      await dispatch("fetchCurrentUser", token);
      return response;
    } catch (err) {
      removeToken();
      delete axios.defaults.headers.common["Authorization"];
      commit(
        "AUTH_ERROR",
        err.response
          ? err.response.data.detail || "Login failed"
          : "Network error or server down"
      );
      throw err;
    }
  },

  async register({ commit }, userData) {
    // userData: { nickname, email, password }
    commit("AUTH_REQUEST");
    try {
      // The backend /auth/register endpoint expects UserCreate schema
      // which includes nickname, email, password.
      const response = await axios.post("http://localhost:8000/auth/register", {
        nickname: userData.nickname,
        email: userData.email,
        password: userData.password,
      });
      // Backend returns the created user, but not a token.
      // The component will call the login action next.
      // No AUTH_SUCCESS commit here as login action will handle it after token retrieval.
      return response.data; // Return the created user data, Register.vue might use it or just proceed to login
    } catch (err) {
      // Ensure token and user are cleared if any old ones existed, though register shouldn't involve tokens directly.
      removeToken();
      delete axios.defaults.headers.common["Authorization"];
      commit(
        "AUTH_ERROR",
        err.response
          ? err.response.data.detail || "Registration failed"
          : "Network error or server down during registration"
      );
      throw err; // Re-throw for component to handle
    }
  },

  async logout({ commit }) {
    commit("LOGOUT");
    removeToken();
    delete axios.defaults.headers.common["Authorization"];
  },

  async fetchCurrentUser({ commit }, token) {
    commit("AUTH_REQUEST");
    try {
      if (token && !axios.defaults.headers.common["Authorization"]) {
        axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      }
      const userResponse = await axios.get("http://localhost:8000/users/me");
      commit("AUTH_SUCCESS", {
        token: token || getToken(),
        user: userResponse.data,
      });
    } catch (error) {
      removeToken();
      delete axios.defaults.headers.common["Authorization"];
      commit("AUTH_ERROR", "Session expired or invalid. Please login again.");
    }
  },

  async tryAutoLogin({ dispatch, commit, state }) {
    const token = getToken();
    if (!token) {
      return;
    }
    if (state.user && state.token === token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      return;
    }

    commit("AUTH_REQUEST");
    await dispatch("fetchCurrentUser", token);
  },
};

const getters = {
  isLoggedIn: (state) => !!state.token,
  authStatus: (state) => state.status,
  authUser: (state) => state.user,
  authError: (state) => state.error,
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
};
