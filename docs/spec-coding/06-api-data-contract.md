# API And Data Contract

This document records the current implemented contract. It is intentionally based on the running code rather than older planning rules.

## 1. Actual API Base

Current backend routes are mounted under:

```text
/api/
```

Examples:

```text
/api/health/
/api/novels/
/api/auth/login/
/api/admin/users/
```

Do not introduce `/api/v1/` unless a migration plan is created.

## 2. Response Envelope

Current success shape:

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

Current paginated shape:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 0,
    "next": null,
    "previous": null,
    "results": []
  }
}
```

Current error shape is normalized by `common.exceptions.custom_exception_handler` and `common.response.error_response`.

Contract rule:

- New APIs must use the same envelope.
- New list APIs must use the same pagination shape unless a deliberate migration is planned.
- Public API success responses must not begin requiring auth accidentally.

## 3. Authentication

JWT:

- Header: `Authorization: Bearer <access_token>`
- Access lifetime: 30 minutes.
- Refresh lifetime: 7 days.

Frontend:

- Stores access/refresh in `localStorage`.
- Automatically attaches bearer token when `apiRequest` uses `auth: true`.
- Public requests must pass `auth: false`.

Risk:

- localStorage token storage is acceptable for development but should be reviewed before production.

## 4. Permission Matrix

| Domain | Public | Reader | Author | Reviewer | Admin/staff/superuser |
| --- | --- | --- | --- | --- | --- |
| Health | Yes | Yes | Yes | Yes | Yes |
| Public novels/categories/chapters/rankings | Yes | Yes | Yes | Yes | Yes |
| AI chat proxy | Yes, with user-supplied API key | Yes | Yes | Yes | Yes |
| Register/login/refresh | Yes | Yes | Yes | Yes | Yes |
| Profile `/users/me` | No | Own | Own | Own | Own |
| Bookshelf/history | No | Own | Own | Own | Own |
| Comment create/delete | Read public; write login | Own | Own | Own | Admin all through admin APIs |
| Rating | Summary public; write login | Own | Own | Own | Own |
| Author workspace | No | No | Own content | No | All/elevated |
| Reviewer workspace | No | No | No | Reviewer tasks | All |
| Admin users/content | No | No | No | No | All |
| Admin categories | No | No | No | No | All |
| Admin rankings | No | No | No | No | All |
| Video projects | No | Own text projects | Own text projects | Own text projects | All through admin APIs |

## 5. AI Chat Proxy

Endpoint:

- `POST /api/ai/chat/`

Permission:

- Public endpoint.
- Requires a user-supplied `api_key` in the request body.
- The API key is not stored by the backend.

Request:

```json
{
  "api_key": "sk-...",
  "api_url": "https://api.openai.com/v1/chat/completions",
  "model": "gpt-4o-mini",
  "messages": [
    { "role": "user", "content": "这本小说讲了什么？" }
  ],
  "context": {
    "novel_title": "小说标题",
    "novel_description": "简介",
    "author_name": "作者",
    "category_name": "分类",
    "chapter_title": "章节标题",
    "chapter_excerpt": "章节摘录"
  }
}
```

Response:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "回答内容",
    "model": "gpt-4o-mini",
    "usage": null
  }
}
```

Rules:

- `api_url` must use HTTPS.
- Backend sends an OpenAI-compatible `chat/completions` request.
- Only non-streaming responses are supported in the first pass.
- Frontend may remember non-sensitive model/API URL config, but must not persist API key.

## 6. Short Video Project Skeleton

Implemented backend endpoints:

- `GET /api/video-projects/`
- `POST /api/video-projects/`
- `GET /api/video-source-chapters/`
- `GET /api/video-source-novels/`
- `POST /api/video-projects/from-chapter/`
- `POST /api/video-projects/from-novel/`
- `POST /api/video-projects/story-draft/`
- `GET /api/video-projects/capabilities/`
- `GET /api/video-projects/{id}/`
- `POST /api/video-projects/{id}/storyboard/`
- `POST /api/video-projects/{id}/storyboard/ai/`
- `POST /api/video-projects/{id}/storyboard/jobs/`
- `GET /api/video-projects/{id}/storyboard/jobs/latest/`
- `PATCH /api/video-projects/{id}/scenes/{scene_id}/`
- `POST /api/video-projects/{id}/assets/subtitles/`
- `POST/GET /api/video-projects/{id}/assets/images/jobs/`
- `POST/GET /api/video-projects/{id}/assets/videos/jobs/`
- `POST/GET /api/video-projects/{id}/assets/audio/jobs/`
- `POST/GET /api/video-projects/{id}/render/jobs/`
- `GET /api/video-generation-jobs/{id}/`
- `POST /api/video-generation-jobs/{id}/retry/`
- `PATCH /api/video-assets/{id}/visual-review/`
- `GET /api/video-assets/{id}/download/`
- `DELETE /api/video-projects/{id}/`
- `GET /api/admin/video-projects/`
- `GET /api/admin/video-projects/{id}/`

Current implementation scope:

- 粘贴文本、经过权限检查的章节和限定章节范围的整本小说来源均已支持。
- Local story draft generation is available and does not call an external AI provider.
- Local storyboard generation is available and does not call an external AI provider.
- Server-configured OpenAI-compatible storyboard generation is available when all `VIDEO_AI_*` settings are valid.
- Durable storyboard jobs are processed by `python manage.py run_video_generation_worker`.
- 图片、逐镜视频、独立旁白、SRT 字幕和最终 MP4 均使用持久化任务或受保护素材记录；统一由 `python manage.py run_video_generation_worker` 处理长任务。
- 逐镜视频采用单参考图连续性链：首镜优先使用本镜最新的已就绪 PNG/JPEG；后续镜头优先使用上一镜成片经本地 FFmpeg 提取的尾帧，尾帧不可用时回退本镜静态图，再不可用时回退文生视频。参考图以不超过 5MB 的 Base64 `image_url` 临时提交，不持久化 Base64 正文。
- 独立旁白生成后执行本地 WAV 波形质检；未通过格式、采样率、时长、响度、静音或削波检查的文件不会进入 `ready` 状态。
- 本地 FFmpeg 成片优先使用逐镜视频、回退静态图片，只混入独立旁白音轨，缺失旁白时补静音，并烧录字幕或降级为内嵌字幕。
- 前端已有列表、创建、详情、素材生成、任务轮询、失败重试、成片预览和鉴权下载页面。

Chapter source rules:

- `GET /api/video-source-chapters/` lists public approved published chapters plus chapters owned by the current author; admins can list all chapters.
- Optional `keyword` searches novel and chapter titles. Results use the standard pagination envelope.
- `POST /api/video-projects/from-chapter/` accepts `chapter_id`, optional `title`, `duration_target`, `style_preset`, and `aspect_ratio`.
- Readers cannot discover or use private, hidden, unapproved, or removed-book chapters owned by others; inaccessible IDs return not found.
- Authors may use their own draft, pending, reviewing, approved, rejected, published, or hidden chapters.
- Chapter content must contain at least 100 characters and pass unsafe HTML/script validation.
- The project stores `source_novel`, `source_chapter`, a source title, SHA-256 snapshot hash, and the first 3000 characters as an immutable project input snapshot.
- Chapter project creation writes a `video_project/create` audit event containing only IDs and snapshot length.

Create request:

```json
{
  "source_type": "text",
  "title": "Story trailer",
  "input_text": "500 to 3000 characters",
  "style_preset": "cinematic_story",
  "duration_target": 60,
  "aspect_ratio": "9:16"
}
```

Rules:

- User must be logged in and not banned.
- `source_type` currently must be `text`.
- `input_text` must be 500-3000 characters.
- Unsafe HTML/script payloads are rejected.
- `duration_target` must be 30-90 seconds.
- `aspect_ratio` currently supports `9:16`.
- User list/detail endpoints expose only the creator's non-deleted projects unless the requester is admin.
- Admin list/detail endpoints can inspect all non-deleted projects by default.
- Delete is a soft delete and writes an audit log.
- Create writes an audit log.
- Storyboard generation writes `VideoScene` records, sets project status to `storyboard_ready`, and writes an audit log.
- Scene edits update one generated `VideoScene`, keep the project duration synchronized, and write an audit log.

Story draft request:

```json
{
  "prompt": "边城少年捡到会发光的旧书，被迫在家人和真相之间做选择",
  "genre": "fantasy",
  "tone": "high_energy",
  "duration_target": 60
}
```

Story draft response:

```json
{
  "title": "边城少年捡到会发光的旧书：短片剧情",
  "summary": "短剧情摘要",
  "input_text": "500 to 3000 characters",
  "duration_target": 60,
  "aspect_ratio": "9:16",
  "style_preset": "cinematic_story",
  "genre": "fantasy",
  "tone": "high_energy"
}
```

Story draft rules:

- User must be logged in and not banned.
- `prompt` is required, 10-300 characters, and unsafe HTML/script payloads are rejected.
- `genre` and `tone` are controlled option sets.
- `duration_target` must be 30-90 seconds.
- The generated `input_text` is designed to satisfy project creation length rules.
- External provider secrets are not accepted or stored.

Storyboard request:

```json
{
  "scene_count": 5
}
```

Storyboard rules:

- User must be logged in and not banned.
- Owner can generate storyboard scenes for own non-deleted projects; admin can use the same owner/admin detail permission path.
- `scene_count` is optional and must be 4-12 when supplied.
- If omitted, scene count is derived from `duration_target`.
- Existing scenes are replaced by the newly generated local storyboard.
- External provider secrets are not accepted or stored.

AI storyboard rules:

- `GET /api/video-projects/capabilities/` returns `ai_storyboard_configured`, `ai_storyboard_model`, `ai_agent_workflow_available`, `ai_agent_workflow_version`, and `local_storyboard_available`; it never returns provider URL or key.
- `POST /api/video-projects/{id}/storyboard/ai/` accepts the same optional `scene_count` field as local generation.
- 供应商地址、密钥、模型和超时仅来自服务端 `VIDEO_AI_*` 配置。`VIDEO_AI_PLANNING_TIMEOUT_SECONDS` 与 `VIDEO_AI_DIRECTING_TIMEOUT_SECONDS` 分别约束制作设定和原子镜头阶段，且不得低于 `VIDEO_AI_TIMEOUT_SECONDS`。
- `VIDEO_AI_THINKING_TYPE` 仅接受空字符串、`enabled` 或 `disabled`；为空时不发送 `thinking` 字段，以保持 OpenAI 兼容性。GLM-4.7 的结构化分镜任务建议使用 `disabled`，避免默认深度思考增加延迟。
- The provider URL must use HTTPS. The key is never accepted from the request, returned to the frontend, or written to audit logs.
- The project moves to `analyzing` while the synchronous provider request runs, then to `storyboard_ready` or `failed`.
- AI 模式先执行一次制作设定编排，在该阶段内依次完成剧情、角色、形象、场景、道具和台词拆解；原子镜头阶段按每批最多 6 个连续节拍串行生成。4-6 镜正常调用 2 次，7-12 镜正常调用 3 次。
- 第一次响应先经过本地确定性规范化和严格契约校验。本地规范化会清理越界台词引用、补全可安全推导的角色形象，并在台词文本密度合法时按比例压缩目标时长与停顿，使每个节拍的计划音频不超过单镜时长；该过程不删减或改写台词。
- 若唯一错误为台词正文密度超限，流程直接调用一次台词预算精编 Agent；其他结构错误只允许调用一次制作设定结构修复 Agent。结构修复后若仅剩台词密度错误，可再调用一次台词预算精编 Agent。台词精编响应只能覆盖诊断列出的全部台词 ID，且只允许返回 `text`、`subtitle_text`、`target_duration_ms` 和 `pause_after_ms`；后端将这些字段合并回原计划，拒绝遗漏、额外 ID 或未授权字段。两个制作设定修复阶段都不得循环，修复结果必须再次本地规范化并严格校验。
- 每个镜头批次只接收本批节拍及其引用的角色、形象、地点、道具和台词，第二批起还接收上一批末镜的结束状态、连续性锚点、转场和实体状态。每批响应立即按本批制作设定严格校验；失败时只允许低温修复当前批次一次，已通过批次不会重跑。所有批次合并后仍须通过全片镜头数和引用关系终检。供应商调用总数为 `1 次策划 + 0/1 次结构修复 + 0/1 次台词精编 + ceil(scene_count / 6) 次镜头生成 + 每个失败镜头批次最多 1 次修复`；12 镜正常为 3 次，全部有界修复均触发时最多 7 次。
- 制作设定中的角色、形象版本、地点、道具和台词单元使用全局唯一稳定 ID。每个节拍必须明确引用地点、出镜角色、对应形象、道具和 0-4 个台词单元；每个出镜角色必须且只能引用一个形象版本。静默节拍不得超过总节拍数的三分之一。
- 工作流 2.2 在制作设定通过校验后确定性生成 `visual_world_model`，不增加供应商调用。`style_bible` 固定项目级画幅、媒介、视觉风格和一致性策略；`character_models` 按 `character_id + look_id` 锁定身份、年龄体态、面容发型、服装、标志特征和配色；`scene_models` 按 `location_id` 锁定地理结构、视觉地标、时间天气、光照配色、镜头轴线和接地规则；`prop_models` 锁定道具外观、归属和连续性规则。每个模型保存可逐字复用的 `canonical_prompt` 和不含原文的 `anchor_fingerprint`。全局物理规则禁止肢体异常及人物、衣物、道具、环境穿透，逻辑规则禁止未引用实体出现、无因瞬移、复制、消失或状态复原。
- 每个镜头必须完整复用对应节拍的 `location_id`、`character_ids`、`look_ids`、`prop_states` 和 `dialogue_unit_ids`，并包含剧情功能、起止状态、连续性锚点、衔接动作和动态提示词。镜头不得改写已拆解的旁白或字幕。
- 每个 `VideoScene.agent_metadata.continuity_contract` 记录绑定的人物模型、场景模型、允许实体、上一镜 `end_state`、本镜必需起止状态及物理/逻辑规则。图片与视频提示词必须注入该契约和防穿模负面约束；相邻镜头形象变化若未说明换装或时间变化，质量报告标记为风险。
- `visual_continuity_plan` 将相邻且共享地点与角色形象的镜头编为连续组，并逐镜记录 `relationship_to_previous`、`inherits_from_scene_no`、不可变资产锚点、唯一视觉差量、镜别、机位、屏幕运动方向和转场匹配方式。首镜建立基准，后续镜头必须明确属于动作承接、同场景主体切换、地点转场或形象转场。
- 台词单元记录说话者、类型、情绪、目标时长、停顿和声音档案标识；当前单声道配音流程允许每镜引用 0-4 个同一说话者的台词单元，其文本密度、目标时长与停顿合计不得超过五秒片段的承载能力。静默镜头不调用 TTS、不生成字幕块，成片阶段使用静音占位。
- 图片提示词、视频提示词和旁白脚本由本地确定性适配器分别生成。图片提示词采用“视觉圣经 + 人物/场景/道具不可变锚点 + 上一镜关系 + 本镜唯一差量 + 构图执行 + 负面约束”的固定优先级编译，并限制在当前 GLM 图片接口的 1000 字符上限内。质量报告检查总时长、模型时长差、单镜多场景、角色形象错配、未知道具、未知台词、台词时长溢出、状态链、无解释形象变化、显式物理异常和缺失转场。文本门禁不能证明实际图片或视频像素没有身份漂移、穿模或违反常理，因此生成后仍标记逐镜视觉语义复核要求。
- 逐镜视频请求通过 `VIDEO_CLIP_FPS` 显式提交 30 或 60 FPS，默认 30 FPS；最终成片仍对每个视频或静态图片段执行 `fps=VIDEO_RENDER_FPS` 过滤和恒定帧率编码后再拼接。供应商实际返回帧率可以不同，但不会直接原样进入最终成片时间轴。
- Existing scenes are replaced only after a complete valid response; failures preserve previous scenes and can be retried.
- If provider durations do not add up to the project target, durations are normalized deterministically.

Durable AI storyboard job rules:

- `POST /api/video-projects/{id}/storyboard/jobs/` validates the same optional `scene_count` field and returns a queued job.
- Only one `queued` or `running` AI storyboard job may exist per project.
- Job states are `queued`, `running`, `succeeded`, `failed`, and `canceled`.
- `GET /api/video-projects/{id}/storyboard/jobs/latest/` restores polling state after page reload.
- `GET /api/video-generation-jobs/{id}/` is owner/admin only; unrelated users receive not-found behavior.
- `POST /api/video-generation-jobs/{id}/retry/` 通常只在 `attempt_count < max_attempts` 时重新排队；视频异步查询超时且已保存供应商任务编号时，允许在普通重试上限后恢复同一外部任务，不重复提交当前镜头。
- 任务响应通过 `can_resume_provider_task` 区分普通重试和供应商异步任务恢复；恢复成功后继续处理尚未提交的后续镜头。
- Defaults are three attempts, two-second worker polling, and five-minute stale-job recovery; all are server-configurable.
- Worker crashes do not delete scenes. Stale running jobs return to the queue or fail after the retry limit.
- Job create and status transitions write `video_job` audit events.

素材能力与元数据规则：

- `GET /api/video-projects/capabilities/` 额外返回连续性、参考帧、视觉复核、局部重拍额度、帧率、旁白质量和本地渲染能力，只描述服务能力，不暴露供应商地址、密钥、图片内容或转写正文。
- 图片和视频任务创建请求可在 `regenerate=true` 时携带 `scene_ids`，只重新生成指定的 1-12 个分镜。指定分镜必须属于当前项目，且对应 `ready` 画面已被人工标记为需要重拍。
- 局部重拍不占整批素材任务额度，改为按实际镜头数受 `VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT` 和 `VIDEO_VISUAL_REGENERATION_PER_SCENE_LIMIT` 双重限制；任务、分镜 ID 和额度消耗保留在审计元数据中。
- 图片素材 `metadata` 保存提示词摘要、适配策略与版本、资产锚点摘要、连续镜头组、上一镜关系、继承来源、参考模式和视觉复核状态，不保存完整提示词或图片 Base64。当前 `reference_mode=text_only_canonical_anchors` 表示图片供应商只接收规范文本锚点，不能被解释为已使用角色参考图。
- 启用 `VIDEO_CLIP_USE_SCENE_IMAGE` 时，视频任务使用同分镜最新的 `ready` 图片；只接受内容与 MIME 一致的 PNG/JPEG，大小上限由 `VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES` 控制且不得超过 5MB。
- 启用 `VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME` 且本地 FFmpeg 可用时，每个成功逐镜视频都提取一张 JPEG 尾帧。尾帧与视频使用可推导的同目录文件名，视频替换、任务失败、项目删除和素材清理时同步删除，不新增数据库表或公开下载地址。
- 第二镜起先读取上一分镜最新 `ready` 视频的 `metadata.tail_frame`；尾帧文件通过路径边界、大小和 JPEG 内容校验后作为本镜单参考图。上一镜视频或尾帧不可用时继续尝试本镜静态图，不因此直接判定任务失败。
- 视频请求可临时携带 Base64 `image_url`。素材 `metadata` 只保存 `reference_frame_used`、模式、引用素材 ID、来源分镜号、SHA-256、完整降级原因列表和尾帧提取结果，不保存 Base64 正文或尾帧内部存储路径。
- `reference_frame_mode` 当前可为 `previous_scene_tail_base64`、`scene_image_base64` 或 `text_to_video`。`reference_frame_fallback_reasons` 按发生顺序记录上一镜缺失、尾帧不可用、文件校验失败、本镜图片缺失等原因；兼容字段 `reference_frame_fallback_reason` 保存主要原因。
- 尾帧提取失败属于可降级能力，当前视频仍可进入 `ready`，但 `metadata.tail_frame.status=unavailable` 并记录不含敏感路径的原因；下一镜自动回退本镜静态图或文生视频。
- `audio` 素材的 `metadata.audio_quality` 包含 `version`、`status`、`issues` 和 `metrics`；指标包括 WAV 时长、采样率、声道、采样位宽、RMS/峰值 dBFS、静音比例和削波比例。
- 启用 `VIDEO_ASR_ENABLED` 且服务端配置有效时，旁白在波形通过后调用 `glm-asr-2512`；仅上传不超过 25MB、时长不超过 30 秒的 WAV，`metadata.speech_quality` 保存规范化后的文本相似度、阈值、转写结果、模型和问题代码。
- ASR 默认关闭；未配置、超过供应商限制或调用失败时，旁白仍可进入 `ready`，但 `speech_quality.status=needs_review`，必须由项目所有者或管理员人工试听。
- `PATCH /api/video-assets/{id}/audio-review/` 接受 `{"decision":"approved"}` 或 `{"decision":"rejected"}`。接口仅允许复核波形已通过的 `ready` 音频，结果写入 `metadata.audio_review`；审计日志记录决定、操作者和素材标识，不记录旁白或转写正文。
- `PATCH /api/video-assets/{id}/visual-review/` 仅允许复核 `ready` 图片或视频。通过请求使用 `{"decision":"approved"}`；拒绝时必须附带 `issue_codes`，可选问题包括人物身份、服装、场景、道具、肢体、穿模、物理运动、镜间连续性和构图。结果写入 `metadata.visual_review` 并记录审核审计，不保存图像 Base64。

最终成片任务规则：

- `POST /api/video-projects/{id}/render/jobs/` 创建本地 FFmpeg 渲染任务，`GET` 返回该项目最近一次渲染任务。
- 每个分镜至少需要一份人工视觉复核通过的逐镜视频或图片，项目必须已有可用 SRT 字幕；独立旁白可缺失，缺失部分使用静音占位。
- 渲染优先采用视觉复核通过的视频；视频未通过或尚未通过时，可回退到同镜视觉复核通过的静态图。未复核和已拒绝素材不得进入成片。
- 独立旁白若存在，必须同时满足 `audio_quality.status=passed`，以及 `speech_quality.status=passed` 或 `audio_review.status=approved`；人工 `rejected` 覆盖 ASR 通过状态。未质检的历史旁白或波形失败旁白必须重新生成后才能进入成片。
- 渲染过程不读取逐镜视频内嵌音轨，避免供应商生成的不可控语音进入成片。
- 成片写入项目级 `final_video` 素材，成功后项目状态为 `completed`；修改分镜或替换相关素材后，旧成片转为 `stale`。
- 渲染任务复用统一任务状态、所有者/管理员权限、重试、陈旧任务恢复、审计和鉴权下载机制。

Scene update request:

```json
{
  "title": "Opening rescue",
  "visual_prompt": "Vertical cinematic frame, rain-soaked courier running through the old city.",
  "narration_text": "He has one hour to cross the flooded city.",
  "subtitle_text": "One hour before sunrise",
  "duration_seconds": 11,
  "camera_direction": "Tracking shot following the courier",
  "mood": "urgent"
}
```

Scene update rules:

- User must be logged in and not banned.
- Owner can edit scenes in an own non-deleted project; admin uses the same detail permission path.
- The project must be in `storyboard_ready` status.
- At least one editable field is required; unknown and read-only fields are ignored by the serializer.
- `duration_seconds` must be 1-30, and the resulting storyboard total must remain 30-90 seconds.
- Text fields reject unsafe HTML/script payloads.
- A successful update records a `video_scene` / `update` audit event.

## 7. Core Data Models

### User

Fields include:

- `username`
- `nickname`
- `avatar`
- `bio`
- `role`
- `phone`
- `is_banned`
- Django auth fields such as `email`, `is_staff`, `is_superuser`, `last_login`, `date_joined`.

Roles:

- `reader`
- `author`
- `reviewer`
- `admin`

### Category

- `name`
- `slug`
- `parent`
- `sort_order`
- `is_active`

Admin category endpoints:

- `GET /api/admin/categories/`
- `POST /api/admin/categories/`
- `GET /api/admin/categories/{id}/`
- `PATCH /api/admin/categories/{id}/`
- `PATCH /api/admin/categories/{id}/status/`

Rules:

- Only `role=admin`, `is_staff=True`, or `is_superuser=True` can access.
- Public `GET /api/categories/` remains unchanged and returns active categories only.
- `slug` must be unique.
- A category cannot use itself or its descendant as parent.

### Novel

- Author and category.
- Cover, description.
- `status`: `serializing`, `completed`, `paused`, `removed`.
- `audit_status`: `draft`, `pending`, `reviewing`, `approved`, `rejected`.
- `reviewer`, `reviewed_at`.
- Statistics: word/view/collect/comment/rating.
- Latest chapter fields.
- `is_featured`.

### Chapter

- Novel relation.
- Title, chapter number, content.
- Word count, free/price.
- `status`: `draft`, `published`, `hidden`.
- `audit_status`: `pending`, `reviewing`, `approved`, `rejected` plus project history may include draft-like flows.
- `reviewer`, `reviewed_at`, `published_at`.

### Bookshelf / ReadingHistory

- Bookshelf unique per `user + novel`.
- Reading history records user, novel, chapter, position, read time.

### Comment

- User, novel, optional chapter, optional parent.
- Content, like count.
- Status: `normal`, `hidden`, `deleted`.

### Ranking

- Ranking type and ranking item.
- Ranking item points to novel, rank, score, calculated time.

Admin ranking endpoints:

- `GET /api/admin/ranking-types/`
- `POST /api/admin/ranking-types/`
- `GET /api/admin/ranking-types/{id}/`
- `PATCH /api/admin/ranking-types/{id}/`
- `PATCH /api/admin/ranking-types/{id}/status/`
- `GET /api/admin/ranking-items/`
- `POST /api/admin/ranking-items/`
- `GET /api/admin/ranking-items/{id}/`
- `PATCH /api/admin/ranking-items/{id}/`

Rules:

- Only `role=admin`, `is_staff=True`, or `is_superuser=True` can access.
- Public `GET /api/rankings/` remains unchanged and only returns active ranking types.
- Ranking type `code` must be unique.
- Ranking items can only point to public approved novels that are not removed.
- A ranking snapshot cannot contain duplicate `novel` or duplicate `rank` under the same ranking type and `calculated_at`.
- Automatic ranking calculation is not part of the first pass.

### NovelRating

- Unique per `user + novel`.
- Score 1-5, optional comment.
- Updates Novel `rating_score` and `rating_count`.

### AuditLog

- `content_type`: novel/chapter/user/category/comment/ranking/video project domains.
- `object_id`.
- `reviewer`.
- `action`: submit/claim/approve/reject/create/update/status_update/delete and related operation actions.
- `from_status`, `to_status`, `reason`, `created_at`.

Author detail responses:

- `GET /api/author/novels/{id}/` includes `audit_logs` ordered by `created_at` descending.
- `GET /api/author/chapters/{id}/` includes `audit_logs` ordered by `created_at` descending.
- Each log exposes only reviewer `id`, `username`, and `nickname`; email, phone, token, and password are never returned.
- Ownership follows the existing author detail permission: authors can access only their own content, while admins retain elevated access.

### VideoProject

- Owner user.
- Source type: `text`, `chapter`, `novel`.
- Optional source novel/chapter references.
- Source title and source excerpt hash.
- Input text for text-sourced projects.
- Title, summary, style preset, target duration, aspect ratio.
- Status: `draft`, `analyzing`, `storyboard_ready`, `asset_generating`, `rendering`, `completed`, `failed`, `canceled`.
- Failure reason.
- `agent_workflow`：工作流版本、阶段状态、内部子 Agent、制作设定、视觉世界模型、各阶段用量和质量报告；2.0 制作设定包含角色、形象版本、地点、道具、台词单元、连续性规则和剧情节拍，2.1 增加人物模型卡、场景空间模型、镜头状态链、物理常理规则和固定帧率策略，2.2 增加视觉圣经、道具模型、连续镜头分组、上一镜谱系、不可变资产锚点、逐镜视觉差量和生成后视觉复核策略。分镜编辑后统一标记为 `stale`。第一次模型响应进入严格序列化校验前，先经过本地确定性结构规范化：删除节拍号越界的台词单元并重建冗余台词引用；按单镜预算归一化合法台词的目标时长与停顿；角色必填字段完整但缺少形象版本时，基于该角色已有身份、稳定外观和项目视觉风格补充默认连续形象，同时清理无定义形象引用并补入对应出镜节拍。若仍不合法，工作流按错误类型最多执行一次结构修复和一次台词预算精编，并在每次响应后重新规范化、严格校验。镜头导演阶段记录批次大小、批次数、批次修复次数和合并用量，质量报告记录全部实际供应商调用数。修复报告只记录调用次数和修复数量，不记录被删除文本、角色正文或校验输入。
- Soft delete via `deleted_at`.

当前实现支持 `text`、`chapter` 和 `novel` 三种来源，并保存创建时的来源快照。

### VideoScene

- Project relation.
- Scene number.
- Title, visual prompt, narration, subtitle, duration, camera direction, mood.
- Status: `draft`, `ready`, `failed`.
- Failure reason.
- `agent_metadata`：剧情功能、角色/形象/地点引用、逐镜道具状态、台词单元引用、起止状态、连续性锚点、转场和 `visual_plan`；`prompt_adapter` 分别保存图片与视频提示词、编译策略、版本和资产锚点摘要，`audio_script` 保存锁定旁白脚本。人工编辑相关字段后移除对应适配结果并标记为 `stale`。
- Unique per `project + scene_no`.

当前实现支持本地或供应商 AI 分镜生成、逐镜编辑，以及图片、视频、旁白、字幕和最终成片素材的失效联动。

## 8. Data Change Rules

When adding model fields:

1. Define user-facing purpose.
2. Define null/default behavior.
3. Add indexes only for real query patterns.
4. Generate migration.
5. Document rollback risk.
6. Update serializers/admin/tests/docs.

When changing statuses:

1. Preserve existing values.
2. Add choices without breaking old data.
3. Update frontend display mapping.
4. Update admin filters.
5. Add regression tests for all transitions.

## 9. API Compatibility Rules

Do not change these without explicit migration plan:

- URL paths.
- HTTP methods.
- Response envelope.
- Pagination fields.
- Public/private auth requirement.
- Field names in JSON.
- Meaning of status values.

Allowed additive changes:

- Add optional fields to response.
- Add optional query filters.
- Add new endpoint.
- Add new enum value if old values keep working.

Breaking changes require:

- Migration doc.
- Frontend compatibility plan.
- Test plan.
- Rollback plan.
