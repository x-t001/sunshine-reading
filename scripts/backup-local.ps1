[CmdletBinding()]
param(
    [string]$BackupRoot = "E:\sunshine-reading-backup",
    [string]$ContainerName = "sunshine-reading-postgres",
    [string]$DatabaseName = "sunshine_reading",
    [string]$DatabaseUser = "sunshine_user"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$targetDirectory = Join-Path $BackupRoot $timestamp
$containerDumpPath = "/tmp/$DatabaseName-$timestamp.dump"
$databaseDumpPath = Join-Path $targetDirectory "$DatabaseName.dump"
$mediaArchivePath = Join-Path $targetDirectory "media.zip"
$environmentBackupPath = Join-Path $targetDirectory "sunshine-reading.env"
$manifestPath = Join-Path $targetDirectory "manifest.json"

$containerState = & docker inspect --format "{{.State.Running}}" $ContainerName 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::Join("", $containerState).Trim() -ne "true") {
    throw "PostgreSQL container $ContainerName is not running. Start Docker Desktop and the database container first."
}

New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null

try {
    & docker exec $ContainerName pg_dump `
        -U $DatabaseUser `
        -d $DatabaseName `
        -Fc `
        -f $containerDumpPath
    if ($LASTEXITCODE -ne 0) {
        throw "Database dump failed."
    }

    & docker exec $ContainerName pg_restore --list $containerDumpPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Database dump validation failed."
    }

    & docker cp "${ContainerName}:${containerDumpPath}" $databaseDumpPath
    if ($LASTEXITCODE -ne 0) {
        throw "Database dump copy failed."
    }
}
finally {
    & docker exec $ContainerName rm -f $containerDumpPath 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not remove the temporary container dump: $containerDumpPath"
    }
}

$mediaPath = Join-Path $projectRoot "media"
if (Test-Path -LiteralPath $mediaPath -PathType Container) {
    Compress-Archive `
        -LiteralPath $mediaPath `
        -DestinationPath $mediaArchivePath `
        -CompressionLevel Optimal
}

$environmentPath = Join-Path $projectRoot ".env"
if (Test-Path -LiteralPath $environmentPath -PathType Leaf) {
    Copy-Item -LiteralPath $environmentPath -Destination $environmentBackupPath
}
else {
    Write-Warning "The project .env file does not exist and was not backed up."
}

$databaseSize = & docker exec $ContainerName psql `
    -U $DatabaseUser `
    -d $DatabaseName `
    -tAc "SELECT pg_size_pretty(pg_database_size('$DatabaseName'));"
if ($LASTEXITCODE -ne 0) {
    $databaseSize = "unknown"
}

$gitCommit = & git -c "safe.directory=$projectRoot" -C $projectRoot rev-parse HEAD 2>$null
if ($LASTEXITCODE -ne 0) {
    $gitCommit = "unknown"
}

$backupFiles = @(
    Get-ChildItem -LiteralPath $targetDirectory -File | ForEach-Object {
        $hash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
        [ordered]@{
            name = $_.Name
            size_bytes = $_.Length
            sha256 = $hash.Hash.ToLowerInvariant()
        }
    }
)

$manifest = [ordered]@{
    created_at = (Get-Date).ToString("o")
    project_root = $projectRoot
    git_commit = [string]::Join("", $gitCommit).Trim()
    database = [ordered]@{
        container = $ContainerName
        name = $DatabaseName
        user = $DatabaseUser
        reported_size = [string]::Join("", $databaseSize).Trim()
        dump_format = "postgres-custom"
        dump_validated = $true
    }
    contains_sensitive_configuration = (Test-Path -LiteralPath $environmentBackupPath)
    files = $backupFiles
}

$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host "Backup completed: $targetDirectory"
Write-Host "Database dump: $databaseDumpPath"
if (Test-Path -LiteralPath $mediaArchivePath) {
    Write-Host "Media archive: $mediaArchivePath"
}
if (Test-Path -LiteralPath $environmentBackupPath) {
    Write-Host "Environment backup: $environmentBackupPath (sensitive; do not commit)"
}
Write-Host "Manifest: $manifestPath"
