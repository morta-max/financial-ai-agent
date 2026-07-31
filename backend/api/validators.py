"""
Input validators for API endpoints.
Protects against injection, malformed input, and abuse.
"""

import re
from datetime import datetime
from typing import Optional

# A-share stock code: 6 digits
# SSE (Shanghai): 600000-609999, 688000-689999
# SZSE (Shenzhen): 000001-004999, 300000-301999
# BSE (Beijing): 8xxxxx, 4xxxxx
STOCK_CODE_PATTERN = re.compile(r"^\d{6}$")

# Fund code: 6 digits
FUND_CODE_PATTERN = re.compile(r"^\d{6}$")

# Date pattern: YYYYMMDD
DATE_PATTERN = re.compile(r"^\d{8}$")

# Index codes
VALID_INDICES = {
    "000001", "000016", "000300", "000688", "000852",
    "399001", "399005", "399006", "399016", "399303",
}


def validate_stock_code(symbol: str) -> str:
    """Validate and normalize a stock code. Raises ValueError if invalid."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("股票代码不能为空")

    symbol = symbol.strip().zfill(6)

    if not STOCK_CODE_PATTERN.match(symbol):
        raise ValueError(f"无效的股票代码格式: {symbol}，需要6位数字")

    return symbol


def validate_fund_code(code: str) -> str:
    """Validate fund code."""
    if not code or not isinstance(code, str):
        raise ValueError("基金代码不能为空")

    code = code.strip().zfill(6)

    if not FUND_CODE_PATTERN.match(code):
        raise ValueError(f"无效的基金代码格式: {code}，需要6位数字")

    return code


def validate_date(date_str: str) -> str:
    """Validate date format YYYYMMDD."""
    if not DATE_PATTERN.match(date_str):
        raise ValueError(f"无效的日期格式: {date_str}，需要YYYYMMDD格式")

    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError(f"无效的日期: {date_str}")

    return date_str


def validate_date_range(start: str, end: str, max_days: int = 3650) -> tuple[str, str]:
    """Validate date range is reasonable."""
    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")

    if start_dt > end_dt:
        raise ValueError("开始日期不能晚于结束日期")

    if (end_dt - start_dt).days > max_days:
        raise ValueError(f"日期范围不能超过{max_days}天")

    return start, end


def validate_symbols_list(symbols: str, max_count: int = 50) -> list[str]:
    """Validate comma-separated symbols list."""
    if not symbols or not isinstance(symbols, str):
        raise ValueError("股票代码列表不能为空")

    parts = [s.strip() for s in symbols.split(",") if s.strip()]

    if not parts:
        raise ValueError("未提供有效的股票代码")

    if len(parts) > max_count:
        raise ValueError(f"批量查询不能超过{max_count}只股票")

    validated = []
    for sym in parts:
        try:
            validated.append(validate_stock_code(sym))
        except ValueError:
            pass  # Skip invalid codes in batch

    if not validated:
        raise ValueError("没有有效的股票代码")

    return validated


def validate_search_query(query: str, max_length: int = 100) -> str:
    """Validate and sanitize search query."""
    if not query or not isinstance(query, str):
        raise ValueError("搜索关键词不能为空")

    query = query.strip()

    if len(query) > max_length:
        raise ValueError(f"搜索关键词不能超过{max_length}个字符")

    # Remove SQL wildcards and special chars for safety
    dangerous = [";", "--", "/*", "*/", "xp_", "sp_", "exec", "drop", "delete"]
    for d in dangerous:
        if d in query.lower():
            raise ValueError("搜索关键词包含非法字符")

    return query


def validate_limit(limit: int, default: int = 20, max_val: int = 1000) -> int:
    """Validate limit parameter."""
    if limit < 1:
        return default
    if limit > max_val:
        return max_val
    return limit


def sanitize_html(text: str) -> str:
    """Sanitize text to prevent XSS in HTML contexts."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
