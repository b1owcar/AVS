# 目标电脑部署清单（尚未授权执行）

## 部署前

- [ ] 复制整个项目目录到目标电脑（不含 `.venv` / `node_modules` / 本地 `data` 产物亦可）
- [ ] 安装 Python 3.10+、Node.js 20+、FFmpeg、NVIDIA 驱动
- [ ] 运行 `scripts/diagnose/check_environment.(sh|ps1)` 并保存输出
- [ ] 记录：GPU 型号、**实测**显存总量/空闲、驱动版本、磁盘剩余
- [ ] 确认 `LAVS_HOST=127.0.0.1`（默认）
- [ ] 阅读各模型许可证后再决定是否下载

## 首次安装顺序（建议）

1. `scripts/windows/setup.ps1` 或 `scripts/linux/setup.sh`（仅主后端+前端）
2. `scripts/*/start.*` 验证 UI/API 可启动
3. 再单独规划 ComfyUI 安装（外部）
4. 用户主动下载 SDXL（首选首个真实模型）到隔离 `env-image`
5. 低分辨率、batch=1 实测；记录峰值显存
6. 再考虑 Wan 2.1 T2V 1.3B（ComfyUI），禁止默认 14B
7. SAM2 / TRELLIS 仅在独立环境实验

## 部署后验收

- [ ] `/api/health` OK
- [ ] `/api/system/info` GPU 字段来自实测，非猜测
- [ ] Mock 任务仍标注 Simulation
- [ ] 未安装模型显示 unavailable
- [ ] 真实 SDXL 任务成功后才可将该功能标为 available
- [ ] OOM 时任务为 failed 并带建议，不得标成功

## 明确未做（当前远程阶段）

- 未在目标机安装
- 未下载权重
- 未宣称 Windows/Linux GPU 兼容完成
