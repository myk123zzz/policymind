# Task 10 第 2 次审查报告

审查日期：2026-07-14

审查范围：
- `backend/src/policymind/evaluation/runner.py`
- `backend/src/policymind/core/telemetry.py`
- `backend/src/policymind/main.py`
- `scripts/run_evaluation.py`
- `deploy/compose.full.yml`
- `deploy/prometheus.yml`
- `deploy/docker/{Dockerfile.api,Dockerfile.worker,Dockerfile.mcp,Dockerfile.frontend}`
- `deploy/grafana/dashboards/policymind.json`
- 上一轮报告：[task-10/review-01](/D:/policymind/docs/reviews/task-10/review-01/README.md:1)

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## 结论

这轮我判断 **Task 10 仍暂不通过，但比上一轮推进明显**。

已经关闭的点：

1. `/metrics` 已经挂到 FastAPI，Prometheus text format 能访问。
2. `deploy/docker/`、`deploy/prometheus.yml`、`deploy/grafana/dashboards/` 已经补齐。
3. Evaluation report 已经带 dataset hash / model config 这类元信息。
4. 评测脚本、指标单测仍能跑。

但 Task 10 是最终交付阶段，目前还剩两个真正会影响交付可信度的问题：

1. Evaluation runner 虽然开始给 citation / graph / mrr 字段赋值，但实际报告里 citation 和 mrr 仍是 `0.00%`，graph path `100.00%` 主要来自 expected 为空的样本，指标仍偏“假亮灯”。
2. 完整部署文件虽然补齐了文件名，但若按 compose 构建，worker / MCP / frontend 容器仍有明显入口或文件缺失问题。

按简历项目口径，这轮不能最终收尾，但已经接近了。再补一小轮，把“评测报告像真的”和“compose 至少不引用坏入口”钉住，就可以放行。

## 已关闭的问题

### 1. `/metrics` 缺失

已关闭到 demo 可用标准。

当前实现：

- [telemetry.py](/D:/policymind/backend/src/policymind/core/telemetry.py:10) 提供内存 telemetry。
- [telemetry.py](/D:/policymind/backend/src/policymind/core/telemetry.py:47) 输出 Prometheus text format。
- [telemetry.py](/D:/policymind/backend/src/policymind/core/telemetry.py:63) 暴露 `/metrics` endpoint。
- [main.py](/D:/policymind/backend/src/policymind/main.py:45) 挂载 metrics router。

实测：

```text
GET /metrics -> 200
request_count 1
spans_total 0
```

这不是完整 OpenTelemetry，但对简历项目的 Prometheus 演示已经够用。

### 2. compose 引用的监控和 Dockerfile 文件不存在

部分关闭。

当前已存在：

- `deploy/docker/Dockerfile.api`
- `deploy/docker/Dockerfile.worker`
- `deploy/docker/Dockerfile.mcp`
- `deploy/docker/Dockerfile.frontend`
- `deploy/prometheus.yml`
- `deploy/grafana/dashboards/policymind.json`

文件存在性问题已解决，但构建入口仍有问题，见 Findings。

### 3. Evaluation report 缺少 dataset 元信息

已关闭到 demo 可用标准。

当前 [runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:161) 会计算 dataset hash，并写入：

- `dataset_version`
- `model_config.prompt_version`
- `model_config.dataset_hash`
- `model_config.code_version`

不过 [scripts/run_evaluation.py](/D:/policymind/scripts/run_evaluation.py:57) 当前写 JSON 时还没有把 `model_config` 原样输出到报告文件，只在 runner 对象里存在。建议顺手补上。

## Findings

### 1. Evaluation runner 的关键指标仍不可信

- 严重性：高
- 位置：
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:105)
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:116)
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:124)

这轮 runner 已经开始计算 citation / graph / mrr，但实际结果仍说明主指标没有真正接到数据：

```text
Citation Precision: 0.00%
Graph Path Acc:     100.00%
MRR:                0.00%
```

具体问题：

- `citation_precision` 只有 `agent_cids` 存在时才设值；当前 agent 基本不产 citation，所以全局仍是 0。
- `mrr` 用 `retrieval_ref` 去匹配 `expected_document_versions`，两者不是同一 ID 空间，实际仍是 0。
- `graph_path_accuracy` 对 expected 为空且 actual 为空的 case 返回 1，大量非图谱题会把平均值抬到 100%，这会误导报告。

改进方向：

- Citation：即使是 demo，也可以从 `citation_ids` 与 case expected version/page 生成一个可解释的 valid id 空间，或者只在需要 citation 的样本上汇总。
- MRR：不要用 `retrieval_ref` 和 document version 直接比；要么输出 retrieved document/version ids，要么把 MRR 标记为 `not_applicable` 并从总分中剔除。
- Graph Path：只在 `expected_graph_edges` 非空的 case 上统计 graph path accuracy，避免空样本虚高。
- 补一个 runner 级测试，确保非空 expected graph edge / citation / retrieved id 能得到非零指标。

### 2. 完整部署的容器入口仍会断

- 严重性：高
- 位置：
  - [deploy/docker/Dockerfile.worker](/D:/policymind/deploy/docker/Dockerfile.worker:8)
  - [deploy/docker/Dockerfile.mcp](/D:/policymind/deploy/docker/Dockerfile.mcp:8)
  - [deploy/docker/Dockerfile.frontend](/D:/policymind/deploy/docker/Dockerfile.frontend:10)

这轮 Dockerfile 已经补了，但入口还不稳：

- `Dockerfile.worker` 启动 `policymind.workers.ingestion_worker.WorkerSettings`，当前代码树里没有 `policymind.workers.ingestion_worker`。
- `Dockerfile.mcp` 执行 `python -m policymind.mcp.server`，但 `server.py` 只有 `run_stdio_server()`，没有模块 main 入口，容器会直接退出。
- `Dockerfile.frontend` 复制 `nginx.conf`，但 `frontend/nginx.conf` 当前不存在。

这几个问题会让 runbook 的完整部署命令看起来有了，但真正 build/run 时失败。

改进方向：

- worker：如果还没有 ARQ worker，先改成可运行的轻量命令，或补真实 worker module。
- mcp：给 `policymind.mcp.server` 增加 `if __name__ == "__main__": run_stdio_server()`，或改 Docker CMD 到真实 HTTP/stdio 服务入口。
- frontend：补 `frontend/nginx.conf`，或移除 Dockerfile 里的 COPY。

### 3. Prometheus/Grafana 配置是最小版，但指标名不匹配

- 严重性：中
- 位置：
  - [deploy/grafana/dashboards/policymind.json](/D:/policymind/deploy/grafana/dashboards/policymind.json:1)
  - [backend/src/policymind/core/telemetry.py](/D:/policymind/backend/src/policymind/core/telemetry.py:47)

Grafana dashboard 里用了：

- `request_count`
- `request_latency_avg`

但当前 `/metrics` 只会输出已经手动 increment 的 counter 和 `spans_total`。代码里没有统一记录 `request_latency_avg`。这不阻塞演示，但会导致 Grafana 某些 panel 没数据。

改进方向：

- 增加 FastAPI middleware，记录 `request_count` 和 `request_latency_ms`。
- 或者把 dashboard 改成当前实际可输出的指标。

## 可先忽略的问题

这些不继续阻塞本轮：

- Docker 命令在当前环境不可用，不能实际执行 `docker compose config`；这属于本机工具限制。
- Telemetry 不是完整 OpenTelemetry SDK；简历项目可用 Prometheus `/metrics` 替代。
- 数据集是 synthetic，但覆盖面很好，可以接受。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\evaluation -q`
   - 结果：通过
   - 摘要：`12 passed`

2. `.\backend\.venv\Scripts\python.exe scripts\run_evaluation.py --output evaluation\reports\review_probe_2.json`
   - 结果：通过
   - 摘要：
     - `Total Cases: 125`
     - `Routing Accuracy: 76.00%`
     - `Fact Coverage: 24.00%`
     - `Citation Precision: 0.00%`
     - `Graph Path Acc: 100.00%`
     - `MRR: 0.00%`
     - `Refusal Accuracy: 76.00%`

3. `/metrics` 探针
   - 结果：通过
   - 摘要：`GET /metrics -> 200`，Prometheus text format 可返回

4. 文件存在性检查：
   - `deploy/docker/Dockerfile.api`: 存在
   - `deploy/prometheus.yml`: 存在
   - `deploy/grafana/dashboards/policymind.json`: 存在
   - `frontend/nginx.conf`: 不存在

## 是否允许收尾

**暂不允许 Task 10 收尾。**

建议最后补一轮很小的修复：

1. 修正 evaluation 汇总口径，避免 citation/mrr 永远 0、graph path 因空 expected 虚高。
2. 修正 `Dockerfile.worker`、`Dockerfile.mcp`、`Dockerfile.frontend` 的不可运行入口。
3. 让 run_evaluation 输出 `model_config` 到 JSON。
4. 简单对齐 `/metrics` 和 Grafana dashboard 的指标名。

补完这几项后，我会倾向于按简历项目标准放行 Task 10。
