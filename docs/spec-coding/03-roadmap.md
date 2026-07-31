# Development Roadmap

This roadmap prioritizes work that improves project stability and makes future feature development safer.

## Phase 0: Stabilize Current Baseline

Goal: make the current project predictable before adding large business modules.

Tasks:

1. Fix text encoding issues in frontend/backend source strings. First pass completed for public/reader frontend paths.
2. Replace external placeholder cover images with local fallback assets. Frontend fallback completed; backend upload/media design remains open.
3. Add minimum backend tests for auth, public APIs, bookshelf/history, comments, ratings, author, reviewer, admin.
4. Add minimum frontend tests or at least Playwright smoke tests for main routes.
5. Generate or maintain API documentation.
6. Update stale `README.md` status from docs-only to current implementation status. Completed first pass.
7. Decide whether actual API envelope remains `{ code, message, data }` or migrates toward rule `03`.

Exit criteria:

- `npm run lint`, `npx tsc --noEmit`, `npm run build` pass.
- `manage.py check` and migrations pass.
- Main public routes and protected dashboards have smoke checks.
- Known local dev instructions are documented.

## Phase 1: Content Quality And Operations

Goal: make the platform manageable by non-developers.

Tasks:

1. Category management backend and frontend. First pass completed; audit logging completed for admin actions; deeper tests remain open.
2. Ranking management backend and frontend. First pass completed; audit logging completed for admin actions; automatic calculation and delete/bulk management remain open.
3. Review feedback visibility for authors. First pass completed in author novel/chapter details.
4. Admin action audit logs for user/content changes. First pass completed for user, category, ranking, novel, chapter, and comment admin write operations.
5. Comment report and moderation queue.
6. Bulk operations for admin/reviewer lists.

Exit criteria:

- Admin can manage taxonomy and rankings without seed scripts.
- Author can see rejection reason/history.
- Reviewer/admin actions are auditable.

## Phase 2: Author Productivity

Goal: improve author creation workflow.

Tasks:

1. Draft autosave. First frontend pass completed for chapter create/edit using browser-local storage.
2. Chapter preview. First frontend pass completed with edit/preview switching and reading-oriented typography.
3. Cover upload and local media storage.
4. Bulk chapter import.
5. Author statistics dashboard.
6. Notifications for review result and comments.

Exit criteria:

- Author can create, preview, submit, and track content without manual support.
- Review results are visible to author.

## Phase 3: Reader Experience

Goal: make reading experience closer to a usable product.

Tasks:

1. Reader settings polish: font family, line height, theme presets.
2. Reader table of contents drawer.
3. Offline/local chapter cache.
4. Bookshelf grouping and sorting.
5. Comment replies UI.
6. Rating distribution and review list.
7. Search history, suggestions, hot keywords.
8. AI chat and novel Q&A. First pass completed with user-supplied API key; streaming, provider config, and whole-novel retrieval remain open.

Exit criteria:

- Reader can comfortably navigate, resume, search, comment, and rate.
- Mobile reading flow has explicit regression tests.

## Phase 4: AI Media Creation

Goal: add controlled AI-assisted content transformation without introducing unbounded provider cost, unsafe storage, or unclear copyright behavior.

Tasks:

1. Novel/story/article short-video generation RFC. First draft completed in `10-short-video-generation-rfc.md`.
2. Storyboard project backend: project and scene models, create/list/detail APIs, owner/admin permissions. First backend pass completed for pasted text projects.
3. User-facing project pages: list/create/detail pages and visible navigation entry. First frontend pass completed for pasted text projects.
4. Local story draft generation: create 500-3000 character story drafts from a short idea. First pass completed without external provider calls.
5. Local storyboard generation: create 4-12 deterministic scene drafts from pasted/generated text. First pass completed without external provider calls.
6. Storyboard scene editing: title, visual prompt, narration, subtitle, duration, camera direction, and mood. First pass completed with owner/admin checks and audit logging.
7. 供应商 AI 剧情/分镜生成：服务端配置、数据库持久队列、轮询、有限重试、僵死任务恢复、本地降级和 token 审计已完成。子 Agent 工作流 2.2 已将剧情、角色、形象、场景、道具和台词拆解为带稳定 ID 的制作设定，再由原子镜头导演、视觉建模、连续镜头规划、提示词编译和质量监督依次处理；新增视觉圣经、规范资产锚点、镜头继承关系和逐镜视觉差量，供应商调用次数不因本地子 Agent 拆分而增加。GLM-4.7 结构化生成已支持显式关闭 Thinking，并为剧情策划和镜头导演设置独立超时；供应商剧情草稿生成仍待实现。
8. Chapter source integration: public approved chapters, author-owned drafts, admin access, source snapshots, searchable frontend selection, and audit logging completed.
9. Whole-novel source integration: searchable accessible novels, bounded chapter ranges, balanced 6000-character snapshots, frontend selection, permission checks, and audit logging completed.
10. 图片、逐镜视频、TTS 与字幕素材生成。SRT 字幕、GLM 图片、CogVideoX-Flash 竖屏 MP4、推荐使用的 GLM 独立旁白、异步任务、受保护预览/下载和分镜变更失效机制已完成第一轮；静态图使用规范文本锚点和连续镜头组，但当前 GLM 图片接口不接收角色参考图，生成结果仍需视觉复核。首镜优先读取本镜静态图，后续镜头优先承接上一镜经 FFmpeg 提取的尾帧，尾帧或静态图不可用时按级降级，模型内嵌音频仅作为可选实验性环境音。
11. 使用 FFmpeg 合并逐镜视频、独立旁白和字幕，生成可下载的 9:16 最终 MP4。首轮已完成：优先使用逐镜视频并回退到静态图片，主动排除模型内嵌音轨，缺失旁白时补静音，支持字幕烧录/内嵌降级、异步任务、失败重试和鉴权预览/下载。
12. 配额、内容审核、存储清理和后台排障视图。素材任务每日额度、项目删除清理和失败重试已完成第一轮；内容审核、存储总量配额和后台排障视图仍待实现。
13. 生成后视觉质检与局部重生成：人工视觉复核、结构化问题代码、渲染门禁、按 `scene_ids` 单镜重拍、每日镜头额度和单镜次数上限已完成第一阶段。下一轮接入视觉模型，对静态图及视频起始/中间/结束帧对照人物、场景、道具和状态链评分；同时评估支持角色/场景参考图以及首尾帧双输入的供应商，并保留当前规范文本锚点和静态图片降级路径。
14. 旁白双层质检首轮已完成：本地检查 WAV 格式、采样率、时长、响度、静音占比和削波；可选 GLM-ASR 转写后比较锁定旁白文本，未启用或调用失败时由用户逐镜试听确认。成片只接受波形通过且 ASR 相似度通过或人工确认清晰的旁白，人工标记异常具有最高优先级。

Exit criteria:

- A user can create a private storyboard project from valid text or accessible chapter content.
- A user can generate a story draft from a short idea and use it as project input.
- A pasted-text project can generate reviewable scene drafts.
- Provider secrets are configured server-side and never stored from user input.
- Long-running jobs have visible queued/running/succeeded/failed states.
- Storyboard-ready projects can generate and securely download a local SRT subtitle asset.
- Admin can inspect failed or unsafe projects.
- 本地确定性成片渲染已具备服务端开关、超时、文件大小限制、所有者权限和失败恢复；面向生产环境的批量渲染仍受存储总量配额与内容审核规则约束。

## Phase 5: Search And Recommendation

Goal: improve discovery.

Tasks:

1. Dedicated search app implementation.
2. Search logs and hot search.
3. Ranking calculation jobs.
4. Basic recommendation by category/popularity.
5. Cache strategy for rankings and home page.

Exit criteria:

- Search and rankings are generated from real signals.
- Home page no longer depends only on simple DB ordering.

## Phase 6: Payment And Membership

Goal: implement monetization after platform basics are stable.

Tasks:

1. Entitlement model.
2. Chapter purchase.
3. Orders and wallet.
4. Membership.
5. Author revenue records.
6. Payment provider integration.

Exit criteria:

- Paid chapter access is enforced server-side.
- Payment records are auditable.
- Refund and failure states are documented.

## Phase 7: Productionization

Goal: prepare for deployment and maintenance.

Tasks:

1. Environment separation: local, staging, production.
2. CI pipeline: lint, typecheck, backend check, tests, build.
3. Docker image build for frontend/backend.
4. Deployment docs.
5. Logging and metrics.
6. Database backup/restore.
7. Security hardening.

Exit criteria:

- Repeatable deployment process.
- Rollback and backup plan documented.
- Operational visibility exists.

## Priority Matrix

| Priority | Work |
| --- | --- |
| P0 | Encoding cleanup, local cover fallback, smoke tests, API docs, README update. |
| P1 | Category/ranking admin, author review feedback, admin audit logs. |
| P2 | Author server-side draft sync/upload, reader UX polish, comment replies, AI chat polish. |
| P3 | Search/recommendation, notifications, bulk moderation, short-video storyboard MVP. |
| P4 | Payment/membership, production deployment automation, direct text-to-video provider rendering. |

## Dependency Rules

- Do not start payment before entitlement and audit rules are designed.
- Do not add recommendation before tracking/search/ranking signals are reliable.
- Do not add complex admin bulk actions before single-item actions have tests.
- Do not replace auth storage strategy without regression tests for all protected pages.
- Do not migrate API envelope without a frontend compatibility plan.
- 在存储总量配额、清理策略和内容审核规则落地前，不得开放生产环境批量渲染或公开发布能力。
- Do not persist user-supplied AI/media provider API keys.
