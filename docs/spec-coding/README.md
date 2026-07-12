# 规格编码索引

本目录用于沉淀 Sunshine Reading 后续迭代所需的项目规格、流程、测试与上下文交接资料。

目标不是替代代码，而是在上下文过长、多人协作或 AI 继续开发时提供稳定入口：

1. 当前项目已经完成了什么。
2. 当前还缺少什么。
3. 新功能应按什么流程设计、实现、测试和交付。
4. 自动迭代工作流未来应如何落地。

## 文档清单

| 文件 | 用途 |
| --- | --- |
| `01-current-state.md` | 当前功能、架构、页面、API、模型、依赖与已知风险盘点。 |
| `02-feature-spec.md` | 按业务域整理的功能设计规格，包括已实现与未实现能力。 |
| `03-roadmap.md` | 后续功能迭代路线图、优先级、阶段目标与依赖关系。 |
| `04-development-flow.md` | 开发流程图、角色流转、审核流转与发布流转。 |
| `05-testing-plan.md` | 测试策略、测试矩阵、手工联调用例与回归清单。 |
| `06-api-data-contract.md` | 当前 API 契约、数据模型边界、权限矩阵与兼容规则。 |
| `07-auto-iteration-workflow-plan.md` | 自动迭代开发工作流计划，仅定义规范，不实现自动化。 |
| `08-context-handoff-template.md` | 长上下文压缩或新会话接手时使用的交接模板。 |
| `09-iteration-workflow.md` | 面向实际开发的迭代工作流、任务准入、验收门禁与近期迭代计划。 |
| `10-short-video-generation-rfc.md` | 短视频生成功能 RFC，定义范围、数据与 API 草案、权限、阶段计划和风险。 |
| `11-api-key-security.md` | 第三方 AI 服务密钥的本地配置、服务端边界、生产注入、轮换与泄露处置。 |

## 后续开发用法

每次开发新功能前按以下顺序执行：

1. 阅读 `AGENTS.md`。
2. 阅读 `.cursor/rules/00` 到 `.cursor/rules/07`。
3. 阅读本目录的 `README.md`。
4. 根据任务类型阅读相关文档：
   - 新功能：`02-feature-spec.md`、`03-roadmap.md`
   - API 或模型：`06-api-data-contract.md`
   - 测试或修复：`05-testing-plan.md`
   - 自动迭代规范：`07-auto-iteration-workflow-plan.md`
   - 下一轮开发：`09-iteration-workflow.md`
5. 开始修改代码前，填写或口头确认 `08-context-handoff-template.md` 中的任务边界。
6. 实现后更新相关文档，尤其是完成状态、风险和测试结果。

## 范围规则

本目录内文档遵循以下边界：

- 不直接改变业务逻辑。
- 不定义与现有代码冲突的 API 返回格式，除非明确标为“待迁移”。
- 不引入新的框架初始化要求。
- 所有文件名使用英文。
- 说明文字默认使用简体中文；文件名、路径、代码标识符、命令、配置键和 API 字段保持英文或原始格式。
- 不再增加中英双语重复段落；确需引用英文原文时，同时提供中文说明。

## 当前基线

当前项目已经从最初的文档阶段推进到可运行的全栈开发状态：

- 前端：Next.js App Router + TypeScript + Tailwind CSS。
- 后端：Django + DRF + SimpleJWT。
- 数据库：通过 Docker Compose 运行 PostgreSQL 16。
- 核心领域：公开阅读、身份认证、书架、历史记录、评论、评分、作者工作台、审核工作流和运营管理。

此目录后续应作为“规格源头”维护。代码变化后，如果功能边界、接口、权限或测试方式发生改变，必须同步更新这里。
