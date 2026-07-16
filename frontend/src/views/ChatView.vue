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

async function approve() { await chat.resume("approve", auth.token); }
async function reject() { await chat.resume("reject", auth.token); }
</script>

<template>
  <div class="chat-layout">
    <aside class="chat-sidebar">
      <h3>会话列表</h3>
      <div v-if="chat.threadId" class="session-item active">{{ chat.threadId }}</div>
      <div v-else class="empty-hint">暂无会话</div>
    </aside>

    <main class="chat-main">
      <div class="chat-messages">
        <div v-for="(msg, i) in chat.messages" :key="i" :class="msg.role">
          <div v-if="msg.role === 'user'"><span class="msg-label">我</span>{{ msg.content }}</div>
          <div v-else v-html="renderSafeMarkdown(msg.content)"></div>
        </div>
        <div v-if="chat.messages.length === 0" class="welcome">
          <h2>PolicyMind 智能问答</h2>
          <p>输入企业制度相关问题，获取有依据的答案</p>
          <div class="suggestions">
            <button @click="query='研发部实习生采购7000元电脑需要谁审批？'; send()">研发部实习生采购7000元电脑需要谁审批？</button>
            <button @click="query='差旅报销需要准备哪些材料？'; send()">差旅报销需要准备哪些材料？</button>
            <button @click="query='2026版采购制度与2025版相比修改了什么？'; send()">2026版采购制度与2025版相比修改了什么？</button>
          </div>
        </div>
      </div>

      <div v-if="chat.pendingReview" class="review-bar">
        <span>审核 #{{ chat.pendingReview.review_id }} 待处理</span>
        <button @click="approve">批准</button>
        <button @click="reject">拒绝</button>
      </div>

      <div class="chat-input-bar">
        <input v-model="query" @keyup.enter="send" placeholder="输入问题..." :disabled="chat.streaming" />
        <button @click="send" :disabled="chat.streaming">{{ chat.streaming ? '思考中...' : '发送' }}</button>
      </div>
    </main>

    <aside class="chat-evidence">
      <h3>引用来源</h3>
      <div v-for="c in chat.citations" :key="c.id" class="citation-item">[{{ c.id }}]</div>
      <div v-if="chat.citations.length === 0" class="empty-hint">暂无引用</div>

      <h3>图谱路径</h3>
      <div v-for="(p, i) in chat.graphPaths" :key="i" class="path-item">{{ p }}</div>
      <div v-if="chat.graphPaths.length === 0" class="empty-hint">暂无图谱</div>

      <h3>执行时间线</h3>
      <div v-for="(evt, i) in chat.timeline" :key="i" class="event-item">
        <strong>{{ evt.type }}</strong>
        <span v-if="evt.type === 'content'">{{ (evt.data.text as string)?.slice(0, 80) }}</span>
      </div>
      <div v-if="chat.timeline.length === 0" class="empty-hint">等待执行</div>
    </aside>
  </div>
</template>
