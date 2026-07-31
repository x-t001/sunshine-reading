# 本地备份与恢复

## 目的

Sunshine Reading 的 PostgreSQL 数据存放在 Docker Desktop 数据卷中，不在 Git 仓库内。重装 Windows、重置 Docker Desktop 或删除数据卷前，必须单独备份数据库、媒体文件和本地环境配置。

实际备份文件可能包含用户数据和 API Key，禁止提交到 GitHub。仓库只保存备份脚本与本说明。

## 创建备份

前置条件：

- Docker Desktop 已运行。
- `sunshine-reading-postgres` 容器处于运行状态。
- PowerShell 可以执行本地脚本。

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-local.ps1
```

默认输出目录：

```text
E:\sunshine-reading-backup\yyyyMMdd-HHmmss\
```

每次备份包含：

- `sunshine_reading.dump`：PostgreSQL 自定义格式转储，创建时已通过 `pg_restore --list` 校验。
- `media.zip`：项目 `media/` 目录归档。
- `sunshine-reading.env`：项目根目录 `.env` 的副本，包含敏感配置。
- `manifest.json`：Git 提交、数据库信息、文件大小及 SHA-256 校验值。

可通过参数修改备份目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-local.ps1 `
  -BackupRoot "F:\sunshine-reading-backup"
```

备份完成后，应将整个时间戳目录再复制到移动硬盘或受控云存储。只保存在同一块硬盘上不能覆盖硬盘故障风险。

## 恢复数据库

以下命令会修改目标数据库。必须先确认目标容器和备份文件正确；对已有数据库恢复前，应再创建一次当前备份。

启动 PostgreSQL：

```powershell
docker compose up -d postgres
```

复制转储到容器：

```powershell
docker cp E:\sunshine-reading-backup\<时间戳>\sunshine_reading.dump `
  sunshine-reading-postgres:/tmp/sunshine_reading.dump
```

恢复到项目数据库：

```powershell
docker exec sunshine-reading-postgres pg_restore `
  -U sunshine_user `
  -d sunshine_reading `
  --clean `
  --if-exists `
  --no-owner `
  --no-privileges `
  /tmp/sunshine_reading.dump
```

完成后运行迁移检查：

```powershell
cd services\api
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

## 恢复媒体和环境配置

将媒体归档解压到项目根目录：

```powershell
Expand-Archive `
  -LiteralPath E:\sunshine-reading-backup\<时间戳>\media.zip `
  -DestinationPath E:\projects\sunshine-reading `
  -Force
```

恢复本地环境配置：

```powershell
Copy-Item `
  -LiteralPath E:\sunshine-reading-backup\<时间戳>\sunshine-reading.env `
  -Destination E:\projects\sunshine-reading\.env
```

`sunshine-reading.env` 包含 API Key，不得上传、截图或发送给无关人员。

## 校验

使用清单中的 SHA-256 检查备份文件：

```powershell
Get-FileHash E:\sunshine-reading-backup\<时间戳>\sunshine_reading.dump -Algorithm SHA256
Get-FileHash E:\sunshine-reading-backup\<时间戳>\media.zip -Algorithm SHA256
Get-FileHash E:\sunshine-reading-backup\<时间戳>\sunshine-reading.env -Algorithm SHA256
```

计算结果必须与 `manifest.json` 中对应文件的 `sha256` 一致。
