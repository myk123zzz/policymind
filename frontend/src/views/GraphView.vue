<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const seed = ref("");
const result = ref<{ nodes: unknown[]; edges: unknown[] }>({ nodes: [], edges: [] });

async function search() {
  const resp = await fetch(`/api/v1/graph/subgraph?seed_ids=${encodeURIComponent(seed.value)}`, {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  if (resp.ok) result.value = await resp.json();
}
</script>

<template>
  <div class="graph-page">
    <h2>Knowledge Graph</h2>
    <input v-model="seed" placeholder="Entity ID" @keyup.enter="search" />
    <button @click="search">Search</button>
    <div>Nodes: {{ result.nodes.length }}, Edges: {{ result.edges.length }}</div>
  </div>
</template>
