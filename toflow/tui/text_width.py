"""Utilities for terminal display-width aware text operations.

`len()` counts code points, not rendered terminal columns. East Asian text
and some symbols occupy two columns, so all layout math should use these
helpers instead of plain string length/slicing.
"""

from __future__ import annotations

from prompt_toolkit.utils import get_cwidth


def char_width(ch: str) -> int:
    """Return rendered width of a single character in terminal columns."""
    return max(0, get_cwidth(ch))


def text_width(text: str) -> int:
    """Return rendered width of text in terminal columns."""
    return sum(char_width(ch) for ch in text)


def take_by_width(text: str, max_width: int) -> str:
    """Take as many characters as fit into `max_width` columns."""
    if max_width <= 0 or not text:
        return ""

    out: list[str] = []
    used = 0
    for ch in text:
        w = char_width(ch)
        if used + w > max_width:
            break
        out.append(ch)
        used += w
    return "".join(out)


def truncate_text(text: str, max_width: int, ellipsis: str = "…") -> str:
    """Truncate text to display width, appending ellipsis when needed."""
    if max_width <= 0:
        return ""
    if text_width(text) <= max_width:
        return text

    ellipsis_w = text_width(ellipsis)
    if ellipsis_w >= max_width:
        return take_by_width(ellipsis, max_width)

    return take_by_width(text, max_width - ellipsis_w) + ellipsis


def wrap_text_lines(text: str, max_width: int) -> list[tuple[int, int]]:
    """Split text into wrapped display lines as (start, end) char index ranges.

    Wrapping is by terminal column width, not code-point count. A single
    oversized glyph occupies its own line. Empty text yields one empty line.
    """
    width = max(1, max_width)
    if not text:
        return [(0, 0)]

    lines: list[tuple[int, int]] = []
    start = 0
    used = 0
    i = 0
    n = len(text)
    while i < n:
        w = char_width(text[i])
        if used > 0 and used + w > width:
            lines.append((start, i))
            start = i
            used = 0
            continue
        if used == 0 and w > width:
            lines.append((i, i + 1))
            i += 1
            start = i
            used = 0
            continue
        used += w
        i += 1
    lines.append((start, n))
    return lines
