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
5. Local storyboard generation: create 4-8 deterministic scene drafts from pasted/generated text. First pass completed without external provider calls.
6. Storyboard scene editing: title, visual prompt, narration, subtitle, duration, camera direction, and mood. First pass completed with owner/admin checks and audit logging.
7. Provider-backed AI story/storyboard generation: server-configured storyboard generation, durable database queue, polling, bounded retry, stale-job recovery, local fallback, and token audit completed; provider-backed story drafting remains open.
8. Chapter source integration: public approved chapters, author-owned drafts, admin access, source snapshots, searchable frontend selection, and audit logging completed.
9. Image, TTS, and subtitle asset generation.
10. FFmpeg-based 9:16 MP4 render and download.
11. Quota, moderation, storage cleanup, and admin troubleshooting views.
12. Optional direct text-to-video provider evaluation after the storyboard/image/TTS/render path is stable.

Exit criteria:

- A user can create a private storyboard project from valid text or accessible chapter content.
- A user can generate a story draft from a short idea and use it as project input.
- A pasted-text project can generate reviewable scene drafts.
- Provider secrets are configured server-side and never stored from user input.
- Long-running jobs have visible queued/running/succeeded/failed states.
- Admin can inspect failed or unsafe projects.
- Real media rendering is gated by quota, storage, and moderation rules.

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
- Do not add real media rendering before storage, quota, cleanup, and moderation rules are designed.
- Do not persist user-supplied AI/media provider API keys.
