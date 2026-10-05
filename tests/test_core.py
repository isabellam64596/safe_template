import unittest

from safe_template import SafeTemplate, render
from safe_template.core import SafeString


class TestBasicSubstitution(unittest.TestCase):
    def test_plain_text_passes_through(self):
        self.assertEqual(render("hello world", {}), "hello world")

    def test_single_variable(self):
        self.assertEqual(render("Hello {{ name }}!", {"name": "Alice"}), "Hello Alice!")

    def test_multiple_variables(self):
        result = render("{{ a }} and {{ b }}", {"a": "one", "b": "two"})
        self.assertEqual(result, "one and two")

    def test_missing_yields_empty(self):
        self.assertEqual(render("[{{ missing }}]", {}), "[]")

    def test_custom_missing(self):
        t = SafeTemplate(missing="?")
        self.assertEqual(t.render("{{ x }}", {}), "?")


class TestEscaping(unittest.TestCase):
    def test_html_escaped_by_default(self):
        self.assertEqual(render("{{ x }}", {"x": "<script>"}), "&lt;script&gt;")

    def test_quotes_escaped(self):
        self.assertEqual(render("{{ x }}", {"x": '"hi"'}), "&quot;hi&quot;")

    def test_autoescape_off(self):
        t = SafeTemplate(autoescape=False)
        self.assertEqual(t.render("{{ x }}", {"x": "<b>"}), "<b>")

    def test_none_renders_as_missing(self):
        self.assertEqual(render("[{{ x }}]", {"x": None}), "[]")


class TestDottedPaths(unittest.TestCase):
    def test_dict_nested(self):
        ctx = {"user": {"name": "Bob"}}
        self.assertEqual(render("{{ user.name }}", ctx), "Bob")

    def test_deeply_nested(self):
        ctx = {"a": {"b": {"c": "deep"}}}
        self.assertEqual(render("{{ a.b.c }}", ctx), "deep")

    def test_missing_segment(self):
        ctx = {"a": {}}
        self.assertEqual(render("{{ a.b.c }}", ctx), "")

    def test_underscore_blocked(self):
        ctx = {"obj": {"_secret": "no"}}
        self.assertEqual(render("{{ obj._secret }}", ctx), "")

    def test_attribute_access_on_object(self):
        class Item:
            def __init__(self):
                self.title = "Hello"
        ctx = {"item": Item()}
        self.assertEqual(render("{{ item.title }}", ctx), "Hello")


class TestFilters(unittest.TestCase):
    def test_upper_filter(self):
        self.assertEqual(render("{{ x | upper }}", {"x": "hi"}), "HI")

    def test_lower_filter(self):
        self.assertEqual(render("{{ x | lower }}", {"x": "HI"}), "hi")

    def test_trim_filter(self):
        self.assertEqual(render("{{ x | trim }}", {"x": "  hi  "}), "hi")

    def test_filter_with_spaces(self):
        self.assertEqual(render("{{ x   |   upper }}", {"x": "a"}), "A")

    def test_unknown_filter_yields_missing(self):
        self.assertEqual(render("{{ x | nope }}", {"x": "a"}), "")

    def test_filter_on_missing_value(self):
        self.assertEqual(render("{{ x | upper }}", {}), "")

    def test_safe_filter_bypasses_escape(self):
        self.assertEqual(render("{{ x | safe }}", {"x": "<b>"}), "<b>")

    def test_upper_filter_escapes_result(self):
        self.assertEqual(render("{{ x | upper }}", {"x": "<b>"}), "&lt;B&gt;")


class TestEdgeCases(unittest.TestCase):
    def test_empty_expression(self):
        self.assertEqual(render("{{}}", {}), "")

    def test_whitespace_only_expression(self):
        self.assertEqual(render("{{   }}", {}), "")

    def test_unterminated_tag_emitted_literally(self):
        self.assertEqual(render("{{ not closed", {}), "{{ not closed")

    def test_consecutive_tags(self):
        self.assertEqual(render("{{ a }}{{ b }}", {"a": "1", "b": "2"}), "12")

    def test_tag_adjacent_to_text(self):
        self.assertEqual(render("x{{v}}y", {"v": "-"}), "x-y")

    def test_empty_path_after_dot(self):
        ctx = {"a": {"b": "x"}}
        self.assertEqual(render("{{ a..b }}", ctx), "")

    def test_custom_lookup(self):
        def lookup(name, obj):
            if name == "custom":
                return "value"
            raise KeyError(name)
        t = SafeTemplate(lookup=lookup)
        self.assertEqual(t.render("{{ custom }}", {}), "value")

    def test_custom_filter(self):
        t = SafeTemplate(filters={"exclaim": lambda v: SafeString((str(v) if v is not None else "") + "!")})
        self.assertEqual(t.render("{{ x | exclaim }}", {"x": "hi"}), "hi!")


class TestSafeString(unittest.TestCase):
    def test_safe_string_passthrough(self):
        t = SafeTemplate()
        ctx = {"x": SafeString("<raw>")}
        self.assertEqual(t.render("{{ x }}", ctx), "<raw>")


if __name__ == "__main__":
    unittest.main()
