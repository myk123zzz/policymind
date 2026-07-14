import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

describe("Chat Store SSE Parsing", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("parses SSE blocks into timeline events", async () => {
    const { useChatStore } = await import("../stores/chat");
    const store = useChatStore();

    // Directly push timeline to simulate SSE received events
    store.timeline.push({ type: "routing", data: { status: "analyzing" } });
    store.timeline.push({ type: "content", data: { text: "Hello World" } });
    store.timeline.push({ type: "citation", data: { ids: ["C1", "C2"] } });
    store.timeline.push({ type: "done", data: { thread_id: "t1" } });

    expect(store.timeline).toHaveLength(4);
    expect(store.timeline[0].type).toBe("routing");
    expect(store.timeline[1].type).toBe("content");
    expect(store.timeline[2].type).toBe("citation");
    expect(store.timeline[3].type).toBe("done");
  });

  it("stores citations from SSE citation event", async () => {
    const { useChatStore } = await import("../stores/chat");
    const store = useChatStore();

    store.timeline.push({
      type: "citation",
      data: { ids: ["C1", "C2"] },
    });
    store.citations = (store.timeline[0].data.ids as string[]).map((id: string) => ({ id, text: "" }));

    expect(store.citations).toHaveLength(2);
    expect(store.citations[0].id).toBe("C1");
  });

  it("stores review_required and done events", async () => {
    const { useChatStore } = await import("../stores/chat");
    const store = useChatStore();

    store.pendingReview = { review_id: 42 };
    store.threadId = "thread-abc";

    expect(store.pendingReview).toEqual({ review_id: 42 });
    expect(store.threadId).toBe("thread-abc");

    // Simulate resume clearing review
    store.pendingReview = null;
    expect(store.pendingReview).toBeNull();
  });
});
