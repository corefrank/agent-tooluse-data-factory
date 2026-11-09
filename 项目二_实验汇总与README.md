# 项目二｜面向 Agent 的 Tool-Use 轨迹合成与质量评估系统

**项目定位**：基于开源教学项目 `data_engineering_book / P07` 的工程扩展。旨在从预设模板轨迹升级为真实模型工具调用、过程记录、数据验证和结构化训练数据供给。**不是从零独立实现原版 P07**。

## 1. 架构

```
任务规格（P07 原始 + 扩展的真实任务）
  └── 自定义 Agent Harness / Qwen-plus（OpenAI-compatible 接口）
        └── Tool Dispatch：Search / SQL / Calendar / Session Memory
             └── Action / Observation / 失败恢复 / 工具状态记录
                  └── Verifier（执行结果、文档证据、日期归一化）
                       └── SFT JSONL（assistant tool_calls + tool response）
                            └── 轨迹评测 / 错误分析 / 报告
```

可选检索后端：P07 原版无序关键词命中、改进的标题加权词项排序（Ranked Retrieval）。

## 2. 已完成并有日志支持的工作

| 工作内容 | 已观测结果 | 注意事项 |
|---|---|---|
| P07 原版教学流水线 | 22 条模板轨迹 | 非自主执行的真实 LLM 轨迹 |
| 过滤执行失败的 Tool Call 正向监督 | 103 → 94 条事件级监督记录 | 只证明规则过滤生效，不是模型准确率提升 |
| 任务级 Group Split | Train 78 / Val 16，Task ID 重叠 0 | 模板/语料相似性仍可能存在 |
| P07 自动回归检查 | 用户本地日志显示 13/13 PASS | 检查覆盖仍有限 |
| 真实 Qwen-plus 工具执行 | P07 Agent Harness 已在用户环境完成在线运行 | 使用自定义 Harness，而非 LangGraph |
| Agent 训练对话导出 | 12/12 条轨迹经当前 Verifier 通过并导出 | SFT-ready，不代表已经做了 SFT |
| 8 个开发任务 | 原始 Baseline 6/8，强化检索提示词后 Enhanced 8/8 | 参与过提示词调试，不是盲测 |
| 16 个合成任务（原始关键词工具） | Baseline 11/16，Enhanced 10/16（当时自动评分） | 不同运行，含潜在 Verifier 误判 |
| 16 个合成任务（Ranked Retrieval） | 原自动评分 13/16 vs 16/16；纠正已确认日期误判后 14/16 vs 16/16 | 同一开发/回归任务集，不可宣称独立泛化收益 |

## 3. 检索改进方法

原版搜索器：`any(query_token in document)` 即保留文档，按原始插入顺序截断 Top-K，容易让“Gamma”专属资料被通用政策覆盖。

Ranked Retrieval：仅使用英文词项化、小型停用词列表和简单复数容忍，对标题匹配给予更高权重：

`score(doc, query) = sum(3 * title_match + body_match)`

然后按得分递减排序，最后截取 Top-K。**不是 BM25、Embedding 或 Dense Retrieval**。

## 4. Verifier 修复（本补丁）

此前 `December 4, 2026` 与 `2026-12-04` 被错误识别为不一致，构成已确认 False Negative。新增日期解析器支持 ISO、中文数字日期、英语月份名称等，并离线 Replay 已存 JSONL：

- 原评分：Baseline 13/16、Enhanced 16/16。
- 修复后：Baseline **14/16 (87.5%)**，Enhanced **16/16 (100%)**。
- 两套策略在该回归集上的任务完成率差距为 **12.5 个百分点**。
- 两组工具执行率分别 **84.21%**、**100%**；调用次数分别 **19**、**17**。
- 这些是已使用过的合成开发题，不是模型微调、独立盲测或大规模泛化证据。

## 5. 技术债和风险

- SFT 数据量极小：目前仅 12 条真实训练对话，不能证明微调效果。
- Verifier 仍基于关键字与预期文档 ID，不等于语义蕴含验证；包含否定、冲突事实的回答仍可能误判。
- Prompt 和检索后端的效果可能受到模型随机性、固定模拟知识库和重试策略影响，缺乏重复运行与置信区间。
- 最终任务并非独立于调试：Ranked Retrieval 部分改进针对之前分析过的 16 个问题。
- `python_exec` 原始模拟实现不能被视为安全沙箱；真实 Harness 刻意没有开放此能力。

## 6. 复现顺序

1. 运行原 P07 `build_tooling.py` → `generate_trajectories.py` → `simulate_tool_env.py` → `prepare_agent_dataset.py` → `evaluate_tooluse.py` → `run_p7_checks.py`。
2. 使用已安装的 Agent Harness 在模型 API 可用情况下生成并保存 JSONL；注意 API Key 通过环境变量配置。
3. 已保存 `data/agent_mvp/holdout_ranked_baseline.jsonl`、`holdout_ranked_enhanced.jsonl` 后执行：

```bash
python3 install_date_verifier.py
python3 -m unittest discover -s src -p 'test_p07_date_facts.py' -v
python3 src/rescore_ranked_holdout.py
```

4. 阅读 `data/agent_mvp/holdout_ranked_report_rescored.md` 及 `holdout_ranked_verifier_audit.csv`。

所有离线复核步骤不发送 API 请求，不覆盖原始轨迹。
