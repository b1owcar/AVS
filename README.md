# Local AI Vision Studio

本地 AI 视觉工作站（Windows 11 / Linux）：React Web UI + FastAPI + SQLite，混合推理架构（ComfyUI + Native + Specialized Worker）。

**当前阶段：Remote Development Mode** — 可在本仓库完成代码、单元测试与模拟推理；真实 GPU 推理与模型下载推迟到目标电脑（RTX 5070 Ti Laptop，32GB RAM）。

## 已实现（Phase 0–1）

- Phase 0 设计报告：`docs/PHASE0_DESIGN.md`
- FastAPI：健康检查、系统探测（可降级）、模型注册表、任务队列、素材库、ComfyUI 连通性探测
- Mock 图像适配器（**Demo / Simulation Mode**，非真实推理）
- React + Vite 深色工作站 UI（全部 Studio 入口；未验证功能明确标注）
- Windows / Linux 安装与启动脚本、诊断脚本、部署清单

## 未实现 / 未验证

- SDXL / Wan / SAM2 / TRELLIS 真实推理：**PENDING TARGET HARDWARE**
- ComfyUI 工作流提交：仅连接探测骨架
- 视频抽帧、姿态、动作迁移、三维生成：入口 only

## 快速启动（开发机）

```bash
# Linux
chmod +x scripts/linux/*.sh scripts/diagnose/*.sh
./scripts/linux/setup.sh
./scripts/linux/start.sh
```

默认：

- API：http://127.0.0.1:18765  
- UI：http://127.0.0.1:18766  

复制 `.env.example` → `.env` 按需修改。默认只监听 localhost。

### 仅跑后端测试

```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest backend/tests -q
```

## 原则

1. UI 有入口 ≠ 功能可用  
2. 禁止用假进度冒充真实推理  
3. 不在远程开发阶段自动下载大型权重  
4. 32GB 是系统内存，不是显存  

更多：`docs/DEPLOYMENT_CHECKLIST.md`、`docs/MODEL_INSTALL.md`、`docs/TROUBLESHOOTING.md`
