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
    <router-link to="/">Chat</router-link>
    <router-link to="/documents">Documents</router-link>
    <router-link to="/reviews">Reviews</router-link>
    <router-link to="/graph">Graph</router-link>
    <span class="spacer"></span>
    <button @click="logout">Logout</button>
  </nav>
  <router-view />
</template>
