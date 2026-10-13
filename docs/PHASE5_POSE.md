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
| env-motion 安装脚本 | **有**（Win + Linux） |
| 可插拔后端 | **已支持** `run_transfer.py` / `backend.json`（`external_script` · `comfyui`） |
| AnimateAnyone / MimicMotion 具体权重 | **用户自备** — 通过 `run_transfer.py` 绑定 |
| `skeleton-compose-preview` | **可用**（明确标注 NOT transfer） |

### 接线后端（办公室）

```powershell
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\install-motion.ps1
# 然后任选其一：
# A) copy envs\motion\run_transfer.example.py → data\models\motion-transfer\run_transfer.py 并实现
# B) 写 data\models\motion-transfer\backend.json（见 backend.example.json）
```

```bash
./scripts/linux/install-motion.sh
```

`README.txt` alone 不会把 transfer 标成 Ready。ComfyUI 示例工作流：`config/workflows/motion_transfer_comfy.example.json`（须换成你的自定义节点图）。

API：

- `POST /api/motion/transfer` — 真实迁移（未接线则失败）
- `POST /api/motion/compose-preview` — 骨架叠图预览

禁止把 compose preview 描述成动作迁移成功。
