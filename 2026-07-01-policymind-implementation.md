# PolicyMind Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零构建可上传企业制度、执行 Hybrid RAG/GraphRAG、多 Agent 与 MCP 工具调用，并提供引用、HITL 和自动评测的完整系统。

**Architecture:** Python 后端采用 `src` 布局和端口/适配器结构，领域服务不直接依赖 Milvus、Neo4j、Redis 或模型厂商；测试使用内存适配器，生产适配器通过相同 Protocol 接入基础设施。LangGraph 只负责编排，文档、权限、检索、引用、图谱与工具执行保持可独立测试。

**Tech Stack:** Python 3.12、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、LangChain、LangGraph、PostgreSQL、Redis/ARQ、Milvus、Neo4j、FastMCP、Vue3、TypeScript、Vite、pytest、Vitest、Playwright。

---

## 0. 执行规则

- 不读取或复制旧项目源码。
- 每个新行为必须先写测试并观察预期失败。
- 每一阶段必须形成可运行纵向切片，禁止用空目录或固定返回值冒充实现。
- 所有数据边界强制携带 `tenant_id`、`user_id`、`access_level` 和查询时间。
- Docker 是可选的依赖启动方式；后端与前端支持本机运行。
- 每个阶段验证通过后单独提交 Git。

## 1. 目录与职责

```text
D:\project
├── backend/
│   ├── src/policymind/
│   │   ├── api/                  # FastAPI 路由、依赖、SSE
│   │   ├── core/                 # 配置、错误、日志、遥测
│   │   ├── auth/                 # JWT、RBAC、用户/租户
│   │   ├── documents/            # 上传、版本、解析、分块、任务
│   │   ├── retrieval/            # Embedding、Hybrid、RRF、Rerank、引用
│   │   ├── graph/                # Ontology、抽取、Neo4j、GraphRAG
│   │   ├── agents/               # Supervisor/Planner/Executor/Critic
│   │   ├── mcp/                  # MCP Client/Server、工具策略
│   │   ├── conversations/        # 会话、Checkpoint、HITL
│   │   ├── evaluation/           # 指标、Runner、报告
│   │   └── infrastructure/       # PostgreSQL/Milvus/Neo4j/Redis/S3/LLM
│   ├── migrations/versions/
│   └── tests/
├── frontend/src/
│   ├── api/
│   ├── components/
│   ├── stores/
│   ├── views/
│   ├── router/
│   └── types/
├── evaluation/
│   ├── datasets/
│   ├── baselines/
│   └── reports/
├── deploy/
│   ├── grafana/
│   └── docker/
├── scripts/
└── docs/
```

## Task 1：工程骨架与质量门禁

**Files**

- Create: `backend/pyproject.toml`
- Create: `backend/src/policymind/__init__.py`
- Create: `backend/src/policymind/main.py`
- Create: `backend/tests/test_smoke.py`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`

- [ ] 写失败测试：

```python
def test_package_and_health(client):
    import policymind

    assert policymind.__version__ == "0.1.0"
    assert client.get("/health/live").json() == {"status": "ok"}
```

- [ ] 运行并确认因包/应用不存在而失败：

```powershell
cd D:\project\backend
uv run pytest tests/test_smoke.py -q
```

- [ ] 实现最小包、`create_app()`、liveness；配置 Ruff、mypy、pytest。
- [ ] 验证：

```powershell
uv run pytest
uv run ruff check src tests
uv run mypy src
```

- [ ] Commit：`chore: bootstrap policymind`

## Task 2：配置、数据库、认证与租户边界

**Files**

- Create: `backend/src/policymind/core/{config,errors,logging}.py`
- Create: `backend/src/policymind/infrastructure/postgres/{base,session}.py`
- Create: `backend/src/policymind/auth/{models,schemas,security,service,router}.py`
- Create: `backend/migrations/versions/0001_foundation.py`
- Test: `backend/tests/auth/`

- [ ] 先测试：生产环境拒绝默认 JWT Secret；禁用用户 Token 立即失效；注册请求不能自行指定租户。
- [ ] 实现 PostgreSQL 模型、Alembic、Argon2id、短期 Access Token、Refresh Token 撤销、RBAC。
- [ ] 用户名唯一约束采用 `(tenant_id, username)`；认证依赖每次查询用户状态。
- [ ] 验证迁移可重复执行，跨租户测试全部通过。
- [ ] Commit：`feat: add tenant-safe authentication`

关键测试：

```python
def test_disabled_user_cannot_reuse_token(client, disabled_user, token):
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
```

## Task 3：文档版本、对象存储、解析与父子分块

**Files**

- Create: `backend/src/policymind/documents/models.py`
- Create: `backend/src/policymind/documents/storage.py`
- Create: `backend/src/policymind/documents/validation.py`
- Create: `backend/src/policymind/documents/parsers/`
- Create: `backend/src/policymind/documents/chunking.py`
- Create: `backend/migrations/versions/0002_documents.py`
- Test: `backend/tests/documents/`

- [ ] 先测试扩展名/文件魔数不一致、同哈希幂等、多版本生效区间、表格表头不被拆散。
- [ ] 实现 PDF、DOCX、XLSX、Markdown Parser；图片通过 OCR Protocol，复杂表格/流程图通过 VLM Protocol。
- [ ] 提供 `LocalObjectStorage` 与 `S3ObjectStorage`，存储 Key 必须随机生成。
- [ ] Parent 1000～1600 字，Leaf 300～500 字，Leaf 强制引用 Parent、页码和 bbox。
- [ ] Commit：`feat: add versioned multimodal documents`

关键测试：

```python
def test_leaf_chunks_keep_provenance(chunker, parsed_document):
    leaves = [c for c in chunker.chunk(parsed_document) if c.level == "leaf"]
    assert all(c.parent_id and c.page_number and c.source_version_id for c in leaves)
```

## Task 4：摄取任务与上传到可检索纵向链路

**Files**

- Create: `backend/src/policymind/documents/pipeline.py`
- Create: `backend/src/policymind/documents/jobs.py`
- Create: `backend/src/policymind/documents/router.py`
- Create: `backend/src/policymind/infrastructure/redis/jobs.py`
- Test: `backend/tests/documents/test_pipeline.py`

- [ ] 先写 E2E 测试：上传 Markdown，等待任务完成，随后检索必须命中其内容。
- [ ] 实现阶段状态：

```text
stored → parsed → chunked → embedded → vector_indexed → graph_indexed → ready
```

- [ ] PostgreSQL 是状态事实来源；每阶段幂等，可从失败阶段重试。
- [ ] 测试使用 inline runner，生产使用 ARQ，二者共享同一 Pipeline。
- [ ] Commit：`feat: connect upload to knowledge indexes`

## Task 5：Milvus Hybrid RAG 与可验证引用

**Files**

- Create: `backend/src/policymind/retrieval/{ports,embeddings,fusion,rerank,parent_expansion,citations,service}.py`
- Create: `backend/src/policymind/infrastructure/milvus/store.py`
- Test: `backend/tests/retrieval/`

- [ ] 先写共享 Contract Test，内存和 Milvus 适配器必须通过同一组租户、权限和时间过滤测试。
- [ ] Embedding 失败抛出 `EmbeddingUnavailable`，禁止返回零向量。
- [ ] Dense Top30 + BM25 Top30 → RRF Top30 → 批量 Rerank Top8 → Parent Expansion。
- [ ] 引用包含文件、版本、页码、bbox、原文、渠道；回答中的未知 `[Cxx]` 必须被识别。
- [ ] Commit：`feat: add secure hybrid rag`

关键测试：

```python
def test_rrf_promotes_dual_channel_hit():
    result = rrf_fuse([hit("a"), hit("b")], [hit("b"), hit("c")], k=60)
    assert result[0].chunk_id == "b"
```

## Task 6：Neo4j GraphRAG

**Files**

- Create: `backend/src/policymind/graph/{ontology,extraction,repository,search,path_ranker,context}.py`
- Create: `backend/src/policymind/infrastructure/neo4j/repository.py`
- Test: `backend/tests/graph/`

- [ ] 先测试关系端点、Ontology 白名单、来源绑定、租户隔离和1～3跳路径。
- [ ] 保留 Regex JSON 提取，再经过 JSON、Pydantic、Ontology 和来源校验。
- [ ] 每个节点/关系保存 `tenant_id`、`source_document_version_id`、`confidence`。
- [ ] Path Ranker 综合 Query 匹配、置信度、版本和路径长度；上下文必须展示关系类型与引用。
- [ ] Commit：`feat: add sourced local graphrag`

## Task 7：真实 MCP、LangGraph 与 HITL

**Files**

- Create: `backend/src/policymind/mcp/{server,client,tools,policy}.py`
- Create: `backend/src/policymind/agents/{state,json_parser,supervisor,planner,executor,synthesizer,critic,graph}.py`
- Create: `backend/src/policymind/agents/prompts/`
- Create: `backend/src/policymind/conversations/{models,service,router,checkpoint}.py`
- Test: `backend/tests/{mcp,agents,conversations}/`

- [ ] 先测试真实 MCP Transport 能列出/调用工具；写工具没有审批 Token 时必须抛出 `ApprovalRequired`。
- [ ] 实现五个工具：员工、审批链、材料、制度版本、审核工单。
- [ ] LangGraph 拓扑必须包含：

```text
Supervisor → Retrieval|Graph|Planner
Planner → Executor
Executor → Executor|Synthesizer
Synthesizer → Critic
Critic → END|Replan|Interrupt
Replan → Planner
```

- [ ] 使用 PostgreSQL Checkpointer；恢复使用相同 `thread_id` 和 `Command(resume=...)`。
- [ ] SSE 只发送公开事件，不转发 Supervisor/Planner 隐藏推理或中间模型 Token。
- [ ] Commit：`feat: add multi-agent mcp and hitl`

## Task 8：FastAPI 完整接口与安全

**Files**

- Create: `backend/src/policymind/api/dependencies.py`
- Create: `backend/src/policymind/api/v1/{auth,documents,chat,reviews,graph,evaluations}.py`
- Test: `backend/tests/api/`

- [ ] 按设计文档实现全部路由、响应 Schema 和 SSE 事件。
- [ ] 先测试匿名访问、跨租户资源、超大文件、伪造 MIME、Prompt Injection 与限流。
- [ ] `/health/ready` 在必要依赖不可用时返回503，不能偷偷降级成“健康”。
- [ ] 对话响应必须返回引用、Agent Trace、Graph Path 和 Review 状态。
- [ ] Commit：`feat: expose secure policymind api`

## Task 9：Vue3 工作台

**Files**

- Create: `frontend/package.json`
- Create: `frontend/src/api/`
- Create: `frontend/src/stores/`
- Create: `frontend/src/router/`
- Create: `frontend/src/views/`
- Create: `frontend/src/components/`
- Test: `frontend/src/**/*.spec.ts`

- [ ] 先测试登录守卫、SSE 事件归并、引用点击、审核操作和 Markdown XSS。
- [ ] 实现登录、三栏问答、文档/版本、图谱、审核、评测和设置页面。
- [ ] Markdown 使用 DOMPurify；SSE 只保留 fetch POST 实现，不创建重复 EventSource。
- [ ] 验证：

```powershell
npm run typecheck
npm test -- --run
npm run build
```

- [ ] Commit：`feat: add policymind web workspace`

## Task 10：评测、观测、部署与交付

**Files**

- Create: `evaluation/datasets/golden_v1.jsonl`
- Create: `backend/src/policymind/evaluation/`
- Create: `backend/src/policymind/core/telemetry.py`
- Create: `deploy/compose.infrastructure.yml`
- Create: `deploy/compose.full.yml`
- Create: `deploy/docker/`
- Create: `scripts/run_evaluation.py`
- Create: `docs/runbook.md`
- Test: `backend/tests/{evaluation,e2e}/`

- [ ] 建立不少于120题的数据集，覆盖事实、跨文档、关系、版本、多模态、拒答、注入和越权。
- [ ] 实现 Recall@K、MRR、NDCG、Citation、Graph Path、Routing、Tool、Faithfulness、延迟和成本指标。
- [ ] 同一数据/模型/Prompt 下运行 Dense、Hybrid、+Rerank、+Graph、完整 Agent 消融实验。
- [ ] OpenTelemetry 覆盖 API、摄取、检索、图谱、Agent 和 MCP；Prometheus 暴露关键指标。
- [ ] Docker Compose 提供可选基础设施版和完整部署版。
- [ ] 最终验证：

```powershell
cd D:\project\backend
uv run ruff check src tests
uv run mypy src
uv run pytest -m "not integration" --cov=policymind
uv run pytest -m integration

cd D:\project\frontend
npm run typecheck
npm test -- --run
npm run build
```

- [ ] Commit：`chore: prepare policymind release`

## 阶段验收顺序

1. 工程能启动、测试门禁可用。
2. 身份、租户和数据库可信。
3. 所有文档格式能产生带来源 Chunk。
4. 上传内容重启后仍可检索。
5. Hybrid RAG 给出可验证引用。
6. GraphRAG 给出带关系和来源的路径。
7. Multi-Agent 执行完整计划，MCP 写操作必须 HITL。
8. API 与前端完成端到端操作。
9. 评测证明各模块增益。
10. 可选 Docker 部署和本机运行均有 Runbook。
