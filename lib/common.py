#!/usr/bin/env python3
"""Shared utilities for iptv-validator and iptv-scraper."""
import re
from typing import List, Dict, Any


def parse_m3u(content: str) -> List[Dict[str, Any]]:
    """Parse M3U content and return channel list.
    
    Returns:
        List of dicts with keys: name, tvg_name, tvg_logo, group, url, raw_extinf
    """
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
                        "raw_extinf": extinf
                    })
                    i += 2
                    continue
        i += 1
    return channels
