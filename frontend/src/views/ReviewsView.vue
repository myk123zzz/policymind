<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useChatStore } from "../stores/chat";

const auth = useAuthStore();
const chat = useChatStore();
const reviews = ref<{ id: number; thread_id: string; reason: string; status: string }[]>([]);

async function loadReviews() {
  const resp = await fetch("/api/v1/reviews", { headers: { Authorization: `Bearer ${auth.token}` } });
  if (resp.ok) reviews.value = await resp.json();
}

async function approve(reviewId: number, threadId: string) {
  await fetch(`/api/v1/reviews/${reviewId}/approve`, {
    method: "POST", headers: { Authorization: `Bearer ${auth.token}` },
  });
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
    <h2>审核中心</h2>
    <div v-for="r in reviews" :key="r.id" class="review-item">
      <div>
        <strong>#{{ r.id }}</strong>
        <span class="review-reason">{{ r.reason }}</span>
      </div>
      <div class="review-status">
        <span :class="r.status">{{ r.status === 'pending' ? '待处理' : r.status === 'approved' ? '已批准' : '已拒绝' }}</span>
        <button v-if="r.status === 'pending'" @click="approve(r.id, r.thread_id)">批准并恢复</button>
      </div>
    </div>
    <p v-if="reviews.length === 0" class="empty-hint">暂无待审核任务</p>
  </div>
</template>

<style scoped>
.review-reason { color: var(--text-secondary, #64748b); margin-left: 12px; font-size: 13px; }
.review-status { display: flex; align-items: center; gap: 10px; }
.review-status .pending { color: #d97706; font-weight: 500; }
.review-status .approved { color: #16a34a; }
.review-status .rejected { color: #dc2626; }
</style>
