# 阳光阅读数据库设计（第一版）

## 文档目的
定义“阳光阅读 Sunshine Reading”第一版核心数据模型、字段建议、关系约束与索引策略，为后续 Django 模型实现提供依据。

## 设计原则
- 命名统一使用英文 `snake_case`。
- 每个核心表包含 `id`、`created_at`、`updated_at`。
- 关系字段明确外键约束与删除策略。
- 高频查询字段必须有索引策略。

## 1. User（用户）
### 作用
- 存储平台账号基础信息与状态。

### 建议字段
- `id`
- `username`（唯一）
- `email`（唯一，可为空）
- `password_hash`
- `role`（reader/author/admin）
- `status`（active/blocked）
- `last_login_at`
- `created_at`
- `updated_at`

### 索引与约束
- 唯一索引：`username`、`email`
- 普通索引：`role`、`status`

## 2. Category（分类）
### 作用
- 定义小说分类体系。

### 建议字段
- `id`
- `name`
- `slug`（唯一）
- `sort_order`
- `is_active`
- `created_at`
- `updated_at`

### 索引与约束
- 唯一索引：`slug`
- 普通索引：`sort_order`、`is_active`

## 3. Novel（小说）
### 作用
- 存储小说主体信息。

### 建议字段
- `id`
- `title`
- `slug`（唯一）
- `author_id`（关联 User）
- `category_id`（关联 Category）
- `cover_url`
- `summary`
- `status`（draft/published/offline）
- `word_count`
- `is_vip`
- `published_at`
- `created_at`
- `updated_at`

### 索引与约束
- 唯一索引：`slug`
- 外键：`author_id` -> `user.id`，`category_id` -> `category.id`
- 普通索引：`status`、`category_id`、`published_at`

## 4. Chapter（章节）
### 作用
- 存储小说章节内容与章节状态。

### 建议字段
- `id`
- `novel_id`（关联 Novel）
- `chapter_no`
- `title`
- `content`
- `word_count`
- `is_vip`
- `price`
- `status`（draft/published/offline）
- `published_at`
- `created_at`
- `updated_at`

### 索引与约束
- 唯一约束：`(novel_id, chapter_no)`
- 外键：`novel_id` -> `novel.id`
- 普通索引：`status`、`published_at`

## 5. Bookshelf（书架）
### 作用
- 存储用户收藏到书架的小说关系。

### 建议字段
- `id`
- `user_id`（关联 User）
- `novel_id`（关联 Novel）
- `is_pinned`
- `added_at`
- `created_at`
- `updated_at`

### 索引与约束
- 唯一约束：`(user_id, novel_id)`
- 外键：`user_id` -> `user.id`，`novel_id` -> `novel.id`
- 普通索引：`user_id`、`added_at`

## 6. ReadingHistory（阅读历史）
### 作用
- 记录用户阅读进度，支持断点续读。

### 建议字段
- `id`
- `user_id`（关联 User）
- `novel_id`（关联 Novel）
- `chapter_id`（关联 Chapter）
- `progress_percent`
- `last_read_at`
- `created_at`
- `updated_at`

### 索引与约束
- 唯一约束：`(user_id, novel_id)`
- 外键：`user_id` -> `user.id`，`novel_id` -> `novel.id`，`chapter_id` -> `chapter.id`
- 普通索引：`last_read_at`

## 7. Comment（评论）
### 作用
- 支持用户对小说发表评论。

### 建议字段
- `id`
- `user_id`（关联 User）
- `novel_id`（关联 Novel）
- `content`
- `status`（visible/hidden/deleted）
- `like_count`
- `created_at`
- `updated_at`

### 索引与约束
- 外键：`user_id` -> `user.id`，`novel_id` -> `novel.id`
- 普通索引：`novel_id`、`status`、`created_at`

## 8. Favorite（收藏）
### 作用
- 记录用户对小说的收藏行为（可与书架能力分离或合并，当前先独立）。

### 建议字段
- `id`
- `user_id`（关联 User）
- `novel_id`（关联 Novel）
- `created_at`
- `updated_at`

### 索引与约束
- 唯一约束：`(user_id, novel_id)`
- 外键：`user_id` -> `user.id`，`novel_id` -> `novel.id`

## 9. Rating（评分）
### 作用
- 存储用户对小说的评分数据。

### 建议字段
- `id`
- `user_id`（关联 User）
- `novel_id`（关联 Novel）
- `score`（建议 1-5）
- `created_at`
- `updated_at`

### 索引与约束
- 唯一约束：`(user_id, novel_id)`
- 外键：`user_id` -> `user.id`，`novel_id` -> `novel.id`
- 校验约束：`score` 取值范围限制

## 模型关系摘要
- User 1:N Novel（作者关系）
- Category 1:N Novel
- Novel 1:N Chapter
- User N:N Novel（通过 Bookshelf/Favorite）
- User 1:N ReadingHistory
- Novel 1:N Comment
- Novel 1:N Rating

## 落地执行清单
- 每个模型先评审字段语义，再评审索引与约束。
- 每次新增字段必须说明查询用途与是否建索引。
- 每次变更必须提供迁移影响评估与回滚方案。
- 写入接口必须校验外键存在性与权限归属。
