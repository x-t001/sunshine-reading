# Sunshine Reading (阳光阅读)

Sunshine Reading is a novel reading platform built with Next.js, Django REST Framework, and PostgreSQL.

阳光阅读是一个小说阅读平台，当前已经从早期规范阶段进入可联调、可迭代的功能实现阶段。

## Current Status / 当前状态

Implemented:

- Public reading: categories, novel list/detail, chapter catalog/detail, rankings, search.
- Auth: register, login, refresh token, current user, profile update.
- Reader features: bookshelf, reading history, comments, ratings.
- Author workspace: novel/chapter create, edit, submit for review.
- Reviewer workflow: pending/reviewing queues, claim, approve, reject, audit logs.
- Operations backend: user management, novel management, chapter management, comment management.
- Database: PostgreSQL 16, Django models, development seed data.
- Frontend fallback assets: local default novel cover.
- Initial backend API smoke tests.

当前已完成：

- 公开阅读：分类、小说列表/详情、章节目录/阅读、榜单、搜索。
- 用户认证：注册、登录、刷新 token、当前用户、资料修改。
- 读者功能：书架、阅读历史、评论、评分。
- 作者工作台：作品和章节创建、编辑、提交审核。
- 审核工作台：待审核/审核中、领取、通过、驳回、审核记录。
- 运营后台：用户、小说、章节、评论管理。
- 数据库：PostgreSQL 16、核心模型、开发种子数据。
- 前端本地默认封面兜底。
- 后端 API 最小烟测。

## Tech Stack / 技术栈

- Frontend: `apps/web`, Next.js 16 App Router, React 19, TypeScript, Tailwind CSS 4.
- Backend: `services/api`, Django 6, Django REST Framework, SimpleJWT.
- Database: PostgreSQL 16 through Docker Compose.
- API envelope: `{ "code": 0, "message": "success", "data": ... }`.

## Repository Layout / 仓库结构

```text
apps/web                 Next.js frontend
services/api             Django backend
docs/spec-coding          Product, workflow, test, API, and iteration docs
docs/ai-skills            AI task checklists
.cursor/rules             Mandatory AI development rules
docker-compose.yml        PostgreSQL local service
```

## Local Development / 本地启动

Start PostgreSQL:

```powershell
docker compose up -d postgres
docker compose ps
```

Install backend dependencies and migrate:

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

Seed development data:

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py seed_dev_data
```

Start backend:

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

Start frontend:

```powershell
cd apps/web
npm.cmd install
npm.cmd run dev -- -H 0.0.0.0
```

Default frontend API base:

```text
http://127.0.0.1:8000/api
```

For LAN/mobile testing, the browser automatically replaces a loopback API host with the frontend page hostname. Start both services on all interfaces:

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
cd apps/web
npm.cmd run dev -- -H 0.0.0.0
```

`NEXT_PUBLIC_API_BASE_URL=http://<host-lan-ip>:8000/api` remains available as an explicit override. Add the LAN host and frontend origin to `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` in the root `.env`.

Then open:

```text
http://<host-lan-ip>:3000
```

## Verification / 验证命令

Backend:

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test common
```

Frontend:

```powershell
cd apps/web
npx.cmd tsc --noEmit --incremental false
npm.cmd run lint
npm.cmd run build
```

## AI Development Workflow / AI 迭代流程

Before changing code:

1. Read `AGENTS.md`.
2. Load `.cursor/rules` in numeric order.
3. Pick one matching checklist from `docs/ai-skills`.
4. Follow `docs/spec-coding/09-iteration-workflow.md`.
5. Keep changes scoped and verifiable.

Main planning documents:

- `docs/spec-coding/01-current-state.md`
- `docs/spec-coding/03-roadmap.md`
- `docs/spec-coding/05-testing-plan.md`
- `docs/spec-coding/09-iteration-workflow.md`

## Known Gaps / 已知待完善

- Frontend route smoke/E2E tests are not complete.
- Category and ranking management are not yet implemented in operations backend/frontend.
- Author review feedback visibility needs improvement.
- Upload/media storage is not designed; frontend currently uses a local default cover fallback.
- Search, notifications, reports, sensitive word filtering, recommendation, payment, and production deployment are future phases.

## Guardrails / 修改边界

- Do not change the API response envelope without an explicit migration plan.
- Do not rely on frontend-only permission checks.
- Do not rename database fields or routes casually.
- Do not mix payment/recommendation/deployment work into ordinary feature iterations.
- Update `docs/spec-coding` whenever routes, permissions, models, tests, or workflow assumptions change.
