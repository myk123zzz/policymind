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
  const events = ref<SSEEvent[]>([]);
  const citations = ref<{ id: string; text: string }[]>([]);
  const pendingReview = ref<{ review_id: number } | null>(null);
  const streaming = ref(false);
  const threadId = ref<string | null>(null);

  async function sendQuery(query: string, token: string) {
    streaming.value = true;
    messages.value.push({ role: "user", content: query });
    const assistantMsg: ChatMessage = { role: "assistant", content: "" };
    messages.value.push(assistantMsg);

    try {
      const resp = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
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
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            buffer = line + "\n" + buffer;
            continue;
          }
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              handleSSE(assistantMsg, { type: "", data } as SSEEvent);
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

  function handleSSE(msg: ChatMessage, event: SSEEvent) {
    const d = event.data;
    if (d.text) msg.content += d.text;
    if (d.review_id) pendingReview.value = { review_id: Number(d.review_id) };
    if (d.thread_id) threadId.value = String(d.thread_id);
    if (d.ids) citations.value = (d.ids as string[]).map((id: string) => ({ id, text: "" }));
  }

  async function resume(decision: string, token: string) {
    if (!threadId.value) return;
    const resp = await fetch(`/api/v1/chat/${threadId.value}/resume`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ decision }),
    });
    if (resp.ok) {
      const data = await resp.json();
      messages.value.push({ role: "assistant", content: data.draft_answer || "Approved." });
      pendingReview.value = null;
    }
  }

  return { messages, events, citations, pendingReview, streaming, threadId, sendQuery, resume };
});
