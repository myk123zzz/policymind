<script setup lang="ts">
import { useAuthStore } from "./stores/auth";
import { useRouter } from "vue-router";

const auth = useAuthStore();
const router = useRouter();

function logout() {
  auth.logout();
  router.push("/login");
}
</script>

<template>
  <nav v-if="auth.isAuthenticated" class="app-nav">
    <span class="brand">PolicyMind</span>
    <router-link to="/">智能问答</router-link>
    <router-link to="/documents">制度管理</router-link>
    <router-link to="/reviews">审核中心</router-link>
    <router-link to="/graph">知识图谱</router-link>
    <span class="spacer"></span>
    <button @click="logout">退出</button>
  </nav>
  <router-view />
</template>
