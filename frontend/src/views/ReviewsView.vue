<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const reviews = ref<{ id: number; reason: string; status: string }[]>([]);

async function loadReviews() {
  const resp = await fetch("/api/v1/reviews", {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  if (resp.ok) reviews.value = await resp.json();
}

async function approve(id: number) {
  await fetch(`/api/v1/reviews/${id}/approve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  await loadReviews();
}

onMounted(loadReviews);
</script>

<template>
  <div class="reviews-page">
    <h2>Review Center</h2>
    <div v-for="r in reviews" :key="r.id" class="review-item">
      <span>#{{ r.id }}: {{ r.reason }} ({{ r.status }})</span>
      <button v-if="r.status === 'pending'" @click="approve(r.id)">Approve</button>
    </div>
  </div>
</template>
