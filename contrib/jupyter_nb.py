#!/usr/bin/env python3
"""mdbook preprocessor: turn .ipynb chapters into markdown.

Notebooks listed in SUMMARY.md load as chapters whose content is the raw
ipynb JSON; this rewrites them to markdown using the outputs saved in the
notebook, without executing anything. Declared before the rendering
preprocessors so math, mermaid and dot in notebook cells still go through
katex/mermaid/graphviz.
"""
import json
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def fence(text, info=""):
    # A fence must be longer than any backtick run inside it.
    runs = re.findall(r"`+", text)
    ticks = "`" * max([len(r) + 1 for r in runs] + [3])
    return "%s%s\n%s\n%s" % (ticks, info, text.rstrip("\n"), ticks)


def output_markdown(output):
    kind = output["output_type"]
    if kind == "stream":
        return fence(ANSI.sub("", "".join(output["text"])))
    if kind == "error":
        return fence(ANSI.sub("", "\n".join(output["traceback"])))
    data = output.get("data", {})
    if "image/png" in data:
        b64 = "".join(data["image/png"].split())
        return '<img src="data:image/png;base64,%s">' % b64
    if "text/markdown" in data:
        return "".join(data["text/markdown"])
    if "text/plain" in data:
        # Last resort; html reprs (dataframes, colab widgets) carry
        # scripts and styles that do not survive outside a notebook.
        return fence(ANSI.sub("", "".join(data["text/plain"])))
    return None


def cell_markdown(cell, language):
    if cell["cell_type"] == "markdown":
        return ["".join(cell["source"])]
    if cell["cell_type"] != "code":
        return []
    source = "".join(cell["source"])
    if not source.strip():
        return []
    parts = [fence(source, language)]
    parts += filter(None, map(output_markdown, cell.get("outputs", [])))
    return parts


def notebook_markdown(content):
    notebook = json.loads(content)
    language = notebook.get("metadata", {}).get("kernelspec", {}).get(
        "language", "python"
    )
    return "\n\n".join(
        part for cell in notebook["cells"] for part in cell_markdown(cell, language)
    ) + "\n"


def walk(items):
    for item in items:
        chapter = item.get("Chapter")
        if not chapter:
            continue
        if (chapter.get("path") or "").endswith(".ipynb"):
            chapter["content"] = notebook_markdown(chapter["content"])
        walk(chapter["sub_items"])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)
    _context, book = json.load(sys.stdin)
    # mdbook 0.5 renamed the top level key from `sections` to `items`.
    walk(book.get("items", book.get("sections")))
    json.dump(book, sys.stdout)


if __name__ == "__main__":
    main()
