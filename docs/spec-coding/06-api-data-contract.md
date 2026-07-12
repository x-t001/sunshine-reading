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
- `POST /api/video-projects/from-chapter/`
- `POST /api/video-projects/story-draft/`
- `GET /api/video-projects/capabilities/`
- `GET /api/video-projects/{id}/`
- `POST /api/video-projects/{id}/storyboard/`
- `POST /api/video-projects/{id}/storyboard/ai/`
- `POST /api/video-projects/{id}/storyboard/jobs/`
- `GET /api/video-projects/{id}/storyboard/jobs/latest/`
- `PATCH /api/video-projects/{id}/scenes/{scene_id}/`
- `GET /api/video-generation-jobs/{id}/`
- `POST /api/video-generation-jobs/{id}/retry/`
- `DELETE /api/video-projects/{id}/`
- `GET /api/admin/video-projects/`
- `GET /api/admin/video-projects/{id}/`

Current implementation scope:

- Pasted text and permission-checked chapter projects are supported.
- Local story draft generation is available and does not call an external AI provider.
- Local storyboard generation is available and does not call an external AI provider.
- Server-configured OpenAI-compatible storyboard generation is available when all `VIDEO_AI_*` settings are valid.
- Durable storyboard jobs are processed by `python manage.py run_video_generation_worker`.
- No whole-novel source ingestion yet.
- No image, audio, subtitle, or video asset generation yet.
- Frontend list/create/detail pages exist.

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
- `scene_count` is optional and must be 4-8 when supplied.
- If omitted, scene count is derived from `duration_target`.
- Existing scenes are replaced by the newly generated local storyboard.
- External provider secrets are not accepted or stored.

AI storyboard rules:

- `GET /api/video-projects/capabilities/` returns `ai_storyboard_configured`, `ai_storyboard_model`, and `local_storyboard_available`; it never returns provider URL or key.
- `POST /api/video-projects/{id}/storyboard/ai/` accepts the same optional `scene_count` field as local generation.
- Provider URL, key, model, and timeout come only from `VIDEO_AI_API_URL`, `VIDEO_AI_API_KEY`, `VIDEO_AI_MODEL`, and `VIDEO_AI_TIMEOUT_SECONDS`.
- The provider URL must use HTTPS. The key is never accepted from the request, returned to the frontend, or written to audit logs.
- The project moves to `analyzing` while the synchronous provider request runs, then to `storyboard_ready` or `failed`.
- Provider output must contain exactly 4-8 validated scenes. Unsafe text and malformed JSON are rejected.
- Existing scenes are replaced only after a complete valid response; failures preserve previous scenes and can be retried.
- If provider durations do not add up to the project target, durations are normalized deterministically.

Durable AI storyboard job rules:

- `POST /api/video-projects/{id}/storyboard/jobs/` validates the same optional `scene_count` field and returns a queued job.
- Only one `queued` or `running` AI storyboard job may exist per project.
- Job states are `queued`, `running`, `succeeded`, `failed`, and `canceled`.
- `GET /api/video-projects/{id}/storyboard/jobs/latest/` restores polling state after page reload.
- `GET /api/video-generation-jobs/{id}/` is owner/admin only; unrelated users receive not-found behavior.
- `POST /api/video-generation-jobs/{id}/retry/` requeues failed jobs while `attempt_count < max_attempts`.
- Defaults are three attempts, two-second worker polling, and five-minute stale-job recovery; all are server-configurable.
- Worker crashes do not delete scenes. Stale running jobs return to the queue or fail after the retry limit.
- Job create and status transitions write `video_job` audit events.

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
- Soft delete via `deleted_at`.

Current implementation only creates `text` projects.

### VideoScene

- Project relation.
- Scene number.
- Title, visual prompt, narration, subtitle, duration, camera direction, mood.
- Status: `draft`, `ready`, `failed`.
- Failure reason.
- Unique per `project + scene_no`.

Current implementation defines the model but does not generate scenes yet.

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
