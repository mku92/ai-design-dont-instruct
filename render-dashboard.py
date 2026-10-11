#!/usr/bin/env python3
"""
결과 파일(마크다운)을 브라우저로 열어볼 수 있는 HTML 한 장으로 바꾼다.

사용법:
    python render-dashboard.py <결과파일.md> [출력파일.html]

외부 패키지가 필요 없다(표준 라이브러리만 사용). 12·13·14장 중 어느 도메인을
골랐든 같은 스크립트로 결과 파일을 렌더링할 수 있다 — 결과 파일의 마크다운
구조(제목/표/체크리스트/굵게)가 전부 같은 규칙을 따르기 때문이다.
"""
import html
import re
import sys
from pathlib import Path

CSS = """
:root {
  --bg: #F7F3EC; --card: #FFFFFF; --ink: #2E3338; --accent: #C2542D;
  --border: #E4DDD0; --muted: #6B6459;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 0 4rem 0; background: var(--bg); color: var(--ink);
  font-family: -apple-system, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
  line-height: 1.65;
}
.wrap { max-width: 860px; margin: 0 auto; padding: 2.5rem 1.5rem; }
header.page-head {
  border-bottom: 3px solid var(--accent); padding-bottom: 1rem; margin-bottom: 2rem;
}
header.page-head .kicker {
  color: var(--accent); font-weight: 700; font-size: 0.85rem; letter-spacing: .04em;
  text-transform: uppercase; margin-bottom: .3rem;
}
h1 { font-size: 1.9rem; margin: 1.6rem 0 .8rem; }
h2 { font-size: 1.4rem; margin: 2.2rem 0 .7rem; border-left: 4px solid var(--accent); padding-left: .6rem; }
h3 { font-size: 1.1rem; margin: 1.6rem 0 .5rem; color: var(--accent); }
h4 { font-size: 1rem; margin: 1.2rem 0 .4rem; }
p { margin: .6rem 0; }
strong { color: var(--accent); }
code { background: #EFE9DC; padding: .1rem .35rem; border-radius: 4px; font-size: .9em; }
pre {
  background: #23262b; color: #eee; padding: 1rem; border-radius: 8px;
  overflow-x: auto; font-size: .85rem;
}
pre code { background: none; color: inherit; padding: 0; }
blockquote {
  margin: 1rem 0; padding: .6rem 1rem; background: var(--card);
  border-left: 4px solid var(--border); color: var(--muted);
}
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
table {
  width: 100%; border-collapse: collapse; margin: 1rem 0; background: var(--card);
  border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
th, td { text-align: left; padding: .55rem .8rem; border-bottom: 1px solid var(--border); font-size: .92rem; }
th { background: #EFE9DC; font-weight: 700; }
tr:last-child td { border-bottom: none; }
ul, ol { padding-left: 1.4rem; margin: .6rem 0; }
li { margin: .3rem 0; }
li.checked { color: var(--muted); }
li.checked::marker { content: "☑ "; }
.checkbox { display: inline-block; width: 1.1em; }
footer.page-foot {
  max-width: 860px; margin: 3rem auto 0; padding: 1rem 1.5rem; color: var(--muted);
  font-size: .82rem; border-top: 1px solid var(--border);
}
"""


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    return text


def render_table(lines):
    header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    body_rows = [
        [c.strip() for c in ln.strip().strip("|").split("|")]
        for ln in lines[2:]
        if ln.strip()
    ]
    out = ["<table><thead><tr>"]
    out += [f"<th>{inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for row in body_rows:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_markdown(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)
    in_list = False
    list_tag = None

    def close_list():
        nonlocal in_list, list_tag
        if in_list:
            out.append(f"</{list_tag}>")
            in_list = False
            list_tag = None

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # fenced code block
        if stripped.startswith("```"):
            close_list()
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            i += 1
            continue

        # table: header row + separator row (---|---)
        if "|" in stripped and i + 1 < n and re.match(r"^\|?[\s:-]+\|[\s:|-]+$", lines[i + 1].strip()):
            close_list()
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip():
                j += 1
            out.append(render_table(lines[i:j]))
            i = j
            continue

        # headers
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # horizontal rule
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            close_list()
            out.append("<hr/>")
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            close_list()
            out.append(f"<blockquote>{inline(stripped.lstrip('>').strip())}</blockquote>")
            i += 1
            continue

        # checklist / unordered list
        m = re.match(r"^[-*]\s+\[([ xX])\]\s+(.*)$", stripped)
        if m:
            if not in_list or list_tag != "ul":
                close_list()
                out.append("<ul>")
                in_list, list_tag = True, "ul"
            checked = m.group(1).lower() == "x"
            box = "☑" if checked else "☐"
            cls = ' class="checked"' if checked else ""
            out.append(f'<li{cls}><span class="checkbox">{box}</span> {inline(m.group(2))}</li>')
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if not in_list or list_tag != "ul":
                close_list()
                out.append("<ul>")
                in_list, list_tag = True, "ul"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if not in_list or list_tag != "ol":
                close_list()
                out.append("<ol>")
                in_list, list_tag = True, "ol"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        # blank line
        if not stripped:
            close_list()
            i += 1
            continue

        # paragraph
        close_list()
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_list()
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("사용법: python render-dashboard.py <결과파일.md> [출력파일.html]")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"파일을 찾을 수 없다: {src}")
        sys.exit(1)

    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    md_text = src.read_text(encoding="utf-8")
    title = src.stem
    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if m:
        title = m.group(1).strip()

    body = render_markdown(md_text)
    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="page-head">
  <div class="kicker">하네스 엔지니어링 · 직접 해보기 완성작</div>
  <div style="color:var(--muted); font-size:.85rem;">원본: {html.escape(src.name)}</div>
</header>
{body}
</div>
<footer class="page-foot">
  이 페이지는 `render-dashboard.py`가 위 결과 파일을 그대로 읽어 만든 것이다.
  결과 파일을 고치고 스크립트를 다시 돌리면 이 페이지도 그만큼 바뀐다.
</footer>
</body>
</html>
"""
    out_path.write_text(page, encoding="utf-8")
    print(f"완성: {out_path}")
    print("브라우저로 이 파일을 열어 확인한다(더블클릭하거나 파일 경로를 주소창에 붙여넣기).")


if __name__ == "__main__":
    main()
