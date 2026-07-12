# 测试计划

本文档定义 Sunshine Reading 的测试层级、手工场景与命令检查。

## 1. 测试层级

| 层级 | 目的 | 当前状态 | 目标 |
| --- | --- | --- | --- |
| 后端系统检查 | 发现 Django 配置错误 | 手工执行 | 每次后端变更都必须执行 |
| 后端单元测试 | 测试服务、选择器和序列化器 | 覆盖有限 | 按业务域补充 |
| 后端 API 测试 | 测试接口、权限和响应封装 | `common.tests.ApiSmokeTests` 已有初步冒烟覆盖 | 按业务域补充 DRF `APITestCase` 覆盖 |
| 前端类型检查 | 发现 TypeScript 错误 | 手工执行 | 每次前端变更都必须执行 |
| 前端代码检查 | 发现代码风格与 Hook 问题 | 手工执行 | 每次前端变更都必须执行 |
| 前端构建 | 发现生产构建问题 | 手工执行 | 发布前必须执行 |
| 前端冒烟或 E2E | 验证路由与流程 | 尚未系统化 | 后续增加 Playwright 或同类方案 |
| 移动端或局域网冒烟 | 验证手机访问 | 手工执行 | 保留检查清单 |

## 2. 标准命令

### 后端

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test common
.\.venv\Scripts\python.exe manage.py migrate
```

`common.tests.ApiSmokeTests` 当前覆盖公开 API、身份认证、读者写操作、作者/审核员/管理员权限边界、分类与排行榜管理、AI 对话校验、短视频项目基础 API 以及管理操作审计日志。

### 前端

```powershell
cd apps/web
npx.cmd tsc --noEmit --incremental false
npm.cmd run lint
npm.cmd run build
```

### 本地服务

```powershell
docker compose up -d postgres
docker compose ps
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
cd apps/web
npm.cmd run dev -- -H 0.0.0.0
```

## 3. 公开 API 冒烟测试

```powershell
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/categories/
curl "http://127.0.0.1:8000/api/novels/?page=1&page_size=10"
curl http://127.0.0.1:8000/api/novels/1/
curl http://127.0.0.1:8000/api/novels/1/chapters/
curl http://127.0.0.1:8000/api/chapters/1/
curl http://127.0.0.1:8000/api/rankings/
```

预期结果：

- HTTP 状态码为 200。
- JSON 使用 `{ code, message, data }` 响应封装。
- 公开 API 不需要令牌。

AI 对话代理校验：

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/ai/chat/" `
  -ContentType "application/json" `
  -Body '{"api_key":"<provider-key>","api_url":"https://api.openai.com/v1/chat/completions","model":"gpt-4o-mini","messages":[{"role":"user","content":"请总结这本小说"}],"context":{"novel_title":"测试小说"}}'
```

预期结果：

- 成功响应使用 `{ code, message, data }`。
- `data.answer` 包含助手回答。
- 缺少 `api_key` 或 `api_url` 不是 HTTPS 时返回统一校验错误。

短视频项目后端校验：

```powershell
# 需要已登录用户的 JWT。
curl -X POST http://127.0.0.1:8000/api/video-projects/story-draft/ `
  -H "Authorization: Bearer <access-token>" `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"边城少年捡到会发光的旧书，被迫在家人和真相之间做选择\",\"genre\":\"fantasy\",\"tone\":\"high_energy\",\"duration_target\":60}"

curl -X POST http://127.0.0.1:8000/api/video-projects/ `
  -H "Authorization: Bearer <access-token>" `
  -H "Content-Type: application/json" `
  -d "{\"source_type\":\"text\",\"title\":\"Story trailer\",\"input_text\":\"<500-3000 chars>\",\"duration_target\":60,\"aspect_ratio\":\"9:16\"}"

curl http://127.0.0.1:8000/api/video-projects/ `
  -H "Authorization: Bearer <access-token>"

curl -X POST http://127.0.0.1:8000/api/video-projects/<id>/storyboard/ `
  -H "Authorization: Bearer <access-token>" `
  -H "Content-Type: application/json" `
  -d "{\"scene_count\":5}"

curl http://127.0.0.1:8000/api/admin/video-projects/ `
  -H "Authorization: Bearer <admin-access-token>"
```

预期结果：

- 登录用户可以根据短创意生成 500 到 3000 字符的本地故事草稿。
- 登录用户可以创建以文本为来源的私有视频项目草稿。
- 项目所有者可以根据文本项目生成 4 到 8 个本地分镜。
- 项目所有者可以编辑分镜内容与时长，其他读者无法访问该分镜。
- 服务商 AI 分镜仅使用服务端配置，校验结构化输出，并在失败时保留现有分镜。
- 持久化分镜任务限制每个项目只能有一个活跃任务，按所有者或管理员控制可见性，限制重试次数，并支持 Worker 处理与过期任务恢复。
- 章节来源创建只暴露公开且已通过审核的章节或用户自己的章节，最多保存 3000 字符快照，并拒绝过短或不安全内容。
- 项目列表使用现有分页封装。
- 用户无法读取不属于自己的项目。
- 管理员可以检查项目草稿。
- 危险脚本或 HTML 输入会被拒绝。

## 4. 身份认证测试用例

| 用例 | 步骤 | 预期结果 |
| --- | --- | --- |
| 注册有效读者 | `POST /api/auth/register/` | 返回用户且不包含密码。 |
| 有效用户登录 | `POST /api/auth/login/` | 返回访问令牌、刷新令牌和用户。 |
| 错误密码登录 | 使用无效凭据发送 POST | 返回统一错误且不返回令牌。 |
| 被封禁用户登录 | 封禁用户后登录 | 返回明确的封禁提示且不返回令牌。 |
| 无令牌获取当前用户 | `GET /api/users/me/` | 返回统一的 401 错误。 |
| 更新当前用户资料 | PATCH 允许字段 | 返回更新后的安全资料。 |
| 更新禁止字段 | PATCH `role` 或 `is_staff` | 字段被忽略或请求被拒绝。 |

## 5. 读者流程测试用例

| 用例 | 步骤 | 预期结果 |
| --- | --- | --- |
| 公开浏览 | 访问 `/`、`/novels`、`/categories`、`/rankings` | 页面无需登录即可渲染。 |
| 顶部分类导航 | 点击站点顶部的分类快捷入口 | 打开 `/novels?category=<slug>`，筛选列表并标记选中分类。 |
| 小说详情 | 访问 `/novels/{id}` | 渲染详情、章节、评论和评分区域。 |
| 阅读章节 | 访问 `/novels/{id}/chapters/{chapterId}` | 渲染内容，上一章和下一章可用。 |
| 阅读设置 | 切换字体、夜间或宽屏模式 | 刷新后视觉设置仍保留。 |
| 书架需要登录 | 未携带令牌访问 `/bookshelf` | 显示登录提示。 |
| 加入书架 | 登录后加入小说 | 按钮状态变化，书架列表更新。 |
| 阅读历史 | 登录状态下阅读章节 | 历史页面出现记录。 |
| 创建与删除评论 | 登录后发表评论并删除自己的评论 | 列表刷新且页面不整体失败。 |
| 创建、更新与删除评分 | 登录后为小说评分 | 汇总数据更新。 |
| 小说详情 AI 对话 | 打开对话，输入服务商密钥、模型和问题 | 渲染回答，API Key 不持久化。 |
| 阅读页 AI 对话 | 针对当前章节提问 | 使用当前章节上下文，失败时不阻塞阅读。 |
| 视频项目列表需要登录 | 未携带令牌访问 `/video-projects` | 显示登录提示。 |
| 视频故事草稿 | 登录后访问 `/video-projects/create`，输入短创意并生成草稿 | 标题与故事文本被填充为有效项目输入。 |
| 创建视频项目 | 登录后在 `/video-projects/create` 提交有效文本 | 创建项目并打开详情页。 |
| 生成视频分镜 | 打开自己的 `/video-projects/[id]` 并生成分镜 | 页面刷新并显示 4 到 8 个分镜卡片，状态变为分镜就绪。 |
| AI 视频分镜 | 配置服务端服务商，打开自己的项目并点击 AI 生成 | 项目从分析中进入分镜就绪；格式错误的服务商输出显示失败并保留旧分镜。 |
| 持久化 AI 分镜任务 | 提交 AI 生成并保持详情页打开 | UI 显示排队或运行状态，轮询至成功或失败，并在剩余重试次数允许时提供重试。 |
| 章节来源视频项目 | 在 `/video-projects/create` 选择可访问章节 | 项目包含章节、小说引用和稳定来源快照，不列出不可访问草稿。 |
| 编辑视频分镜 | 编辑生成的分镜并保存 | 分镜卡片刷新，总时长保持在 30 到 90 秒，刷新后变更仍存在。 |
| 视频项目详情与删除 | 打开自己的 `/video-projects/[id]` 后删除 | 详情显示来源文本和分镜卡片或占位；删除后返回列表。 |

## 6. 作者流程测试用例

| 用例 | 步骤 | 预期结果 |
| --- | --- | --- |
| 拒绝读者访问 | 读者访问 `/author` | 返回无权限状态。 |
| 作者作品列表 | 作者访问 `/author/novels` | 只显示自己的小说。 |
| 创建小说 | 提交有效表单 | 创建小说草稿。 |
| 编辑小说 | PATCH 允许字段 | 统计和审计字段不变。 |
| 提交小说 | 提交草稿或被驳回小说 | `audit_status` 变为 `pending`。 |
| 创建章节 | 提交内容 | 创建带字数统计的草稿或待审核章节。 |
| 章节草稿自动保存 | 编辑章节，等待一秒后重新打开页面 | 恢复提示显示最新浏览器本地草稿。 |
| 丢弃章节草稿 | 打开存在本地草稿的页面并选择丢弃 | 保留服务端加载值，并删除本地草稿。 |
| 章节草稿保存成功 | 恢复或编辑草稿并成功保存 | 仅在 API 保存成功后清除本地草稿。 |
| 章节预览 | 输入标题、序号、付费模式和段落后切换预览 | 不调用 API，按阅读布局渲染未保存内容。 |
| 提交章节 | 提交有效章节 | `audit_status` 变为 `pending`。 |
| 小说审核反馈 | 小说被驳回后打开作者详情 | 显示审计历史和最新驳回原因。 |
| 章节审核反馈 | 章节被驳回后打开作者编辑页 | 显示审计历史和最新驳回原因。 |
| 审核历史归属 | 读者或其他作者请求作者详情 | 返回统一权限或不存在响应，不泄露审计数据。 |

## 7. 审核员流程测试用例

| 用例 | 步骤 | 预期结果 |
| --- | --- | --- |
| 拒绝非审核员访问 | 读者或作者访问 `/reviewer` | 返回无权限状态。 |
| 待审核列表 | 审核员打开待审核小说或章节 | 显示待审核任务。 |
| 领取任务 | POST 领取 | `audit_status` 变为 `reviewing` 并设置 `reviewer`。 |
| 我的审核中列表 | 打开审核中页面 | 任务显示给领取它的审核员。 |
| 阻止其他审核员 | 其他审核员尝试通过已领取任务 | 返回权限错误。 |
| 管理员覆盖 | 管理员通过已领取任务 | 操作成功。 |
| 驳回任务 | 提交原因 | `audit_status` 变为 `rejected` 并创建 `AuditLog`。 |
| 审计日志 | 打开审计日志 | 显示 `submit`、`claim`、`approve`、`reject`。 |

## 8. 管理员流程测试用例

| 用例 | 步骤 | 预期结果 |
| --- | --- | --- |
| 拒绝非管理员访问 | 读者、作者或审核员访问 `/admin` | 返回无权限状态。 |
| 用户列表 | 管理员打开 `/admin/users` | 渲染用户页面。 |
| 更新角色 | 在列表或详情中修改角色 | 角色更新并刷新。 |
| 封禁用户 | 封禁非超级用户 | `is_banned=true`，用户无法登录。 |
| 解封用户 | 解除封禁 | `is_banned=false`。 |
| 分类管理 | 列表、创建、更新、启用或停用分类 | 管理员操作成功，读者被拒绝。 |
| 排行榜管理 | 列表、创建或更新排行榜类型和条目 | 管理员操作成功，读者被拒绝。 |
| 视频项目检查 | 查看短视频项目草稿列表或详情 | 管理员可以检查项目草稿以及失败和状态字段。 |
| 小说状态 | 设置小说为下架或连载中 | 状态更新。 |
| 推荐切换 | 切换推荐状态 | `is_featured` 更新。 |
| 章节状态 | 设置为隐藏或已发布 | 状态更新。 |
| 评论状态 | 设置为 `hidden`、`normal` 或 `deleted` | 只进行软状态变更。 |

## 9. 移动端与局域网检查清单

1. 获取主机局域网 IP，例如 `192.168.3.10`。
2. 后端监听 `0.0.0.0:8000`。
3. 前端监听 `0.0.0.0:3000`。
4. 确认根目录 `.env` 的 `DJANGO_ALLOWED_HOSTS` 和 `CORS_ALLOWED_ORIGINS` 包含局域网主机与前端来源。
5. 启动前端，请求层会把回环 API 主机转换为当前局域网页面的主机名：

```powershell
npm.cmd run dev -- -H 0.0.0.0
```

6. 可选设置 `NEXT_PUBLIC_API_BASE_URL=http://192.168.3.10:8000/api` 作为显式覆盖。
7. 必要时确保 Next 配置允许主机 IP 的开发来源。
8. 手机打开 `http://192.168.3.10:3000`。
9. 验证：
   - 首页加载公开数据。
   - 登录正常。
   - 阅读页面设置正常。
   - 手机浏览器不会请求 `127.0.0.1:8000`。
   - 错误 API 配置不会导致后端 404 或 CORS 失败。

## 10. 完成任务前的回归清单

- 公开页面在未登录状态下仍可使用。
- 受保护页面会显示登录或无权限状态。
- API 响应封装保持稳定。
- 分页仍返回预期结构。
- 令牌过期不会破坏公开页面。
- 未暴露敏感字段。
- 模型变更包含迁移。
- 管理员、审核员与作者角色边界保持正确。
- 路由、模型、权限或命令发生变化时已更新文档。
