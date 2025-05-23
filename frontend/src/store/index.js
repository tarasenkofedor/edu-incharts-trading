import Vue from "vue";
import Vuex from "vuex";
import chart from "./modules/chart";
import auth from "./modules/auth";
import news from "./modules/news";
import perflogs from "./modules/perflogs";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {},
  getters: {},
  mutations: {},
  actions: {},
  modules: {
    chart,
    auth,
    news,
    perflogs,
  },
});
