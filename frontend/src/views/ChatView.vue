<script setup lang="ts">
import { ref } from "vue";
import { useChatStore } from "../stores/chat";
import { useAuthStore } from "../stores/auth";
import { renderSafeMarkdown } from "../utils/markdown";

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

function activeCitation(_id: string) {
  // highlight citation in right panel
}
</script>

<template>
  <div class="chat-layout">
    <!-- Left: Session list -->
    <aside class="chat-sidebar">
      <h3>Sessions</h3>
      <div v-if="chat.threadId" class="session-item active">Thread: {{ chat.threadId }}</div>
    </aside>

    <!-- Center: Chat -->
    <main class="chat-main">
      <div class="messages">
        <div v-for="(msg, i) in chat.messages" :key="i" :class="msg.role">
          <div v-html="renderSafeMarkdown(msg.content)"></div>
        </div>
      </div>
      <div v-if="chat.pendingReview" class="review-bar">
        <span>Review #{{ chat.pendingReview.review_id }} pending</span>
        <button @click="approve">Approve</button>
        <button @click="reject">Reject</button>
      </div>
      <div class="input-bar">
        <input v-model="query" @keyup.enter="send" placeholder="Ask..." :disabled="chat.streaming" />
        <button @click="send" :disabled="chat.streaming">Send</button>
      </div>
    </main>

    <!-- Right: Evidence -->
    <aside class="chat-evidence">
      <h3>Citations</h3>
      <div v-for="c in chat.citations" :key="c.id" class="citation-item" @click="activeCitation(c.id)">
        [{{ c.id }}]
      </div>
      <h3>Graph Paths</h3>
      <div v-for="(p, i) in chat.graphPaths" :key="i">
        {{ p }}
      </div>
      <h3>Timeline</h3>
      <div v-for="(evt, i) in chat.timeline" :key="i" class="event-item">
        <strong>{{ evt.type }}</strong>
        <span v-if="evt.type === 'content'">{{ (evt.data.text as string)?.slice(0, 50) }}</span>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.chat-layout { display: flex; height: 100vh; }
.chat-sidebar { width: 200px; border-right: 1px solid #ccc; padding: 1rem; }
.chat-main { flex: 1; display: flex; flex-direction: column; padding: 1rem; }
.chat-evidence { width: 280px; border-left: 1px solid #ccc; padding: 1rem; overflow-y: auto; }
.messages { flex: 1; overflow-y: auto; }
.input-bar { display: flex; gap: 0.5rem; margin-top: 1rem; }
.input-bar input { flex: 1; padding: 0.5rem; }
.review-bar { background: #fff3cd; padding: 0.5rem; display: flex; gap: 0.5rem; align-items: center; }
.citation-item { cursor: pointer; color: #0066cc; }
.event-item { font-size: 0.85em; margin: 0.25rem 0; }
</style>
