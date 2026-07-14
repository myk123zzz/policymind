import { defineStore } from "pinia";
import { ref } from "vue";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SSEEvent {
  type: string;
  data: Record<string, unknown>;
}

export const useChatStore = defineStore("chat", () => {
  const messages = ref<ChatMessage[]>([]);
  const timeline = ref<SSEEvent[]>([]);
  const citations = ref<{ id: string; text: string }[]>([]);
  const graphPaths = ref<string[]>([]);
  const pendingReview = ref<{ review_id: number } | null>(null);
  const streaming = ref(false);
  const threadId = ref<string | null>(null);

  async function sendQuery(query: string, token: string) {
    streaming.value = true;
    timeline.value = [];
    citations.value = [];
    graphPaths.value = [];
    messages.value.push({ role: "user", content: query });
    const assistantMsg: ChatMessage = { role: "assistant", content: "" };
    messages.value.push(assistantMsg);

    try {
      const resp = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ query, thread_id: threadId.value }),
      });
      if (!resp.ok || !resp.body) throw new Error("Stream failed");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Split by double newline (SSE event boundary)
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          if (!block.trim()) continue;
          const lines = block.split("\n");
          let eventType = "message";
          let dataStr = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.slice(6);
            }
          }

          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              const evt: SSEEvent = { type: eventType, data };
              timeline.value.push(evt);

              if (eventType === "content" && data.text) {
                assistantMsg.content += data.text;
              } else if (eventType === "citation" && data.ids) {
                citations.value = (data.ids as string[]).map((id) => ({ id, text: "" }));
              } else if (eventType === "graph_path" && data.ref) {
                graphPaths.value.push(String(data.ref));
              } else if (eventType === "review_required" && data.review_id) {
                pendingReview.value = { review_id: Number(data.review_id) };
              } else if (eventType === "done" && data.thread_id) {
                threadId.value = String(data.thread_id);
              }
            } catch {
              // skip invalid JSON
            }
          }
        }
      }
    } finally {
      streaming.value = false;
    }
  }

  async function resume(decision: string, token: string) {
    if (!threadId.value) return;
    const resp = await fetch(`/api/v1/chat/${threadId.value}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ decision }),
    });
    if (resp.ok) {
      const data = await resp.json();
      if (data.draft_answer) {
        messages.value.push({ role: "assistant", content: data.draft_answer });
      }
      pendingReview.value = null;
    }
  }

  return { messages, timeline, citations, graphPaths, pendingReview, streaming, threadId, sendQuery, resume };
});
