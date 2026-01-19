"""
Test configuration and shared fixtures.

Stubs optional third-party modules when they are not installed.
"""

import sys
import types


def _ensure_stub(module_name: str, attributes: dict) -> None:
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    for name, value in attributes.items():
        setattr(module, name, value)
    sys.modules[module_name] = module


try:
    import newsapi  # type: ignore  # pragma: no cover
except Exception:
    class _DummyNewsApiClient:
        def __init__(self, *args, **kwargs):
            pass

    _ensure_stub("newsapi", {"NewsApiClient": _DummyNewsApiClient})


try:
    import feedparser  # type: ignore  # pragma: no cover
except Exception:
    def _dummy_parse(*args, **kwargs):
        class _DummyFeed:
            entries = []
            feed = {}
        return _DummyFeed()

    _ensure_stub("feedparser", {"parse": _dummy_parse})


try:
    import streamlit  # type: ignore  # pragma: no cover
except Exception:
    def _cache_decorator(*args, **kwargs):
        def _wrap(func):
            return func
        return _wrap

    _ensure_stub(
        "streamlit",
        {
            "cache_data": _cache_decorator,
            "cache_resource": _cache_decorator,
        }
    )


try:
    import pandas  # type: ignore  # pragma: no cover
except Exception:
    class _DummyDataFrame:
        empty = True

        def __init__(self, *args, **kwargs):
            pass

    def _dummy_to_datetime(*args, **kwargs):
        return []

    _ensure_stub(
        "pandas",
        {
            "DataFrame": _DummyDataFrame,
            "to_datetime": _dummy_to_datetime,
        }
    )
