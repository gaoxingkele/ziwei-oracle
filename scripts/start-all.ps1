# DS-Oracle 一键拉起所有服务（4 个常用 + ngrok 可选）
# 用法:
#   .\scripts\start-all.ps1                # 起 ds-oracle + xiaozhi-server + ngrok
#   .\scripts\start-all.ps1 -DsOracleOnly  # 只起 ds-oracle (api + mcp)
#   .\scripts\start-all.ps1 -WithManager   # 加起 manager-api + manager-web (Java/Vue)
#   .\scripts\start-all.ps1 -Stop          # 停掉所有相关进程

param(
    [switch]$DsOracleOnly,
    [switch]$WithManager,
    [switch]$Stop
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VendorXz = "$ProjectRoot\vendor\xiaozhi-esp32-server\main\xiaozhi-server"
$VendorVenvPy = "$VendorXz\.venv\Scripts\python.exe"
$Py314 = 'D:\Python314\python.exe'

function Stop-AllServices {
    Write-Host "▶ 停掉所有相关进程..." -ForegroundColor Yellow
    $ports = @(8000, 8001, 8002, 8003, 8765, 8811, 8812, 4040)
    foreach ($p in $ports) {
        $conn = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue
        if ($conn) {
            $pid = $conn.OwningProcess | Select-Object -First 1
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  ✓ 已停 :$p (PID=$pid)" -ForegroundColor Green
            } catch {}
        }
    }
}

if ($Stop) { Stop-AllServices; exit 0 }

Set-Location $ProjectRoot
Write-Host "▶ 项目根: $ProjectRoot" -ForegroundColor Cyan

# 1. DS-Oracle FastAPI :8812
$api = Start-Process -FilePath $Py314 `
    -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8812' `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput 'logs_api.log' -RedirectStandardError 'logs_api_err.log' `
    -WindowStyle Hidden -PassThru
Write-Host "  ✓ FastAPI    :8812 (PID=$($api.Id))  代码: app/" -ForegroundColor Green

# 2. DS-Oracle MCP :8811
$mcp = Start-Process -FilePath $Py314 `
    -ArgumentList 'mcp_server.py','--port','8811' `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput 'logs_mcp.log' -RedirectStandardError 'logs_mcp_err.log' `
    -WindowStyle Hidden -PassThru
Write-Host "  ✓ MCP Server :8811 (PID=$($mcp.Id))  代码: mcp_server.py" -ForegroundColor Green

if ($DsOracleOnly) {
    Start-Sleep -Seconds 3
    Write-Host "▶ ds-oracle 启动完成" -ForegroundColor Cyan
    exit 0
}

# 3. xiaozhi-server :8765 ws + :8003 http
if (Test-Path $VendorVenvPy) {
    $xz = Start-Process -FilePath $VendorVenvPy `
        -ArgumentList 'app.py' `
        -WorkingDirectory $VendorXz `
        -RedirectStandardOutput "$ProjectRoot\logs_xz.log" -RedirectStandardError "$ProjectRoot\logs_xz_err.log" `
        -WindowStyle Hidden -PassThru
    Write-Host "  ✓ xiaozhi-server :8765 ws / :8003 http (PID=$($xz.Id))  代码: vendor/xiaozhi-esp32-server/main/xiaozhi-server/" -ForegroundColor Green
} else {
    Write-Host "  ✗ xiaozhi-server 跳过 ($VendorVenvPy 不存在)" -ForegroundColor Red
}

# 4. ngrok (如果 ngrok.exe 存在且 4040 没占)
$ngrokExe = "$ProjectRoot\ngrok.exe"
$ngrokRunning = Get-NetTCPConnection -State Listen -LocalPort 4040 -ErrorAction SilentlyContinue
if ((Test-Path $ngrokExe) -and (-not $ngrokRunning)) {
    $ng = Start-Process -FilePath $ngrokExe `
        -ArgumentList 'http','8811' `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden -PassThru
    Write-Host "  ✓ ngrok      :4040 admin → :8811 (PID=$($ng.Id))" -ForegroundColor Green
} elseif ($ngrokRunning) {
    Write-Host "  - ngrok 已运行 (PID=$($ngrokRunning.OwningProcess))" -ForegroundColor DarkGray
}

# 5. manager-api / manager-web (可选)
if ($WithManager) {
    Write-Host ""
    Write-Host "▶ manager-api / manager-web 需要 Java + Maven + Node, 手动跑:" -ForegroundColor Yellow
    Write-Host "  cd vendor\xiaozhi-esp32-server\main\manager-api    && mvn spring-boot:run    # :8002"
    Write-Host "  cd vendor\xiaozhi-esp32-server\main\manager-web    && npm install && npm run serve   # :8001"
}

Start-Sleep -Seconds 4
Write-Host ""
Write-Host "▶ 端口检查..." -ForegroundColor Cyan
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in 8001,8002,8003,8765,8811,8812,4040 } |
    Select-Object @{N='Service';E={
        switch ($_.LocalPort) {
            8812 {'DS-Oracle API'}
            8811 {'DS-Oracle MCP'}
            8765 {'xiaozhi-server ws'}
            8003 {'xiaozhi-server http'}
            8002 {'manager-api'}
            8001 {'manager-web'}
            4040 {'ngrok admin'}
        }
    }}, LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize

Write-Host "▶ 全部服务起完。日志: logs_api.log / logs_mcp.log / logs_xz.log" -ForegroundColor Cyan
Write-Host "  停止: .\scripts\start-all.ps1 -Stop" -ForegroundColor DarkGray
