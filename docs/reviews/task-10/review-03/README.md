# Task 10 第 3 次审查报告

审查日期：2026-07-14

审查范围：
- `backend/src/policymind/evaluation/runner.py`
- `backend/src/policymind/core/telemetry.py`
- `backend/src/policymind/main.py`
- `scripts/run_evaluation.py`
- `deploy/docker/{Dockerfile.api,Dockerfile.worker,Dockerfile.mcp,Dockerfile.frontend}`
- `deploy/prometheus.yml`
- `deploy/grafana/dashboards/policymind.json`
- `docs/runbook.md`
- 上一轮报告：[task-10/review-02](/D:/policymind/docs/reviews/task-10/review-02/README.md:1)

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## 结论

这轮我判断 **Task 10 可以收口**。

按简历项目标准，Task 10 的交付主线已经成立：

1. 评测数据集规模和覆盖面足够。
2. 基础指标函数有测试。
3. `scripts/run_evaluation.py` 可以跑完整 125 条 golden case，并输出 JSON 报告。
4. 报告包含 dataset hash、prompt version、code version 等元信息。
5. `/metrics` 可以返回 Prometheus text format。
6. 基础设施 compose、完整 compose、Dockerfile、Prometheus、Grafana 和 runbook 都已具备。

剩余问题主要是指标深度和部署成熟度，不再阻塞简历项目收尾。

## 已关闭的问题

### 1. Evaluation report 缺少元信息

已关闭。

当前输出报告包含：

```json
"model_config": {
  "prompt_version": "v1",
  "dataset_hash": "c64140e21fee4693",
  "code_version": "Task 10 release"
}
```

### 2. Graph Path 虚高

已关闭。

上一轮 `graph_path_accuracy` 是 `100.00%`，主要因为 expected 为空的 case 被计为满分。当前 runner 已将不适用样本标记为 `-1.0`，汇总时只统计适用样本。实测本轮报告里：

```text
Graph Path Acc: 0.00%
```

这虽然不好看，但比虚高可信，说明当前 demo agent 没有真实输出 graph path。

### 3. Dockerfile 引用缺失文件或坏入口

已关闭到 demo 可用标准。

当前状态：

- `Dockerfile.worker` 不再引用不存在的 `policymind.workers.ingestion_worker.WorkerSettings`。
- `Dockerfile.mcp` 改为直接导入并运行 `run_stdio_server()`。
- `Dockerfile.frontend` 不再复制缺失的 `frontend/nginx.conf`。
- `deploy/docker/Dockerfile.*`、`deploy/prometheus.yml`、`deploy/grafana/dashboards/policymind.json` 均存在。

### 4. `/metrics` 缺失

已关闭。

实测：

```text
GET /metrics -> 200
request_count 1
spans_total 0
```

## 保留但不阻塞的问题

### 1. Citation / MRR / Graph 指标仍为 0

实测评测输出：

```text
Citation Precision: 0.00%
Graph Path Acc:     0.00%
MRR:                0.00%
```

这说明当前 demo agent 还没有把真实 retrieval ids、citation ids、graph edges 暴露给 runner。按生产标准这不能算完整评测，但按简历项目收尾标准可以接受，因为：

- runner 不再造假或虚高。
- 数据集、脚本、报告格式和指标口径已经存在。
- 后续接真实 RAG/Graph trace 时有落点。

建议最终演示前补一个小型 demo corpus，让至少 3-5 条 case 产出非零 citation / MRR / graph 指标。

### 2. Worker 容器仍是轻量占位

`Dockerfile.worker` 当前只是导入 `ingest_document_job` 并打印 ready，不是真正 ARQ worker 常驻进程。简历项目可接受，但真实部署前应恢复为正式 worker。

### 3. Grafana dashboard 仍是最小版

Dashboard 只有 request count / latency 类面板，且部分指标仍依赖后续 middleware 记录。可以后续打磨，不影响当前收口。

### 4. Docker 未在当前环境实际启动验证

当前环境没有 `docker` 命令，无法实际执行 compose up。这里不作为代码阻塞，只记录验证限制。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\evaluation -q`
   - 结果：通过
   - 摘要：`12 passed`

2. `.\backend\.venv\Scripts\python.exe scripts\run_evaluation.py --output evaluation\reports\review_probe_3.json`
   - 结果：通过
   - 摘要：
     - `Total Cases: 125`
     - `Routing Accuracy: 76.00%`
     - `Fact Coverage: 24.00%`
     - `Citation Precision: 0.00%`
     - `Graph Path Acc: 0.00%`
     - `MRR: 0.00%`
     - `Refusal Accuracy: 76.00%`

3. `/metrics` 探针
   - 结果：通过
   - 摘要：`GET /metrics -> 200`

4. 文件存在性检查：
   - `deploy/docker/Dockerfile.worker`: 存在
   - `deploy/docker/Dockerfile.mcp`: 存在
   - `deploy/docker/Dockerfile.frontend`: 存在
   - `deploy/prometheus.yml`: 存在
   - `deploy/grafana/dashboards/policymind.json`: 存在

## 是否允许最终收尾

**允许 Task 10 收口。**

整个项目已经具备可展示的端到端骨架：后端 API、文档上传、RAG/GraphRAG/MCP/HITL 主线、Vue 工作台、评测脚本、Prometheus 指标入口、Docker Compose 和运行手册。剩余事项属于演示质量和生产化增强，不再阻塞简历项目交付。
