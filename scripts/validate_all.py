#!/usr/bin/env python3
"""IPTV URL Validator - 独立验证服务

支持 tier-based 验证调度、代理域名黑名单、URL 质量评分。
"""
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from pathlib import Path

FORCE_VALIDATE = os.getenv("FORCE_VALIDATE", "false") == "true"
MAX_WORKERS = int(os.getenv("VALIDATOR_WORKERS", "100"))

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from lib.common import parse_m3u
from lib.validators import validate_url_head_first, is_proxy_domain, PROXY_BLACKLIST_DOMAINS

CACHE_FILE = ROOT_DIR / "cache" / "validation_cache.json"
FILTERED_DIR = ROOT_DIR / "filtered"

TIER_FREQUENCY = {
    "hk_tw_mo": 1,
    "china": 7,
    "global": 30,
}

SOURCE_QUALITY = {
    "vbskycn-iptv4": {"weight": 0.5, "note": "高问题率"},
    "gitee-why006-TV": {"weight": 0.7, "note": "中等问题率"},
    "iptv-org": {"weight": 0.8, "note": "相对稳定"},
    "fanmingming-live": {"weight": 0.95, "note": "稳定"},
    "sammy0101": {"weight": 0.95, "note": "稳定"},
    "default": {"weight": 0.8, "note": "默认"},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("iptv-validator")


def get_source_weight(filename: str) -> float:
    for src, info in SOURCE_QUALITY.items():
        if src in filename:
            return info["weight"]
    return SOURCE_QUALITY["default"]["weight"]


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = CACHE_FILE.with_suffix('.tmp')
    tmp_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_file.replace(CACHE_FILE)
    logger.info(f"Cache 已保存: {CACHE_FILE} ({len(cache)} 条记录)")


def guess_tier(url: str) -> str:
    url_lower = url.lower()
    if any(kw in url_lower for kw in ["tvb", "viutv", "rthk", "nowtv", "cable", "tdm", "hoy",
                                       "bilibili", "kktv", "mytv", "ontv", "jdshipin", "jiduo"]):
        return "hk_tw_mo"
    elif any(kw in url_lower for kw in ["cctv", "sina", "qq.", "baidu", "163189"]):
        return "china"
    return "global"


def calculate_url_score(url: str, cache_entry: dict, source_weight: float) -> int:
    score = 50
    if is_proxy_domain(url):
        return 0
    from lib.whitelist import is_whitelisted
    if is_whitelisted(url):
        score += 30
    score += (source_weight - 0.5) * 40
    if cache_entry:
        if cache_entry.get("valid"):
            score += 10
        else:
            score -= 20
    return max(0, min(100, int(score)))


def should_validate(url: str, cache_entry: dict) -> bool:
    if FORCE_VALIDATE:
        return True
    if not cache_entry:
        return True
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


def validate_url_worker(url: str, timeout: int = 3) -> tuple:
    try:
        is_valid = validate_url_head_first(url, timeout=timeout)
    except Exception:
        is_valid = False
    return (url, is_valid)


def validate_all():
    logger.info("=" * 60)
    logger.info("IPTV Validator 启动")
    logger.info(f"并发 workers: {MAX_WORKERS}")
    logger.info("=" * 60)

    cache = load_cache()
    from lib.whitelist import is_whitelisted

    total_urls = 0
    to_validate_list = []
    skipped_whitelisted = 0
    skipped_cached = 0
    skipped_proxy = 0
    quality_scores = []

    for filepath in sorted(FILTERED_DIR.glob("*.m3u*")):
        logger.info(f"扫描文件: {filepath.name}")
        source_weight = get_source_weight(filepath.name)
        
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
            quality_score = calculate_url_score(url, cache_entry, source_weight)
            quality_scores.append(quality_score)

            if is_proxy_domain(url):
                cache[url] = {
                    "valid": False,
                    "last_validated": date.today().strftime("%Y-%m-%d"),
                    "tier": guess_tier(url),
                    "source": ch.get("group", ""),
                    "quality_score": 0,
                    "reason": "proxy_blocked"
                }
                skipped_proxy += 1
                continue

            if is_whitelisted(url):
                if not should_validate(url, cache_entry):
                    skipped_whitelisted += 1
                    continue
                cache[url] = {
                    "valid": True,
                    "last_validated": date.today().strftime("%Y-%m-%d"),
                    "tier": guess_tier(url),
                    "source": ch.get("group", ""),
                    "quality_score": quality_score,
                }
                skipped_whitelisted += 1
                continue

            if not should_validate(url, cache_entry):
                skipped_cached += 1
                continue

            to_validate_list.append((url, ch))

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    logger.info(f"总 URL: {total_urls}")
    logger.info(f"代理域名跳过: {skipped_proxy}")
    logger.info(f"白名单跳过: {skipped_whitelisted}")
    logger.info(f"缓存命中: {skipped_cached}")
    logger.info(f"待验证: {len(to_validate_list)}")
    logger.info(f"平均质量评分: {avg_quality:.1f}")

    validated = 0
    valid_count = 0

    if to_validate_list:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(validate_url_worker, url): (url, ch)
                for url, ch in to_validate_list
            }
            
            for future in as_completed(futures):
                url, ch = futures[future]
                try:
                    result_url, is_valid = future.result()
                    cache[result_url] = {
                        "valid": is_valid,
                        "last_validated": date.today().strftime("%Y-%m-%d"),
                        "tier": guess_tier(result_url),
                        "source": ch.get("group", ""),
                        "quality_score": calculate_url_score(result_url, None, source_weight),
                    }
                    validated += 1
                    if is_valid:
                        valid_count += 1
                    if validated % 100 == 0:
                        logger.info(f"进度: {validated}/{len(to_validate_list)}, 有效: {valid_count}")
                except Exception as e:
                    logger.debug(f"验证异常 {url}: {e}")
                    cache[url] = {
                        "valid": False,
                        "last_validated": date.today().strftime("%Y-%m-%d"),
                        "tier": guess_tier(url),
                        "source": ch.get("group", ""),
                        "quality_score": 0,
                    }
                    validated += 1

    save_cache(cache)

    logger.info("=" * 60)
    logger.info("验证完成")
    logger.info(f"  总 URL 数量:    {total_urls}")
    logger.info(f"  代理跳过:      {skipped_proxy}")
    logger.info(f"  白名单跳过:     {skipped_whitelisted}")
    logger.info(f"  缓存命中:       {skipped_cached}")
    logger.info(f"  本次验证:       {validated}")
    logger.info(f"  有效:           {valid_count}")
    logger.info(f"  平均质量评分:   {avg_quality:.1f}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(validate_all())
