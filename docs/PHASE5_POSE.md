# Phase 5 — 姿态提取（阶段一）

## 范围

| 步骤 | 状态 |
|------|------|
| 参考视频抽帧（复用 Video Studio / FFmpeg） | 可用 |
| 人物选择（person_id；MediaPipe Pose 为单人） | 可用 |
| 姿态序列 JSON | 可用（需 env-pose） |
| 骨架预览图 | 可用 |
| 动作迁移（阶段二） | **未接线** |

## 安装（办公室）

```powershell
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\install-pose.ps1
# 写入 LAVS_POSE_PYTHON，然后重启 start.ps1
```

## API

- `GET /api/motion/status`
- `POST /api/motion/pose/validate`
- `POST /api/motion/pose/extract` — 单帧/图像 asset
- `POST /api/motion/pose/extract-frames` — `{ frame_asset_ids: [...] }`
- 任务模型：`pose-mediapipe`

未安装 env-pose 时任务失败并给出安装提示，**不会**伪装成功。
