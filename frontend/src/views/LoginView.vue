<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const tenant = ref("test-tenant");
const username = ref("");
const password = ref("");
const error = ref("");

async function doLogin() {
  try {
    await auth.login(tenant.value, username.value, password.value);
    router.push("/");
  } catch {
    error.value = "Invalid credentials";
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>PolicyMind</h1>
      <p>Enterprise Policy Intelligence Platform</p>
      <form @submit.prevent="doLogin">
        <label>Tenant</label>
        <input v-model="tenant" placeholder="test-tenant" />
        <label>Username</label>
        <input v-model="username" placeholder="admin" />
        <label>Password</label>
        <input v-model="password" type="password" placeholder="admin123" />
        <button type="submit">Sign In</button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>
