import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "../stores/auth";

describe("Auth Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("starts unauthenticated", () => {
    const auth = useAuthStore();
    expect(auth.isAuthenticated).toBe(false);
  });

  it("sets token after login-like state", () => {
    const auth = useAuthStore();
    auth.token = "test-token";
    expect(auth.isAuthenticated).toBe(true);
  });

  it("logout clears token", () => {
    const auth = useAuthStore();
    auth.token = "test-token";
    auth.logout();
    expect(auth.isAuthenticated).toBe(false);
  });
});
