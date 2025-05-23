import axios from "axios";

const state = {
  currentNewsSymbol: null,
  newsArticles: [],
  isLoading: false,
  error: null,
};

const getters = {
  currentNewsSymbol: (state) => state.currentNewsSymbol,
  newsArticles: (state) => state.newsArticles,
  isNewsLoading: (state) => state.isLoading,
  newsError: (state) => state.error,
};

const mutations = {
  SET_NEWS_LOADING(state, isLoading) {
    state.isLoading = isLoading;
  },
  SET_NEWS_ERROR(state, error) {
    state.error = error;
  },
  SET_CURRENT_NEWS_SYMBOL(state, symbol) {
    state.currentNewsSymbol = symbol;
  },
  SET_NEWS_ARTICLES(state, articles) {
    state.newsArticles = Array.isArray(articles) ? articles : [];
    console.log(
      "[Vuex news.js SET_NEWS_ARTICLES] Mutation called. Articles received:",
      JSON.parse(JSON.stringify(articles))
    );
    console.log(
      "[Vuex news.js SET_NEWS_ARTICLES] state.newsArticles is now:",
      JSON.parse(JSON.stringify(state.newsArticles))
    );
    console.log(
      `[Vuex news.js SET_NEWS_ARTICLES] state.newsArticles length: ${state.newsArticles.length}`
    );
  },
  CLEAR_NEWS(state) {
    state.newsArticles = [];
    state.newsError = null;
    console.log(
      "[Vuex news.js CLEAR_NEWS] Cleared news articles. State is now:",
      JSON.parse(JSON.stringify(state))
    );
  },
};

const actions = {
  async fetchNewsForSymbol({ commit }, symbol) {
    if (!symbol || symbol === "N/A") {
      commit("CLEAR_NEWS");
      commit("SET_NEWS_ERROR", "No symbol selected to fetch news.");
      return;
    }
    // Optional: Prevent re-fetching if already loaded for the same symbol
    // if (state.currentNewsSymbol === symbol && state.articles.length > 0 && !forceRefresh) {
    //   return;
    // }

    commit("SET_NEWS_LOADING", true);
    commit("SET_NEWS_ERROR", null);
    commit("SET_CURRENT_NEWS_SYMBOL", symbol);

    try {
      console.log(`[Vuex news.js] Fetching for: ${symbol}`);
      const response = await axios.get(
        `http://localhost:8000/api/news/${symbol}`
      );
      console.log("[Vuex news.js] API Response:", response);
      const responseData = response.data;
      console.log("[Vuex news.js] Response Data:", responseData);

      if (responseData && responseData.length > 0) {
        console.log(
          "[Vuex news.js] Committing articles:",
          JSON.parse(JSON.stringify(responseData))
        );
        commit("SET_NEWS_ARTICLES", responseData);
      } else {
        console.log("[Vuex news.js] No articles from API. Committing [].");
        commit("SET_NEWS_ARTICLES", []);
      }
    } catch (err) {
      console.error("Error fetching news in Vuex store:", err);
      commit("SET_NEWS_ARTICLES", []); // Clear articles on error
      commit("SET_NEWS_ERROR", "Failed to load news. Please try again.");
    } finally {
      commit("SET_NEWS_LOADING", false);
    }
  },
  clearNews({ commit }) {
    commit("CLEAR_NEWS");
  },
};

export default {
  namespaced: true, // Important: Keep module namespaced
  state,
  getters,
  mutations,
  actions,
};
