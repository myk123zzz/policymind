# PolicyMind 运行手册

## 环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.12 | 后端运行环境 |
| Conda (Miniconda/Anaconda) | 任意 | 虚拟环境管理 |
| Node.js | 20+ | 前端构建 |
| Git | 任意 | 版本控制 |
| Docker (可选) | 任意 | 生产部署 |

## 快速启动（开发模式）

### 0. 克隆项目

```bash
git clone https://github.com/myk123zzz/policymind.git
cd policymind
```

### 1. 创建 Conda 虚拟环境

```bash
conda create -n policymind python=3.12 -y
conda activate policymind
```

### 2. 配置 pip 镜像（国内加速，可选）

```bash
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
pip install -e .                                # 安装项目本身（editable mode）
```

### 4. 初始化数据库

```bash
# 默认使用 SQLite（本地文件，无需安装 PostgreSQL）
python -m alembic upgrade head
```

### 5. 启动后端

```bash
python -m uvicorn policymind.main:app --reload --host 0.0.0.0 --port 8000
```

验证：
```bash
curl http://localhost:8000/health/live
# → {"status":"ok"}

curl http://localhost:8000/health/ready
# → {"status":"ok","dependencies":{"database":"ok"}}

curl http://localhost:8000/metrics
# → spans_total 0
```

### 6. 启动前端

```bash
cd frontend
npm ci
npm run dev
```

浏览器打开 `http://localhost:5173`（Vite 自动代理 `/api` 到后端 `8000` 端口）。

---

## 运行测试

### 后端

```bash
cd backend
conda activate policymind

python -m pytest                                      # 全部测试 (137)
python -m pytest -m "not integration"                  # 跳过集成测试
python -m pytest -m integration                        # 仅集成测试
python -m ruff check src tests                         # 代码风格
python -m mypy src                                      # 类型检查
```

### 前端

```bash
cd frontend
npm run typecheck                                      # TypeScript 检查
npm test -- --run                                      # 单元测试 (9)
npm run build                                          # 生产构建
```

---

## API 调用示例

以下示例假设后端已启动在 `localhost:8000`。

### 注册与登录

```bash
# 首先创建一个种子用户（首次使用需要）
cd backend
python -c "
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic import SecretStr
import asyncio
from policymind.infrastructure.postgres.base import Base
from policymind.auth.models import Tenant, User
from policymind.auth.security import hash_password

async def seed():
    engine = create_async_engine('sqlite+aiosqlite:///policymind.db')
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    f = async_sessionmaker(engine, class_=AsyncSession)
    async with f() as s:
        s.add(Tenant(id=1, name='Test Org', slug='test-tenant'))
        s.add(User(id=1, tenant_id=1, username='admin',
            password_hash=hash_password(SecretStr('admin123')),
            role='employee', access_level=1, is_active=True))
        await s.commit()
    print('Seed done!')
asyncio.run(seed())
"

# 登录获取 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"tenant_slug":"test-tenant","username":"admin","password":"admin123"}'

# 返回: {"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"bearer"}
```

### 上传文档

```bash
TOKEN="<上一步获取的 access_token>"

echo "# Procurement Policy

## Approval Thresholds
- Purchases over \$5,000 require manager approval
- Purchases over \$50,000 require director approval" > /tmp/policy.md

curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/policy.md;type=text/markdown"
```

### 问答对话（SSE 流式）

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the procurement approval threshold?"}'

# SSE 事件流:
# event: routing
# data: {"status":"analyzing"}
# event: content
# data: {"text":"Answer: ..."}
# event: done
# data: {"thread_id":"thread-xxx"}
```

### HITL 审核流程

```bash
# 1) 发起审批类查询
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"approval review ticket for procurement"}'
# SSE 事件: review_required {"review_id": 12345}

# 2) 查看审核列表
curl http://localhost:8000/api/v1/reviews \
  -H "Authorization: Bearer $TOKEN"

# 3) 批准审核
curl -X POST http://localhost:8000/api/v1/reviews/12345/approve \
  -H "Authorization: Bearer $TOKEN"

# 4) 恢复对话
curl -X POST "http://localhost:8000/api/v1/chat/thread-xxx/resume" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision":"approve"}'
```

### 知识图谱查询

```bash
curl "http://localhost:8000/api/v1/graph/subgraph?seed_ids=p1,d1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 运行评测

```bash
cd backend
python ../scripts/run_evaluation.py

# 输出:
# Total Cases:        125
# Routing Accuracy:   76.00%
# Fact Coverage:      24.00%
# Citation Precision: 0.00%
# Graph Path Acc:     0.00%
# MRR:                0.00%
# Refusal Accuracy:   76.00%
# Avg Latency:        XXms
```

---

## Docker 部署（可选）

```bash
# 仅启动基础设施（PostgreSQL / Redis / Milvus / Neo4j / MinIO）
docker compose -f deploy/compose.infrastructure.yml up -d

# 完整部署（含 API / Worker / MCP / 前端 / Prometheus / Grafana）
docker compose -f deploy/compose.infrastructure.yml -f deploy/compose.full.yml up -d
```

---

## 项目架构

```
浏览器 (Vue3 Frontend :5173)
  → FastAPI API (:8000)
    → Agent Runtime (PolicyAgentRuntime)
      → Hybrid RAG (Milvus Dense + BM25)
      → GraphRAG (Neo4j Knowledge Graph)
      → MCP Client → MCP Server (enterprise tools)
    → Auth (JWT + RBAC)
  → SQLite / PostgreSQL (业务数据 + checkpoints)

文档摄取:
  Upload → Parse → Chunk → Embed → Milvus + Neo4j
```

## 快速参考

| 操作 | 命令 |
|------|------|
| 激活环境 | `conda activate policymind` |
| 后端启动 | `cd backend && python -m uvicorn policymind.main:app --reload` |
| 前端启动 | `cd frontend && npm run dev` |
| 后端测试 | `cd backend && python -m pytest` |
| 前端测试 | `cd frontend && npm test -- --run` |
| 代码检查 | `cd backend && python -m ruff check src tests && python -m mypy src` |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health/live |
| Prometheus | http://localhost:8000/metrics |
| 前端页面 | http://localhost:5173 |
| 评测 | `cd backend && python ../scripts/run_evaluation.py` |

## 常见问题

### 数据库迁移失败

```bash
cd backend
python -m alembic downgrade base      # 回滚
python -m alembic upgrade head         # 重新迁移
```

### 端口被占用

```bash
# Windows 查看端口占用
netstat -ano | findstr :8000
# 改用其他端口
python -m uvicorn policymind.main:app --reload --port 8001
```

### pip 安装慢

```bash
# 使用国内镜像
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
# 或
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```
