# Phase 4 — Wan 对齐 + I2V

对齐本机已验证能力到仓库主线，并补齐 Wan I2V。

## 对齐内容（本机 → 代码）

| 能力 | 状态 |
|------|------|
| Wan T2V 1.3B ComfyUI adapter | **已接线** `WanT2VAdapter` |
| Wan I2V 480P (14B class) | **已接线** `WanI2VAdapter`（短默认 length=17 / steps=12） |
| Workflow JSON | `config/workflows/wan_t2v_1.3b_api.json`, `wan_i2v_480p_api.json` |
| Comfy 输出收集 gif/video | `ComfyUIAdapter._collect_outputs` |
| SDXL warm worker | `envs/image/worker_http.py` + `start_sdxl_worker.ps1` |
| Comfy 启动脚本 | `start_comfyui.ps1` |
| Video Studio 真实入队 | `POST /api/video/generate` |

## 本机运行顺序（D:\avs）

```powershell
# 1) 同步代码
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -SourceDir "<fresh-checkout>"

# 2) ComfyUI + Wan 权重（若尚未安装）
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start_comfyui.ps1

# 3) 可选：SDXL warm worker
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start_sdxl_worker.ps1

# 4) LAVS
powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start.ps1
```

`.env` 示例：

```
LAVS_RUN_MODE=real
LAVS_COMFYUI_URL=http://127.0.0.1:8188
LAVS_SDXL_WORKER_URL=http://127.0.0.1:18767
```

## 约束

- T2V 与 I2V **禁止共用**参数 schema / 默认模型。
- 不把 Wan 14B 当作默认 T2V。
- I2V 在 12GB 上可能 OOM — 保持短帧数；失败必须真实报错。
