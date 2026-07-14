import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("token") || "");
  const user = ref<{ username: string; role: string } | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  async function login(tenantSlug: string, username: string, password: string) {
    const resp = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_slug: tenantSlug, username, password }),
    });
    if (!resp.ok) throw new Error("Login failed");
    const data = await resp.json();
    token.value = data.access_token;
    localStorage.setItem("token", data.access_token);
    await fetchMe();
  }

  async function fetchMe() {
    const resp = await fetch("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${token.value}` },
    });
    if (resp.ok) user.value = await resp.json();
  }

  function logout() {
    token.value = "";
    user.value = null;
    localStorage.removeItem("token");
  }

  return { token, user, isAuthenticated, login, fetchMe, logout };
});
