# iptv-validator

独立 IPTV URL 可用性验证服务，与 [iptv-scraper](https://github.com/xJEYDAin/iptv-scraper) 配合使用。

---

## 🎯 功能

- **独立验证**：不依赖 iptv-scraper 运行时环境
- **并发验证**：100 workers，约 24 分钟处理 ~48k URL
- **Tier 调度**：HK/TW/MO: 1天 / China: 7天 / Global: 30天
- **白名单加速**：已知优质 CDN（HK CDN 等）跳过验证
- **缓存机制**：验证结果持久化，避免重复验证

---

## 📊 验证参数

| 指标 | 数值 |
|------|------|
| 总 URL（filtered） | ~52,000 |
| 白名单跳过 | ~3,980 |
| 需验证 | ~48,000 |
| 并发数 | 100 workers |
| 验证频率 | HK: 1天 / China: 7天 / Global: 30天 |

---

## 🏗️ 架构流程

```
03:00  iptv-scraper   拉取缓存 → 生成 → 推送 filtered/
                ↓
03:30  iptv-validator 拉取 filtered/
                ↓
         解析 M3U → Tier 调度 → 并发验证
                ↓
         更新 validation_cache.json
```

---

## 🚀 快速开始

```bash
# 克隆
git clone https://github.com/xJEYDAin/iptv-validator.git
cd iptv-validator

# 安装依赖
pip install -r requirements.txt

# 运行验证
python scripts/validate_all.py

# 强制全量验证（忽略 Tier 调度和缓存）
FORCE_VALIDATE=1 python scripts/validate_all.py

# 自定义并发数
VALIDATOR_WORKERS=50 python scripts/validate_all.py
```

---

## 📄 许可证

MIT License
