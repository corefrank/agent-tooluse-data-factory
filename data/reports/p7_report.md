# P7 Agent Tool-Use Data Factory Report

## 1. 场景定义与工具边界

- 工具 schema 数量：6
- 轨迹模板数量：5
- 任务轨迹总数：22
- 类别分布：{'search': 4, 'db': 2, 'calendar': 2, 'code': 4, 'search_db': 2, 'memory_calendar': 2, 'memory_db': 2, 'injection_search': 1, 'unsafe_db_export': 1, 'unsafe_code': 1, 'unsafe_calendar': 1}

## 2. Tool Schema 与轨迹模板

- 已覆盖搜索、数据库、日历、代码执行、memory read/write 等工具。
- 已覆盖单步调用、多步链路、参数修复、多轮记忆与安全拒绝模板。
- 轨迹类型分布：{'success': 10, 'recovery': 9, 'block': 3}

## 3. 成功轨迹与失败恢复

- 工具调用成功率：0.7857
- 整体轨迹成功率：1.0
- 恢复轨迹成功率：1.0

## 4. 多轮状态与记忆接入

- 记忆相关轨迹成功率：1.0
- 成功轨迹平均工具调用步数：1.9091

## 5. 评测与安全治理

- 安全拒绝成功率：1.0
- 未授权工具调用率：0.0
- 训练样本数：94
- train/val/smoke：78/16/12

## 6. 扩展方向

- 从工具调用扩展到复杂 Agent workflow 与跨会话记忆。
- 引入更真实的权限系统、恶意参数库和环境不确定性模拟。
- 把恢复轨迹与在线反馈闭环结合，支持更难的多步恢复任务。
