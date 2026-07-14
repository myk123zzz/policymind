# Task 9 第 1 次审查报告

审查日期：2026-07-14

审查范围：
- `frontend/package.json`
- `frontend/src/{App.vue,main.ts,style.css}`
- `frontend/src/stores/{auth,chat}.ts`
- `frontend/src/router/index.ts`
- `frontend/src/views/{LoginView,ChatView,DocumentsView,ReviewsView,GraphView}.vue`
- `frontend/src/__tests__/router.spec.ts`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- 上一轮报告：[task-08/review-02](/D:/policymind/docs/reviews/task-08/review-02/README.md:1)

## 结论

这轮我判断 **Task 9 暂不通过**。

先说好消息：Task 9 已经不是空白了。Vue3 + TypeScript + Vite 项目已经建起来，登录页、文档页、聊天页、审核页、图谱页和基础 store/router 都有了，`typecheck/test/build` 也能跑通。

但按简历项目的前端演示标准，现在还差几个会被一眼看出来的闭环：

1. Markdown/DOMPurify 依赖装了，但没有实际用于渲染 LLM Markdown，XSS 测试也没有。
2. SSE 解析没有保留事件类型，也没有真正把事件归并到 `events` 时间线。
3. 审核中心的 approve 只调用 `/reviews/{id}/approve`，没有继续恢复对应 chat thread，和 Task 8 的 HITL resume 主线没有接起来。
4. 当前界面还不是“三栏问答工作台”，引用/Graph Path/Review 状态没有形成一个可演示的工作台布局。
5. 测试只有 auth store 的 3 个基础用例，没有覆盖 Task 9 要求的登录守卫、SSE 归并、引用点击、审核操作和 Markdown XSS。

所以当前可以算 **Task 9 的前端骨架已完成**，但还不能收口进入 Task 10。

## 做得不错的部分

- 已创建 `frontend/package.json`，包含 Vue3、Pinia、Vue Router、Vite、Vitest、DOMPurify、marked。
- 已创建 `LoginView`、`ChatView`、`DocumentsView`、`ReviewsView`、`GraphView`。
- `auth` store 能登录、保存 token、退出。
- 路由守卫已经按 `meta.requiresAuth` 拦截未登录访问。
- `chat` store 使用 `fetch` POST 调 `/api/v1/chat/stream`，没有创建 `EventSource`。
- 前端门禁通过：
  - `npm run typecheck`
  - `npm test -- --run`
  - `npm run build`

## Findings

### 1. Markdown/DOMPurify 没有接入，XSS 验收点缺失

- 严重性：高
- 位置：
  - [frontend/package.json](/D:/policymind/frontend/package.json:17)
  - [frontend/package.json](/D:/policymind/frontend/package.json:18)
  - [frontend/src/views/ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:28)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:261)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:862)

`dompurify` 和 `marked` 已安装，但当前聊天消息使用 `{{ msg.content }}` 纯文本渲染。纯文本不会触发 XSS，但也没有满足“Markdown 使用 DOMPurify”的要求，引用、列表、表格等回答格式也展示不出来。

改进方向：
- 增加 `src/utils/markdown.ts`，实现 `renderSafeMarkdown(source)`。
- Chat 消息用 `v-html="renderSafeMarkdown(msg.content)"` 渲染。
- 补测试：输入 `<script>alert(1)</script> **ok**`，输出不含 script，保留安全 markdown HTML。

### 2. SSE 事件归并不完整，事件类型丢失

- 严重性：高
- 位置：
  - [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:28)
  - [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:55)
  - [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:67)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:259)

当前 parser 看到 `event: ` 时只是把这一行重新塞回 `buffer`，真正处理 `data: ` 时传入的事件类型固定是空字符串。`events` ref 也没有 push。

这会导致：

- 前端无法展示 routing / retrieval / graph_path / review_required / done 时间线。
- 后续引用点击、Graph Path 展示、Review 状态很难从事件流中恢复。
- 测试里也没有覆盖“多条 SSE 事件归并”。

改进方向：
- 把 SSE parser 改成按空行切分 event block。
- 解析 `event:` 和 `data:`，写入 `events.value`。
- 针对 `content`、`citation`、`graph_path`、`review_required`、`done` 分别更新状态。
- 补 `chat.spec.ts`，mock ReadableStream，验证事件归并。

### 3. Review 页面没有接上 chat resume 主线

- 严重性：高
- 位置：
  - [frontend/src/views/ReviewsView.vue](/D:/policymind/frontend/src/views/ReviewsView.vue:14)
  - [frontend/src/views/ReviewsView.vue](/D:/policymind/frontend/src/views/ReviewsView.vue:20)
  - [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:78)

`ChatView` 里的 pending review 可以调用 `chat.resume()`，但 `ReviewsView` 只调用 `/api/v1/reviews/{id}/approve`，没有用 review 的 `thread_id` 去调用 `/api/v1/chat/{thread_id}/resume`。

这意味着从“审核中心”批准后，对话不会自动恢复，和 Task 8 刚收口的 API 演示链路没有完全接上。

改进方向：
- Review item 类型加入 `thread_id`。
- 审核中心 approve 后调用 chat resume 或统一封装 `approveAndResume(review)`。
- 补测试：点击 approve 后应调用 `/reviews/{id}/approve` 和 `/chat/{thread_id}/resume`，并刷新列表。

### 4. 工作台布局和引用/Graph Path 展示还不够

- 严重性：中
- 位置：
  - [frontend/src/views/ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:26)
  - [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:17)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:260)

Task 9 要求“三栏问答、文档/版本、图谱、审核、评测和设置页面”。现在有多个页面，但 Chat 不是三栏工作台：

- 没有左侧会话/文档栏。
- 没有右侧引用、Graph Path、Review 时间线。
- `citations` 只有 id，没有点击行为。
- `graph_path` 事件没有落入 UI。
- 没有评测和设置页面。

按简历项目口径，评测页可等 Task 10，但 Chat 工作台至少应该能把引用、图谱路径和审核状态摆出来。

改进方向：
- ChatView 改成三栏：左侧会话/文档，中间问答，右侧 citations / graph paths / review。
- citation id 可点击并高亮或展示原文。
- graph_path 事件进入右侧面板。

### 5. 测试覆盖不符合 Task 9 要求

- 严重性：中
- 位置：
  - [frontend/src/__tests__/router.spec.ts](/D:/policymind/frontend/src/__tests__/router.spec.ts:1)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:259)

当前测试文件名叫 `router.spec.ts`，但内容只测 auth store：

- starts unauthenticated
- sets token
- logout clears token

缺少 Task 9 明确要求的：

- 登录守卫测试。
- SSE 事件归并测试。
- 引用点击测试。
- 审核操作测试。
- Markdown XSS 测试。

改进方向：
- 增加 `router.spec.ts` 真正测试未登录跳转。
- 增加 `chat-store.spec.ts` 测 SSE 归并。
- 增加 `markdown.spec.ts` 测 DOMPurify。
- 增加 `reviews.spec.ts` 测 approve/resume。

## 可先忽略的问题

这些不建议在第一轮继续卡：

- `HelloWorld.vue`、Vite/Vue 默认资源还没清理，后面整理 UI 时顺手删。
- 评测页面可以等 Task 10 后再接真实数据。
- 图谱可以先用列表或计数展示，不必第一轮就做复杂可视化。
- 视觉设计目前偏脚手架风格，但先把工作流打通更重要。

## 验证记录

实际执行：

1. `npm run typecheck`
   - 结果：通过

2. `npm test -- --run`
   - 结果：通过
   - 摘要：`1 passed (1)`，`3 passed`

3. `npm run build`
   - 结果：通过
   - 摘要：Vite build 成功，生成 `dist`

## 是否允许进入下一 Task

**暂不建议进入 Task 10。**

建议先补一轮小闭环：

1. 接入 `renderSafeMarkdown()`，用 DOMPurify 清洗 Markdown。
2. 重写 SSE parser，保留事件类型并归并到 timeline。
3. ChatView 做成简洁三栏：会话/问答/引用与审核。
4. ReviewsView 批准后能 resume 对应 thread。
5. 补登录守卫、SSE、Markdown XSS、审核操作测试。

补完这几项后，Task 9 就可以按简历项目标准收口。
