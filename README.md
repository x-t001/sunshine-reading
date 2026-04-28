# Sunshine Reading (阳光阅读)

## Purpose / 目的
- Define executable AI development standards for a novel reading platform.
- 为小说阅读平台定义可执行的 AI 开发规范。

## Inputs / 输入
- Project Chinese name / 项目中文名: 阳光阅读
- Project English name / 项目英文名: Sunshine Reading
- Repository name / 仓库名: sunshine-reading

## Technical Stack / 技术栈
- Frontend (planned) / 前端（规划）: Next.js + TypeScript
- Backend (planned) / 后端（规划）: Django + Django REST Framework
- Database (planned) / 数据库（规划）: PostgreSQL
- Current stage / 当前阶段: documentation-only（仅文档规范阶段）

## Steps / 步骤
1. Read `AGENTS.md`, then load `.cursor/rules` in numeric order. / 先读 `AGENTS.md`，再按编号加载 `.cursor/rules`。
2. Pick one task template from `docs/ai-skills` before implementation. / 实施前先从 `docs/ai-skills` 选一个任务模板。
3. Follow API/database/security constraints before writing any code. / 写代码前先满足 API/数据库/安全约束。
4. Keep edits minimal, testable, and scoped to requested files. / 变更保持最小、可验证、且范围可控。
5. Reject forbidden actions in current stage. / 当前阶段拒绝禁用动作。

## Forbidden Actions (Current Stage) / 当前阶段禁用项
- Do not initialize Next.js. / 不初始化 Next.js。
- Do not initialize Django. / 不初始化 Django。
- Do not add business feature code. / 不新增业务功能代码。

## Output / 产出
- A strict and reusable AI collaboration baseline for future implementation phases.
- 为后续实现阶段提供严格、可复用的 AI 协作基线。

## Checklist / 检查清单
- [ ] Rules and skills are loaded before execution. / 执行前已加载规则与技能模板。
- [ ] API response format follows rule `03-api-contract.mdc`. / API 响应格式遵循 `03-api-contract.mdc`。
- [ ] Security and permission checks follow rule `06-security-permission.mdc`. / 安全与权限遵循 `06-security-permission.mdc`。
- [ ] No Next.js/Django initialization and no business code. / 未初始化 Next.js/Django 且未新增业务代码。
