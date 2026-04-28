# 阳光阅读 API 规范

## 文档目的
统一“阳光阅读 Sunshine Reading”前后端接口设计与实现约束，确保接口可预测、可测试、可扩展。

## 1. RESTful URL 规范
- 基础前缀：`/api/v1`
- 资源命名：使用复数名词与英文小写短横线（示例：`/api/v1/novels`）
- 资源层级：父子资源使用路径层级表示（示例：`/api/v1/novels/{novel_id}/chapters`）
- 禁止在 URL 中使用动词表达动作（动作语义通过 HTTP 方法表达）

### HTTP 方法约定
- `GET`：查询
- `POST`：创建
- `PUT`：整体更新
- `PATCH`：部分更新
- `DELETE`：删除

## 2. 字段命名规范
- JSON 字段统一使用 `snake_case`。
- 布尔字段使用 `is_`、`has_` 前缀（如 `is_vip`、`has_purchased`）。
- 时间字段统一使用 ISO 8601 字符串，字段名建议 `*_at`（如 `created_at`）。
- ID 字段统一命名为 `id` 或 `<resource>_id`。

## 3. 统一返回结构
### 成功返回
```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_20260428_xxx"
}
```

### 失败返回
```json
{
  "code": 10001,
  "message": "validation_error",
  "errors": [
    {
      "field": "chapter_id",
      "reason": "required"
    }
  ],
  "request_id": "req_20260428_xxx"
}
```

### 约束
- `code=0` 仅用于成功。
- 非 0 `code` 必须对应明确错误类别，不得一号多义。
- `request_id` 必须全链路透传，便于日志排障。

## 4. 分页格式
列表接口统一将分页对象放在 `data` 内。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "page": 1,
    "page_size": 20,
    "total": 125,
    "items": []
  },
  "request_id": "req_20260428_xxx"
}
```

### 分页参数
- `page`：页码，从 1 开始。
- `page_size`：每页数量，建议默认 20，最大不超过 100。

## 5. 错误码格式
- 推荐格式：5 位或以上整数，按域分段。
- 示例分段：
  - `10xxx`：通用参数与请求错误
  - `20xxx`：鉴权与权限错误
  - `30xxx`：资源不存在或状态冲突
  - `40xxx`：业务规则错误
  - `50xxx`：系统内部错误

### 基础错误码示例
- `10001`：参数校验失败
- `20001`：未登录或 token 无效
- `20003`：权限不足
- `30001`：资源不存在
- `50000`：服务器内部错误

## 6. JWT 鉴权方式
### 认证头
- 使用 `Authorization: Bearer <jwt_token>`。
- 所有需要登录的接口必须校验 JWT。

### Token 规则
- Access Token 短有效期（建议 2 小时以内）。
- Refresh Token 长有效期（建议 7-30 天）。
- Refresh 接口必须校验 token 状态与黑名单。

### 鉴权失败处理
- 统一返回鉴权错误码（如 `20001`）。
- 不暴露敏感实现细节（如签名算法、密钥信息）。

## 7. 接口设计执行清单
- 每个接口必须有：路径、方法、权限、请求字段、响应字段、错误码说明。
- 每个列表接口必须有：分页参数、排序字段、筛选字段说明。
- 每个写接口必须定义幂等策略与重复提交处理策略。
- 每个接口必须有至少一个成功与一个失败示例。
