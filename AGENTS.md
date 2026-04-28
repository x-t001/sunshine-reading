# AGENTS Guide - Sunshine Reading (阳光阅读)

## Purpose / 目的
- Define mandatory workflow and boundaries for AI changes.
- 定义 AI 变更的强制流程与边界。

## Inputs / 输入
- Rules directory / 规则目录: `.cursor/rules`
- Skills directory / 技能目录: `docs/ai-skills`

## Mandatory Workflow / 强制流程
1. Clarify scope, deliverable, and forbidden actions. / 澄清范围、交付物与禁用动作。
2. Load applicable rules in order (`00` -> `07`). / 按顺序加载适用规则（`00` -> `07`）。
3. Select one matching skill and execute its checklist. / 选择匹配技能并执行清单。
4. Implement minimal changes only in requested files. / 仅在请求文件内做最小变更。
5. Verify and report changed files + risks. / 验证并汇报变更文件与风险。

## AI Boundary / AI 修改边界
- Must refuse scaffold commands during docs-only stage. / 文档阶段必须拒绝脚手架命令。
- Must refuse unrelated refactor outside request scope. / 必须拒绝超范围无关重构。
- Must not change naming conventions or response envelope without explicit approval. / 未经明确批准，不得修改命名规范或响应封装格式。

## Output / 产出
- Predictable, auditable, and scope-controlled AI execution.
- 可预测、可审计、范围可控的 AI 执行过程。

## Checklist / 检查清单
- [ ] Rule order is respected. / 规则加载顺序正确。
- [ ] Skill checklist is applied. / 技能清单已执行。
- [ ] Scope boundaries are respected. / 范围边界已遵守。
- [ ] Forbidden actions are not executed. / 禁用动作未执行。
