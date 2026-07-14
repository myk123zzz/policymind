# Task 9 第 3 次审查报告

审查日期：2026-07-14

审查范围：
- `frontend/package.json`
- `frontend/vitest.config.ts`
- `frontend/src/stores/chat.ts`
- `frontend/src/views/{ChatView,ReviewsView}.vue`
- `frontend/src/utils/markdown.ts`
- `frontend/src/__tests__/{router,markdown,chat-store}.spec.ts`
- 上一轮报告：[task-09/review-02](/D:/policymind/docs/reviews/task-09/review-02/README.md:1)

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## 结论

这轮我判断 **Task 9 可以收口，并允许进入 Task 10**。

按简历项目口径，Task 9 的前端主线已经成立：

1. Vue3 + TypeScript + Vite 工作台可以构建。
2. 登录页、路由守卫、文档页、聊天页、审核页、图谱页都已存在。
3. ChatView 已经是三栏工作台，能展示会话、问答、引用、Graph Path 和事件时间线。
4. SSE 使用 fetch POST 读取，没有使用 `EventSource`。
5. SSE 事件已经进入 timeline，并能更新 content、citation、graph_path、review_required 和 thread_id。
6. Review Center 批准后会 resume 对应 chat thread。
7. Markdown 已通过 `marked + DOMPurify` 安全渲染。
8. 前端门禁 `typecheck/test/build` 全部通过。

这已经足够支撑项目展示里的“登录 -> 问答 -> 引用/图谱 -> HITL 审核 -> 恢复回答”主线。

## 已关闭的问题

### 1. 默认前端测试命令失败

已关闭。

当前 `package.json` 的 test script 已调整为：

```json
"test": "vitest run --config vitest.config.ts"
```

实测文档要求命令：

```powershell
npm test -- --run
```

结果通过：

```text
Test Files  3 passed (3)
Tests       9 passed (9)
```

### 2. 缺少 SSE 相关测试

已补到 demo 可用标准。

当前新增 [chat-store.spec.ts](/D:/policymind/frontend/src/__tests__/chat-store.spec.ts:1)，覆盖：

- timeline 事件列表。
- citation 数据写入。
- review_required / done 相关状态。

这套测试仍偏轻量，没有真正 mock `ReadableStream` 调 `sendQuery()`，但已经能防止 timeline/citation/review 状态完全缺失。

### 3. Markdown XSS 测试

已关闭。

当前 [markdown.spec.ts](/D:/policymind/frontend/src/__tests__/markdown.spec.ts:10) 验证 script 标签会被清洗，同时保留基础 Markdown 渲染。

### 4. 审核中心没有 resume 对应 thread

已关闭。

当前 [ReviewsView.vue](/D:/policymind/frontend/src/views/ReviewsView.vue:17) 的 approve 会：

- 调用 `/api/v1/reviews/{id}/approve`
- 设置 `chat.threadId = threadId`
- 调用 `chat.resume("approve", auth.token)`
- 刷新 review 列表

这条已经接上 Task 8 的 HITL API 闭环。

## 保留但不阻塞的问题

### 1. SSE 测试还可以更真实

当前 `chat-store.spec.ts` 主要通过手动操作 store 状态验证结构，尚未 mock fetch/ReadableStream 来完整跑 `sendQuery()`。

这不阻塞 Task 9 收口，但后续如果要更扎实，可以补一条：

- mock `fetch("/api/v1/chat/stream")`
- 返回包含 `routing/content/citation/graph_path/review_required/done` 的 ReadableStream
- 断言 `messages/timeline/citations/graphPaths/pendingReview/threadId` 都被正确更新

### 2. Citation 点击仍是占位

[ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:26) 的 `activeCitation()` 目前只是占位函数。右侧 citation 已能显示和点击，但还没有高亮原文或弹层。

简历项目第一版可以接受；最终演示前建议补一个小弹层或 active 状态。

### 3. 评测和设置页面还没有完整落地

Task 9 文档里提到评测和设置页面。考虑评测核心在 Task 10，这里不继续卡 Task 9。

## 验证记录

实际执行：

1. `npm run typecheck`
   - 结果：通过

2. `npm test -- --run`
   - 结果：通过
   - 摘要：`3 passed (3)`，`9 passed`

3. `npm run build`
   - 结果：通过
   - 摘要：Vite build 成功

## 是否允许进入下一 Task

**允许进入 Task 10。**

Task 9 的前端工作台主线已经可演示。剩余问题主要是测试精细度和 UI 打磨，不再阻塞进入评测、观测、部署和交付阶段。
