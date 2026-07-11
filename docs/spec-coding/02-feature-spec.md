# Feature Specification

This document defines the functional scope for Sunshine Reading. It separates implemented capabilities from planned gaps so future work can be scoped without re-reading the whole codebase.

## 1. Role Model

| Role | Meaning | Current Capabilities |
| --- | --- | --- |
| `reader` | Normal user | Browse public content, manage profile, bookshelf, history, comments, ratings. |
| `author` | Creator | Reader capabilities plus author workspace for novels and chapters. |
| `reviewer` | Content reviewer | Review center, pending/reviewing task handling, audit logs. |
| `admin` | Operations/admin | User management, content management, can also access elevated workflows. |
| `is_staff` / `is_superuser` | Django privileged flags | Treated as admin in backend permission checks. |

Role rule:

- Backend is the source of truth.
- Frontend only hides or shows entry points for UX.
- Every protected API must enforce permissions server-side.

## 2. Public Reading

### Implemented

- Home page pulls categories, recommended novels, rankings, latest novels.
- Category list.
- Novel list with pagination and filters.
- Novel detail with author/category/statistics/latest chapter/chapters/comments/rating/bookshelf state.
- Chapter detail with content, previous/next chapter navigation.
- Reader toolbar:
  - Font size.
  - Night mode.
  - Wide/narrow reading.
  - Reading progress.
- Search page uses public novel keyword query.
- Ranking page shows ranking types and top items.

### Planned

- Local cover assets or real upload-backed cover images.
- Better mobile reading typography tokens.
- Table of contents drawer in reader.
- Full-screen reader mode.
- Chapter prefetch and offline cache.
- Better search: suggestions, hot words, highlight, history.
- Better ranking categories and calculation schedule.

## 3. Authentication And Profile

### Implemented

- Register.
- Login.
- Refresh token.
- Current user API.
- Profile edit.
- Frontend login/register/profile pages.
- Token storage in localStorage.
- Logout clears local tokens.

### Planned

- Password reset.
- Change password.
- Email/phone verification.
- Secure cookie-based auth option for production.
- Device/session management.
- Login audit logs and rate limiting.

## 4. Bookshelf And Reading History

### Implemented

- Add/remove/check bookshelf.
- Bookshelf page with continue reading.
- Reading history list.
- Reading page reports progress.
- Local fallback progress through localStorage.

### Planned

- Bookshelf grouping.
- Sort/filter bookshelf.
- Batch remove.
- Cross-device progress conflict resolution.
- Last-read chapter display consistency after deleted/hidden chapters.

## 5. Comments

### Implemented

- Public novel comments.
- Public chapter comments.
- Create novel comment when logged in.
- Delete own comment through soft status change.
- Admin list/detail/status management.
- Replies can be displayed in limited form.

### Planned

- Reply UI for frontend.
- Likes.
- Reports.
- Sensitive word review.
- Bulk moderation.
- Comment notification.
- Richer threading and pagination for replies.

## 6. Ratings

### Implemented

- Rating summary.
- One rating per user per novel.
- Create/update/delete rating.
- Average rating and rating count maintained on Novel.
- Frontend rating panel on novel detail.

### Planned

- Rating distribution.
- Rating review list.
- Anti-spam controls.
- Weighted rating for rankings.

## 7. Author Workspace

### Implemented

- Author dashboard.
- Novel list, create, detail, edit.
- Chapter list, create, edit.
- Submit novel/chapter for review.
- Category selection in novel form.
- Permission checks: author/admin only.

### Planned

- Draft autosave.
- Rich text editor.
- Cover upload.
- Chapter preview.
- Bulk chapter import.
- Author statistics: views, collects, comments, ratings over time.
- Review feedback visibility and notifications.
- Revenue/paywall management when payment is added.

## 8. Reviewer Workflow

### Implemented

- `reviewer` role.
- Audit states: `draft`, `pending`, `reviewing`, `approved`, `rejected`.
- AuditLog model.
- Pending novel/chapter lists.
- Reviewing novel/chapter lists assigned to reviewer.
- Claim review task.
- Approve task.
- Reject task with reason.
- Audit logs page.
- Reviewer permissions.

### Planned

- Reviewer workload dashboard.
- Assignment rules.
- Bulk review operations.
- SLA/timeout rules for reviewing tasks.
- Review reason templates.
- Notification to author after approve/reject.
- Audit log export.

## 9. Admin / Operations

### Implemented

- Admin dashboard.
- User list/detail.
- Update user role.
- Ban/unban user.
- Novel list/detail/status/featured.
- Chapter list/detail/status.
- Comment list/detail/status.

### Planned

- Category management.
- Ranking type/item management.
- Audit policy management.
- Bulk content actions.
- Operational dashboard metrics.
- Data export.
- Admin action audit trail for user/content management.

## 10. Payment / Membership

### Not Implemented

This whole domain is intentionally not implemented yet.

Future modules:

- Wallet/account balance.
- Orders.
- Chapter purchase.
- Membership.
- Author revenue.
- Refunds.
- Payment provider integration.
- Entitlement checks in chapter detail.

Dependency:

- Requires clear business rules and security review before implementation.

## 11. Recommendation And Search

### Current

- Search is basic database keyword search through novel list.
- Ranking data exists but calculation is simple/static/dev-data-oriented.

### Planned

- Search app implementation.
- Keyword logs.
- Hot search.
- Search suggestions.
- Personalized recommendations.
- Ranking calculation jobs.
- Cache strategy.

## 12. Media And Assets

### Current

- Covers are URL strings.
- Dev data can point to fake or external placeholder images.

### Planned

- Local default cover assets.
- Upload backend.
- Storage abstraction: local filesystem for dev, object storage for production.
- Image validation.
- Thumbnail generation.
- Fallback image component.

## 13. Short Video Generation

### Current

- Design RFC exists at `10-short-video-generation-rfc.md`.
- Backend first pass exists for text-sourced private video project drafts.
- Implemented backend pieces: `VideoProject`, `VideoScene`, create/list/detail/delete APIs, admin list/detail APIs, soft delete, audit logs, and smoke tests.
- No frontend page, AI storyboard generation, media asset generation, or video rendering exists yet.

### Planned MVP

- Create a video project from accessible novel/chapter content.
- Generate story analysis and storyboard scenes.
- Save scene visual prompts, narration, subtitles, duration, mood, and status.
- Keep outputs as private project drafts in the first implementation.

### Later Phases

- Generate scene images.
- Generate narration audio.
- Generate subtitle assets.
- Compose 9:16 MP4 with FFmpeg.
- Add download and render retry.
- Add admin moderation, quota, provider usage logs, and storage cleanup.
- Evaluate direct text-to-video providers only after the storyboard/image/TTS/render path is stable.

### Rules

- Preserve the current `/api/` route base and `{ code, message, data }` response envelope.
- Do not store user-supplied provider API keys.
- Enforce backend source access checks for chapter/novel-based projects.
- Keep early outputs private until copyright and moderation policy is approved.

## 14. Non-Functional Requirements

| Category | Requirement |
| --- | --- |
| Performance | Lists must paginate; heavy content should not be embedded in list APIs. |
| Security | Protected APIs must use JWT and server-side role checks. |
| Reliability | Public pages must not white-screen when optional APIs fail. |
| Accessibility | Buttons need semantic labels, forms need clear labels and errors. |
| Mobile | Public reading flows must be mobile-first. Admin pages can use horizontal scroll tables. |
| Compatibility | Existing API envelope and route paths must remain stable unless a migration is planned. |

## 15. Acceptance Checklist For New Features

Every new feature spec must define:

- User role and permission.
- Page route, if frontend is involved.
- API route, method, request, response.
- Data model changes and migration risk.
- Empty/loading/error/forbidden states.
- Manual test cases.
- Automated test targets.
- Rollback plan.
- Documentation update location.
