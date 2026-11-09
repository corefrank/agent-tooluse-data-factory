# P07 项目二 — 英文日期 Verifier 修复与实验复核补丁

> 仅修复日期事实比较，不改变 Qwen 提示词、检索排序、工具执行和原始轨迹。
> 离线重新评分 **不需要 API Key，不会发起付费模型调用**。

## 安装到当前 P07 根目录

把此包的 `install_date_verifier.py` 放在仓库根目录；把 `src/` 中三个 Python 文件复制到现有 `src/` 下。

在 WSL 项目根目录运行：

```bash
python3 install_date_verifier.py
python3 -m unittest discover -s src -p 'test_p07_date_facts.py' -v
python3 src/rescore_ranked_holdout.py
```

请确保 `data/agent_mvp/` 中已有：

- `holdout_ranked_baseline.jsonl`
- `holdout_ranked_enhanced.jsonl`

脚本会创建以下新文件，不覆盖老文件：

- `holdout_ranked_baseline_rescored.jsonl`
- `holdout_ranked_enhanced_rescored.jsonl`
- `holdout_ranked_comparison_rescored.json`
- `holdout_ranked_verifier_audit.csv`
- `holdout_ranked_report_rescored.md`

## 学习要点

- **False Negative**：正确答案 `December 4, 2026` 因未包含 `2026-12-04` 而误判失败。
- **Normalization**：先解析日历日期为标准 ISO 字符串，再比较事实。
- **Replay / Offline Verification**：从已保存的轨迹中重新运行验证器，避免重复调用模型。
- **Audit Trail**：旧判定与新判定同时保留，便于审计。
- **实验限制**：这是被反复用于调试的小样本合成测试集，不是新的盲测数据，也未进行任何模型微调。

安全说明：ZIP 不包含你的云服务 API Key，也不会读取或输出它。
