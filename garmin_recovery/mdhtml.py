"""Renderizador mínimo de Markdown → HTML (solo biblioteca estándar) para ``informe_completo``.

Admite lo que usa el informe: títulos, párrafos, listas, listas numeradas, tablas, bloques de código,
negrita, cursiva y código en línea. Todo el texto se escapa.
"""
from __future__ import annotations

import html
import re

_INLINE = ((re.compile(r"`([^`]+)`"), r"<code>\1</code>"), (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
           (re.compile(r"(?<![\w*])_([^_]+)_(?![\w*])"), r"<em>\1</em>"))


def inline(text: str) -> str:
    out = html.escape(text.replace("\\*", "\u0001"), quote=False)
    for rx, rep in _INLINE:
        out = rx.sub(rep, out)
    return out.replace("\u0001", "*")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render(md: str) -> str:
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre>" + html.escape("\n".join(lines[i + 1:j])) + "</pre>")
            i = j + 1
        elif ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head, j, body = _cells(ln), i + 2, []
            while j < len(lines) and lines[j].startswith("|"):
                body.append(_cells(lines[j]))
                j += 1
            out.append('<div class="scroll"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table></div>")
            i = j
        elif ln.startswith("#"):
            lvl = min(len(ln) - len(ln.lstrip("#")), 4)
            out.append(f"<h{lvl}>{inline(ln.lstrip('#').strip())}</h{lvl}>")
            i += 1
        elif re.match(r"^(- |\d+\. )", ln):
            ordered = ln[0].isdigit()
            items, j = [], i
            while j < len(lines) and re.match(r"^(- |\d+\. |  )", lines[j]) and lines[j].strip():
                if re.match(r"^(- |\d+\. )", lines[j]):
                    items.append(re.sub(r"^(- |\d+\. )", "", lines[j]))
                else:
                    items[-1] += "<br>" + lines[j].strip()
                j += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t).replace('&lt;br&gt;', '<br>')}</li>" for t in items) + f"</{tag}>")
            i = j
        elif ln.strip() == "---":
            out.append("<hr>")
            i += 1
        elif ln.strip():
            j, buf = i, []
            while j < len(lines) and lines[j].strip() and not re.match(r"^(#|\||```|- |\d+\. |---)", lines[j]):
                buf.append(lines[j])
                j += 1
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
            i = max(j, i + 1)
        else:
            i += 1
    return "\n".join(out)


PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe completo · Garmin Recovery</title><link rel="manifest" href="manifest.webmanifest">
<style>:root{{--bg:#fff;--fg:#1b1f24;--mut:#59636e;--line:#d0d7de;--card:#f6f8fa}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0d1117;--fg:#e6edf3;--mut:#9198a1;--line:#30363d;--card:#161b22}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:16px}}a{{color:inherit}}h1{{font-size:1.5rem}}h2{{font-size:1.2rem;margin-top:1.8em;border-bottom:1px solid var(--line);padding-bottom:.2em}}
h3{{font-size:1.02rem}}table{{border-collapse:collapse;width:100%;font-size:.92rem}}th,td{{border:1px solid var(--line);padding:6px 8px;text-align:left}}
th{{background:var(--card)}}.scroll{{overflow-x:auto}}pre{{background:var(--card);padding:10px;overflow-x:auto;border-radius:6px}}
code{{background:var(--card);padding:1px 4px;border-radius:4px}}li{{margin:.3em 0}}.back{{color:var(--mut);font-size:.9rem}}</style></head>
<body><main><p class="back"><a href="./">← Panel</a></p>{body}</main></body></html>
"""


def page(md: str) -> str:
    return PAGE.format(body=render(md))
