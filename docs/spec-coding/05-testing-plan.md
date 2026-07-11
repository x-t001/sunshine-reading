# Testing Plan

This document defines test layers, manual scenarios, and command checks for Sunshine Reading.

## 1. Test Layers

| Layer | Purpose | Current Status | Target |
| --- | --- | --- | --- |
| Backend system check | Catch Django config errors | Used manually | Required for every backend change |
| Backend unit tests | Test services/selectors/serializers | Limited | Add per domain |
| Backend API tests | Test endpoints, permissions, envelopes | Initial smoke coverage in `common.tests.ApiSmokeTests` | Add per-domain DRF APITestCase coverage |
| Frontend typecheck | Catch TypeScript errors | Used manually | Required for every frontend change |
| Frontend lint | Catch style/hooks issues | Used manually | Required for every frontend change |
| Frontend build | Catch production build issues | Used manually | Required before release |
| Frontend smoke/E2E | Verify routes and flows | Not systematic | Add Playwright or equivalent later |
| Mobile/LAN smoke | Verify phone access | Manual | Keep checklist |

## 2. Standard Commands

### Backend

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test common
.\.venv\Scripts\python.exe manage.py migrate
```

`common.tests.ApiSmokeTests` currently includes smoke coverage for public APIs, auth, reader writes, author/reviewer/admin permission boundaries, category/ranking management, AI chat validation, short-video project skeleton APIs, and admin operation audit-log creation.

### Frontend

```powershell
cd apps/web
npx.cmd tsc --noEmit --incremental false
npm.cmd run lint
npm.cmd run build
```

### Local Services

```powershell
docker compose up -d postgres
docker compose ps
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
cd apps/web
npm.cmd run dev -- -H 0.0.0.0
```

## 3. Public API Smoke Tests

```powershell
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/categories/
curl "http://127.0.0.1:8000/api/novels/?page=1&page_size=10"
curl http://127.0.0.1:8000/api/novels/1/
curl http://127.0.0.1:8000/api/novels/1/chapters/
curl http://127.0.0.1:8000/api/chapters/1/
curl http://127.0.0.1:8000/api/rankings/
```

Expected:

- HTTP 200.
- JSON envelope `{ code, message, data }`.
- Public APIs should not require token.

AI chat proxy validation:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/ai/chat/" `
  -ContentType "application/json" `
  -Body '{"api_key":"<provider-key>","api_url":"https://api.openai.com/v1/chat/completions","model":"gpt-4o-mini","messages":[{"role":"user","content":"请总结这本小说"}],"context":{"novel_title":"测试小说"}}'
```

Expected:

- Success uses `{ code, message, data }`.
- `data.answer` contains the assistant answer.
- Missing `api_key` or non-HTTPS `api_url` returns a unified validation error.

Short-video project backend validation:

```powershell
# Requires a logged-in JWT.
curl -X POST http://127.0.0.1:8000/api/video-projects/ `
  -H "Authorization: Bearer <access-token>" `
  -H "Content-Type: application/json" `
  -d "{\"source_type\":\"text\",\"title\":\"Story trailer\",\"input_text\":\"<500-3000 chars>\",\"duration_target\":60,\"aspect_ratio\":\"9:16\"}"

curl http://127.0.0.1:8000/api/video-projects/ `
  -H "Authorization: Bearer <access-token>"

curl http://127.0.0.1:8000/api/admin/video-projects/ `
  -H "Authorization: Bearer <admin-access-token>"
```

Expected:

- Logged-in users can create text-sourced private video project drafts.
- Project lists use the existing pagination envelope.
- Another user cannot read a project they do not own.
- Admin can inspect project drafts.
- Unsafe script/HTML input is rejected.

## 4. Auth Test Cases

| Case | Steps | Expected |
| --- | --- | --- |
| Register valid reader | POST `/api/auth/register/` | User returned, no password. |
| Login valid user | POST `/api/auth/login/` | Access, refresh, user returned. |
| Login bad password | POST invalid credentials | Unified error, no token. |
| Login banned user | Ban user then login | Clear banned message, no token. |
| Get me without token | GET `/api/users/me/` | 401 unified error. |
| Patch me | PATCH allowed fields | Updated safe profile. |
| Patch forbidden fields | PATCH role/is_staff | Fields ignored or rejected. |

## 5. Reader Flow Test Cases

| Case | Steps | Expected |
| --- | --- | --- |
| Public browse | Visit `/`, `/novels`, `/categories`, `/rankings` | Pages render without login. |
| Header category navigation | Click a category shortcut in the site header | Opens `/novels?category=<slug>`, filters the list, and marks the selected category active. |
| Novel detail | Visit `/novels/{id}` | Detail, chapters, comments, rating area render. |
| Read chapter | Visit `/novels/{id}/chapters/{chapterId}` | Content renders, previous/next works. |
| Reader settings | Toggle font/night/wide | Visual change persists after refresh. |
| Bookshelf login required | Visit `/bookshelf` without token | Login prompt. |
| Add bookshelf | Login, add novel | Button state changes, bookshelf list updates. |
| Reading history | Read chapter while logged in | History page contains record. |
| Comment create/delete | Login, post comment, delete own | List refreshes, no full page failure. |
| Rating create/update/delete | Login, score novel | Summary updates. |
| AI chat on novel detail | Open chat, enter provider key/model/question | Answer renders; API key is not persisted. |
| AI chat on reading page | Ask about current chapter | Uses current chapter context and does not block reading if it fails. |

## 6. Author Flow Test Cases

| Case | Steps | Expected |
| --- | --- | --- |
| Reader denied | Reader visits `/author` | No permission. |
| Author list | Author visits `/author/novels` | Own novels only. |
| Create novel | Submit valid form | Draft novel created. |
| Edit novel | Patch allowed fields | Stats/audit fields unchanged. |
| Submit novel | Submit draft/rejected | audit_status becomes pending. |
| Create chapter | Submit content | Draft/pending chapter created with word count. |
| Chapter draft autosave | Edit a chapter, wait one second, then reopen the page | A recovery prompt shows the latest browser-local draft. |
| Chapter draft discard | Open a page with a saved local draft and choose discard | Server-loaded values remain and the saved local draft is removed. |
| Chapter draft save success | Restore or edit a draft, then save successfully | Local draft is cleared only after the API save succeeds. |
| Chapter preview | Enter title, number, price mode, and paragraphs, then switch to preview | Current unsaved content renders in reading layout without an API call. |
| Submit chapter | Submit valid chapter | audit_status becomes pending. |
| Novel review feedback | Open author novel detail after reject | Audit history and latest rejection reason are visible. |
| Chapter review feedback | Open author chapter edit after reject | Audit history and latest rejection reason are visible. |
| Review history ownership | Reader or another author requests author detail | Unified permission/not-found response; no audit data leak. |

## 7. Reviewer Flow Test Cases

| Case | Steps | Expected |
| --- | --- | --- |
| Non-reviewer denied | Reader/author visits `/reviewer` | No permission. |
| Pending list | Reviewer opens pending novels/chapters | Pending tasks show. |
| Claim task | POST claim | audit_status reviewing, reviewer set. |
| My reviewing list | Open reviewing page | Claimed task appears for owner reviewer. |
| Other reviewer blocked | Other reviewer approves claimed task | Permission error. |
| Admin override | Admin approves claimed task | Success. |
| Reject task | Submit reason | audit_status rejected, AuditLog created. |
| Audit logs | Open audit logs | submit/claim/approve/reject visible. |

## 8. Admin Flow Test Cases

| Case | Steps | Expected |
| --- | --- | --- |
| Non-admin denied | Reader/author/reviewer visits `/admin` | No permission. |
| User list | Admin opens `/admin/users` | Users page renders. |
| Update role | Change role in list/detail | Role updates and refreshes. |
| Ban user | Ban non-superuser | `is_banned=true`, user cannot login. |
| Unban user | Unban user | `is_banned=false`. |
| Category management | List/create/update/enable-disable category | Category changes succeed for admin; reader is denied. |
| Ranking management | List/create/update ranking type and item | Ranking changes succeed for admin; reader is denied. |
| Video project inspection | List/detail short-video project drafts | Admin can inspect project drafts and failure/status fields. |
| Novel status | Set novel removed/serializing | Status updates. |
| Featured toggle | Toggle featured | `is_featured` updates. |
| Chapter status | Set hidden/published | Status updates. |
| Comment status | hidden/normal/deleted | Soft status changes only. |

## 9. Mobile/LAN Test Checklist

1. Find host LAN IP, for example `192.168.3.10`.
2. Backend runs on `0.0.0.0:8000`.
3. Frontend runs on `0.0.0.0:3000`.
4. Confirm root `.env` includes the LAN host and frontend origin in `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.
5. Start the frontend. The request layer automatically converts a loopback API host to the current LAN page hostname:

```powershell
npm.cmd run dev -- -H 0.0.0.0
```

6. Optionally set `NEXT_PUBLIC_API_BASE_URL=http://192.168.3.10:8000/api` as an explicit override.
7. Next config includes allowed dev origin for host IP when needed.
8. Phone opens `http://192.168.3.10:3000`.
9. Verify:
   - Home loads public data.
   - Login works.
   - Reader page settings work.
   - The browser does not request `127.0.0.1:8000` from the phone.
   - No backend 404 or CORS failure is caused by malformed API configuration.

## 10. Regression Checklist Before Completing A Task

- Public pages still work without login.
- Protected pages show login/forbidden states.
- API envelope is stable.
- Pagination still returns expected structure.
- Token expiration does not break public pages.
- No sensitive fields exposed.
- Model changes have migrations.
- Admin/reviewer/author role boundaries are intact.
- Docs are updated when routes, models, permissions, or commands change.
