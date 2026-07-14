# Task 10 第 1 次审查报告

审查日期：2026-07-14

审查范围：
- `evaluation/datasets/golden_v1.jsonl`
- `backend/src/policymind/evaluation/{metrics,runner}.py`
- `backend/src/policymind/core/telemetry.py`
- `backend/tests/evaluation/test_metrics.py`
- `scripts/run_evaluation.py`
- `deploy/compose.infrastructure.yml`
- `deploy/compose.full.yml`
- `docs/runbook.md`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- 上一轮报告：[task-09/review-03](/D:/policymind/docs/reviews/task-09/review-03/README.md:1)

## 结论

这轮我判断 **Task 10 暂不通过**。

按简历项目口径，Task 10 已经有不少好东西：

1. Golden dataset 已经存在，而且不是凑数，覆盖了事实、跨文档、图谱/审批、版本、多模态、拒答、注入和越权。
2. 基础评测指标函数有单测，`backend/tests/evaluation` 当前通过。
3. `scripts/run_evaluation.py` 可以跑完整数据集并输出 JSON 报告。
4. 基础设施 compose、完整 compose、runbook 都已经起稿。

但 Task 10 是“交付收尾”阶段，目前还有 3 个会直接影响演示可信度的问题：

1. Evaluation runner 还没真正计算 Citation、Graph Path、MRR 等核心指标，报告里这些指标固定为 0。
2. `telemetry.py` 只是内存 collector，不是 OpenTelemetry，也没有 Prometheus `/metrics` 暴露。
3. `compose.full.yml` 引用了不存在的 Dockerfile、Prometheus 配置和 Grafana 目录，完整部署版目前无法按文档构建。

所以现在可以说 Task 10 已经有骨架和数据，但还不能说“评测、观测、部署与交付”完成。

## 做得不错的部分

- `golden_v1.jsonl` 当前有 125 条 case，明显超过“不少于 20 题”的要求。
- 数据集类别覆盖较广：`single_doc_fact`、`cross_document`、`department_role_approval`、`policy_version`、`multimodal`、`refusal`、`prompt_injection`、`unauthorized`。
- `metrics.py` 实现了 `recall_at_k`、`reciprocal_rank`、`ndcg_at_k`、`citation_precision`、`graph_path_accuracy`、`required_fact_coverage`。
- `test_metrics.py` 覆盖了基础指标函数。
- `run_evaluation.py` 能加载数据集、运行 runner、写出报告。
- `docs/runbook.md` 覆盖了开发启动、测试、评测、部署和常见问题。

## Findings

### 1. Evaluation runner 没有真实计算 Citation / Graph Path / MRR 等指标

- 严重性：高
- 位置：
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:41)
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:42)
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:43)
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:140)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:287)

当前 runner 只实际计算了：

- routing correctness
- required fact coverage
- refusal correctness
- latency

但 `citation_precision`、`graph_path_accuracy`、`mrr` 在 `CaseResult` 里默认是 `0.0`，`run_case()` 没有给它们赋值。实际运行 `scripts/run_evaluation.py` 后也能看到：

```text
Citation Precision: 0.00%
Graph Path Acc:     0.00%
MRR:                0.00%
```

这会让最终评测报告看起来像“跑了很多题，但关键 RAG/GraphRAG 指标没接上”。

改进方向：
- 从 agent/retrieval trace 中抽取 retrieved ids，计算 Recall@K 和 MRR。
- 从回答 citation ids 与有效 citation ids 计算 citation precision。
- 从 graph path 输出与 `expected_graph_edges` 计算 graph path accuracy。
- 至少补一个 runner 级测试，验证某个 fake case 能得到非零 citation / graph / mrr 指标。

### 2. Telemetry 不是 OpenTelemetry，也没有 Prometheus 暴露

- 严重性：高
- 位置：
  - [backend/src/policymind/core/telemetry.py](/D:/policymind/backend/src/policymind/core/telemetry.py:1)
  - [backend/src/policymind/core/telemetry.py](/D:/policymind/backend/src/policymind/core/telemetry.py:22)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:289)

文件注释写的是 “OpenTelemetry 遥测 + Prometheus 指标暴露”，但实现是一个内存 `Telemetry` 类：

- 没有 OpenTelemetry SDK 初始化。
- 没有 FastAPI middleware instrumentation。
- 没有 API / ingestion / retrieval / graph / agent / MCP span 接入。
- 没有 `/metrics` endpoint。
- 没有 Prometheus client 格式输出。

这对 Task 10 来说是主线问题，因为交付阶段必须能展示“系统可观测”。

改进方向：
- 简历项目可以不做完整 OTEL collector，但至少补一个 `/metrics` 路由，输出 Prometheus text format。
- 在 API 或 agent 关键路径记录 request count / latency / evaluation count。
- runbook 里说明 Prometheus scrape 的路径。

### 3. 完整 Docker Compose 引用不存在的构建文件和监控配置

- 严重性：高
- 位置：
  - [deploy/compose.full.yml](/D:/policymind/deploy/compose.full.yml:10)
  - [deploy/compose.full.yml](/D:/policymind/deploy/compose.full.yml:44)
  - [deploy/compose.full.yml](/D:/policymind/deploy/compose.full.yml:58)
  - [deploy/compose.full.yml](/D:/policymind/deploy/compose.full.yml:67)
  - [deploy/compose.full.yml](/D:/policymind/deploy/compose.full.yml:76)
  - [deploy/compose.full.yml](/D:/policymind/deploy/compose.full.yml:87)

`compose.full.yml` 引用了：

- `deploy/docker/Dockerfile.api`
- `deploy/docker/Dockerfile.worker`
- `deploy/docker/Dockerfile.mcp`
- `deploy/docker/Dockerfile.frontend`
- `deploy/prometheus.yml`
- `deploy/grafana/dashboards`

但当前检查结果：

```text
Test-Path deploy/docker       -> False
Test-Path deploy/prometheus.yml -> False
Test-Path deploy/grafana      -> False
```

这意味着 runbook 里的完整部署命令即使 Docker 可用，也会在构建/挂载阶段失败。

改进方向：
- 补齐四个 Dockerfile。
- 补 `deploy/prometheus.yml`。
- 创建 `deploy/grafana/dashboards/`，哪怕先放占位 dashboard/provisioning 文件。
- 最少跑 `docker compose ... config` 验证配置可解析。

### 4. Golden dataset 很大，但 runner 目前没有准备隔离 corpus

- 严重性：中
- 位置：
  - [backend/src/policymind/evaluation/runner.py](/D:/policymind/backend/src/policymind/evaluation/runner.py:64)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:910)

开发手册要求评测先创建隔离 corpus，并记录代码、数据、Prompt 和模型版本。当前 runner 直接 `build_policy_graph()` 后逐题 invoke，没有：

- corpus version
- prompt version 真正来源
- model config 记录
- dataset hash
- variant / ablation 标识

简历项目可以简化，但至少建议把 report 里写入：

- dataset path/hash
- code version 或 git sha
- prompt version
- model/provider 配置
- variant 名称

## 可先忽略的问题

这些不建议在第一轮继续卡：

- 数据集很多题是 synthetic policy facts，不一定都有真实 corpus 支撑；简历项目第一版可以接受。
- Docker 当前环境没有 `docker` 命令，无法实际启动 compose；这不作为代码问题，只记录为本机验证限制。
- 还没有完整消融实验 Dense/Hybrid/Rerank/Graph/Agent；可以等 runner 指标先接实后再补。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\evaluation -q`
   - 结果：通过
   - 摘要：`12 passed`

2. `.\backend\.venv\Scripts\python.exe scripts\run_evaluation.py --output evaluation\reports\review_probe.json`
   - 结果：通过
   - 摘要：
     - `Total Cases: 125`
     - `Routing Accuracy: 76.00%`
     - `Fact Coverage: 24.00%`
     - `Citation Precision: 0.00%`
     - `Graph Path Acc: 0.00%`
     - `MRR: 0.00%`
     - `Refusal Accuracy: 76.00%`

3. `docker compose -f deploy\compose.infrastructure.yml -f deploy\compose.full.yml config`
   - 结果：未执行成功
   - 原因：当前环境没有 `docker` 命令

4. 文件存在性检查：
   - `deploy/docker`: 不存在
   - `deploy/prometheus.yml`: 不存在
   - `deploy/grafana`: 不存在

## 是否允许收尾

**暂不允许 Task 10 收尾。**

建议先补一个最小交付闭环：

1. 让 evaluation runner 至少真实计算 citation / graph path / mrr 中的两项，并在报告里体现。
2. 补 `/metrics` 或 Prometheus text 输出，runbook 写清 scrape 路径。
3. 补齐 compose.full 引用的 Dockerfile 和 Prometheus/Grafana 文件。
4. 给 runner 增加 report 元信息：dataset hash、prompt version、model config、variant。

补完这些后，Task 10 就可以按简历项目标准进入最终收口。
