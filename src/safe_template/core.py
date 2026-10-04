from __future__ import annotations

import html
from typing import Any, Mapping


class SafeTemplate:
    """A template renderer with no code execution.

    Only two constructs are supported:
      {{ expr }}  — renders an expression looked up on the context.
      {{ expr | filter }}  — applies a named filter to the value.

    Expressions are dotted attribute/index paths: a.b.c. Each segment is
    looked up via the configured lookup function. By default, lookups are
    restricted to dict keys and attribute names that do NOT start with an
    underscore (see _default_lookup).

    No template inheritance, no conditionals, no loops, no expressions
    other than a dotted path optionally followed by a single filter. The
    trade-off: you cannot express logic in the template — that's the point.
    """

    _NO_DEFAULT = object()

    def __init__(
        self,
        *,
        autoescape: bool = True,
        missing: str = "",
        lookup: Any = None,
        filters: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize a renderer.

        Args:
            autoescape: If True (default), interpolated text is HTML-escaped.
                Filters are responsible for their own escaping; the escaping
                is applied to the value *before* the filter runs, because a
                filter like 'upper' should operate on the raw value, and a
                'safe' filter can then opt out by returning a SafeString.
            missing: String used when a lookup fails. The empty string is
                chosen so a missing value produces empty output rather than
                surfacing 'None' to template authors.
            lookup: Callable(name, obj) -> Any. Override for custom access
                semantics. See _default_lookup for the default.
            filters: Mapping of filter name to callable(value) -> str.
                Built-in filters: upper, lower, trim. A 'safe' filter is also
                provided to mark a value as pre-escaped.
        """
        self._autoescape = autoescape
        self._missing = missing
        self._lookup = lookup if lookup is not None else _default_lookup
        self._filters = _BUILTIN_FILTERS.copy()
        if filters:
            self._filters.update(filters)
        # Precompile the template lazily per-instance is not needed since
        # render() is stateless apart from configuration.

    def render(self, template: str, context: Mapping[str, Any]) -> str:
        """Render a template string with the given context.

        Args:
            template: Raw template text.
            context: Mapping of top-level names available to the template.

        Returns:
            The rendered string.
        """
        parts: list[str] = []
        i = 0
        n = len(template)
        while i < n:
            start = template.find("{{", i)
            if start == -1:
                parts.append(template[i:])
                break
            parts.append(template[i:start])
            # Find the closing braces. We do not support nested tags, so a
            # simple find is correct and avoids any state machine complexity.
            end = template.find("}}", start + 2)
            if end == -1:
                # Unterminated tag: emit literally. This is a deliberate
                # choice so a typo doesn't raise; the output still shows the
                # braces, making the mistake visible.
                parts.append(template[start:])
                break
            expr = template[start + 2:end].strip()
            parts.append(self._render_expr(expr, context))
            i = end + 2
        return "".join(parts)

    def _render_expr(self, expr: str, context: Mapping[str, Any]) -> str:
        """Render a single {{ ... }} expression."""
        if not expr:
            return ""
        filter_name = None
        if "|" in expr:
            # Only one filter allowed. Splitting on the first pipe means a
            # filter argument containing a pipe is unsupported — but no
            # built-in filter takes arguments, so this is fine.
            path, _, filter_name = expr.partition("|")
            path = path.strip()
            filter_name = filter_name.strip()
        else:
            path = expr

        value = self._resolve_path(path, context)
        if filter_name is not None:
            filt = self._filters.get(filter_name)
            if filt is None:
                # Unknown filter: emit the missing-fallback so a typo is
                # visible but non-fatal.
                return self._missing
            return filt(value)
        return self._escape(value)

    def _resolve_path(self, path: str, context: Mapping[str, Any]) -> Any:
        """Resolve a dotted path against the context.

        Returns self._missing (the raw sentinel string) when any segment
        fails; callers that apply a filter will still see the missing string,
        which is intentional — a filter on a missing value should also yield
        the missing fallback rather than raising.
        """
        if not path:
            return self._missing
        current: Any = context
        for segment in path.split("."):
            if segment == "":
                return self._missing
            try:
                current = self._lookup(segment, current)
            except LookupError:
                return self._missing
        return current

    def _escape(self, value: Any) -> str:
        if value is None or value == self._missing:
            return self._missing
        if isinstance(value, SafeString):
            return str(value)
        text = str(value)
        if self._autoescape:
            return html.escape(text, quote=True)
        return text


class SafeString(str):
    """A str subclass marking already-escaped text.

    Returning a SafeString from a filter bypasses autoescaping. This is the
    single escape hatch for trusted content; it is intentionally minimal so
    template authors cannot accidentally enable code execution.
    """

    __slots__ = ()


def _default_lookup(name: str, obj: Any) -> Any:
    """Default lookup: dict keys or public attributes only.

    Underscore-prefixed names are forbidden to prevent reaching into dunder
    methods or private internals, which is the most common vector for turning
    a 'safe' template into an unsafe one.
    """
    if name.startswith("_"):
        raise KeyError(name)
    if isinstance(obj, Mapping):
        if name in obj:
            return obj[name]
        raise KeyError(name)
    # For non-mappings, allow attribute access but still block underscores
    # (checked above). This lets dataclasses and simple objects work.
    try:
        return getattr(obj, name)
    except AttributeError as exc:
        raise KeyError(name) from exc


def _filter_upper(value: Any) -> str:
    text = "" if value is None else str(value)
    return SafeString(html.escape(text.upper(), quote=True)) if True else text


def _filter_lower(value: Any) -> str:
    text = "" if value is None else str(value)
    return SafeString(html.escape(text.lower(), quote=True))


def _filter_trim(value: Any) -> str:
    text = "" if value is None else str(value)
    return SafeString(html.escape(text.strip(), quote=True))


def _filter_safe(value: Any) -> str:
    """Mark a value as pre-escaped, bypassing autoescape."""
    if isinstance(value, SafeString):
        return value
    return SafeString("" if value is None else str(value))


def _make_filter_upper(autoescape: bool):
    def _upper(value: Any) -> str:
        text = "" if value is None else str(value)
        if autoescape:
            return SafeString(html.escape(text.upper(), quote=True))
        return text.upper()
    return _upper


_BUILTIN_FILTERS: dict[str, Any] = {
    "upper": _filter_upper,
    "lower": _filter_lower,
    "trim": _filter_trim,
    "safe": _filter_safe,
}


def render(
    template: str,
    context: Mapping[str, Any],
    *,
    autoescape: bool = True,
    missing: str = "",
) -> str:
    """Convenience function: render a template with default settings.

    For repeated renders or custom filters, instantiate SafeTemplate once
    and reuse it.
    """
    return SafeTemplate(autoescape=autoescape, missing=missing).render(template, context)
