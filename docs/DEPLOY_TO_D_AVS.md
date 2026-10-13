# 部署到办公室电脑 `D:\avs`

**目标路径**：`D:\avs`  
**硬件验证**：按用户要求，部署完成后 **不再执行** 设备硬件验证。  
**说明**：Cursor 云端代理无法直接写入你办公室电脑的 D 盘；请在本机 PowerShell 执行下列步骤。

## 前置条件（本机）

- Windows 11
- Python 3.10+（`python` 在 PATH）
- Node.js 20+（`npm` 在 PATH）
- 已创建空目录 `D:\avs`（或允许脚本创建）

## 方式 A：已有项目文件夹时（推荐）

1. 把本仓库完整复制到任意临时目录，例如 `C:\Temp\lavs`（或从 Git 拉下）。
2. 在该目录打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\deploy-to-d-avs.ps1 -InstallRoot "D:\avs"
```

脚本会把代码同步到 `D:\avs`，创建 `.venv`、安装后端/前端依赖，并写入 `.env`。

## 方式 B：从当前已在 `D:\avs` 的代码安装

若你已把代码解压/克隆进 `D:\avs`：

```powershell
cd D:\avs
powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start.ps1
```

## 启动

```powershell
cd D:\avs
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start.ps1
```

- UI：http://127.0.0.1:18766  
- API：http://127.0.0.1:18765  

默认 `LAVS_RUN_MODE=simulation`（Mock 可用）。真实 SDXL/Wan 等仍需你之后主动装依赖并下载权重；本步骤不下载模型。

## 云端进度部署到本机（推荐）

Cloud Agent **不能直接写** `D:\avs`。请下载同步包后在办公室执行：

1. 下载 `lavs-cloud-sync-latest.zip`（agent 产物 / store media）
2. 解压到 `C:\Temp\lavs-fresh`（目录内应有 `APPLY-TO-D-AVS.ps1`、`backend\`、`frontend\`）
3. 本机 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File C:\Temp\lavs-fresh\APPLY-TO-D-AVS.ps1
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start-all.ps1
```

会保留 `data` / `engines` / `external` / `.venv`，并强制写入 `scripts\windows\*`。

## 云端改完 ≠ 自动进 D:\avs

仓库里有新脚本时，本机要先按上面同步一次才会出现该文件。

```powershell
# 方式 A：D:\avs 本身是 git clone
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -GitPull

# 方式 B：另有一份最新 checkout / zip 解压目录
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -SourceDir "C:\Temp\lavs-fresh"

# 方式 C：用远程 URL 拉到 TEMP 再灌进 D:\avs（需本机已配 git 凭据）
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -GitUrl "<your-repo-url>"
```

同步成功后应存在：`D:\avs\scripts\windows\start-all.ps1`。

## 日常启动（ComfyUI + 前后端）

```powershell
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start-all.ps1
```

同步新代码后必须**重启**该脚本（或分别重启 API/UI）。仅刷新浏览器不够。

## 下一步：ComfyUI / SDXL（Phase 2/3）

见 **[PHASE2_COMFYUI_SDXL.md](./PHASE2_COMFYUI_SDXL.md)**：

```powershell
cd D:\avs
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-phase2.ps1 -DownloadWeights
```

## 部署后不会做的事

- 不跑 `scripts/diagnose/check_environment.*` 作为必经步骤  
- 不强制 GPU / CUDA 验收  
- 不在 API 进程内流式下载多 GB 权重（改用本机安装脚本）  
