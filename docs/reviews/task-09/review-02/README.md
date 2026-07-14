# Task 9 第 2 次审查报告

审查日期：2026-07-14

审查范围：
- `frontend/package.json`
- `frontend/vitest.config.ts`
- `frontend/src/stores/chat.ts`
- `frontend/src/views/{ChatView,ReviewsView}.vue`
- `frontend/src/utils/markdown.ts`
- `frontend/src/__tests__/{router,markdown}.spec.ts`
- 上一轮报告：[task-09/review-01](/D:/policymind/docs/reviews/task-09/review-01/README.md:1)

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## 结论

这轮我判断 **Task 9 暂不通过，但已经非常接近收口**。

和第 1 次审查相比，核心前端能力已经明显补上：

1. Markdown 已接入 `marked + DOMPurify`。
2. Chat 消息已经用安全 HTML 渲染。
3. SSE parser 已经按事件块解析，并把事件写入 `timeline`。
4. ChatView 已改成左中右三栏，能展示会话、问答、引用、Graph Path 和事件时间线。
5. ReviewsView 的 approve 已经会设置对应 `thread_id` 并调用 chat resume。
6. Markdown XSS 测试已补。

现在我还保留两个阻塞点：

1. 文档要求的默认测试命令 `npm test -- --run` 在当前环境失败。
2. Task 9 关键交互测试仍缺：SSE 归并、审核 approve/resume、登录守卫、引用点击。

按简历项目标准，这已经不是大问题，但 Task 9 要正式收口，至少要把默认测试命令和一两条核心交互测试补上。

## 已关闭的问题

### 1. Markdown/DOMPurify 未接入

已关闭。

当前实现：

- [frontend/src/utils/markdown.ts](/D:/policymind/frontend/src/utils/markdown.ts:4) 实现 `renderSafeMarkdown()`。
- [frontend/src/views/ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:43) 使用 `v-html="renderSafeMarkdown(msg.content)"` 渲染。
- [frontend/src/__tests__/markdown.spec.ts](/D:/policymind/frontend/src/__tests__/markdown.spec.ts:10) 覆盖 script 清洗。

### 2. SSE 事件类型丢失

已基本关闭。

当前实现：

- [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:50) 按 `\n\n` 切分 SSE event block。
- [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:60) 解析 `event:`。
- [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:71) 将事件写入 `timeline`。
- [frontend/src/stores/chat.ts](/D:/policymind/frontend/src/stores/chat.ts:73) 按 `content/citation/graph_path/review_required/done` 更新状态。

剩余问题是还没有对应测试。

### 3. Review 页面没有接上 chat resume

已关闭到 demo 可用标准。

当前实现：

- [frontend/src/views/ReviewsView.vue](/D:/policymind/frontend/src/views/ReviewsView.vue:17) approve 接收 `reviewId` 和 `threadId`。
- [frontend/src/views/ReviewsView.vue](/D:/policymind/frontend/src/views/ReviewsView.vue:24) 设置 `chat.threadId = threadId`。
- [frontend/src/views/ReviewsView.vue](/D:/policymind/frontend/src/views/ReviewsView.vue:25) 调用 `chat.resume("approve", auth.token)`。

这条已经能把审核中心和 Task 8 的 resume API 主线接起来。

### 4. Chat 不是三栏工作台

已关闭到 demo 可用标准。

当前实现：

- [frontend/src/views/ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:31) 左侧 sessions。
- [frontend/src/views/ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:39) 中间 chat。
- [frontend/src/views/ChatView.vue](/D:/policymind/frontend/src/views/ChatView.vue:57) 右侧 citations、graph paths、timeline。

这已经足够支撑简历项目演示，不必继续卡视觉细节。

## Findings

### 1. 默认前端测试命令失败

- 严重性：高
- 位置：
  - [frontend/package.json](/D:/policymind/frontend/package.json:9)
  - [frontend/vitest.config.ts](/D:/policymind/frontend/vitest.config.ts:1)

执行文档要求的命令：

```powershell
npm test -- --run
```

结果失败：

```text
Test Files  2 failed (2)
Tests       no tests
Error: Cannot find module '/@fs/D:/policymind/frontend/src/__tests__/markdown.spec.ts'
Error: Cannot find module '/@fs/D:/policymind/frontend/src/__tests__/router.spec.ts'
```

同一套测试用显式 root 可以通过：

```powershell
npm exec vitest -- run --root D:\policymind\frontend
```

结果：

```text
2 passed (2)
6 passed
```

这看起来像 Vitest/Vite 在当前沙箱路径映射下的 root 解析问题，但 Task 9 收口最好让默认脚本也稳定。建议把 test script 或 vitest config 固定 root，例如让 `npm test -- --run` 在本仓库环境直接通过。

### 2. 关键交互测试仍不足

- 严重性：中
- 位置：
  - [frontend/src/__tests__/router.spec.ts](/D:/policymind/frontend/src/__tests__/router.spec.ts:1)
  - [frontend/src/__tests__/markdown.spec.ts](/D:/policymind/frontend/src/__tests__/markdown.spec.ts:1)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:259)

当前测试覆盖：

- auth store 初始状态、设置 token、logout。
- Markdown 渲染和 script 清洗。

仍缺 Task 9 明确要求的：

- 登录守卫测试。
- SSE 事件归并测试。
- 引用点击测试。
- 审核操作测试。

考虑到简历项目口径，不需要每个交互都测得很细，但至少建议补两条：

- `chat-store.spec.ts`：mock SSE stream，验证 `timeline/content/citation/graph_path/review_required/threadId` 都被写入。
- `reviews.spec.ts`：点击 approve 后调用 `/reviews/{id}/approve` 和 `/chat/{thread_id}/resume`。

## 可先忽略的问题

这些不再阻塞 Task 9：

- 视觉设计还偏基础，但已有三栏工作台结构。
- `HelloWorld.vue` 和默认资源仍可后续清理。
- 评测和设置页面可以在 Task 10 或最终打磨阶段补。
- citation 点击目前只是占位函数，后面可以补高亮/原文弹层。

## 验证记录

实际执行：

1. `npm run typecheck`
   - 结果：通过

2. `npm test -- --run`
   - 结果：失败
   - 摘要：`2 failed (2)`，原因是 Vitest 无法从 `/@fs/D:/...` 加载测试模块

3. `npm exec vitest -- run --root D:\policymind\frontend`
   - 结果：通过
   - 摘要：`2 passed (2)`，`6 passed`

4. `npm run build`
   - 结果：通过
   - 摘要：Vite build 成功

## 是否允许进入下一 Task

**暂不建议进入 Task 10。**

建议先做一个很小的收尾：

1. 修正 Vitest 默认测试命令，让 `npm test -- --run` 直接通过。
2. 补一个 SSE 归并测试。
3. 补一个审核 approve/resume 测试。

这三项完成后，我倾向于判断 Task 9 可以按简历项目标准收口。
