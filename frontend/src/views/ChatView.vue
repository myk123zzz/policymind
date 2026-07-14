<script setup lang="ts">
import { ref } from "vue";
import { useChatStore } from "../stores/chat";
import { useAuthStore } from "../stores/auth";

const chat = useChatStore();
const auth = useAuthStore();
const query = ref("");

async function send() {
  if (!query.value.trim()) return;
  const q = query.value;
  query.value = "";
  await chat.sendQuery(q, auth.token);
}

async function approve() {
  await chat.resume("approve", auth.token);
}

async function reject() {
  await chat.resume("reject", auth.token);
}
</script>

<template>
  <div class="chat-workspace">
    <div class="chat-messages">
      <div v-for="(msg, i) in chat.messages" :key="i" :class="msg.role">
        {{ msg.content }}
      </div>
    </div>
    <div v-if="chat.pendingReview" class="review-bar">
      <span>Review #{{ chat.pendingReview.review_id }} pending</span>
      <button @click="approve">Approve</button>
      <button @click="reject">Reject</button>
    </div>
    <div class="chat-input">
      <input v-model="query" @keyup.enter="send" placeholder="Ask a question..." />
      <button @click="send" :disabled="chat.streaming">Send</button>
    </div>
  </div>
</template>
