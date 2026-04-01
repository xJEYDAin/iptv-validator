# iptv-validator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)

独立 IPTV URL 可用性验证服务，与 [iptv-scraper](https://github.com/xJEYDAin/iptv-scraper) 配合使用。

---

## 🎯 项目目标

- 提供**独立的 IPTV URL 验证服务**，不依赖 iptv-scraper 的运行时环境
- 按 **Tier 级别调度验证频率**，重要频道高频验证，普通频道低频验证
- 验证结果自动 **Push 回 iptv-scraper**，更新其缓存

---

## ⚙️ 工作原理

```
1. 从 iptv-scraper 克隆 filtered/ 目录
2. 遍历所有 m3u 文件中的 URL，按 tier 调度验证
3. 验证完成后，将结果 Push 回 iptv-scraper
```

### Tier 调度规则

| Tier | 验证频率 | 适用场景 |
|------|----------|----------|
| `hk_tw_mo` | **1 天** | 港澳台主要频道（TVB / ViuTV / RTHK / now TV 等） |
| `china` | **7 天** | 中国大陆频道（CCTV / 腾讯 / 百度等） |
| `global` | **30 天** | 全球其他频道 |

---

## 🚀 快速开始

```bash
git clone https://github.com/xJEYDAin/iptv-validator.git
cd iptv-validator
pip install -r requirements.txt
python scripts/validate_all.py
```

### 环境变量

| 变量 | 说明 |
|------|------|
| `FORCE_VALIDATE` | 设为 `1` 强制全量验证，忽略缓存和 tier 调度 |

```bash
# 强制全量验证（忽略缓存）
FORCE_VALIDATE=1 python scripts/validate_all.py
```

---

## 📁 项目结构

```
iptv-validator/
├── .github/workflows/
│   └── validate.yml          # GitHub Actions 验证工作流
├── scripts/
│   └── validate_all.py       # 主验证脚本
├── lib/
│   ├── __init__.py
│   ├── whitelist.py          # CDN 白名单（已知可靠来源跳过验证）
│   └── validators.py         # URL 验证逻辑（HEAD + GET 双策略）
├── cache/
│   └── validation_cache.json  # 验证结果缓存
├── filtered/                   # 克隆自 iptv-scraper 的 m3u 文件
├── README.md
└── requirements.txt
```

---

## 💾 缓存格式

```json
{
  "url": {
    "valid": true,
    "last_validated": "2026-04-01",
    "tier": "hk_tw_mo"
  }
}
```

---

## 🔄 GitHub Actions

- **自动运行**：每天凌晨 **3:00（UTC+8）** 执行验证
- **手动触发**：支持 `workflow_dispatch`，可随时手动运行

工作流步骤：
1. 克隆 iptv-scraper 和 iptv-validator
2. 同步 filtered/ 目录
3. 执行验证
4. Push 验证结果回 iptv-scraper

---

## 🔧 验证策略

- **白名单加速**：已知可靠的 CDN / 官方源直接跳过验证
- **HEAD + GET 双策略**：先用 `HEAD` 请求快速探测，失败再 Fallback 到 `GET`
- **独立运行**：不依赖 iptv-scraper 的运行时环境，结果定期同步回源仓库

---

## 📝 注意事项

- 验证结果会同时更新 iptv-scraper 和 iptv-validator 的 cache
- 不推送到 GitHub（等待维护者决定后再推送）
