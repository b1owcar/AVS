# Local AI Vision Studio — Phase 0 设计报告

**状态**：Phase 0 完成（设计与调研）  
**模式**：Remote Development Mode（当前 Cursor 环境 ≠ 目标电脑）  
**日期**：2026-10-12  

---

## 1. 当前开发环境快照（非目标机）

| 项目 | 当前开发环境实测 | 目标电脑（用户声明，未验证） |
|------|------------------|------------------------------|
| OS | Linux x86_64 (Cursor VM) | Windows 11 / Linux |
| GPU | 无 NVIDIA / `nvidia-smi` 不可用 | RTX 5070 Ti Laptop |
| 系统 RAM | ~15 GiB | 32 GB |
| Python | 3.12.3 | 待目标机检测 |
| Node | 22.14.0 | 待目标机检测 |
| FFmpeg | `/usr/bin/ffmpeg` 可用 | 待目标机检测 |
| PyTorch CUDA | **未安装**（禁止在本阶段安装大型推理框架） | PENDING TARGET HARDWARE |

> 本报告中的目标机 GPU 显存、驱动、CUDA 能力一律标记为 **未验证**，不得用型号猜测替代实测。

---

## 2. 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| 前端 | React + TypeScript + Vite | 本地工作站 UI，热更新；禁止浏览器内跑大型 GPU 推理 |
| UI | 深色工作站风格 + 自研轻量组件 | 导航多、任务状态重；不引入第二套组件库 |
| 主后端 | FastAPI + Pydantic + SQLAlchemy + SQLite | 统一 API、本地持久化、易复制部署 |
| 实时进度 | HTTP 轮询（首版）+ WebSocket 预留 | 降低首版复杂度 |
| 推理 | ComfyUI Adapter + Native Adapter + Specialized Worker | 混合架构，按依赖隔离 |
| 资源监控 | psutil +（目标机）NVML/nvidia-smi 探测 | 失败时降级，不阻塞启动 |
| 视频预处理 | FFmpeg / OpenCV（后期） | Phase 1 仅登记能力与脚本检查 |

---

## 3. 架构概览

```
Browser (React UI)
    │  HTTP / (future WS)
    ▼
FastAPI Gateway ─── SQLite (tasks, models, assets, config)
    │
    ├── HardwareProbe (degraded OK)
    ├── ModelRegistry
    ├── TaskQueue (serial GPU jobs by default)
    ├── AssetLibrary
    └── InferenceRouter
            ├── MockAdapter          ← Remote Dev / Demo Mode
            ├── ComfyUIAdapter       ← optional external engine
            ├── NativeAdapter        ← Diffusers / Torch (isolated env)
            └── SpecializedWorker    ← TRELLIS / SAM2 etc. subprocess
```

**原则**：应用可启动 ≠ 功能可用。入口全部保留；仅通过验证的任务类型标记为 `available`。

---

## 4. 项目目录结构

```
/
├── backend/                 # FastAPI 主后端
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # config, logging, hardware
│   │   ├── db/              # SQLAlchemy models & session
│   │   ├── api/             # routers
│   │   ├── schemas/         # Pydantic
│   │   ├── services/        # queue, assets, registry
│   │   └── adapters/        # ModelAdapter + Mock / ComfyUI stubs
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── tests/
├── frontend/                # Vite React TS
├── config/                  # 非密钥配置模板
├── scripts/windows|linux|diagnose/
├── docs/                    # 设计、部署、模型、排障
├── data/                    # 本地运行时（gitignore）
├── .env.example
└── README.md
```

---

## 5. 模型候选表（官方来源核对）

| model_id | 官方名称 / 来源 | 许可证（需目标机再确认） | 估计体量 | 适配器 | 硬件兼容（相对目标机） | 状态 |
|----------|-----------------|--------------------------|----------|--------|------------------------|------|
| `sdxl-base-1.0` | [stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) via Diffusers | CreativeML Open RAIL++-M | ~6–7 GB 权重 | Native (Diffusers) | 有条件支持（FP16、batch=1） | 未下载 / 未验证 |
| `wan2.1-t2v-1.3b` | [Wan-AI/Wan2.1-T2V-1.3B](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B)；Comfy 重打包 [Comfy-Org/Wan_2.1_ComfyUI_repackaged](https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged) | Apache-2.0（官方声明） | T2V 1.3B + CLIP/VAE；官方称约 8GB VRAM | ComfyUI 优先 | 有条件支持 | 未下载 / 未验证 |
| `wan2.1-i2v` | Wan I2V 多为 14B 档位（480P/720P） | 同上 | 显著大于 1.3B | ComfyUI | 有条件支持 / 可能不足 | 未验证；与 T2V 参数结构分离 |
| `sam2.1` | [facebookresearch/sam2](https://github.com/facebookresearch/sam2) | Apache-2.0 | 按 checkpoint | Specialized Worker | Linux 优先；Windows 官方建议 WSL | 未验证；原生 Windows ≠ 已验证 |
| `dwpose` | DWPose / ControlNet 生态（接入前再核许可证） | 待核 | 中等 | Native / Comfy | 未验证 | 候选 |
| `trellis-image-to-3d` | [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) | 见仓库 | 官方要求 ≥16GB VRAM、Linux 测试 | Specialized Worker | **有条件 / 可能不支持**（目标机显存未测；官方≥16GB） | 实验；独立环境 |
| `mock-demo` | 内置 | N/A | 0 | MockAdapter | 已验证（逻辑） | Demo / Simulation Mode |

**不得默认启动 Wan 14B。** TRELLIS / SAM2 不得并入主后端 venv。

---

## 6. 依赖隔离方案

| 环境 | 用途 | 安装时机 |
|------|------|----------|
| `backend` | FastAPI、SQLite、任务、素材、探测 | Phase 1（当前） |
| `frontend` | Node/npm | Phase 1（当前） |
| `comfyui` | 用户自建的外部 ComfyUI | 目标机用户安装 |
| `env-image` | PyTorch + Diffusers（SDXL） | 目标机授权后 |
| `env-video` | 视频生成（若不用 Comfy） | 目标机授权后 |
| `env-pose` | DWPose 等 | 目标机授权后 |
| `env-sam2` | SAM 2.1 | 目标机；优先 Linux/WSL |
| `env-trellis` | TRELLIS | 目标机 Linux 实验 |

分层 requirements：

- `backend/requirements.txt` — 主后端
- `backend/requirements-dev.txt` — pytest 等
- 后续：`envs/image/requirements.txt` 等（不在本阶段安装大型框架）

---

## 7. 跨平台风险清单

| 风险 | 影响 | 缓解 |
|------|------|------|
| SAM2 原生 Windows CUDA 扩展编译失败 | 分割功能 | WSL2 或 `SAM2_BUILD_CUDA=0`；不宣称 Windows 原生已验证 |
| TRELLIS 仅官方测 Linux，且 ≥16GB VRAM | 3D | 独立实验环境；显存不足则标记不支持 |
| RTX 50 系驱动 / CUDA / PyTorch 兼容性 | 全部推理 | 目标机实测后更新兼容等级 |
| 路径分隔符与数据目录 | 部署 | 配置用 `pathlib`，禁止硬编码绝对路径 |
| 32GB 系统内存 ≠ 显存 | OOM | 资源管理区分 VRAM/RAM；卸载增加 RAM 压力 |
| ComfyUI 未运行 | 视频工作流 | 降级：可浏览 UI，任务提交返回明确错误 |

兼容等级：**已验证 / 有条件支持 / 未验证 / 不支持**。

---

## 8. API 设计（首版）

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/system/info` | 硬件与运行模式（可降级） |
| GET | `/api/models` | 模型注册表 |
| GET | `/api/models/{id}` | 模型详情 |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks` | 任务列表 |
| GET | `/api/tasks/{id}` | 任务详情 |
| POST | `/api/tasks/{id}/cancel` | 取消 |
| POST | `/api/tasks/{id}/retry` | 用户发起重试 |
| GET | `/api/assets` | 素材列表 |
| POST | `/api/assets/upload` | 上传 |
| DELETE | `/api/assets/{id}` | 删除（保护进行中任务输入） |
| GET | `/api/comfyui/status` | ComfyUI 可达性 |

任务状态：`pending → preparing → running → completed | failed | cancelled`（另有 `cancelling`）。

---

## 9. 开发阶段计划（远程开发）

| Phase | 内容 | 本会话 |
|-------|------|--------|
| 0 | 调研与设计 | ✅ |
| 1 | 可启动前后端 + SQLite + Registry + Queue + Mock | ✅ 目标 |
| 2 | ComfyUI / Native / Worker 接口框架 | 骨架 + Mock |
| 3 | 图像/视频参数与预处理框架 | 入口 + schema |
| 4 | 部署自检脚本与清单 | ✅ 目标 |
| 5 | 等待目标电脑验证 | 报告后暂停真实部署 |

---

## 10. 禁止事项（本阶段）

- 不下载大型模型权重  
- 不安装 PyTorch/CUDA/Diffusers 等大型推理框架到当前机器  
- 不把当前环境测试结果当作目标机 GPU / Windows 验证  
- 不将 Demo/Mock 成功描述为真实推理成功  
