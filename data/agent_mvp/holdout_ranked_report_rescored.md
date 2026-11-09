# 项目二：Agent Tool-Use 数据工厂 — Ranked Retrieval 离线评测复核

## 评测边界

- 模型：`qwen-plus`；基于既有真实模型输出的离线评分，**没有重新调用模型**。
- 数据：16 个手工构造的合成任务，新增模拟知识库与客户记录。
- 由于这 16 个任务已被用于发现和修复检索缺陷，**现在属于开发 / 回归测试，不能声称独立泛化提升**。

## 结果

| 同一 Ranked Retrieval 搜索器 | Baseline | Enhanced |
|---|---:|---:|
| 原始自动判定 | 13/16 (81.25%) | 16/16 (100.00%) |
| 更正日期语义后的离线判定 | 14/16 (87.50%) | 16/16 (100.00%) |
| 工具执行成功率 | 76.19% | 100.00% |
| 工具调用次数 | 21 | 17 |
| 平均任务耗时（原运行日志） | 3.436s | 2.818s |

两种 Prompt 对照：Enhanced 比 Baseline 高 **12.5 个百分点**（任务完成率；仅当前小样本回归集）。

## 误判审计

- `baseline/holdout_09`：False → True；原失败原因 `['missing_answer_keyword:2026-12-04']`；新失败原因 `[]`。

## 失败分析

- Baseline 未通过：`holdout_03`, `holdout_10`。
- Enhanced 未通过：无。
- Enhanced 相对 Baseline 改善的任务：`holdout_03`, `holdout_10`。
- Enhanced 相对 Baseline 退步的任务：无。

## 可复现性与限制

1. `python3 install_date_verifier.py` 安装日期比较钩子（不覆盖已有工具或提示词）。
2. `python3 -m unittest discover -s src -p 'test_p07_date_facts.py' -v` 验证多种日期写法、无效日期。
3. `python3 src/rescore_ranked_holdout.py` 对保存的 JSONL 执行离线重新评分；**不会覆盖原始 JSONL**。
4. 质量结论受限于预设 Task Verifier：文本包含匹配不等于语义正确，不具备反事实、否定句或权限系统完整审计能力。
5. 样本量很小，模型执行具有随机性，且曾根据这组任务修复检索排序；不能声称大规模泛化，也没有模型微调带来的收益。

## 数据工程贡献（基于当前可确认事实）

- 扩展原版 P07，从模板轨迹引入真实 `qwen-plus` 工具调用及多轮日志。
- 实现失败 Tool Call 正向监督过滤、Task 级 Train/Val 隔离、Evidence Verifier 与日期归一化。
- 增加轻量 Lexical Ranked Retrieval，研究 Top-1 检索召回和 Agent 最终任务完成间的关系。
- 建立 JSONL 轨迹记录、Verifier 复核、错误审计与 SFT 对话导出通路；本轮重新评分不产生新的 SFT 样本。
