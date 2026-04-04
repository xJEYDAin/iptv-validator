#!/usr/bin/env python3
"""Unified URL validation for IPTV streams.

Unified implementation: HEAD first + GET fallback + CDN whitelist.
Used by all modules - no more duplicate implementations.
"""
import logging
import requests
from typing import Tuple, Optional

from lib.whitelist import is_whitelisted

DEFAULT_TIMEOUT = 3


def validate_url(url: str, session: Optional[requests.Session] = None,
                 timeout: int = DEFAULT_TIMEOUT, logger=None) -> Tuple[str, bool]:
    """Validate stream URL: whitelist → HEAD first → GET fallback.

    Returns:
        tuple: (url, is_valid)
    """
    # 1. CDN whitelist - skip validation
    if is_whitelisted(url):
        if logger:
            logger.debug(f"  [Whitelist] Skipping validation for {url}")
        return (url, True)

    if session is None:
        session = requests.Session()

    headers = {"User-Agent": "Mozilla/5.0 (compatible; IPTV-Scraper/1.0)"}
    
    # 不接受的内容类型（只拒绝明确错误的内容）
    INVALID_CONTENT_TYPES = ["text/html", "null"]

    # 2. Try HEAD first (fast)
    try:
        resp = session.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if resp.status_code in (200, 206, 301, 302, 303, 307, 308):
            # 检查 Content-Type，拒绝 HTML 等错误页面和空响应
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
            # 检查 Content-Type，拒绝 HTML 等错误页面和空响应
            content_type = resp.headers.get("Content-Type", "").lower().strip()
            if any(invalid in content_type for invalid in INVALID_CONTENT_TYPES):
                if logger:
                    logger.debug(f"  [Invalid Content-Type] '{content_type}' for {url}")
                return (url, False)
            return (url, True)
    except Exception as e:
        if logger:
            logger.debug(f"  GET fallback failed for {url}: {e}")

    return (url, False)


def validate_url_head_first(url: str, session=None, timeout=DEFAULT_TIMEOUT, logger=None):
    """Legacy wrapper: returns bool instead of tuple."""
    return validate_url(url, session=session, timeout=timeout, logger=logger)[1]
