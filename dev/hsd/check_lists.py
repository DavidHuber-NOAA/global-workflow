#!/usr/bin/env python3
"""Sanity-check the HSD exclude lists against the tracked files of the repository.

For every tier of a system the script checks that

* each list entry matches at least one tracked file (no stale entries),
* no entry is repeated within or across the cumulative tier lists, and
* no file that is kept at that tier imports a Python module that is excluded
  (module-level imports only; imports inside functions are treated as lazy).

Usage: check_lists.py [SYSTEM]    (default: gcafs)
"""
import ast
import fnmatch
import os
import subprocess
import sys

HSD_DIR = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.abspath(os.path.join(HSD_DIR, '..', '..'))
TIERS = [('1', ['tier1']), ('1.5', ['tier1', 'tier1p5']), ('2', ['tier1', 'tier1p5', 'tier2'])]
# Directories that Python code adds to sys.path (module root -> repository directory)
PY_ROOTS = ['dev/workflow', 'ush/python', 'sorc/wxflow/src']


def read_list(system, name):
    path = os.path.join(HSD_DIR, f'{system}.{name}.list')
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]


def tracked_files():
    out = subprocess.check_output(['git', 'ls-files'], cwd=TOP, text=True)
    return [f for f in out.splitlines() if os.path.lexists(os.path.join(TOP, f))]


def matches(entry, path):
    if path == entry or path.startswith(entry.rstrip('/') + '/'):
        return True
    return '*' in entry and fnmatch.fnmatch(path, entry + ('*' if entry.endswith('/') else ''))


def module_to_file(module, files):
    parts = module.split('.')
    for root in PY_ROOTS:
        for cand in (f"{root}/{'/'.join(parts)}.py", f"{root}/{'/'.join(parts)}/__init__.py"):
            if cand in files:
                return cand
    return None


def module_imports(path):
    try:
        tree = ast.parse(open(os.path.join(TOP, path)).read())
    except (SyntaxError, UnicodeDecodeError):
        return []
    found = []

    def walk(body):
        for node in body:
            if isinstance(node, ast.Import):
                found.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.append(node.module)
                found.extend(f'{node.module}.{a.name}' for a in node.names)
            elif isinstance(node, (ast.Try, ast.If)):
                walk(node.body)
                walk(getattr(node, 'orelse', []))
                for handler in getattr(node, 'handlers', []):
                    walk(handler.body)
    walk(tree.body)
    return found


def main():
    system = sys.argv[1] if len(sys.argv) > 1 else 'gcafs'
    files = tracked_files()
    fileset = set(files)
    errors = 0
    seen = {}
    for tier, names in TIERS:
        entries = [(n, e) for n in names for e in read_list(system, n)]
        excluded = set()
        for n, e in entries:
            hit = [f for f in files if matches(e, f)]
            if not hit:
                print(f'ERROR tier {tier}: entry matches no tracked file: {e} ({n})')
                errors += 1
            excluded.update(hit)
        for n, e in entries:
            if seen.setdefault(e, n) != n and n == names[-1]:
                print(f'ERROR tier {tier}: entry {e} is in both {seen[e]} and {n}')
                errors += 1
        kept = [f for f in files if f not in excluded]
        for f in kept:
            if not f.endswith('.py'):
                continue
            for mod in module_imports(f):
                target = module_to_file(mod, fileset)
                if target and target in excluded:
                    print(f'ERROR tier {tier}: {f} imports excluded {target}')
                    errors += 1
        print(f'tier {tier}: {len(excluded)} files excluded, {len(kept)} kept')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
