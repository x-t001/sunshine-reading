# API Key 安全规范

本文档定义 Sunshine Reading 配置第三方 AI 服务凭据的方式。

## 安全边界

- 服务商密钥仅属于 Django API 与后台任务 Worker。
- 浏览器不得接收、持久化或提交 `VIDEO_AI_API_KEY`。
- 服务商凭据不得使用 `NEXT_PUBLIC_*` 环境变量。
- 不得把凭据写入源代码、URL、文档、截图、日志、测试夹具或 API 响应。
- 短视频能力接口只能返回配置状态与模型名称。

## 本地开发

1. 从已纳入版本控制的根目录 `.env.example` 复制变量名到被忽略的根目录 `.env`。
2. 在本机 `.env` 中直接设置 `VIDEO_AI_API_KEY`，不得通过聊天发送真实值，也不得提交到仓库。
3. `VIDEO_AI_API_URL` 必须是绝对 HTTPS 地址，`VIDEO_AI_MODEL` 必须是服务商支持的模型。
4. 修改服务商配置后，重启 Django API 与 `run_video_generation_worker`。

必需变量：

```env
VIDEO_AI_API_URL=https://api.openai.com/v1/chat/completions
VIDEO_AI_API_KEY=
VIDEO_AI_MODEL=gpt-4o-mini
VIDEO_AI_TIMEOUT_SECONDS=60
```

本地开发会加载根目录 `.env`。显式进程环境变量优先级更高，因此部署时可以注入密钥，而无需修改应用代码。

## 验证

执行服务端配置检查：

```powershell
cd services/api
.\.venv\Scripts\python.exe manage.py check --tag security
.\.venv\Scripts\python.exe manage.py test video_generation --noinput
```

登录后，`GET /api/video-projects/capabilities/` 可确认 AI 分镜是否已配置。响应不得包含服务商 URL 或密钥。

提交前确认本地环境文件已被忽略，并且示例文件仍可纳入版本控制：

```powershell
git check-ignore -v .env
git check-ignore .env.example
git ls-files -- .env
```

第二条和第三条命令应无输出。

## 生产环境

- 通过托管平台密钥管理、Docker Secret、Kubernetes Secret 或同等级机制注入相同变量。
- 只允许 API 与 Worker 的运行身份读取密钥。
- 不得将密钥写入镜像，或提交到 Compose、Kubernetes、CI 和部署清单。
- 如果服务商支持，应按项目、环境、配额与允许调用的 API 限制凭据。
- 定期轮换密钥；人员权限或基础设施访问发生变化时也必须轮换。

## 轮换与泄露处置

1. 创建替代密钥并更新运行时密钥配置。
2. 重启或滚动更新 API 与 Worker，然后验证能力接口和一个受控生成任务。
3. 确认替代密钥生效后撤销旧密钥。
4. 如果密钥可能泄露，立即撤销，检查服务商用量与应用日志，并从所有产物中删除泄露值。
5. 如果密钥进入 Git 历史，必须轮换；仅从最新文件中删除并不安全。

## 现有小说 AI 对话

旧版小说 AI 对话目前仍接收用户提供的密钥，该字段只写入请求且不会持久化。这是独立的兼容路径。新增短视频功能必须使用本文定义的服务端配置。
