#!/usr/bin/env python3
import argparse
import os
import re
import signal
import sys
from datetime import datetime
from shellcolorize import Color

VERSION = "2.0.0"

EXCLUDE_DIRS = {'/proc', '/sys', '/dev', '/run', '/mnt', '/media', '/lost+found'}

# ── ANSI helpers ──────────────────────────────────────────────────────────────

_ANSI = re.compile(r'\033\[[0-9;]*m')

def _vlen(s: str) -> int:
    return len(_ANSI.sub('', s))

def _rpad(s: str, width: int) -> str:
    return ' ' * max(0, width - _vlen(s)) + s

# ── Display primitives ────────────────────────────────────────────────────────

def _header(*parts: str) -> None:
    inner = '  ' + '  ·  '.join(p for p in parts if p)
    w = max(46, len(inner) + 4)
    border = '═' * w
    print()
    print(f"  {Color.CYAN}╔{border}╗{Color.RESET}")
    print(f"  {Color.CYAN}║{Color.RESET}{Color.BOLD}{inner}{Color.RESET}"
          + ' ' * max(0, w - len(inner))
          + f"  {Color.CYAN}║{Color.RESET}")
    print(f"  {Color.CYAN}╚{border}╝{Color.RESET}")
    print()

def _separator(width: int = 52) -> None:
    print(f"  {Color.DIM}{'─' * width}{Color.RESET}")

# ── Size formatting ───────────────────────────────────────────────────────────

def format_size(size: int, block_size: int = 1024) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    value = size * block_size
    for unit in units[:-1]:
        if value < 1024:
            return f"{value:7.2f} {unit}"
        value /= 1024
    return f"{value:7.2f} {units[-1]}"

def _fmt_time(path: str, time_style: str = 'iso') -> str:
    t = datetime.fromtimestamp(os.path.getmtime(path))
    if time_style.startswith('+'):
        return t.strftime(time_style[1:])
    fmts = {'full-iso': '%Y-%m-%d %H:%M:%S', 'long-iso': '%Y-%m-%d %H:%M', 'iso': '%Y-%m-%d'}
    return t.strftime(fmts.get(time_style, time_style))

# ── Core scanner ──────────────────────────────────────────────────────────────

def scan(start: str, max_depth=None, follow_symlinks=False, same_filesystem=False,
         block_size=1024, threshold=None, show_all=False, apparent_size=False,
         extra_excludes=None) -> tuple:
    """
    Returns (total_size, sizes_dict) where sizes_dict maps each path
    to the sum of its DIRECT files only (used for flat view and tree rollup).
    """
    excludes = EXCLUDE_DIRS | set(extra_excludes or [])
    base_dev = os.stat(start).st_dev if same_filesystem else None
    depth0   = start.rstrip(os.sep).count(os.sep)
    sizes    = {}
    total    = 0

    for dirpath, dirnames, filenames in os.walk(start, followlinks=follow_symlinks):
        cur_depth = dirpath.count(os.sep) - depth0

        if max_depth is not None and cur_depth >= max_depth:
            dirnames[:] = []
            continue

        dirnames[:] = [
            d for d in dirnames
            if os.path.join(dirpath, d) not in excludes
            and (base_dev is None or os.stat(os.path.join(dirpath, d)).st_dev == base_dev)
        ]

        dir_size = 0
        for fname in filenames:
            fp = os.path.join(dirpath, fname)
            try:
                if os.path.islink(fp) and not follow_symlinks:
                    continue
                fsize = (os.path.getsize(fp) if apparent_size
                         else (os.stat(fp).st_blocks * 512)) // block_size
                if threshold is None or (threshold > 0 and fsize >= threshold) or \
                   (threshold < 0 and fsize <= abs(threshold)):
                    dir_size += fsize
                    if show_all:
                        sizes[fp] = fsize
            except OSError:
                continue

        sizes[dirpath] = dir_size
        total += dir_size

    return total, sizes


def _cumulative(sizes: dict) -> dict:
    """Roll up sizes so every directory contains total size of all descendants."""
    cum = dict(sizes)
    for path in sorted(cum.keys(), key=lambda p: -p.count(os.sep)):
        parent = os.path.dirname(path)
        if parent != path and parent in cum:
            cum[parent] += cum[path]
    return cum

# ── Output: flat list ─────────────────────────────────────────────────────────

def print_flat(directory: str, total: int, sizes: dict, block_size: int,
               show_time: bool, time_style: str, sort_order, exclude_zero: bool) -> None:
    _header('duBE', os.path.abspath(directory))

    entries = {p: s for p, s in sizes.items() if not (exclude_zero and s == 0)}
    reverse = sort_order == 'desc'
    sorted_entries = sorted(entries.items(), key=lambda x: x[1], reverse=reverse)

    # Right-align size column
    size_w = max((_vlen(format_size(s, block_size)) for _, s in sorted_entries), default=9)

    for path, size in sorted_entries:
        sz = _rpad(f"{Color.YELLOW}{format_size(size, block_size)}{Color.RESET}", size_w + 9)
        line = f"  {sz}   {path}"
        if show_time:
            try:
                ts = _fmt_time(path, time_style)
                line += f"  {Color.DIM}{ts}{Color.RESET}"
            except OSError:
                pass
        print(line)

    _separator(size_w + 52)
    total_str = f"{Color.YELLOW}{Color.BOLD}{format_size(total, block_size)}{Color.RESET}"
    print(f"  {_rpad(total_str, size_w + 9)}   {Color.BOLD}Total{Color.RESET}")
    print()

# ── Output: tree ──────────────────────────────────────────────────────────────

def print_tree(directory: str, sizes: dict, block_size: int) -> None:
    _header('duBE', os.path.abspath(directory), 'tree')

    cum = _cumulative(sizes)
    dirs_only = {p: s for p, s in cum.items() if os.path.isdir(p)}

    def _render(path: str, prefix: str = '', is_last: bool = True, root: bool = False) -> None:
        size   = dirs_only.get(path, 0)
        name   = os.path.basename(path) or path
        sz_str = f"{Color.YELLOW}{format_size(size, block_size)}{Color.RESET}"

        if root:
            print(f"  {Color.CYAN}{Color.BOLD}{path}{Color.RESET}   {sz_str}")
            child_prefix = ''
        else:
            conn = f"{Color.DIM}{'└── ' if is_last else '├── '}{Color.RESET}"
            print(f"  {Color.DIM}{prefix}{Color.RESET}{conn}{sz_str}   {name}")
            child_prefix = prefix + ('    ' if is_last else '│   ')

        children = sorted(
            [p for p in dirs_only if os.path.dirname(p) == path and p != path]
        )
        for i, child in enumerate(children):
            _render(child, child_prefix, i == len(children) - 1, root=False)

    _render(directory, root=True)
    print()

# ── CLI ───────────────────────────────────────────────────────────────────────

def _handle_sigint(signum, frame):
    print(f"\n  {Color.RED}✖  Interrupted{Color.RESET}\n")
    sys.exit(1)


def main() -> None:
    signal.signal(signal.SIGINT, _handle_sigint)

    parser = argparse.ArgumentParser(
        prog='dube',
        description='duBE — du But Easier: enhanced disk usage analyser',
    )
    parser.add_argument('directory', nargs='?', default='.',
                        help='Directory to analyse (default: current directory)')
    parser.add_argument('--max-depth',      type=int,
                        help='Maximum directory depth to recurse')
    parser.add_argument('-a', '--all',      action='store_true',
                        help='Include individual files in output')
    parser.add_argument('--tree',           action='store_true',
                        help='Display results as a directory tree')
    parser.add_argument('--block-size',     type=int, default=1024,
                        help='Block size in bytes (default: 1024)')
    parser.add_argument('--apparent-size',  action='store_true',
                        help='Show apparent size instead of disk usage')
    parser.add_argument('--follow-symlinks',action='store_true',
                        help='Follow symbolic links')
    parser.add_argument('--same-filesystem',action='store_true',
                        help='Restrict to a single filesystem')
    parser.add_argument('--exclude',        action='append', metavar='DIR',
                        help='Exclude a directory (repeatable)')
    parser.add_argument('-z', '--exclude-zero', action='store_true',
                        help='Hide entries with zero size')
    parser.add_argument('--threshold',      type=int, metavar='N',
                        help='Only show entries ≥ N blocks (negative = ≤ |N|)')
    parser.add_argument('--time',           action='store_true',
                        help='Show last modification time alongside each entry')
    parser.add_argument('--time-style',     default='iso', metavar='FMT',
                        help='Date format for --time: iso, long-iso, full-iso, or strftime string')
    parser.add_argument('--sort',           choices=['asc', 'desc'],
                        help='Sort output by size')
    parser.add_argument('-v', '--version',  action='version', version=f'dube {VERSION}')
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"\n  {Color.RED}✖  Not a directory: {directory}{Color.RESET}\n")
        sys.exit(1)

    total, sizes = scan(
        directory,
        max_depth=args.max_depth,
        follow_symlinks=args.follow_symlinks,
        same_filesystem=args.same_filesystem,
        block_size=args.block_size,
        threshold=args.threshold,
        show_all=args.all,
        apparent_size=args.apparent_size,
        extra_excludes=args.exclude,
    )

    if args.tree:
        print_tree(directory, sizes, args.block_size)
    else:
        print_flat(
            directory, total, sizes, args.block_size,
            show_time=args.time,
            time_style=args.time_style,
            sort_order=args.sort,
            exclude_zero=args.exclude_zero,
        )


if __name__ == '__main__':
    main()
