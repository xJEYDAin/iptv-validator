# iptv-validator

IPTV 频道 URL 可用性验证服务，与 [iptv-scraper](https://github.com/xJEYDAin/iptv-scraper) 分离。

## 功能特性

- **Tier-based 验证调度**：按频道重要性分级，重要频道每天验证，普通频道每月验证
- **白名单加速**：已知可靠的 CDN/官方源直接跳过验证
- **HEAD + GET 双策略**：先用 HEAD 快速探测，失败再 Fallback 到 GET
- **独立运行**：不依赖 iptv-scraper 的运行时环境
- **结果回推**：验证结果自动 Push 回 iptv-scraper 的 cache

## Tier 分级

| Tier | 频率 | 适用场景 |
|------|------|----------|
| `hk_tw_mo` | 每天 | 港澳台主要频道（TVB/ViuTV/RTHK/now TV 等） |
| `china` | 每周 | 中国大陆频道（CCTV/腾讯/百度等） |
| `global` | 每月 | 全球其他频道 |

## 项目结构

```
iptv-validator/
├── .github/workflows/
│   └── validate.yml          # GitHub Actions 每日验证
├── scripts/
│   └── validate_all.py      # 主验证脚本
├── lib/
│   ├── __init__.py
│   ├── whitelist.py          # CDN 白名单（从 iptv-scraper 迁移）
│   └── validators.py         # URL 验证逻辑（从 iptv-scraper 迁移）
├── cache/
│   └── validation_cache.json # 验证结果缓存
├── filtered/                  # 克隆自 iptv-scraper 的 m3u 文件
├── README.md
└── requirements.txt
```

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 同步 filtered 文件（从 iptv-scraper）
cp -r ../iptv-scraper/filtered/* filtered/

# 运行验证
python scripts/validate_all.py
```

## GitHub Actions

自动每天凌晨 3:00（UTC+8）运行：

1. 克隆 iptv-scraper 和 iptv-validator
2. 同步 filtered/ 目录
3. 执行验证
4. Push cache 到两个仓库

手动触发：`workflow_dispatch`

## 缓存格式

```json
{
  "http://example.com/stream.m3u8": {
    "valid": true,
    "last_validated": "2026-04-01",
    "tier": "hk_tw_mo",
    "source": "HK"
  }
}
```

## 注意事项

- 不推送到 GitHub（等待 y 总决定后再推送）
- 验证结果会同时更新 iptv-scraper 和 iptv-validator 的 cache
