<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const docs = ref<{ id: number; logical_name: string }[]>([]);

async function loadDocs() {
  const resp = await fetch("/api/v1/documents", {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  if (resp.ok) docs.value = await resp.json();
}

async function uploadFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch("/api/v1/documents", {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.token}` },
    body: form,
  });
  if (resp.ok) await loadDocs();
}

onMounted(loadDocs);
</script>

<template>
  <div class="documents-page">
    <h2>Documents</h2>
    <input type="file" @change="(e) => {
      const f = (e.target as HTMLInputElement).files?.[0];
      if (f) uploadFile(f);
    }" />
    <ul>
      <li v-for="d in docs" :key="d.id">{{ d.logical_name }}</li>
    </ul>
  </div>
</template>
