# Phase 3 — 图像 / 视频功能框架

## 已完成（本轮）

| 能力 | 状态 |
|------|------|
| 视频信息读取（ffprobe） | **可用** |
| 按间隔抽帧 / 关键帧 | **可用** |
| 裁剪 clip / 转码 / 预览图 | **可用** |
| 源文件保护（不覆盖） | **是** |
| T2V / I2V 参数模型（分离） | **schema 可用，不执行生成** |
| 姿态 / 动作迁移参数模型 | **schema 可用** |
| 图像/视频→3D 参数模型 | **schema 可用** |
| SpecializedModelWorker 接口 | **骨架** |
| Video Studio UI | **可用（预处理）** |

## 办公室 `D:\avs` 更新代码

```powershell
# 将最新仓库解压到临时目录后：
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -SourceDir "C:\Temp\lavs-fresh"
cd D:\avs\frontend; npm install
& D:\avs\.venv\Scripts\pip.exe install -r D:\avs\backend\requirements.txt
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start.ps1
```

仍建议并行跑 Phase 2 安装（ComfyUI/SDXL）：`install-phase2.ps1`。

## API

- `GET /api/video/status`
- `POST /api/video/preprocess`
- `POST /api/video/generate/validate`
- `GET /api/task-schemas`
