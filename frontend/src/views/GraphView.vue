<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const seed = ref("");
const result = ref<{ nodes: { id: string; type: string; name: string }[]; edges: { source: string; target: string; type: string }[] }>({ nodes: [], edges: [] });

async function search() {
  const resp = await fetch(`/api/v1/graph/subgraph?seed_ids=${encodeURIComponent(seed.value)}`, {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  if (resp.ok) result.value = await resp.json();
}
</script>

<template>
  <div class="graph-page">
    <h2>企业知识图谱</h2>
    <div class="search-row">
      <input v-model="seed" placeholder="输入实体ID，如 p1, d1" @keyup.enter="search" />
      <button @click="search">搜索</button>
    </div>
    <div class="graph-result">
      <div class="graph-stats">
        <span>节点 {{ result.nodes.length }}</span>
        <span>关系 {{ result.edges.length }}</span>
      </div>
      <div class="node-list" v-if="result.nodes.length">
        <div v-for="n in result.nodes" :key="n.id" class="node-card">
          <span class="node-type">{{ n.type }}</span>
          <span class="node-name">{{ n.name }}</span>
        </div>
      </div>
      <div v-if="result.edges.length" class="edge-list">
        <div v-for="(e, i) in result.edges" :key="i" class="edge-item">
          {{ e.source }} → {{ e.target }} <span class="edge-type">{{ e.type }}</span>
        </div>
      </div>
      <p v-if="!result.nodes.length && !seed" class="empty-hint">输入实体ID搜索图谱关系</p>
    </div>
  </div>
</template>

<style scoped>
.search-row { display: flex; gap: 10px; margin-bottom: 24px; }
.graph-stats { display: flex; gap: 20px; margin-bottom: 16px; font-weight: 500; color: var(--text-secondary, #64748b); }
.node-card { display: flex; gap: 12px; padding: 10px 16px; background: var(--surface, #fff); border: 1px solid var(--border, #e2e8f0); border-radius: 8px; margin-bottom: 8px; }
.node-type { background: var(--primary-light, #eff6ff); color: var(--primary, #2563eb); padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.node-name { font-weight: 500; }
.edge-item { padding: 8px 14px; background: var(--surface, #fff); border: 1px solid var(--border, #e2e8f0); border-radius: 6px; margin-bottom: 6px; font-size: 13px; }
.edge-type { background: #f0fdf4; color: #16a34a; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 8px; }
</style>
