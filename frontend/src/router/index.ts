import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import LoginView from "../views/LoginView.vue";
import ChatView from "../views/ChatView.vue";
import DocumentsView from "../views/DocumentsView.vue";
import ReviewsView from "../views/ReviewsView.vue";
import GraphView from "../views/GraphView.vue";

const routes = [
  { path: "/login", component: LoginView },
  { path: "/", component: ChatView, meta: { requiresAuth: true } },
  { path: "/documents", component: DocumentsView, meta: { requiresAuth: true } },
  { path: "/reviews", component: ReviewsView, meta: { requiresAuth: true } },
  { path: "/graph", component: GraphView, meta: { requiresAuth: true } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.token) {
    next("/login");
  } else {
    next();
  }
});

export default router;
