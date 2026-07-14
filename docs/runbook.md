# PolicyMind 运行手册

## 环境要求

- Python 3.12+
- Node.js 20+
- Docker (可选，用于启动基础设施)

## 快速启动（开发模式）

### 1. 启动基础设施

```bash
# 方式 A: Docker Compose
docker compose -f deploy/compose.infrastructure.yml up -d

# 方式 B: 本机安装
# 需要安装并启动 PostgreSQL、Redis、Milvus、Neo4j、MinIO
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际的 LLM API key 等信息
```

### 3. 启动后端

```bash
cd backend
uv sync --all-extras
uv run alembic upgrade head
uv run uvicorn policymind.main:app --reload
```

### 4. 启动前端

```bash
cd frontend
npm ci
npm run dev
```

### 5. 访问应用

- 前端: http://localhost:5173
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health/live

## 运行测试

### 后端

```bash
cd backend
uv run pytest                                      # 单元测试
uv run pytest -m "not integration"                 # 跳过集成测试
uv run pytest -m integration                       # 仅集成测试
uv run ruff check src tests                        # Lint
uv run mypy src                                     # 类型检查
```

### 前端

```bash
cd frontend
npm run typecheck                                   # TypeScript 检查
npm test -- --run                                  # 单元测试
npm run build                                      # 生产构建
```

### 评测

```bash
python scripts/run_evaluation.py
python scripts/run_evaluation.py --dataset evaluation/datasets/golden_v1.jsonl
python scripts/run_evaluation.py --output evaluation/reports/report.json
```

## 生产部署

```bash
# 完整部署（含应用 + 基础设施）
docker compose -f deploy/compose.infrastructure.yml -f deploy/compose.full.yml up -d

# 初始化数据库
docker compose exec api alembic upgrade head
```

## 监控

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- MinIO Console: http://localhost:9001

## 架构概览

```
用户 (Vue3 Frontend)
  → FastAPI API (/api/v1/*)
    → Agent Runtime (LangGraph topology)
      → Hybrid RAG (Milvus Dense + BM25)
      → GraphRAG (Neo4j Knowledge Graph)
      → MCP Client → MCP Server (enterprise tools)
    → Auth (JWT + RBAC)
  → PostgreSQL (business data + checkpoints)
  → Redis (async jobs via ARQ)

文档摄取 Worker (ARQ):
  Upload → Parse → Chunk → Embed → Milvus + Neo4j
```

## 常见问题

### 数据库迁移失败

```bash
cd backend
uv run alembic downgrade base  # 回滚到初始状态
uv run alembic upgrade head    # 重新迁移
```

### Milvus 连接失败

检查 Milvus 是否启动:
```bash
docker compose -f deploy/compose.infrastructure.yml ps
```
确保 MILVUS_HOST 和 MILVUS_PORT 配置正确。

### 前端开发代理

开发模式下 Vite dev server 自动将 `/api` 请求代理到 `http://localhost:8000`。
