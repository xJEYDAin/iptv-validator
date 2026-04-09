#!/usr/bin/env python3
"""Unified URL validation for IPTV streams.

Unified implementation: HEAD first + GET fallback + CDN whitelist.
"""
import logging
import requests
from typing import Tuple, Optional

from lib.whitelist import is_whitelisted

DEFAULT_TIMEOUT = 3

# 代理域名黑名单 - 直接拒绝这些域名
PROXY_BLACKLIST_DOMAINS = [
    "jdshipin.com",
    "jiduo.me",
    "v2h.jdshipin.com",
    "php.jdshipin.com",
    "kkk.jjjj.jiduo.me",
    "jjjj.jiduo.me",
]


def is_proxy_domain(url: str) -> bool:
    """检测是否为代理/播放器页面 URL"""
    from urllib.parse import urlparse
    try:
        domain = urlparse(url).netloc.lower()
        return any(proxy in domain for proxy in PROXY_BLACKLIST_DOMAINS)
    except:
        return False


def validate_url(url: str, session: Optional[requests.Session] = None,
                 timeout: int = DEFAULT_TIMEOUT, logger=None) -> Tuple[str, bool]:
    """Validate stream URL: proxy blacklist → whitelist → HEAD first → GET fallback.

    Returns:
        tuple: (url, is_valid)
    """
    # 0. 代理域名直接拒绝
    if is_proxy_domain(url):
        if logger:
            logger.debug(f"  [Proxy Blocked] {url}")
        return (url, False)

    # 1. CDN whitelist - skip validation
    if is_whitelisted(url):
        if logger:
            logger.debug(f"  [Whitelist] Skipping validation for {url}")
        return (url, True)

    if session is None:
        session = requests.Session()

    headers = {"User-Agent": "Mozilla/5.0 (compatible; IPTV-Scraper/1.0)"}
    
    # 不接受的内容类型
    INVALID_CONTENT_TYPES = ["text/html", "null", "application/xml", "text/plain"]

    # 2. Try HEAD first (fast)
    try:
        resp = session.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if resp.status_code in (200, 206, 301, 302, 303, 307, 308):
            content_type = resp.headers.get("Content-Type", "").lower().strip()
            if any(invalid in content_type for invalid in INVALID_CONTENT_TYPES):
                if logger:
                    logger.debug(f"  [Invalid Content-Type] '{content_type}' for {url}")
                return (url, False)
            return (url, True)
    except Exception as e:
        if logger:
            logger.debug(f"  HEAD failed for {url}: {e}")

    # 3. Fallback to GET (only on HEAD failure)
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True,
                          headers=headers, stream=True)
        if resp.status_code in (200, 206, 301, 302, 303, 307, 308):
            content_type = resp.headers.get("Content-Type", "").lower().strip()
            if any(invalid in content_type for invalid in INVALID_CONTENT_TYPES):
                if logger:
                    logger.debug(f"  [Invalid Content-Type] '{content_type}' for {url}")
                return (url, False)
            # 深度检测：检查响应内容是否像视频流（使用 raw.read 而非 resp.text 避免 stream=True 时内存爆炸）
            try:
                content = resp.raw.read(500).decode('utf-8', errors='ignore').lower()
                if '#extm3u' in content or '.ts' in content or 'manifest' in content:
                    return (url, True)
            except Exception as e:
                if logger:
                    logger.debug(f"  Deep check failed: {e}")
            return (url, True)
    except Exception as e:
        if logger:
            logger.debug(f"  GET fallback failed for {url}: {e}")

    return (url, False)


def validate_url_head_first(url: str, session=None, timeout=DEFAULT_TIMEOUT, logger=None):
    """Legacy wrapper: returns bool instead of tuple."""
    return validate_url(url, session=session, timeout=timeout, logger=logger)[1]
