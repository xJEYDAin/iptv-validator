#!/usr/bin/env python3
"""IPTV URL Validator - 独立验证服务

从 iptv-scraper 迁移的验证逻辑，支持 tier-based 验证调度。
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path

FORCE_VALIDATE = os.getenv("FORCE_VALIDATE", "false") == "true"

# 添加项目根目录到 sys.path，以便导入 lib 模块
ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from lib.validators import validate_url_head_first

# ─── 配置 ────────────────────────────────────────────────────────────────────

CACHE_FILE = ROOT_DIR / "cache" / "validation_cache.json"
FILTERED_DIR = ROOT_DIR / "filtered"

# tier 验证频率（天）
TIER_FREQUENCY = {
    "hk_tw_mo": 1,   # 每天验证
    "china": 7,      # 每周验证
    "global": 30,    # 每月验证
}

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("iptv-validator")


# ─── M3U 解析 ────────────────────────────────────────────────────────────────

def parse_m3u(content: str):
    """解析 m3u 内容，返回频道列表。"""
    import re
    channels = []
    lines = content.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            extinf = line
            name = line.split(',', 1)[1].strip() if ',' in line else ""
            tvg_name = re.search(r'tvg-name="([^"]*)"', line)
            tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
            group = re.search(r'group-title="([^"]*)"', line)
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    channels.append({
                        "name": name,
                        "tvg_name": tvg_name.group(1) if tvg_name else name,
                        "tvg_logo": tvg_logo.group(1) if tvg_logo else "",
                        "group": group.group(1) if group else "",
                        "url": url,
                    })
                    i += 2
                    continue
        i += 1
    return channels


# ─── Cache 管理 ──────────────────────────────────────────────────────────────

def load_cache() -> dict:
    """加载验证缓存。"""
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Cache 文件损坏，重新创建: {e}")
    return {}


def save_cache(cache: dict):
    """保存验证缓存（原子写入）。"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(CACHE_FILE)
    logger.info(f"Cache 已保存: {CACHE_FILE} ({len(cache)} 条记录)")


# ─── Tier 推断 ──────────────────────────────────────────────────────────────

def guess_tier(url: str) -> str:
    """根据 URL 猜测 tier。"""
    url_lower = url.lower()
    if any(kw in url_lower for kw in ["tvb", "viutv", "rthk", "nowtv", "cable", "tdm", "hoy",
                                       "bilibili", "kktv", "mytv", "ontv", "jdshipin", "jiduo"]):
        return "hk_tw_mo"
    elif any(kw in url_lower for kw in ["cctv", "sina", "qq.", "baidu", "163189"]):
        return "china"
    return "global"


# ─── 验证调度 ───────────────────────────────────────────────────────────────

def should_validate(url: str, cache_entry: dict | None) -> bool:
    """判断 URL 是否需要重新验证。"""
    if FORCE_VALIDATE:
        return True

    if not cache_entry:
        return True  # 新 URL

    last_validated = cache_entry.get("last_validated")
    if not last_validated:
        return True

    tier = cache_entry.get("tier", "global")
    try:
        last_date = datetime.fromisoformat(last_validated).date()
        days_since = (date.today() - last_date).days
    except (ValueError, TypeError):
        return True

    return days_since >= TIER_FREQUENCY.get(tier, 30)


# ─── 主验证流程 ─────────────────────────────────────────────────────────────

def validate_all():
    """验证所有待验证的 URL。"""
    logger.info("=" * 60)
    logger.info("IPTV Validator 启动")
    logger.info("=" * 60)

    cache = load_cache()
    total_urls = 0
    to_validate = 0
    validated = 0
    valid_count = 0
    skipped_whitelisted = 0

    from lib.whitelist import is_whitelisted

    for filepath in sorted(FILTERED_DIR.glob("*.m3u*")):
        logger.info(f"处理文件: {filepath.name}")
        try:
            content = filepath.read_text(encoding="utf-8")
            channels = parse_m3u(content)
        except Exception as e:
            logger.error(f"解析失败 {filepath.name}: {e}")
            continue

        for ch in channels:
            url = ch["url"]
            total_urls += 1

            cache_entry = cache.get(url)

            # 白名单 URL 也走 tier-based 过期机制
            if is_whitelisted(url):
                if not should_validate(url, cache_entry):
                    skipped_whitelisted += 1
                    continue
                # 需要验证（tier过期），按白名单处理
                cache[url] = {
                    "valid": True,
                    "last_validated": date.today().strftime("%Y-%m-%d"),
                    "tier": guess_tier(url),
                    "source": "whitelist",
                }
                skipped_whitelisted += 1
                continue

            if not should_validate(url, cache_entry):
                # 不需要验证，跳过
                continue

            to_validate += 1
            try:
                is_valid = validate_url_head_first(url, timeout=3)
            except Exception as e:
                logger.debug(f"验证异常 {url}: {e}")
                is_valid = False

            cache[url] = {
                "valid": is_valid,
                "last_validated": date.today().strftime("%Y-%m-%d"),
                "tier": guess_tier(url),
                "source": ch.get("group", ""),
            }

            validated += 1
            if is_valid:
                valid_count += 1

            # 避免请求过快
            time.sleep(0.05)

    # 保存缓存
    save_cache(cache)

    # 打印统计
    logger.info("=" * 60)
    logger.info("验证完成")
    logger.info(f"  总 URL 数量:    {total_urls}")
    logger.info(f"  白名单跳过:     {skipped_whitelisted}")
    logger.info(f"  本次验证:        {validated}")
    logger.info(f"  有效:            {valid_count}")
    logger.info(f"  缓存总记录:      {len(cache)}")
    logger.info("=" * 60)

    # 返回退出码：0=全部有效, 1=有无效URL, 2=异常
    invalid = validated - valid_count
    if invalid > 0:
        logger.warning(f"{invalid} 个 URL 无效")
    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(validate_all())
