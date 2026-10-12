# 故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 后端无法启动 | 缺依赖 / 端口占用 | 重跑 setup；更换 `LAVS_PORT` |
| 前端 API offline | 后端未起或代理错误 | 确认 18765；Vite proxy `/api` |
| GPU 全空 | 无驱动 / 无 nvidia-smi | 降级模式仍可浏览；目标机装驱动 |
| ComfyUI offline | 服务未开 | 其他页面可浏览；视频任务不可用 |
| 任务立刻 failed + PENDING TARGET HARDWARE | 模型未实现 | 预期行为；先用 mock-demo |
| CUDA OOM（目标机） | 分辨率/帧数过大 | 降分辨率、减帧、启用模型支持的卸载；不要无限重试 |
| SAM2 编译失败 | Windows CUDA 扩展 | WSL 或 `SAM2_BUILD_CUDA=0` |
| TRELLIS 装不上 | Linux/CUDA 扩展冲突 | 保持独立环境；勿并入主后端 |

测试结果分级：PASS / SIMULATED / NOT RUN / PENDING TARGET HARDWARE / FAILED。
