# Phase 5 — 姿态与动作迁移

## 阶段一：姿态提取

| 步骤 | 状态 |
|------|------|
| 参考视频抽帧（Video Studio / FFmpeg） | 可用 |
| 人物选择（person_id；MediaPipe Pose 单人） | 可用 |
| 姿态序列 JSON | 可用（需 env-pose） |
| 骨架预览图 | 可用 |

```powershell
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\install-pose.ps1
```

```bash
./scripts/linux/install-pose.sh
```

## 阶段二：动作迁移

| 步骤 | 状态 |
|------|------|
| `motion-transfer` 适配器 + 入队 API | **已接线** |
| env-motion 安装脚本 | **有**（权重仍用户自备） |
| 具体迁移后端（AnimateAnyone 等） | **未绑定** — worker 诚实失败 |
| `skeleton-compose-preview` | **可用**（明确标注 NOT transfer） |

API：

- `POST /api/motion/transfer` — 真实迁移（未装则失败）
- `POST /api/motion/compose-preview` — 骨架叠图预览

禁止把 compose preview 描述成动作迁移成功。
