# Spec Coding Index

本目录用于沉淀 Sunshine Reading 后续迭代所需的项目规格、流程、测试与上下文交接资料。

目标不是替代代码，而是在上下文过长、多人协作或 AI 继续开发时，提供稳定入口：

1. 当前项目已经做了什么。
2. 还缺什么。
3. 新功能应该按什么流程设计、实现、测试、交付。
4. 自动化迭代工作流未来应该如何落地。

## Documents

| File | Purpose |
| --- | --- |
| `01-current-state.md` | 当前功能、架构、页面、API、模型、依赖与已知风险盘点。 |
| `02-feature-spec.md` | 按业务域整理的功能设计规格，包括已实现与未实现能力。 |
| `03-roadmap.md` | 后续功能迭代路线图、优先级、阶段目标与依赖关系。 |
| `04-development-flow.md` | 开发流程图、角色流转、审核流转、发布流转。 |
| `05-testing-plan.md` | 测试策略、测试矩阵、手工联调用例、回归清单。 |
| `06-api-data-contract.md` | 当前 API 契约、数据模型边界、权限矩阵与兼容规则。 |
| `07-auto-iteration-workflow-plan.md` | 自动迭代开发工作流计划，只定义规范，不实现自动化。 |
| `08-context-handoff-template.md` | 长上下文压缩或新会话接手时使用的交接模板。 |
| `09-iteration-workflow.md` | 面向后续实际开发的迭代工作流、任务准入、验收门禁和近期迭代计划。 |
| `10-short-video-generation-rfc.md` | 短视频生成功能 RFC，定义范围、数据/API 草案、权限、阶段计划与风险。 |

## Usage For Future Development

每次开发新功能前按顺序执行：

1. 读 `AGENTS.md`。
2. 读 `.cursor/rules/00` 到 `.cursor/rules/07`。
3. 读本目录 `README.md`。
4. 根据任务类型读：
   - 新功能：`02-feature-spec.md`、`03-roadmap.md`
   - API/模型：`06-api-data-contract.md`
   - 测试/修复：`05-testing-plan.md`
   - 自动迭代规范：`07-auto-iteration-workflow-plan.md`
   - 下一轮开发：`09-iteration-workflow.md`
5. 在开始改代码前填写或口头确认 `08-context-handoff-template.md` 中的任务边界。
6. 实现后更新相关文档，特别是已完成状态、风险、测试结果。

## Scope Rules

本目录内文档遵循以下边界：

- 不直接改变业务逻辑。
- 不定义与现有代码冲突的 API 返回格式，除非明确标为“待迁移”。
- 不引入新的框架初始化要求。
- 所有文件名使用英文。
- 文档内容可以使用中文，便于产品与开发沟通。

## Current Baseline

当前项目已经从最初文档阶段推进到可运行的全栈开发态：

- Frontend: Next.js App Router + TypeScript + Tailwind CSS。
- Backend: Django + DRF + SimpleJWT。
- Database: PostgreSQL 16 via Docker Compose。
- Core domains: public reading, authentication, bookshelf, history, comments, ratings, author workspace, reviewer workflow, admin operations.

此目录后续应作为“规格源头”维护；代码变化后，如果功能边界、接口、权限或测试方式改变，应同步更新这里。
