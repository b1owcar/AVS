# Phase 7 — Linux 对等冒烟

Windows 目标机上的 SDXL/Wan **PASS 不自动迁移**到 Linux。本阶段提供 Linux 侧逻辑冒烟，与 GPU 实测分级分离。

## 冒烟

```bash
# 先启动
./scripts/linux/setup.sh
./scripts/linux/start.sh   # 另一终端

# 冒烟（默认 API http://127.0.0.1:18765）
chmod +x scripts/linux/smoke.sh
./scripts/linux/smoke.sh
```

检查项：health / features / models / video / motion / studio3d、mock 任务完成、SDXL 未就绪时诚实失败。

## 分级

| 项 | 等级 |
|----|------|
| Linux API + mock | PASS（逻辑）当 smoke 通过 |
| Linux 真 GPU SDXL/Wan/TRELLIS | NOT RUN（需目标 Linux GPU 机） |
| Windows GPU 结果可迁移 | **不可宣称** |
