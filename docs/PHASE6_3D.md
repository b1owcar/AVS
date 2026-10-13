# Phase 6 — 三维资产

## 范围

| 能力 | 状态 |
|------|------|
| TRELLIS image-to-3D 隔离 env + adapter | **代码完成**（需本机安装 runner） |
| Video→3D `keyframe_approx` | **可用**（FFmpeg 抽帧 + manifest；非完整几何） |
| Video→3D `multiview_rebuild` | **未实现**（API 明确拒绝） |
| 目标机 VRAM ≥16GB 实测 | **PENDING TARGET HARDWARE** |

## 安装

**优先 Linux：**

```bash
chmod +x scripts/linux/install-trellis.sh
./scripts/linux/install-trellis.sh
# 再按 microsoft/TRELLIS 官方文档装入 env-trellis，并实现 trellis_runner.py
```

Windows 仅脚手架：`scripts/windows/install-trellis.ps1` — **不得宣称 Windows 已验证**。

## API

- `GET /api/studio3d/status`
- `POST /api/studio3d/image-to-3d`
- `POST /api/studio3d/video-to-3d`
- 模型：`trellis-image-to-3d`、`video-to-3d-keyframe`
