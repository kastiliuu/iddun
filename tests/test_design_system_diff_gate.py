"""Gate do Design System nas linhas novas (FE-DEC-011–020, D-VIS-01).

Só as linhas ADICIONADAS de um diff são conferidas: o legado não é
cobrado de uma vez (DS-V1-01-D03, migração gradual). Web usa tokens
`var(--...)`; o app usa `theme.ts`.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_design_system_diff import find_violations, main  # noqa: E402


def _diff(path, *added, removed=()):
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        "@@ -1,0 +1,9 @@",
    ]
    lines += [f"-{line}" for line in removed]
    lines += [f"+{line}" for line in added]
    return "\n".join(lines) + "\n"


def _rules(diff):
    return [item.rule for item in find_violations(diff)]


@pytest.mark.parametrize(
    "line, rule",
    [
        ("  color: #6B2EFF;", "cor literal"),
        ("  color: #fff;", "cor literal"),
        ("  background: rgba(11, 11, 15, .96);", "cor literal"),
        ("  background: rgb(0 0 0);", "cor literal"),
        ("  border-color: hsl(260 100% 59%);", "cor literal"),
        ("  padding: 12px;", "px literal"),
        ("  border: 1px solid var(--color-border-light);", "px literal"),
        ("  font-family: Inter, sans-serif;", "font-family literal"),
        ("  display: none !important;", "!important"),
    ],
)
def test_web_css_added_lines_are_checked(line, rule):
    assert _rules(_diff("app/static/css/feed.css", line)) == [rule]


def test_web_html_inline_style_is_checked_but_anchors_and_entities_are_not():
    diff = _diff(
        "app/templates/feed/index.html",
        '<a href="#post-composer">Publicar</a>',
        '<use href="#icon-abc"></use>',
        "<span>&#39;aspas&#39; e &#8230;</span>",
        '<a href="{{ url }}#fff">ok</a>',
        '<p style="color: #fff">ruim</p>',
    )
    found = find_violations(diff)
    assert [(item.rule, item.line_number) for item in found] == [("cor literal", 5)]


def test_tokens_and_relative_units_pass():
    diff = _diff(
        "app/static/css/posts.css",
        "  color: var(--color-ink);",
        "  border: 0.0625rem solid var(--color-border-light);",
        "  font-family: var(--font-sans);",
        "  font: inherit;",
        "  min-height: var(--ds-control-min-target);",
        "  max-width: 56.25em;",
        "  /* 16px de respiro no desenho original */",
    )
    assert find_violations(diff) == []


def test_removed_lines_context_and_token_file_are_ignored():
    removed = _diff("app/static/css/feed.css", removed=["  color: #000;", "  padding: 4px !important;"])
    assert find_violations(removed) == []
    tokens = _diff("app/static/css/tokens.css", "  --color-plum: #6B2EFF;", "  --ds-space-1: 4px;")
    assert find_violations(tokens) == []
    # Linha de conteúdo que começa com "+" (vira "++" no diff) não é cabeçalho.
    plus = _diff("app/static/css/feed.css", "+ color: #000;")
    assert _rules(plus) == ["cor literal"]


@pytest.mark.parametrize(
    "line, rule",
    [
        ('  color: "#6B2EFF",', "cor literal"),
        ("  backgroundColor: 'rgba(0,0,0,0.5)',", "cor literal"),
        ("  fontSize: 15,", "fontSize numérico"),
        ("  borderRadius: 12,", "borderRadius numérico"),
    ],
)
def test_mobile_added_lines_are_checked(line, rule):
    assert _rules(_diff("mobile/src/app/create-post.tsx", line)) == [rule]


def test_mobile_tokens_theme_file_and_other_folders_pass():
    ok = _diff(
        "mobile/src/app/create-post.tsx",
        "  color: colors.plum,",
        "  fontSize: designScale.typography.body,",
        "  borderRadius: radius.lg,",
        "  borderRadius: 0,",
        '  router.push("/post/123#comentarios");',
    )
    assert find_violations(ok) == []
    theme = _diff("mobile/src/theme.ts", '  plum: "#6B2EFF",', "  body: 16,")
    assert find_violations(theme) == []
    # Fora do escopo: backend, testes e scripts.
    other = _diff("tests/test_x.py", 'COLOR = "#6B2EFF"  # 12px')
    assert find_violations(other) == []


def test_exit_codes_with_a_real_repository(tmp_path, capsys):
    def git(*args):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=tmp_path, check=True, capture_output=True,
        )

    css = tmp_path / "app" / "static" / "css"
    css.mkdir(parents=True)
    (css / "feed.css").write_text(".a {\n  color: var(--color-ink);\n}\n")
    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "feature")

    (css / "feed.css").write_text(".a {\n  color: var(--color-ink);\n}\n.b {\n  color: #000;\n  padding: 8px;\n}\n")
    git("commit", "-q", "-am", "ruim")
    assert main(["--base", "main", "--repo", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "app/static/css/feed.css:5" in out and "cor literal" in out
    assert "app/static/css/feed.css:6" in out and "px literal" in out

    (css / "feed.css").write_text(
        ".a {\n  color: var(--color-ink);\n}\n.b {\n  color: var(--color-ink);\n  padding: var(--ds-space-2);\n}\n"
    )
    git("commit", "-q", "-am", "tokens")
    assert main(["--base", "main", "--repo", str(tmp_path)]) == 0

    # Sem conseguir o diff, falha fechado (2): nunca aprova no escuro.
    assert main(["--base", "ramo-que-nao-existe", "--repo", str(tmp_path)]) == 2
