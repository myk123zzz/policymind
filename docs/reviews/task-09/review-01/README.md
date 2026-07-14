# Task 9 第 1 次审查报告

审查日期：2026-07-14

审查范围：
- `frontend/`
- `docs/policymind/2026-07-01-policymind-implementation.md`
- `docs/policymind/DEVELOPMENT_GUIDE.md`
- `docs/reviews/task-08/review-02/README.md`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- 上一轮报告：[task-08/review-02](/D:/policymind/docs/reviews/task-08/review-02/README.md:1)

## 结论

这轮我判断 **Task 9 暂不通过**。

原因很直接：当前仓库里还没有 `frontend/` 目录，Task 9 要求的 Vue3 工作台还没有开始落地。

按简历项目口径，不需要第一轮就做成完整生产级前端，但至少需要一个可运行的 Vue3/Vite 工作台，能演示：

1. 登录守卫。
2. 三栏问答界面。
3. fetch POST 方式消费 SSE，不使用重复 `EventSource`。
4. 引用、Graph Path、Review 状态的基础展示。
5. HITL 审核批准/拒绝操作。
6. Markdown 使用 DOMPurify 清洗。

现在这些文件和测试都不存在，所以不能进入 Task 10。

## Findings

### 1. `frontend/` 工作台目录不存在

- 严重性：高
- 位置：
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:247)
  - 仓库根目录：未发现 `frontend/`

Task 9 明确要求创建：

- `frontend/package.json`
- `frontend/src/api/`
- `frontend/src/stores/`
- `frontend/src/router/`
- `frontend/src/views/`
- `frontend/src/components/`
- `frontend/src/**/*.spec.ts`

当前这些都不存在。

改进方向：
- 初始化 Vue3 + TypeScript + Vite 项目。
- 建立 Pinia、Vue Router、Vitest 基础配置。
- 至少补一个可运行的 app shell，而不是只放空目录。

### 2. Task 9 核心交互还没有实现

- 严重性：高
- 位置：
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:259)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:850)

Task 9 的演示价值在前端闭环：

- 登录后进入工作台。
- 左侧文档/会话，中间问答，右侧引用/图谱/审核。
- `/api/v1/chat/stream` 通过 fetch POST 读取 ReadableStream。
- `review_required` 出现后能展示审核卡片。
- 用户批准后调用 `/api/v1/chat/{thread_id}/resume` 并显示恢复结果。

当前没有任何前端代码能承接 Task 8 已经收口的 API。

改进方向：
- 实现 `src/api/client.ts`：token 注入、错误处理。
- 实现 `src/api/streamChat.ts`：仅使用 fetch POST 读取 SSE。
- 实现 `src/stores/auth.ts` 和 `src/stores/chat.ts`。
- 实现 `LoginView`、`WorkspaceView`、`DocumentsView`、`GraphView`、`ReviewsView`。

### 3. 前端安全测试尚未建立

- 严重性：中
- 位置：
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:259)

Task 9 要求先测试：

- 登录守卫。
- SSE 事件归并。
- 引用点击。
- 审核操作。
- Markdown XSS。

当前没有 `frontend/src/**/*.spec.ts`，也没有 Vitest 配置。

改进方向：
- 用 Vitest + Vue Test Utils 建立最小测试。
- 至少覆盖：
  - 未登录访问工作台跳转登录。
  - `streamChat()` 能归并 `routing/content/review_required/done`。
  - Markdown 中 `<script>` 被 DOMPurify 清掉。
  - 点击 approve 会调用 resume API。

## 可先忽略的问题

这些不建议在第一轮 Task 9 阻塞：

- Playwright E2E 可以晚一点补。
- 评测页面可以先放一个占位页，等 Task 10 后接真实数据。
- 图谱可视化可以先用列表或简单 SVG/HTML 表示，不必第一轮就接 Cytoscape。
- 设计细节可以先保持简洁，但必须能跑通核心操作。

## 验证记录

实际检查：

1. `Test-Path frontend`
   - 结果：`False`

2. `rg --files frontend`
   - 结果：没有文件

3. 未执行前端门禁：
   - `npm run typecheck`
   - `npm test -- --run`
   - `npm run build`

原因：当前没有 `frontend/package.json`，前端项目尚未初始化。

## 是否允许进入下一 Task

**不允许进入 Task 10。**

建议先补一个最小可演示前端：

1. 初始化 Vue3 + TypeScript + Vite。
2. 做登录页和路由守卫。
3. 做三栏问答工作台。
4. 用 fetch POST 接 `/api/v1/chat/stream`。
5. 展示 `review_required` 并调用 resume。
6. Markdown 用 DOMPurify。
7. 补 Vitest 测试和 `typecheck/test/build` 门禁。

这几项完成后，Task 9 就可以按简历项目标准复审收口。
