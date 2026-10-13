# Local AI Vision Studio

本地 AI 视觉工作站（Windows 11 / Linux）：React Web UI + FastAPI + SQLite，混合推理架构（ComfyUI + Native + Specialized Worker）。

## 进度（§11 产品阶段）

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 设计 | 完成 |
| 1 | 基础前后端 / Mock | 完成 |
| 2 | ComfyUI + SDXL（含 warm worker） | 代码完成；本机 GPU 验证在办公室 |
| 3 | 视频预处理框架 | 完成（FFmpeg） |
| 4 | Wan T2V + **I2V** | 代码完成；需 ComfyUI + 权重 |
| 5 | 姿态提取 + 动作迁移 | 代码完成；`run_transfer.py` / `backend.json` 可插拔后端 |
| 6 | TRELLIS / video keyframe≈3D | 代码完成；`trellis_runner.py` 已提供（需本机装 TRELLIS） |
| 7 | Linux 冒烟 | `scripts/linux/smoke.sh` |
| — | SAST | 见 `docs/SAST_REPORT.md` |

**办公室剩余**：装 Comfy/权重；为 motion 写 `run_transfer.py`；Linux 装 microsoft/TRELLIS；不做假进度。

Cloud / 远程环境**不能**写入 `D:\avs`；用更新脚本同步到办公室 PC。

## 办公室 Windows 部署（`D:\avs`）

见 **[docs/DEPLOY_TO_D_AVS.md](docs/DEPLOY_TO_D_AVS.md)**。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\deploy-to-d-avs.ps1 -InstallRoot "D:\avs"
# 或增量更新：
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -SourceDir "<fresh-checkout>"
```

### 常用启动

```powershell
# 一键：ComfyUI + 后端 + 前端（推荐）
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start-all.ps1
# 可选热 SDXL worker：
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start-all.ps1 -WithSdxlWorker
```

浏览器刷新**不会**重载 Python。`update-avs.ps1` 同步代码后请关掉旧窗口再跑 `start-all.ps1`。

Model Manager 里 `unavailable` = 环境/权重未就绪（适配器已接线），不是“功能未实现”。

## 快速启动（开发机 / Linux）

```bash
chmod +x scripts/linux/*.sh scripts/diagnose/*.sh
./scripts/linux/setup.sh
./scripts/linux/start.sh
```

默认 API：http://127.0.0.1:18765 · UI：http://127.0.0.1:18766

### 测试

```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest backend/tests -q
```

## 文档

- `docs/PHASE0_DESIGN.md` · `docs/PHASE2_COMFYUI_SDXL.md` · `docs/PHASE3_VIDEO_FRAMEWORK.md`
- `docs/PHASE4_WAN_ALIGN.md` · `docs/PHASE5_POSE.md` · `docs/PHASE6_3D.md` · `docs/PHASE7_LINUX.md`
- `docs/SAST_REPORT.md`
- `docs/MODEL_INSTALL.md` · `docs/TROUBLESHOOTING.md`

## 原则

1. UI 有入口 ≠ 功能可用  
2. 禁止用假进度冒充真实推理  
3. 不在远程开发阶段自动下载大型权重  
4. T2V / I2V 参数与模型严格分离  
