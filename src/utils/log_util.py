"""Logging utilities for the Discord Pasta Bot"""
import logging
from typing import Any, Mapping, Optional

import discord

# Response headers we extract for diagnostic logging. Lowered for
# case-insensitive lookup; aiohttp returns a CIMultiDict so case is normally
# irrelevant, but we still iterate to stay defensive against plain dicts.
RATE_LIMIT_HEADERS: tuple[str, ...] = (
    "retry-after",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "x-ratelimit-reset-after",
    "x-ratelimit-bucket",
    "x-ratelimit-global",
    "x-ratelimit-scope",
    "cf-ray",
    "cf-cache-status",
    "via",
    "server",
    "x-discord-region",
)

# Substrings that *may* indicate a Cloudflare / Discord anti-abuse IP-level
# block. NOTE: ``discord.HTTPException.text`` is populated from the parsed
# JSON ``message`` (or ``response.reason`` as a fallback). Cloudflare's plain
# HTML 429 page has no JSON body, so its ``reason`` is just
# ``"Too Many Requests"`` and most of these substrings will *not* match for
# that case. Treat the fragments as a soft fallback — the reliable detection
# path is the header check in ``_is_global_block``
# (X-RateLimit-Global, Server: cloudflare, cf-ray).
_GLOBAL_BLOCK_TEXT_FRAGMENTS: tuple[str, ...] = (
    "global rate limit",
    "globally rate-limited",
    "accessing our api temporarily",
    "you are being blocked",
)


def header_value(headers, name: str) -> Optional[str]:
    """Look up ``name`` in ``headers`` (case-insensitive), returning None on miss.

    Public-named (not underscore-prefixed) so ``main.py`` and any future call
    site can reuse the same case-insensitive lookup without duplicating the
    iteration. aiohttp exposes ``CIMultiDict`` which is already case-insensitive,
    but the manual loop keeps us safe if a plain dict ever leaks through.
    """
    if headers is None:
        return None
    lower = name.lower()
    try:
        for k, v in headers.items():
            if k.lower() == lower:
                return v
    except (KeyError, TypeError, AttributeError):
        return None
    return None


def _is_global_block(error: discord.HTTPException) -> bool:
    """Return True if this exception looks like a global (IP/account-wide) block.

    Detection proceeds from most reliable to least:
      1. ``X-RateLimit-Global`` header — definitive Discord API global block.
      2. ``Server: cloudflare`` — strong signal that a Cloudflare edge
         intercepted the request (Discord's gateway never returns that header).
      3. Substring fragments over ``response.reason`` + ``error.text`` — soft
         fallback. Works for JSON-bodied global-block responses; for bare
         Cloudflare HTML 429 pages neither ``reason`` nor ``text`` typically
         contains the fragments, so this branch may miss.
    """
    headers = getattr(getattr(error, "response", None), "headers", None)
    if header_value(headers, "x-ratelimit-global") is not None:
        return True
    server_header = header_value(headers, "server")
    if server_header and "cloudflare" in server_header.lower():
        return True
    response = getattr(error, "response", None)
    reason = (getattr(response, "reason", "") or "").lower()
    text = (getattr(error, "text", "") or "").lower()
    # Use a single-space separator rather than "\n" so that any future
    # _GLOBAL_BLOCK_TEXT_FRAGMENTS entry containing a newline can't accidentally
    # match across the reason/text boundary.
    haystack = f"{reason} {text}"
    return any(fragment in haystack for fragment in _GLOBAL_BLOCK_TEXT_FRAGMENTS)


def unwrap_http_exception(error: BaseException) -> Optional[discord.HTTPException]:
    """Return ``error.original`` if it's an HTTPException, otherwise ``error`` itself.

    ``commands.CommandInvokeError`` wraps whatever the command raised, so a
    raw ``isinstance(error, discord.HTTPException)`` check on the outer
    exception will never match an HTTP failure that happened inside a cog.
    Callers should always go through this helper for consistent unwrap.
    """
    if isinstance(error, discord.HTTPException):
        return error
    original = getattr(error, "original", None)
    if isinstance(original, discord.HTTPException):
        return original
    return None


def format_http_exception(
    error: discord.HTTPException,
    context: Optional[Mapping[str, Any]] = None,
) -> str:
    """Return a structured, multi-line summary suitable for log records.

    Designed for grep-ability: a single ``GlobalRateLimitHit`` /
    ``RateLimitHit`` / ``HTTPException`` label on the first line, followed by
    ``key=value`` lines so Render's log viewer / shell filters can pivot on
    individual fields like ``scope=shared`` or ``retry_after=...``.
    """
    is_rate_limit = getattr(error, "status", None) == 429
    is_global = is_rate_limit and _is_global_block(error)

    if is_rate_limit and is_global:
        label = "GlobalRateLimitHit"
    elif is_rate_limit:
        label = "RateLimitHit"
    else:
        label = "HTTPException"

    # ``code`` and ``text`` may be None on discord.py exceptions raised
    # without a parsed JSON body (e.g. Cloudflare HTML 429s). Coerce to "?"
    # so the formatted output always has non-null tokens. Truncate ``text``
    # aggressively because a Cloudflare HTML 429 body can be several KB
    # and would otherwise eat log quota while still conveying no extra
    # signal — the headers line below is the diagnostic value.
    status = getattr(error, "status", None) or "?"
    code = getattr(error, "code", None)
    if code is None:
        code = "?"
    text = getattr(error, "text", None) or "?"
    if len(text) > 240:
        text = text.replace("\n", " ")[:237] + "..."

    lines = [
        f"{label}: status={status} code={code}",
        f"text={text}",
    ]

    headers = getattr(getattr(error, "response", None), "headers", None)
    rl_pairs = [(name, header_value(headers, name)) for name in RATE_LIMIT_HEADERS]
    rl_pairs = [(name, val) for name, val in rl_pairs if val is not None]
    if rl_pairs:
        lines.append("headers: " + ", ".join(f"{name}={val}" for name, val in rl_pairs))

    if context:
        ctx_pairs = [f"{k}={v}" for k, v in context.items()]
        lines.append("context: " + ", ".join(ctx_pairs))

    # Joined with newlines so Render's log viewer preserves indentation.
    return "\n  ".join(lines)


def log_http_exception(
    logger: logging.Logger,
    error: discord.HTTPException,
    context: Optional[Mapping[str, Any]] = None,
    level: Optional[int] = None,
) -> None:
    """Log a discord.HTTPException with diagnostic rate-limit detail.

    429 hits log at WARNING (expected, recoverable) and other HTTPExceptions
    at ERROR. Pass an explicit ``level`` to override. Does not raise.
    """
    if level is None:
        if getattr(error, "status", None) == 429:
            level = logging.WARNING
        else:
            level = logging.ERROR
    logger.log(level, format_http_exception(error, context))
