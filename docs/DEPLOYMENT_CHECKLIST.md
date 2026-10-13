# 目标电脑部署清单

**办公室安装根目录**：`D:\avs`  
**硬件验证**：用户已确认部署后 **跳过** 设备硬件验证（见 `docs/DEPLOY_TO_D_AVS.md`）。

## 部署前

- [ ] 本机已安装 Python 3.10+、Node.js 20+（`python` / `npm` 在 PATH）
- [ ] 已创建 `D:\avs`（或允许部署脚本创建）
- [ ] 确认 `LAVS_HOST=127.0.0.1`（默认）
- [ ] （可选）FFmpeg / NVIDIA 驱动 — 仅真实推理需要，非本次必验项

## 首次安装顺序

1. 在办公室 PC 运行：`scripts\windows\deploy-to-d-avs.ps1 -InstallRoot "D:\avs"`
2. 或已在 `D:\avs` 内：`scripts\windows\setup.ps1` → `start.ps1`
3. 浏览器打开 http://127.0.0.1:18766 确认 UI/API
4. 模型权重 / ComfyUI / SDXL 等：**另行、用户主动** 安装（本步骤不下载）

## 部署后验收（不含硬件验证）

- [ ] `/api/health` OK
- [ ] Mock 任务仍标注 Simulation
- [ ] 未安装模型显示 unavailable
- [ ] `data\DEPLOYED_OFFICE.txt` 存在（一键部署脚本会写入）

## 明确跳过

- 不强制 `check_environment` GPU / CUDA 验收
- 不自动下载大型模型权重
