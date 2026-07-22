#!/usr/bin/env python3
"""Build a Markdown summary of pycodestyle findings for a PR comment.

Repurposed from bash_analysis_summary.py for the Python code analysis
workflow. Reads pycodestyle's default output:

  <dir>/pycodestyle.txt   lines of "path:line:col: CODE message"

Writes the Markdown body to <out> and prints "1" to stdout if there were
findings, else "0".

The input is produced by an untrusted analysis run, so all values are
treated as text and never executed or interpolated into shell commands.
"""
import os
import re
import sys

MARKER = "<!-- python-code-analysis-summary -->"
MAX_ROWS = 100

# pycodestyle: "path:line:col: CODE message"
LINE_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>\S+)\s+(?P<msg>.*)$")


def parse_pycodestyle(path):
    rows = []
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        return rows
    with open(path, "r", errors="replace") as fh:
        for raw in fh:
            m = LINE_RE.match(raw.rstrip("\r\n"))
            if not m:
                continue  # skips verbose/statistics lines
            name = m.group("file")
            if name.startswith("./"):
                name = name[2:]
            rows.append({
                "file": name,
                "line": m.group("line"),
                "col": m.group("col"),
                "code": m.group("code"),
                "message": m.group("msg"),
            })
    return rows


def md_cell(text):
    # Neutralize characters that would break a Markdown table cell.
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    out = sys.argv[2] if len(sys.argv) > 2 else "comment.md"
    run_url = os.environ.get("RUN_URL", "")

    rows = parse_pycodestyle(os.path.join(d, "pycodestyle.txt"))
    has_findings = bool(rows)

    lines = [MARKER, "## Python code analysis (pycodestyle)", ""]

    if not has_findings:
        lines.append(":white_check_mark: **pycodestyle** found no issues.")
    else:
        lines.append("**pycodestyle** reported {} finding(s).".format(len(rows)))
        lines.append("")
        lines.append("| File | Line:Col | Code | Message |")
        lines.append("| --- | --- | --- | --- |")
        for r in rows[:MAX_ROWS]:
            lines.append("| `{}` | {}:{} | {} | {} |".format(
                md_cell(r["file"]), md_cell(r["line"]), md_cell(r["col"]),
                md_cell(r["code"]), md_cell(r["message"]),
            ))
        if len(rows) > MAX_ROWS:
            lines.append("")
            lines.append("_...and {} more. See the full run for details._".format(len(rows) - MAX_ROWS))

    if run_url:
        lines.append("")
        lines.append("[View the analysis run]({})".format(run_url))

    body = "\n".join(lines) + "\n"
    if len(body) > 65000:  # GitHub comment hard limit is 65536 chars
        body = body[:64000] + "\n_...comment truncated._\n"
    with open(out, "w") as fh:
        fh.write(body)
    print("1" if has_findings else "0")


if __name__ == "__main__":
    main()
