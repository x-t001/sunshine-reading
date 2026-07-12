# Sunshine Reading（阳光阅读）

阳光阅读是一个基于 Next.js、Django REST Framework 和 PostgreSQL 的小说阅读平台，当前已经从早期规范阶段进入可联调、可迭代的功能实现阶段。

## 当前状态

当前已完成：

- 公开阅读：分类、小说列表与详情、章节目录与阅读、榜单、搜索。
- 用户认证：注册、登录、刷新令牌、当前用户、资料修改。
- 读者功能：书架、阅读历史、评论、评分。
- 作者工作台：作品和章节创建、编辑、提交审核。
- 审核工作台：待审核、审核中、领取、通过、驳回、审核记录。
- 运营后台：用户、小说、章节、评论管理。
- 数据库：PostgreSQL 16、核心模型、开发种子数据。
- 前端本地默认封面兜底。
- 后端 API 基础冒烟测试。

## 技术栈

- 前端：`apps/web`，Next.js 16 App Router、React 19、TypeScript、Tailwind CSS 4。
- 后端：`services/api`，Django 6、Django REST Framework、SimpleJWT。
- 数据库：通过 Docker Compose 运行 PostgreSQL 16。
- API 响应封装：`{ "code": 0, "message": "success", "data": ... }`。

## 仓库结构

```text
apps/web                 Next.js 前端
services/api             Django 后端
docs/spec-coding         产品、流程、测试、API 与迭代文档
docs/ai-skills           AI 任务检查清单
.cursor/rules            AI 开发强制规则
docker-compose.yml       PostgreSQL 本地服务
```

## 本地启动

启动 PostgreSQL：

```powershell
docker compose up -d postgres
docker compose ps
```

安装后端依赖并执行迁移：

```powershell
cd services/api
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

写入开发种子数据：

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py seed_dev_data
```

启动后端：

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

启动前端：

```powershell
cd apps/web
npm.cmd install
npm.cmd run dev -- -H 0.0.0.0
```

前端默认 API 地址：

```text
http://127.0.0.1:8000/api
```

进行局域网或手机测试时，浏览器会自动将回环 API 主机替换为前端页面主机名。前后端都必须监听所有网络接口：

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
cd apps/web
npm.cmd run dev -- -H 0.0.0.0
```

仍可使用 `NEXT_PUBLIC_API_BASE_URL=http://<host-lan-ip>:8000/api` 显式覆盖 API 地址。根目录 `.env` 的 `DJANGO_ALLOWED_HOSTS` 和 `CORS_ALLOWED_ORIGINS` 必须包含局域网主机与前端来源。

短视频 AI 服务商凭据只能配置在 Django 服务端环境中。具体要求见 `docs/spec-coding/11-api-key-security.md`，禁止通过 `NEXT_PUBLIC_*` 变量暴露服务商密钥。

然后打开：

```text
http://<host-lan-ip>:3000
```

## 验证命令

后端：

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test common video_generation
```

前端：

```powershell
cd apps/web
npx.cmd tsc --noEmit --incremental false
npm.cmd run lint
npm.cmd run build
```

## AI 迭代流程

修改代码前：

1. 阅读 `AGENTS.md`。
2. 按数字顺序加载 `.cursor/rules`。
3. 从 `docs/ai-skills` 选择一个匹配的检查清单。
4. 遵循 `docs/spec-coding/09-iteration-workflow.md`。
5. 保持变更范围明确且可以验证。
6. 指导文档、规则、技能与提示模板的说明文字使用简体中文。

主要规划文档：

- `docs/spec-coding/01-current-state.md`
- `docs/spec-coding/03-roadmap.md`
- `docs/spec-coding/05-testing-plan.md`
- `docs/spec-coding/09-iteration-workflow.md`

## 已知待完善项

- 前端路由冒烟与 E2E 测试尚未完成。
- 运营前后端的分类与排行榜管理尚未完全实现。
- 作者查看审核反馈的体验仍需改进。
- 上传与媒体存储尚未设计，前端目前使用本地默认封面兜底。
- 搜索、通知、举报、敏感词过滤、推荐、支付和生产部署属于后续阶段。

## 修改边界

- 没有明确迁移计划时，不得修改 API 响应封装。
- 不得只依赖前端权限检查。
- 不得随意重命名数据库字段或路由。
- 不得将支付、推荐或部署工作混入普通功能迭代。
- 路由、权限、模型、测试或工作流假设变化时，必须更新 `docs/spec-coding`。
