# Current Project State

## 1. Technical Baseline

| Area | Current State |
| --- | --- |
| Frontend | `apps/web`, Next.js 16 App Router, React 19, TypeScript, Tailwind CSS 4. |
| Backend | `services/api`, Django 6, Django REST Framework, SimpleJWT. |
| Database | PostgreSQL 16 through `docker-compose.yml`. |
| Auth | JWT access token + refresh token, frontend stores tokens in `localStorage`. |
| API envelope | Current implementation uses `{ "code": 0, "message": "success", "data": ... }`. |
| Pagination | Current implementation uses DRF style `{ count, next, previous, results }` inside `data`. |
| Dev seed | `seed_dev_data` creates categories, authors, readers, novels, chapters, bookshelf/history/comments/rankings. |

Important mismatch:

- `.cursor/rules/03-api-contract.mdc` still describes an older `/api/v1` + `request_id` contract.
- Actual implemented code uses `/api/...` and `{ code, message, data }`.
- For current development, preserve the actual implemented contract unless a migration task explicitly changes it.

## 2. Backend Apps And Models

| App | Models / Responsibility |
| --- | --- |
| `common` | `TimeStampedModel`, `AuditLog`, operation/review audit logging, health check, response, pagination, exception handling, seed command. |
| `users` | Custom `User`, roles: `reader`, `author`, `reviewer`, `admin`; auth and admin user management. |
| `novels` | `Category`, `Novel`, `NovelRating`; public novel APIs, author novel APIs, reviewer/admin novel APIs. |
| `chapters` | `Chapter`; public chapter APIs, author chapter APIs, reviewer/admin chapter APIs. |
| `bookshelf` | `Bookshelf`, `ReadingHistory`; authenticated bookshelf and reading progress APIs. |
| `comments` | `Comment`; public comments, create/delete own comments, admin comment management. |
| `rankings` | `RankingType`, `RankingItem`; public ranking API. |
| `search` | App exists, currently no dedicated search model/API beyond novel keyword query. |
| `video_generation` | `VideoProject`, `VideoScene`; private text-based short-video project draft APIs and admin inspection. |

## 3. Backend API Surface

### Public APIs

- `GET /api/health/`
- `GET /api/categories/`
- `GET /api/novels/`
- `GET /api/novels/{id}/`
- `GET /api/novels/{novel_id}/chapters/`
- `GET /api/chapters/{id}/`
- `GET /api/rankings/`
- `GET /api/novels/{novel_id}/comments/`
- `GET /api/chapters/{chapter_id}/comments/`
- `GET /api/novels/{novel_id}/ratings/summary/`
- `POST /api/ai/chat/`

### Auth / User APIs

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/users/me/`
- `PATCH /api/users/me/`

### Reader APIs

- `GET /api/bookshelf/`
- `POST /api/bookshelf/`
- `DELETE /api/bookshelf/{novel_id}/`
- `GET /api/bookshelf/check/?novel_id=...`
- `GET /api/reading-history/`
- `POST /api/reading-history/`
- `POST /api/novels/{novel_id}/comments/`
- `DELETE /api/comments/{id}/`
- `POST /api/novels/{novel_id}/ratings/`
- `DELETE /api/novels/{novel_id}/ratings/`

### Video Generation APIs

- `GET /api/video-projects/`
- `POST /api/video-projects/`
- `GET /api/video-projects/{id}/`
- `DELETE /api/video-projects/{id}/`

### Author APIs

- `GET /api/author/novels/`
- `POST /api/author/novels/`
- `GET /api/author/novels/{id}/`
- `PATCH /api/author/novels/{id}/`
- `POST /api/author/novels/{id}/submit/`
- `GET /api/author/novels/{novel_id}/chapters/`
- `POST /api/author/novels/{novel_id}/chapters/`
- `GET /api/author/chapters/{id}/`
- `PATCH /api/author/chapters/{id}/`
- `POST /api/author/chapters/{id}/submit/`

### Reviewer APIs

- `GET /api/reviewer/novels/pending/`
- `GET /api/reviewer/novels/reviewing/`
- `GET /api/reviewer/novels/{id}/`
- `POST /api/reviewer/novels/{id}/claim/`
- `POST /api/reviewer/novels/{id}/approve/`
- `POST /api/reviewer/novels/{id}/reject/`
- `GET /api/reviewer/chapters/pending/`
- `GET /api/reviewer/chapters/reviewing/`
- `GET /api/reviewer/chapters/{id}/`
- `POST /api/reviewer/chapters/{id}/claim/`
- `POST /api/reviewer/chapters/{id}/approve/`
- `POST /api/reviewer/chapters/{id}/reject/`
- `GET /api/reviewer/audit-logs/`

### Admin APIs

- `GET /api/admin/users/`
- `GET /api/admin/users/{id}/`
- `PATCH /api/admin/users/{id}/role/`
- `POST /api/admin/users/{id}/ban/`
- `POST /api/admin/users/{id}/unban/`
- `GET /api/admin/categories/`
- `POST /api/admin/categories/`
- `GET /api/admin/categories/{id}/`
- `PATCH /api/admin/categories/{id}/`
- `PATCH /api/admin/categories/{id}/status/`
- `GET /api/admin/ranking-types/`
- `POST /api/admin/ranking-types/`
- `GET /api/admin/ranking-types/{id}/`
- `PATCH /api/admin/ranking-types/{id}/`
- `PATCH /api/admin/ranking-types/{id}/status/`
- `GET /api/admin/ranking-items/`
- `POST /api/admin/ranking-items/`
- `GET /api/admin/ranking-items/{id}/`
- `PATCH /api/admin/ranking-items/{id}/`
- `GET /api/admin/novels/`
- `GET /api/admin/novels/{id}/`
- `PATCH /api/admin/novels/{id}/status/`
- `PATCH /api/admin/novels/{id}/featured/`
- `GET /api/admin/chapters/`
- `GET /api/admin/chapters/{id}/`
- `PATCH /api/admin/chapters/{id}/status/`
- `GET /api/admin/comments/`
- `GET /api/admin/comments/{id}/`
- `PATCH /api/admin/comments/{id}/status/`
- `GET /api/admin/video-projects/`
- `GET /api/admin/video-projects/{id}/`

Legacy or overlapping review APIs also exist under `/api/admin/novels/pending/`, `/approve/`, `/reject/` and chapter equivalents. Future work should decide whether admin review remains separate or delegates to reviewer flow.

## 4. Frontend Pages

### Public / Reader

- `/`
- `/novels`
- `/novels/[id]`
- `/novels/[id]/chapters/[chapterId]`
- `/categories`
- `/rankings`
- `/search`
- `/login`
- `/register`
- `/profile`
- `/bookshelf`
- `/history`

### Author

- `/author`
- `/author/novels`
- `/author/novels/create`
- `/author/novels/[id]`
- `/author/novels/[id]/edit`
- `/author/novels/[id]/chapters`
- `/author/novels/[id]/chapters/create`
- `/author/chapters/[id]/edit`

### Reviewer

- `/reviewer`
- `/reviewer/novels`
- `/reviewer/novels/reviewing`
- `/reviewer/novels/[id]`
- `/reviewer/chapters`
- `/reviewer/chapters/reviewing`
- `/reviewer/chapters/[id]`
- `/reviewer/audit-logs`

### Admin / Operations

- `/admin`
- `/admin/users`
- `/admin/users/[id]`
- `/admin/categories`
- `/admin/rankings`
- `/admin/novels`
- `/admin/novels/[id]`
- `/admin/chapters`
- `/admin/chapters/[id]`
- `/admin/comments`
- `/admin/comments/[id]`

User-facing label has been adjusted toward “运营后台”; route remains `/admin`.

## 5. Completed Functional Areas

| Domain | Completed |
| --- | --- |
| Public reading | Categories, clickable header category shortcuts with active state, novel list/detail, chapter catalog/detail, rankings, search by keyword. |
| Auth | Register, login, refresh token, current user, profile update. |
| Reader account | Bookshelf, reading history, reading progress sync, profile. |
| Comments | Public list, logged-in create, own delete, admin moderation. |
| Ratings | Summary, create/update own rating, delete own rating. |
| AI chat | First-pass OpenAI-compatible chat proxy and frontend chat panel on novel detail / chapter reading pages. |
| Short video generation | Backend first pass for text-sourced private video projects: project/scene models, create/list/detail/delete APIs, admin list/detail, audit logs, and smoke tests. No AI storyboard or media rendering yet. |
| Author workspace | Novel create/edit/submit, chapter create/edit/submit, local chapter draft recovery, chapter reading preview, list/detail pages, review history and rejection feedback. |
| Review workflow | Reviewer role, pending/reviewing lists, claim, approve, reject, audit logs. |
| Admin user management | List/detail, role update, ban/unban. |
| Admin category management | Backend API and `/admin/categories` frontend page for list/create/update/enable-disable. |
| Admin ranking management | Backend API and `/admin/rankings` frontend page for ranking types and ranking items. |
| Admin content management | Novel/chapter/comment list/detail/status actions, novel featured toggle. |
| Admin action audit logs | User role/ban/unban, category changes, ranking changes, novel status/featured, chapter status, and comment status actions now write `AuditLog` entries. |
| Django Admin | Chinese names and admin list/filter/search optimizations were added in prior work. |

## 6. Known Gaps

| Area | Gap |
| --- | --- |
| Media | Frontend now has a local default cover fallback; backend seed data may still contain fake external cover URLs; upload/media storage is not designed. |
| Short video generation | Backend project skeleton exists for pasted text only; AI storyboard generation, chapter source integration, frontend pages, assets, rendering, quota, and moderation are not implemented yet. |
| Search | No dedicated search index, highlight, suggestions, hot keywords, typo tolerance. |
| AI chat | First pass is non-streaming and user-supplied-key only; no server-side provider config, embeddings, RAG index, prompt templates per genre, or usage metering. |
| Categories | Admin category backend and frontend first pass exists; deeper validation tests remain open. |
| Rankings | Admin ranking backend and frontend first pass exists; automatic ranking calculation and delete/bulk management are not implemented yet. |
| Author drafts | Chapter drafts are stored in the current browser only; there is no server-side draft synchronization or cross-device recovery. |
| Notifications | No notification system for review result, comment reply, author events. |
| Security | Token stored in localStorage; acceptable for early dev, not ideal for production. |
| Moderation | No sensitive word filtering, reporting, comment like moderation, bulk actions. |
| Payments | No paid chapter purchase, wallet, order, membership, revenue. |
| Recommendation | No recommendation algorithm or personalized feeds. |
| Deployment | No production deployment docs, CI/CD, environment separation, observability. |
| Automated tests | Project relies heavily on manual checks; systematic backend/frontend/E2E tests are not complete. |
| Encoding | Public/reader core pages and reader API error messages have had a first UTF-8 cleanup pass; backend/admin/author/reviewer files may still need a controlled follow-up scan. |
| API docs | No generated OpenAPI/Swagger or versioned API documentation. |
| Data lifecycle | No backup/restore, data retention, audit export, soft delete strategy across all models. |

README status:

- Root `README.md` has been updated from the old documentation-only stage to the current implemented project state, startup commands, verification commands, and workflow pointers.

## 7. Current Verification Commands

Backend:

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
```

Frontend:

```powershell
cd apps/web
npx.cmd tsc --noEmit --incremental false
npm.cmd run lint
npm.cmd run build
```

Local services:

```powershell
docker compose up -d postgres
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
cd apps/web
npm.cmd run dev -- -H 0.0.0.0
```

LAN development note:

- Frontend can be accessed from phone via `http://<host-lan-ip>:3000`.
- When the configured API base uses localhost/loopback, the browser request layer automatically reuses the frontend page hostname with port `8000` for LAN clients.
- `NEXT_PUBLIC_API_BASE_URL=http://<host-lan-ip>:8000/api` can still explicitly override the API address.
- Root `.env` must allow the LAN host and `http://<host-lan-ip>:3000` CORS origin.
- Next 16 dev resource access needs `allowedDevOrigins` for the LAN host.
