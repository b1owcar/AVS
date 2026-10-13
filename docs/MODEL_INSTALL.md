# 模型安装指引（用户主动触发）

> 办公室安装根目录：`D:\avs`。云端代理不下载权重；请在本机跑安装脚本。

## 推荐：一键 Phase 2

```powershell
cd D:\avs
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-phase2.ps1 -DownloadWeights
```

详情：`docs/PHASE2_COMFYUI_SDXL.md`

## 通用步骤

1. 在 Model Manager 查看 `download_url`、体积提示、许可证、依赖环境。
2. 检查磁盘剩余空间。
3. 在对应隔离环境安装依赖（不要污染主后端 venv）。
4. 用本机脚本下载权重（`install-sdxl.ps1` / `install-comfyui.ps1`）。
5. 重启 LAVS；注册表会刷新 `availability`。
6. Image Studio 选对应模型跑最小用例（768、batch=1）。

## SDXL Base 1.0

- 官方：https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- Diffusers 文档：https://huggingface.co/docs/diffusers/en/api/pipelines/stable_diffusion/stable_diffusion_xl
- 环境：`D:\avs\envs\image`（torch + diffusers + transformers + accelerate）
- 首测：768、batch=1、fp16
- Comfy 路径：checkpoint → `engines\ComfyUI\models\checkpoints\`

## Wan 2.1 T2V 1.3B

- 官方：https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B
- Comfy 重打包：https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged
- 教程：https://docs.comfy.org/tutorials/video/wan/wan-video
- 优先 ComfyUI；不要默认 14B

## SAM 2.1

- https://github.com/facebookresearch/sam2
- Windows：官方建议 WSL；原生 Windows 成功不得默认宣称

## TRELLIS

- https://github.com/microsoft/TRELLIS
- 官方：Linux 测试、≥16GB VRAM
- 必须 `env-trellis` 独立环境
