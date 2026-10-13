# Phase 6 — 三维资产

## 范围

| 能力 | 状态 |
|------|------|
| TRELLIS image-to-3D 隔离 env + adapter | **代码完成** |
| `trellis_runner.py` | **已随仓库提供**（调用 `TrellisImageTo3DPipeline`；需本机装好 microsoft/TRELLIS） |
| Video→3D `keyframe_approx` | **可用**（FFmpeg 抽帧 + manifest；非完整几何） |
| Video→3D `multiview_rebuild` | **未实现**（API 明确拒绝） |
| 目标机 VRAM ≥16GB 实测 | **PENDING TARGET HARDWARE** |

## 安装

**优先 Linux：**

```bash
chmod +x scripts/linux/install-trellis.sh
./scripts/linux/install-trellis.sh
# 再按 microsoft/TRELLIS 官方文档把包装进 env-trellis
# trellis_runner.py 已复制进 envs/trellis — 可 import trellis 后即可跑
```

Windows 仅脚手架：`scripts/windows/install-trellis.ps1` — **不得宣称 Windows 已验证**。

可选环境变量：

- `LAVS_TRELLIS_MODEL`（默认 `microsoft/TRELLIS-image-large`）
- `LAVS_TRELLIS_SEED`

## API

- `GET /api/studio3d/status`
- `POST /api/studio3d/image-to-3d`
- `POST /api/studio3d/video-to-3d`
- 模型：`trellis-image-to-3d`、`video-to-3d-keyframe`
