# Skill: Debug Frontend / 前端 Bug 排查

## Purpose / 目的
- Diagnose frontend bugs quickly with reproducible evidence.
- 用可复现证据快速定位前端 Bug。

## Inputs / 输入
- Bug symptom and screenshot / 问题现象与截图
- Reproduction environment / 复现环境
- Related API requests / 相关 API 请求

## Steps / 步骤
1. Reproduce bug with exact environment and deterministic steps. / 在指定环境下按固定步骤复现。
2. Triage layer: UI state, route guard, network response, rendering, cache. / 分层定位：状态、路由守卫、网络响应、渲染、缓存。
3. Compare expected vs actual data shape from API contract. / 对照 API 合同比较期望与实际数据结构。
4. Apply minimal fix and remove temporary debug code. / 采用最小修复并清理临时调试代码。
5. Run regression checks on adjacent pages and shared components. / 对相邻页面与共享组件执行回归检查。

## Output / 产出
- Frontend bug report with root cause and verification results.
- 含根因与验证结果的前端缺陷报告。

## Checklist / 检查清单
- [ ] Reproduction is stable / 复现稳定
- [ ] Root cause is proven / 根因已证实
- [ ] Fix scope is minimal / 修复范围最小
- [ ] Regression is completed / 回归验证完成
