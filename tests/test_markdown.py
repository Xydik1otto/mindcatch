"""Minimal Markdown renderer: safe (HTML-escaped) subset."""

from app.logic.markdown import markdown_to_html as md


class TestHeadings:
    def test_h1(self):
        assert md("# Заголовок") == "<h1>Заголовок</h1>"

    def test_h3(self):
        assert md("### дрібний") == "<h3>дрібний</h3>"

    def test_h4_not_supported(self):
        assert "<h4>" not in md("#### чотири")


class TestInline:
    def test_bold(self):
        assert md("**важливо**") == "<p><strong>важливо</strong></p>"

    def test_italic(self):
        assert md("*курсив*") == "<p><em>курсив</em></p>"

    def test_code(self):
        assert md("`print(1)`") == "<p><code>print(1)</code></p>"

    def test_link(self):
        out = md("[docs](https://example.com)")
        assert '<a href="https://example.com"' in out

    def test_javascript_link_rejected(self):
        out = md("[x](javascript:alert(1))")
        assert "<a " not in out


class TestSafety:
    def test_html_escaped(self):
        assert "<script>" not in md("<script>alert(1)</script>")
        assert "&lt;script&gt;" in md("<script>alert(1)</script>")

    def test_bold_target_is_escaped(self):
        assert md("**<b>x</b>**") == "<p><strong>&lt;b&gt;x&lt;/b&gt;</strong></p>"


class TestStructure:
    def test_unordered_list(self):
        out = md("- один\n- два")
        assert out == "<ul>\n<li>один</li>\n<li>два</li>\n</ul>"

    def test_ordered_list(self):
        out = md("1. перший\n2. другий")
        assert out.startswith("<ol>") and out.count("<li>") == 2

    def test_paragraphs_and_blank_lines(self):
        out = md("перший абзац\n\nдругий абзац")
        assert out.count("<p>") == 2

    def test_empty_and_none(self):
        assert md("") == ""
        assert md("   \n  ") == ""
