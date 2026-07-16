<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const docs = ref<{ id: number; logical_name: string }[]>([]);
const uploading = ref(false);

async function loadDocs() {
  const resp = await fetch("/api/v1/documents", { headers: { Authorization: `Bearer ${auth.token}` } });
  if (resp.ok) docs.value = await resp.json();
}

async function uploadFile(file: File) {
  uploading.value = true;
  const form = new FormData();
  form.append("file", file);
  await fetch("/api/v1/documents", {
    method: "POST", headers: { Authorization: `Bearer ${auth.token}` }, body: form,
  });
  await loadDocs();
  uploading.value = false;
}

onMounted(loadDocs);
</script>

<template>
  <div class="documents-page">
    <h2>制度文档管理</h2>
    <label class="upload-btn">
      {{ uploading ? '上传中...' : '上传制度文件' }}
      <input type="file" @change="(e) => {
        const f = (e.target as HTMLInputElement).files?.[0];
        if (f) uploadFile(f);
      }" accept=".pdf,.docx,.xlsx,.md,.txt" />
    </label>
    <p class="hint">支持 PDF、Word、Excel、Markdown 格式</p>
    <ul>
      <li v-for="d in docs" :key="d.id">{{ d.logical_name }}</li>
    </ul>
    <p v-if="docs.length === 0" class="empty-hint">暂无制度文档，请上传</p>
  </div>
</template>

<style scoped>
.upload-btn {
  display: inline-block; padding: 10px 24px; background: var(--primary, #2563eb);
  color: #fff; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px;
}
.upload-btn input { display: none; }
.hint { color: var(--text-secondary, #64748b); font-size: 13px; margin: 8px 0 20px; }
</style>
