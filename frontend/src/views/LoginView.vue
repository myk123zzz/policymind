<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const tenant = ref("default");
const username = ref("");
const password = ref("");
const error = ref("");

async function doLogin() {
  try {
    await auth.login(tenant.value, username.value, password.value);
    router.push("/");
  } catch {
    error.value = "用户名或密码错误";
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>PolicyMind</h1>
      <p>企业制度智能问答平台</p>
      <form @submit.prevent="doLogin">
        <label>租户</label>
        <input v-model="tenant" placeholder="default" />
        <label>用户名</label>
        <input v-model="username" placeholder="请输入用户名" />
        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" />
        <button type="submit">登 录</button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>
