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
    <h1>PolicyMind</h1>
    <form @submit.prevent="doLogin">
      <input v-model="tenant" placeholder="Tenant Slug" />
      <input v-model="username" placeholder="Username" />
      <input v-model="password" type="password" placeholder="Password" />
      <button type="submit">Login</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </div>
</template>
