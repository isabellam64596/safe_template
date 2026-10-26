# Safe Template

A template renderer that cannot execute anything. Supports only variable substitution and single filters — no conditionals, no loops, no expressions beyond a dotted path.

## Usage

```python
from safe_template import render, SafeTemplate
from safe_template.core import SafeString

# One-off render
output = render("Hello {{ name }}!", {"name": "<b>World</b>"})
# -> "Hello &lt;b&gt;World&lt;/b&gt;!"

# Reusable instance with a custom filter
t = SafeTemplate(filters={
    "exclaim": lambda v: SafeString(str(v) + "!"),
})
print(t.render("{{ msg | exclaim }}", {"msg": "hi"}))
# -> "hi!"
```

## Why

Template engines that embed logic (conditionals, loops, expressions) create a surface for injection and code execution. This library exists for the case where you need variable substitution in untrusted contexts and nothing more. The trade-off: if your template needs logic, this is the wrong tool.

## Edge Cases

- **Missing variables** render as the empty string (or whatever you pass as `missing=`), not an error. A typo in a path is silent by design.
- **Unterminated `{{` tags** are emitted literally rather than raising, so the mistake is visible in output.
- **Underscore-prefixed names** (`_private`, `__class__`) are blocked from lookup. This prevents reaching into dunder internals.
- The `safe` filter and `SafeString` are the only escape hatch from autoescaping. Use them only for content you trust.

## API

- `render(template: str, context: dict, *, autoescape=True, missing="") -> str` — convenience function.
- `SafeTemplate(autoescape=True, missing="", lookup=None, filters=None)` — reusable renderer with `.render(template, context)`.
- `SafeString(str)` — mark a value as pre-escaped to bypass autoescaping.

Built-in filters: `upper`, `lower`, `trim`, `safe`. All transform to escaped output except `safe`.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Contributing

Issues and pull requests are welcome. Please keep the dependency list empty —
that constraint is the point of the project, not an oversight.

