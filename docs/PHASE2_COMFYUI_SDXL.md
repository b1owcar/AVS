# Phase 2/3 — ComfyUI + SDXL（办公室 `D:\avs`）

云端代理**不能**在你的 D 盘执行安装。请在已部署的 `D:\avs` 上运行下列脚本。

## 一键安装

```powershell
cd D:\avs
# 仅装环境，不下载权重：
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-phase2.ps1

# 同时下载 SDXL 权重（多 GB，需磁盘与网络）：
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-phase2.ps1 -DownloadWeights
```

若 PyTorch CUDA wheel 与驱动不匹配（例如较新的 50 系 GPU），可改索引：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-phase2.ps1 -DownloadWeights -TorchIndexUrl "https://download.pytorch.org/whl/cu128"
```

## 启动顺序

1. **ComfyUI**（独立终端）  
   `D:\avs\engines\ComfyUI\.venv\Scripts\python.exe D:\avs\engines\ComfyUI\main.py --listen 127.0.0.1 --port 8188`
2. **LAVS**  
   `powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start.ps1`
3. 浏览器：http://127.0.0.1:18766 → Image Studio  
   - `mock-demo`：模拟  
   - `sdxl-base-1.0`：原生 Diffusers（`envs\image`）  
   - `sdxl-comfyui`：经 ComfyUI API  

## 本阶段代码已完成

- 原生 SDXL 适配器（子进程，不污染主后端 venv）
- ComfyUI 健康检查 + SDXL txt2img 工作流提交/轮询/取图
- 模型注册表按磁盘/Comfy 状态刷新 availability
- `LAVS_ALLOW_MODEL_DOWNLOAD=1` 时给出本机安装命令（不在 API 内流式下大文件）

## 明确不做

- 不在云端下载权重  
- 不强制硬件验收（办公室策略）  
- 不把 Mock 成功当成真实推理 PASS  
