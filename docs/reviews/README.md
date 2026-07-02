# 审查报告目录规范

从本次开始，所有审查报告统一存放在 `docs/reviews/` 下，并使用固定命名：

```text
docs/reviews/
  README.md
  task-01/
    review-01/
      README.md
    review-02/
      README.md
  task-02/
    review-01/
      README.md
```

命名规则：

1. Task 目录使用 `task-XX`，两位数字补零，例如 `task-01`、`task-02`。
2. 同一 Task 的第 N 次审查使用 `review-YY`，两位数字补零，例如 `review-01`、`review-02`。
3. 每次审查单独建目录，报告正文文件统一命名为 `README.md`。
4. 报告标题必须明确写出：
   - Task 编号
   - 第几次审查
   - 审查日期
5. 报告正文至少包含：
   - 审查范围
   - 审查基线
   - 结论
   - 发现的问题
   - 改进方向
   - 验证记录

使用约定：

- 若本次审查没有发现问题，也仍然要生成对应的审查报告。
- 若是对上一次问题的复审，需要在“结论”中说明：
  - 已修复的问题
  - 仍未关闭的问题
  - 是否允许进入下一 Task
