<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useChatStore } from "../stores/chat";

const auth = useAuthStore();
const chat = useChatStore();
const reviews = ref<{ id: number; thread_id: string; reason: string; status: string }[]>([]);

async function loadReviews() {
  const resp = await fetch("/api/v1/reviews", {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  if (resp.ok) reviews.value = await resp.json();
}

async function approve(reviewId: number, threadId: string) {
  await fetch(`/api/v1/reviews/${reviewId}/approve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  // Resume the corresponding chat thread
  if (threadId) {
    chat.threadId = threadId;
    await chat.resume("approve", auth.token);
  }
  await loadReviews();
}

onMounted(loadReviews);
</script>

<template>
  <div class="reviews-page">
    <h2>Review Center</h2>
    <div v-for="r in reviews" :key="r.id" class="review-item">
      <span>#{{ r.id }}: {{ r.reason }} ({{ r.status }})</span>
      <button v-if="r.status === 'pending'" @click="approve(r.id, r.thread_id)">Approve & Resume</button>
    </div>
    <p v-if="reviews.length === 0">No pending reviews.</p>
  </div>
</template>
