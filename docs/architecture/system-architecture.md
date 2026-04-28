# 阳光阅读系统架构说明

## 文档目的
定义“阳光阅读 Sunshine Reading”整体技术架构、模块边界、部署拓扑和演进原则，作为实现阶段的技术基线。

## 当前阶段约束
- 本文档只定义架构，不初始化框架和服务。
- 禁止在当前阶段创建业务代码。

## 技术栈基线
- 前端：Next.js + TypeScript + Tailwind CSS
- 后端：Django + Django REST Framework
- 数据库：PostgreSQL
- 缓存：Redis
- 搜索：Meilisearch
- 文件存储：MinIO
- App 打包：Capacitor
- 部署：Docker Compose + Nginx

## 架构分层
### 1. 客户端层
- Web 客户端：使用 Next.js 渲染页面与交互。
- App 客户端：通过 Capacitor 封装 Web 能力，复用主要业务逻辑。

### 2. 接入层
- Nginx 负责 HTTPS 终止、反向代理、静态资源分发、基础限流。
- 所有外部请求统一从 Nginx 进入应用层。

### 3. 应用层
- Django + DRF 提供 REST API。
- 应用层按领域拆分模块（用户域、小说域、阅读域、互动域、运营域）。
- 业务逻辑放在服务层，接口层只负责协议转换与鉴权。

### 4. 数据与基础服务层
- PostgreSQL：持久化核心业务数据。
- Redis：缓存热点数据、会话和短期状态。
- Meilisearch：提供小说全文与多字段搜索能力。
- MinIO：存储封面图、插图、附件等对象资源。

## 核心数据流
1. 客户端请求经 Nginx 转发到 Django API。
2. API 完成 JWT 鉴权、参数校验、权限判断后进入服务层。
3. 服务层按需读取 PostgreSQL，并结合 Redis 缓存提升性能。
4. 搜索请求优先访问 Meilisearch，必要时回源数据库。
5. 文件上传下载通过 MinIO，数据库保存文件元信息与访问地址。

## 模块边界约束
- 前端只通过 API 调用后端，不直接访问数据库。
- 后端服务层不得依赖前端实现细节。
- 搜索索引与主库数据一致性由异步任务或事件机制保障。
- 缓存命中失败必须具备数据库回退逻辑。

## 非功能性要求
- 可用性：核心阅读链路需具备降级方案。
- 性能：热点章节、榜单、详情页可缓存并定义失效策略。
- 安全：全链路 HTTPS，敏感字段脱敏，关键操作审计。
- 可维护性：模块内聚、接口稳定、配置分环境管理。

## 部署拓扑（逻辑）
- `Nginx` -> `Frontend(Next.js)` + `Backend(Django API)`
- `Backend` -> `PostgreSQL` + `Redis` + `Meilisearch` + `MinIO`
- `Capacitor App` 复用 `Frontend` 与 `Backend API`

## 演进建议
- 优先保证 API 稳定与数据模型稳定，再扩大功能面。
- 搜索、推荐、付费等高复杂模块采用增量接入策略。
- 统一日志、监控、告警规范后再扩大并发容量。
