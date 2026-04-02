# iptv-validator

独立 IPTV URL 可用性验证服务，与 [iptv-scraper](https://github.com/xJEYDAin/iptv-scraper) 配合使用。

---

## 🎯 功能

- **独立验证**：不依赖 iptv-scraper 运行时环境
- **并发验证**：100 workers，约 24 分钟处理 48k URL
- **Tier 调度**：HK: 1天 / China: 7天 / Global: 30天
- **白名单加速**：已知 CDN 跳过验证

---

## 📊 验证结果

| 指标 | 数值 |
|------|------|
| 总 URL | ~52,680 |
| 白名单跳过 | ~3,980 |
| 需验证 | ~48,700 |
| 并发数 | 100 workers |

---

## 🏗️ 架构

```
iptv-scraper (03:00) → pull cache → run → push output/filtered
iptv-validator (03:30) → pull filtered → validate → push cache
```

---

## 🚀 快速开始

```bash
# 运行验证
python scripts/validate_all.py

# 强制全量验证
FORCE_VALIDATE=1 python scripts/validate_all.py
```

---

## 📄 许可证

MIT License
