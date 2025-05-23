import Vue from "vue";
import VueRouter from "vue-router";
import Home from "../views/Home.vue";
import LoginView from "../views/Login.vue";
import RegisterView from "../views/Register.vue";
// eslint-disable-next-line no-unused-vars
import store from "../store";

Vue.use(VueRouter);

const routes = [
  {
    path: "/",
    name: "home",
    component: Home,
    meta: { requiresAuth: true },
  },
  {
    path: "/about",
    name: "about",
    component: () =>
      import(/* webpackChunkName: "about" */ "../views/AboutView.vue"),
  },
  {
    path: "/login",
    name: "login",
    component: LoginView,
    meta: { guest: true },
  },
  {
    path: "/register",
    name: "register",
    component: RegisterView,
    meta: { guest: true },
  },
];

const router = new VueRouter({
  routes,
});

export default router;
