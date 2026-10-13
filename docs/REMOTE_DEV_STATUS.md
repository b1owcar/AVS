# 远程开发状态报告

**模式**：Remote Development Mode  
**更新日期**：2026-10-13  

以 `README.md` §11 为准（勿用 `PHASE0_DESIGN.md` §9 旧表）。

## 已实现（代码）

- Phase 0–7 主线：见 README 进度表
- FastAPI + SQLite + 任务队列 + 素材库 + Model Registry
- SDXL native / ComfyUI / Wan T2V+I2V / pose / motion（可插拔） / TRELLIS runner
- Dashboard 实时 Feature readiness
- Windows `D:\avs` 同步：`APPLY-TO-D-AVS` / `git-sync` / `start-all`
- Linux `scripts/linux/smoke.sh`

## 测试分级

| 项 | 结果 |
|----|------|
| 后端 pytest | **PASS**（逻辑） |
| Mock 图像任务 | **SIMULATED** |
| 办公室 Windows GPU SDXL / Wan | **本机验收**（云端不代跑） |
| Motion 真实迁移 | **需用户接线** `run_transfer.py` / Comfy 工作流 |
| TRELLIS 真推理 | **需本机** microsoft/TRELLIS + ≥16GB VRAM |
| Linux GPU 对等 | **NOT RUN** |

## 禁止声称

- 未将 Mock / compose preview 当作真实推理或动作迁移
- 未将 keyframe_approx 当作完整几何重建
- 未将云端 Linux 逻辑测试当作 Windows GPU PASS
- 未在远程环境自动下载大型权重
