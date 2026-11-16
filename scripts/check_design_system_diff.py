#!/usr/bin/env python3
"""Gate do Design System: confere só as linhas ADICIONADAS de um diff.

FE-DEC-011–020 e D-VIS-01: na Web, cor, medida e fonte vêm de tokens
`var(--...)`; no app, de `mobile/src/theme.ts`. O legado não é cobrado
de uma vez (DS-V1-01-D03): quem toca numa linha deixa a linha nos tokens.

Saída: 0 sem achados; 1 com violações; 2 quando o diff não pôde ser lido
(falha fechada: nunca aprova no escuro).

Uso: python scripts/check_design_system_diff.py --base origin/main
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

WEB_SUFFIXES = (".css", ".html")
WEB_PREFIX = "app/"
WEB_EXEMPT = ("app/static/css/tokens.css",)
MOBILE_PREFIX = "mobile/src/"
MOBILE_SUFFIXES = (".ts", ".tsx")
MOBILE_EXEMPT = ("mobile/src/theme.ts",)

_COLOR_FUNCTION = re.compile(r"\b(?:rgba?|hsla?)\(", re.IGNORECASE)
# Cor em hexadecimal como valor: depois de ":" ou espaço, nunca dentro de
# um endereço (href="#secao", url(#id), "{{ url }}#abc") nem de &#39;.
_WEB_HEX = re.compile(r"(?<![\w&\"'(/}])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
_MOBILE_HEX = re.compile(r"[\"']#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})[\"']")
_PX = re.compile(r"(?<![\w.-])\d*\.?\d+px\b")
_FONT_FAMILY = re.compile(r"font-family\s*:(?!\s*(?:var\(|inherit\b))", re.IGNORECASE)
_IMPORTANT = re.compile(r"!\s*important\b", re.IGNORECASE)
_FONT_SIZE_NUMBER = re.compile(r"\bfontSize\s*:\s*\d")
_BORDER_RADIUS_NUMBER = re.compile(r"\bborderRadius\s*:\s*(?!0\b)\d")
_CSS_COMMENT = re.compile(r"/\*.*?\*/")
_JINJA_COMMENT = re.compile(r"\{#.*?#\}")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass(frozen=True)
class Violation:
    path: str
    line_number: int
    rule: str
    text: str


def _web_rules(text):
    code = _JINJA_COMMENT.sub("", _CSS_COMMENT.sub("", text))
    stripped = code.strip()
    if stripped.startswith(("/*", "*", "{#")):
        return
    if _WEB_HEX.search(code) or _COLOR_FUNCTION.search(code):
        yield "cor literal"
    if _PX.search(code):
        yield "px literal"
    if _FONT_FAMILY.search(code):
        yield "font-family literal"
    if _IMPORTANT.search(code):
        yield "!important"


def _mobile_rules(text):
    stripped = text.strip()
    if stripped.startswith(("//", "*", "/*")):
        return
    if _MOBILE_HEX.search(text) or _COLOR_FUNCTION.search(text):
        yield "cor literal"
    if _FONT_SIZE_NUMBER.search(text):
        yield "fontSize numérico"
    if _BORDER_RADIUS_NUMBER.search(text):
        yield "borderRadius numérico"


def _rules_for(path):
    if path.startswith(WEB_PREFIX) and path.endswith(WEB_SUFFIXES) and path not in WEB_EXEMPT:
        return _web_rules
    if path.startswith(MOBILE_PREFIX) and path.endswith(MOBILE_SUFFIXES) and path not in MOBILE_EXEMPT:
        return _mobile_rules
    return None


def find_violations(diff_text):
    """Violações nas linhas adicionadas de um diff unificado."""
    found = []
    path = None
    rules = None
    line_number = 0
    in_hunk = False

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            path, rules, in_hunk = None, None, False
            continue
        if not in_hunk and raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else target.removeprefix("b/")
            rules = _rules_for(path) if path else None
            continue
        hunk = _HUNK.match(raw)
        if hunk:
            line_number = int(hunk.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("+"):
            if rules is not None:
                text = raw[1:]
                for rule in rules(text):
                    found.append(Violation(path, line_number, rule, text.strip()))
            line_number += 1
        elif raw.startswith("-") or raw.startswith("\\"):
            continue
        else:
            line_number += 1
    return found


def _read_diff(base, repo):
    result = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", "--no-ext-diff", f"{base}...HEAD"],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff falhou")
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main", help="ramo de comparação")
    parser.add_argument("--repo", default=".", help="pasta do repositório")
    args = parser.parse_args(argv)

    try:
        diff = _read_diff(args.base, args.repo)
    except (OSError, RuntimeError) as exc:
        print(f"Gate do Design System INCONCLUSIVO (falha fechada): {exc}")
        return 2

    violations = find_violations(diff)
    if not violations:
        print("Gate do Design System: 0 violações nas linhas novas.")
        return 0

    print(f"Gate do Design System: {len(violations)} violação(ões) nas linhas novas.")
    for item in violations:
        print(f"{item.path}:{item.line_number}: {item.rule}: {item.text}")
    print("Use tokens: var(--...) na Web; theme.ts no app.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
