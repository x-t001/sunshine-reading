# Development Flow

This document defines the standard flow for designing, implementing, testing, and documenting future work.

## 1. Standard Feature Flow

```mermaid
flowchart TD
  A[User request or backlog item] --> B[Clarify scope and forbidden actions]
  B --> C[Load AGENTS and rules 00-07]
  C --> D[Select matching docs/ai-skills checklist]
  D --> E[Read relevant spec-coding docs]
  E --> F[Inspect current code and routes]
  F --> G[Write implementation plan]
  G --> H{Needs model change?}
  H -- Yes --> I[Design migration and rollback risk]
  H -- No --> J[Implement minimal scoped changes]
  I --> J
  J --> K[Run targeted checks]
  K --> L{Checks pass?}
  L -- No --> M[Debug and fix]
  M --> K
  L -- Yes --> N[Update docs and handoff notes]
  N --> O[Final report: files, tests, risks]
```

## 2. Backend Feature Flow

```mermaid
flowchart TD
  A[Backend feature] --> B[Model and permission design]
  B --> C[Serializer request/response design]
  C --> D[Selector query design]
  D --> E[Service business logic design]
  E --> F[View handles request only]
  F --> G[URL registration]
  G --> H[Admin registration if needed]
  H --> I[Migration if model changed]
  I --> J[manage.py check + migrations]
  J --> K[API manual tests]
```

Rules:

- Query logic belongs in `selectors.py`.
- Write/business logic belongs in `services.py`.
- Validation belongs in serializers.
- Views should remain thin.
- Response envelope must remain stable.
- Protected endpoints must enforce backend permissions.

## 3. Frontend Feature Flow

```mermaid
flowchart TD
  A[Frontend feature] --> B[Define route and user role]
  B --> C[Add or update types]
  C --> D[Add or update API wrapper]
  D --> E[Build page/component states]
  E --> F[Implement loading/empty/error/forbidden]
  F --> G[Mobile layout check]
  G --> H[Typecheck + lint + build]
  H --> I[Manual browser/LAN verification]
```

Rules:

- API calls should use `apps/web/src/lib/api/request.ts`.
- Pages own data loading and state.
- Shared components should not perform hidden API calls.
- Public pages must work without login.
- Protected pages must handle missing/expired token clearly.

## 4. Content Review Flow

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> pending: author submit
  rejected --> pending: author resubmit
  pending --> reviewing: reviewer claim
  pending --> approved: reviewer/admin approve
  pending --> rejected: reviewer/admin reject
  reviewing --> approved: owner reviewer/admin approve
  reviewing --> rejected: owner reviewer/admin reject
  approved --> pending: future edit policy if enabled
  approved --> [*]
  rejected --> [*]
```

Audit rules:

- `submit`, `claim`, `approve`, `reject` should create `AuditLog`.
- `reviewer` and `reviewed_at` should preserve task ownership/history.
- Regular reviewer can only finish own `reviewing` task.
- Admin/staff/superuser can handle all.

## 5. Release Flow

```mermaid
flowchart LR
  A[Feature branch or local change] --> B[Static checks]
  B --> C[Backend checks]
  C --> D[Manual API tests]
  D --> E[Frontend smoke tests]
  E --> F[Docs update]
  F --> G[Version note]
  G --> H[Ready for commit/review]
```

Minimum release gates:

- Frontend:
  - `npx.cmd tsc --noEmit --incremental false`
  - `npm.cmd run lint`
  - `npm.cmd run build`
- Backend:
  - `.\.venv\Scripts\python.exe manage.py check`
  - `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` when no migration is expected.
  - `.\.venv\Scripts\python.exe manage.py migrate` when migration is expected.

## 6. Documentation Update Flow

After every meaningful feature:

1. Update `01-current-state.md` if routes/models/pages changed.
2. Update `02-feature-spec.md` if functional behavior changed.
3. Update `03-roadmap.md` if priority or completion changes.
4. Update `05-testing-plan.md` if test cases or commands changed.
5. Update `06-api-data-contract.md` if API or permissions changed.
6. Update `08-context-handoff-template.md` only if handoff format itself changes.

## 7. Stop Conditions

Stop and ask for explicit approval when:

- API envelope would change.
- Existing route path would change.
- Database field would be removed or renamed.
- Auth/token strategy would change.
- Payment/security-sensitive functionality is added.
- A destructive migration or data cleanup is needed.
- Existing user data would be modified outside a requested operation.
