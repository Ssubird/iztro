#!/usr/bin/env python3
"""Extract VitePress documentation HTML from the built assets and convert it to Markdown."""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "docs" / "assets"
OUTPUT_DIR = ROOT / "docs-md"


@dataclass
class HtmlNode:
    tag: Optional[str]
    attrs: Dict[str, str] = field(default_factory=dict)
    children: List[Union["HtmlNode", str]] = field(default_factory=list)
    parent: Optional["HtmlNode"] = None

    def append(self, child: Union["HtmlNode", str]) -> None:
        if isinstance(child, HtmlNode):
            child.parent = self
        self.children.append(child)


class HtmlTreeBuilder(HTMLParser):
    _void_tags = {"br", "img", "hr", "meta", "link", "input", "source", "track", "wbr", "area", "base", "col", "embed", "param"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = HtmlNode(tag=None)
        self._current = self.root

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr_dict = {name: (value or "") for name, value in attrs}
        node = HtmlNode(tag=tag, attrs=attr_dict)
        self._current.append(node)
        if tag not in self._void_tags:
            self._current = node

    def handle_startendtag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        node = self._current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self._current = node.parent

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self._current.append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")


def extract_page_meta(text: str) -> Dict[str, str]:
    match = re.search(r"JSON.parse\('(\{.*?\})'\)", text)
    if not match:
        return {}
    json_literal = ast.literal_eval(f"'{match.group(1)}'")
    return json.loads(json_literal)


def extract_content_html(text: str) -> Optional[str]:
    segments: List[str] = []
    idx = 0
    text_len = len(text)
    while idx < text_len:
        next_single = text.find("'", idx)
        next_double = text.find('"', idx)
        if next_single == -1 and next_double == -1:
            break
        if next_single == -1 or (next_double != -1 and next_double < next_single):
            q_index = next_double
        else:
            q_index = next_single
        if q_index == -1:
            break
        quote = text[q_index]
        # ignore escaped quotes
        backslashes = 0
        check_index = q_index - 1
        while check_index >= 0 and text[check_index] == "\\":
            backslashes += 1
            check_index -= 1
        if backslashes % 2 == 1:
            idx = q_index + 1
            continue
        start = q_index + 1
        if start >= text_len or text[start] != '<':
            idx = start
            continue
        buf: List[str] = []
        escaped = False
        pos = start
        for ch in text[start:]:
            if escaped:
                buf.append(ch)
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                break
            else:
                buf.append(ch)
            pos += 1
        else:
            break
        raw = ''.join(buf)
        segments.append(ast.literal_eval(f"{quote}{raw}{quote}"))
        idx = pos + 1
    if not segments:
        return None
    return ''.join(segments)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def split_lines(text: str) -> List[str]:
    return text.splitlines()


def convert_inline(children: Iterable[Union[HtmlNode, str]], ctx: Dict[str, Union[int, bool]]) -> str:
    parts: List[str] = []
    for child in children:
        if isinstance(child, str):
            if ctx.get("in_code"):
                parts.append(unescape(child))
            else:
                text = unescape(child)
                parts.append(normalize_whitespace(text))
            continue
        tag = child.tag or ""
        attrs = child.attrs
        if tag in {"strong", "b"}:
            parts.append(f"**{convert_inline(child.children, ctx)}**")
        elif tag in {"em", "i"}:
            parts.append(f"*{convert_inline(child.children, ctx)}*")
        elif tag == "code":
            if child.parent and child.parent.tag == "pre":
                parts.append(convert_block(child, ctx))
            else:
                inner_ctx = dict(ctx)
                inner_ctx["in_code"] = True
                parts.append(f"`{convert_inline(child.children, inner_ctx)}`")
        elif tag == "span":
            parts.append(convert_inline(child.children, ctx))
        elif tag == "sup":
            parts.append("^" + convert_inline(child.children, ctx))
        elif tag == "sub":
            parts.append("~" + convert_inline(child.children, ctx))
        elif tag == "br":
            parts.append("  \n")
        elif tag == "a":
            classes = attrs.get("class", "")
            if "header-anchor" in classes.split():
                continue
            href = attrs.get("href", "")
            text = convert_inline(child.children, ctx).strip()
            href = re.sub(r"\.html(?=(?:#|$))", ".md", href)
            parts.append(f"[{text}]({href})" if text else href)
        elif tag == "img":
            alt = attrs.get("alt", "")
            src = attrs.get("src", "")
            parts.append(f"![{alt}]({src})")
        else:
            parts.append(convert_block(child, ctx).strip())
    return ''.join(parts)


def convert_table(node: HtmlNode, ctx: Dict[str, Union[int, bool]]) -> str:
    headers: List[str] = []
    rows: List[List[str]] = []

    def extract_row(row_node: HtmlNode) -> List[str]:
        cells: List[str] = []
        for cell in row_node.children:
            if isinstance(cell, HtmlNode) and cell.tag in {"td", "th"}:
                inner = convert_inline(cell.children, ctx).strip()
                cells.append(inner)
        return cells

    for child in node.children:
        if isinstance(child, HtmlNode):
            if child.tag == "thead":
                for row in child.children:
                    if isinstance(row, HtmlNode) and row.tag == "tr":
                        headers = extract_row(row)
            elif child.tag == "tbody":
                for row in child.children:
                    if isinstance(row, HtmlNode) and row.tag == "tr":
                        rows.append(extract_row(row))
            elif child.tag == "tr":
                rows.append(extract_row(child))

    if not headers and rows:
        headers = ["" for _ in rows[0]]
    if not headers:
        return ''
    col_count = len(headers)
    md_lines = ["| " + " | ".join(headers) + " |"]
    md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
    for row in rows:
        padded = row + ["" for _ in range(col_count - len(row))]
        md_lines.append("| " + " | ".join(padded) + " |")
    return "\n".join(md_lines) + "\n\n"


def convert_list(node: HtmlNode, ctx: Dict[str, Union[int, bool]], ordered: bool) -> str:
    level = int(ctx.get("list_level", 0)) + 1
    new_ctx = dict(ctx)
    new_ctx["list_level"] = level
    if ordered:
        counters = list(ctx.get("list_counters", []))
        counters.append(0)
        new_ctx["list_counters"] = counters
    lines: List[str] = []
    for child in node.children:
        if isinstance(child, HtmlNode) and child.tag == "li":
            index = None
            if ordered:
                counters = new_ctx["list_counters"]
                counters[-1] += 1
                index = counters[-1]
            lines.append(convert_list_item(child, new_ctx, ordered, index))
    result = ''.join(lines)
    if ctx.get("list_level", 0) == 0:
        result += "\n"
    return result


def convert_list_item(node: HtmlNode, ctx: Dict[str, Union[int, bool]], ordered: bool, index: Optional[int]) -> str:
    level = int(ctx.get("list_level", 1))
    indent = '  ' * (level - 1)
    bullet = f"{index}. " if ordered and index is not None else "- "
    body = convert_block_children(node, ctx).strip()
    if not body:
        line = indent + bullet
    else:
        body_lines = body.split('\n')
        first = indent + bullet + body_lines[0]
        rest = [indent + '  ' + line for line in body_lines[1:]]
        line = '\n'.join([first] + rest)
    return line + '\n'


def convert_block_children(node: HtmlNode, ctx: Dict[str, Union[int, bool]]) -> str:
    parts: List[str] = []
    for child in node.children:
        parts.append(convert_block(child, ctx))
    return ''.join(parts).strip('\n')


def convert_block(node: Union[HtmlNode, str], ctx: Dict[str, Union[int, bool]]) -> str:
    if isinstance(node, str):
        if ctx.get("in_code"):
            return unescape(node)
        return normalize_whitespace(unescape(node))
    tag = node.tag or ""
    if tag in {"style", "script"}:
        return ""
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(tag[1])
        text = convert_inline(node.children, ctx).strip()
        return ("\n" + "#" * level + f" {text}\n\n") if text else ""
    if tag == "p":
        text = convert_inline(node.children, ctx).strip()
        return (text + "\n\n") if text else ""
    if tag == "br":
        return "  \n"
    if tag == "blockquote":
        inner_ctx = dict(ctx)
        inner_ctx["blockquote"] = int(ctx.get("blockquote", 0)) + 1
        content = convert_block_children(node, inner_ctx)
        if not content:
            return ""
        lines = split_lines(content)
        prefix = '>' * inner_ctx["blockquote"]
        formatted = '\n'.join(prefix + (' ' + line if line else '') for line in lines)
        return formatted + "\n\n"
    if tag == "ul":
        return convert_list(node, ctx, ordered=False)
    if tag == "ol":
        return convert_list(node, ctx, ordered=True)
    if tag == "li":
        return convert_block_children(node, ctx)
    if tag == "pre":
        code_node = None
        if node.children and isinstance(node.children[0], HtmlNode) and node.children[0].tag == "code":
            code_node = node.children[0]
        code_ctx = dict(ctx)
        code_ctx["in_code"] = True
        code = convert_block(code_node, code_ctx) if code_node else ''.join(convert_block(child, code_ctx) for child in node.children)
        language = ""
        if code_node:
            cls = code_node.attrs.get("class", "")
            match = re.search(r"language-([\w+-]+)", cls)
            if match:
                language = match.group(1)
        return f"```{language}\n{code}\n```\n\n"
    if tag == "code":
        if node.parent and node.parent.tag == "pre":
            code_ctx = dict(ctx)
            code_ctx["in_code"] = True
            return ''.join(convert_block(child, code_ctx) for child in node.children)
        inner_ctx = dict(ctx)
        inner_ctx["in_code"] = True
        return f"`{convert_inline(node.children, inner_ctx)}`"
    if tag == "hr":
        return "---\n\n"
    if tag == "table":
        return convert_table(node, ctx)
    if tag == "img":
        alt = node.attrs.get("alt", "")
        src = node.attrs.get("src", "")
        return f"![{alt}]({src})\n\n"
    if tag in {"div", "section", "main", "article", "body"}:
        return convert_block_children(node, ctx)
    return convert_inline(node.children, ctx)


def html_to_markdown(html: str) -> str:
    parser = HtmlTreeBuilder()
    parser.feed(html)
    parser.close()
    content = convert_block_children(parser.root, {"blockquote": 0, "list_level": 0})
    content = content.strip()
    if not content.endswith('\n'):
        content += '\n'
    return content


def iter_asset_files() -> Iterable[Path]:
    for path in sorted(ASSETS_DIR.glob("*.md.*.js")):
        if path.name.endswith(".lean.js"):
            continue
        yield path


def export_docs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for asset_path in iter_asset_files():
        text = asset_path.read_text(encoding="utf-8")
        meta = extract_page_meta(text)
        html = extract_content_html(text)
        if not html:
            continue
        markdown = html_to_markdown(html)
        rel_path = meta.get("relativePath", asset_path.stem)
        target_path = OUTPUT_DIR / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(markdown, encoding="utf-8")
        print(f"Exported {rel_path} -> {target_path.relative_to(ROOT)}")


if __name__ == "__main__":
    export_docs()
