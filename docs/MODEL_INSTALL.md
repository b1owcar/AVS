# 模型安装指引（用户主动触发）

> Remote Development Mode：**禁止**在当前 Cursor 环境自动下载大型权重。

## 通用步骤

1. 在 Model Manager 查看 `download_url`、体积提示、许可证、依赖环境。
2. 检查磁盘剩余空间。
3. 在对应隔离环境安装依赖（不要污染主后端 venv）。
4. 下载权重并校验文件完整性。
5. 更新注册表：`download_status` / `verification_status`。
6. 在目标硬件跑最小用例；通过后才标记 available。

## SDXL Base 1.0

- 官方：https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- Diffusers 文档：https://huggingface.co/docs/diffusers/en/api/pipelines/stable_diffusion/stable_diffusion_xl
- 环境：`env-image`（torch + diffusers + transformers + accelerate）
- 首测：512–1024、batch=1、fp16

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
