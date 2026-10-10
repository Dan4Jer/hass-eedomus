"""Box-tagged logging for the eedomus integration.

On a multi-box install no log line says which box emitted it. This
module is the single tagging engine (ticket 113):

- `get_logger(name)` returns the standard named logger with the box
  tag filter attached (idempotent). Logger names pass through
  untouched - unit tests pin them via caplog.
- `box_log_context(tag)` is a context manager that tags every log
  line emitted inside it, across `await` boundaries within the task
  (ContextVar semantics). A nested context wins until it exits.
- `resolve_box_tag(entry, client=None)` resolves the tag: config
  entry title, then api host, then entry_id - never empty.

The filter only appends ` [box: <tag>]` to the record message when a
box context is set; records emitted outside any box context pass
through untouched, and no record is ever dropped.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Optional

_BOX_TAG: ContextVar[Optional[str]] = ContextVar("eedomus_box_tag", default=None)


class _BoxTagFilter(logging.Filter):
    """Append the current box tag to records emitted in a box context.

    The tag is appended to the record message (not the formatter), so
    HA's stock log format shows it with no formatter change. Outside
    a box context the record passes through unchanged.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Append the tag to the message; always keep the record."""
        tag = _BOX_TAG.get()
        if tag:
            record.msg = f"{record.msg} [box: {tag}]"
        return True


def get_logger(name: str) -> logging.Logger:
    """Return the named logger with the box tag filter attached.

    The filter is attached at most once per logger; the logger name is
    passed through unchanged so caplog pinning keeps working.
    """
    logger = logging.getLogger(name)
    if not any(isinstance(flt, _BoxTagFilter) for flt in logger.filters):
        logger.addFilter(_BoxTagFilter())
    return logger


@contextmanager
def box_log_context(tag: str) -> Iterator[None]:
    """Tag every log line emitted inside this context with the box name.

    An empty tag is treated as no tag (never appends ` [box: ]`).
    """
    token = _BOX_TAG.set(tag or None)
    try:
        yield
    finally:
        _BOX_TAG.reset(token)


def resolve_box_tag(entry: Any = None, client: Any = None) -> str:
    """Resolve the box tag: entry title, then api host, then entry_id.

    Mirrors the coordinator's box display name resolution (config
    entry title first, then the configured box address), with a final
    entry_id fallback so the tag is never empty.
    """
    entries = tuple(
        candidate
        for candidate in (entry, getattr(client, "config_entry", None))
        if candidate is not None
    )
    for candidate in entries:
        title = getattr(candidate, "title", None)
        if isinstance(title, str) and title.strip():
            return title
    for source in (client, *entries):
        for host_attr in ("api_host", "host"):
            host = getattr(source, host_attr, None)
            if isinstance(host, str) and host.strip():
                return host
        data = getattr(source, "data", None)
        if isinstance(data, dict):
            host = data.get("api_host")
            if isinstance(host, str) and host.strip():
                return host
    for candidate in entries:
        entry_id = getattr(candidate, "entry_id", None)
        if isinstance(entry_id, str) and entry_id.strip():
            return entry_id
    return "unknown"
