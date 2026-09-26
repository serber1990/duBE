#!/usr/bin/env python3
"""
duBE — du But Easier.
Disk usage analyser with cumulative sizes, percentage bars, tree view,
top-N, filters and JSON output.
"""
import argparse
import fnmatch
import json
import os
import re
import stat
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from shellcolorize import Color

VERSION = "2.1.0"

# Virtual/removable filesystems skipped unless --no-default-excludes is given.
DEFAULT_EXCLUDES = ('/proc', '/sys', '/dev', '/run', '/mnt', '/media', '/lost+found')

# ── Sizes ─────────────────────────────────────────────────────────────────────

_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


def human_size(n: int) -> str:
    """Fixed-width human readable size (IEC multiples of 1024): '  1.5 GB'."""
    value = float(n)
    for unit in _UNITS:
        if abs(value) < 1024 or unit == _UNITS[-1]:
            if unit == 'B':
                return f"{int(value):7d} B "
            return f"{value:7.1f} {unit}"
        value /= 1024
    raise AssertionError('unreachable')


_SIZE_RE = re.compile(r'^(-?\d+(?:\.\d+)?)\s*([KMGTP]?)(?:I?B)?$', re.I)


def parse_size(text: str, block_size: int = 1024) -> int:
    """
    Parse a threshold: '100M', '1.5G', '-1G' or a plain number of blocks
    (plain numbers are multiplied by block_size, like du). Returns bytes.
    """
    m = _SIZE_RE.match(text.strip())
    if not m:
        raise ValueError(f"invalid size: '{text}'")
    number, suffix = float(m.group(1)), m.group(2).upper()
    if not suffix:
        return int(number * block_size)
    return int(number * 1024 ** ('KMGTP'.index(suffix) + 1))

# ── Scanner ───────────────────────────────────────────────────────────────────

@dataclass
class ScanResult:
    root: str
    dirs: Dict[str, int]                                  # cumulative bytes per directory
    files: Dict[str, int] = field(default_factory=dict)   # bytes per file (with include_files)
    errors: List[str] = field(default_factory=list)       # directories that could not be read

    @property
    def total(self) -> int:
        return self.dirs.get(self.root, 0)

    def depth(self, path: str) -> int:
        rel = os.path.relpath(path, self.root)
        return 0 if rel == '.' else rel.count(os.sep) + 1


def _entry_size(st: os.stat_result, apparent_size: bool) -> int:
    if apparent_size or not hasattr(st, 'st_blocks'):
        return st.st_size
    return st.st_blocks * 512


def scan(root: str, *, apparent_size: bool = False, follow_symlinks: bool = False,
         same_filesystem: bool = False, excludes: Sequence[str] = (),
         include_files: bool = False) -> ScanResult:
    """
    Walk `root` and compute the cumulative size of every directory, like `du`.

    - Hard-linked files are counted once.
    - Symlinks are skipped unless follow_symlinks; directory loops are detected.
    - `excludes` entries containing '/' are paths, others are fnmatch name patterns.
    """
    root = os.path.normpath(root)
    abs_excludes = {os.path.abspath(p) for p in excludes if os.sep in p}
    name_patterns = [p for p in excludes if os.sep not in p]

    def excluded(entry: os.DirEntry) -> bool:
        if any(fnmatch.fnmatch(entry.name, p) for p in name_patterns):
            return True
        return bool(abs_excludes) and os.path.abspath(entry.path) in abs_excludes

    root_st = os.stat(root)
    direct: Dict[str, int] = {root: _entry_size(root_st, apparent_size)}
    result = ScanResult(root=root, dirs={})
    seen_files = set()
    seen_dirs = {(root_st.st_dev, root_st.st_ino)}
    stack = [root]

    while stack:
        path = stack.pop()
        try:
            with os.scandir(path) as it:
                entries = list(it)
        except OSError:
            result.errors.append(path)
            continue

        for entry in entries:
            try:
                if entry.is_symlink() and not follow_symlinks:
                    continue
                st = entry.stat(follow_symlinks=follow_symlinks)
            except OSError:
                continue   # vanished or broken symlink
            if excluded(entry):
                continue

            if stat.S_ISDIR(st.st_mode):
                if same_filesystem and st.st_dev != root_st.st_dev:
                    continue
                key = (st.st_dev, st.st_ino)
                if key in seen_dirs:
                    continue
                seen_dirs.add(key)
                direct[entry.path] = _entry_size(st, apparent_size)
                stack.append(entry.path)
            else:
                if st.st_nlink > 1:
                    key = (st.st_dev, st.st_ino)
                    if key in seen_files:
                        continue
                    seen_files.add(key)
                size = _entry_size(st, apparent_size)
                direct[path] += size
                if include_files:
                    result.files[entry.path] = size

    # Roll sizes up: deepest directories first, each one added to its parent.
    cumulative = dict(direct)
    for path in sorted(direct, key=lambda p: p.count(os.sep), reverse=True):
        if path != root:
            cumulative[os.path.dirname(path)] += cumulative[path]
    result.dirs = cumulative
    return result

# ── Selection ─────────────────────────────────────────────────────────────────

@dataclass
class Entry:
    path: str
    size: int
    is_dir: bool
    depth: int


def select_entries(res: ScanResult, *, max_depth: Optional[int] = None,
                   threshold: Optional[int] = None, exclude_zero: bool = False,
                   sort: Optional[str] = None, top: Optional[int] = None) -> List[Entry]:
    """Entries to display (root excluded) after depth/size filters and sorting."""
    items = [Entry(p, s, True, res.depth(p)) for p, s in res.dirs.items() if p != res.root]
    items += [Entry(p, s, False, res.depth(p)) for p, s in res.files.items()]

    def keep(e: Entry) -> bool:
        if max_depth is not None and e.depth > max_depth:
            return False
        if exclude_zero and e.size == 0:
            return False
        if threshold is not None:
            return e.size >= threshold if threshold >= 0 else e.size <= -threshold
        return True

    items = [e for e in items if keep(e)]
    if top is not None:
        sort = 'desc'
    if sort:
        items.sort(key=lambda e: (e.size, e.path), reverse=(sort == 'desc'))
    else:
        items.sort(key=lambda e: e.path)
    return items[:top] if top is not None else items

# ── Output helpers ────────────────────────────────────────────────────────────

def _header(*parts: str) -> None:
    inner = '  ' + '  ·  '.join(p for p in parts if p)
    w = max(46, len(inner) + 4)
    print()
    print(f"  {Color.CYAN}╔{'═' * w}╗{Color.RESET}")
    print(f"  {Color.CYAN}║{Color.RESET}{Color.BOLD}{inner}{Color.RESET}"
          + ' ' * (w - len(inner)) + f"{Color.CYAN}║{Color.RESET}")
    print(f"  {Color.CYAN}╚{'═' * w}╝{Color.RESET}")
    print()


def _bar(size: int, total: int, width: int = 12) -> str:
    frac = size / total if total else 0.0
    filled = min(width, round(frac * width))
    return (f"{Color.CYAN}{'█' * filled}{Color.DIM}{'░' * (width - filled)}{Color.RESET}"
            f" {frac * 100:5.1f}%")


def _fmt_time(path: str, time_style: str = 'iso') -> str:
    t = datetime.fromtimestamp(os.lstat(path).st_mtime)
    if time_style.startswith('+'):
        return t.strftime(time_style[1:])
    fmts = {'full-iso': '%Y-%m-%d %H:%M:%S', 'long-iso': '%Y-%m-%d %H:%M', 'iso': '%Y-%m-%d'}
    return t.strftime(fmts.get(time_style, time_style))


def _time_suffix(path: str, show_time: bool, time_style: str) -> str:
    if not show_time:
        return ''
    try:
        return f"  {Color.DIM}{_fmt_time(path, time_style)}{Color.RESET}"
    except OSError:
        return ''


def _footer(res: ScanResult, width: int) -> None:
    print(f"  {Color.DIM}{'─' * width}{Color.RESET}")
    print(f"  {Color.YELLOW}{Color.BOLD}{human_size(res.total)}{Color.RESET}"
          f"  {Color.BOLD}Total{Color.RESET}  {Color.DIM}{res.root}{Color.RESET}")
    if res.errors:
        print(f"\n  {Color.YELLOW}⚠  {len(res.errors)} director"
              f"{'y' if len(res.errors) == 1 else 'ies'} could not be read "
              f"(permission denied?) — run with sudo for a complete total{Color.RESET}",
              file=sys.stderr)
    print()

# ── Output: flat list ─────────────────────────────────────────────────────────

def print_flat(res: ScanResult, entries: List[Entry], show_time: bool = False,
               time_style: str = 'iso') -> None:
    _header('duBE', os.path.abspath(res.root))
    for e in entries:
        name = f"{Color.BOLD}{e.path}{os.sep}{Color.RESET}" if e.is_dir else e.path
        print(f"  {Color.YELLOW}{human_size(e.size)}{Color.RESET}  {_bar(e.size, res.total)}  "
              f"{name}{_time_suffix(e.path, show_time, time_style)}")
    _footer(res, 72)

# ── Output: tree ──────────────────────────────────────────────────────────────

def print_tree(res: ScanResult, entries: List[Entry], sort: Optional[str] = None,
               show_time: bool = False, time_style: str = 'iso') -> None:
    _header('duBE', os.path.abspath(res.root), 'tree')

    visible = {e.path: e for e in entries}
    children: Dict[str, List[Entry]] = {}
    for e in entries:
        parent = os.path.dirname(e.path)
        # Only attach to a visible parent (or the root) so hidden subtrees stay hidden.
        if parent == res.root or parent in visible:
            children.setdefault(parent, []).append(e)
    for kids in children.values():
        if sort:
            kids.sort(key=lambda e: (e.size, e.path), reverse=(sort == 'desc'))
        else:
            kids.sort(key=lambda e: (not e.is_dir, e.path))

    print(f"  {Color.YELLOW}{human_size(res.total)}{Color.RESET}  "
          f"{Color.CYAN}{Color.BOLD}{res.root}{Color.RESET}")

    # Iterative depth-first render (no recursion limit on deep trees).
    stack = [(kid, '', i == len(children.get(res.root, [])) - 1)
             for i, kid in reversed(list(enumerate(children.get(res.root, []))))]
    while stack:
        e, prefix, is_last = stack.pop()
        conn = '└── ' if is_last else '├── '
        name = os.path.basename(e.path)
        label = f"{Color.BOLD}{name}{os.sep}{Color.RESET}" if e.is_dir else name
        print(f"  {Color.YELLOW}{human_size(e.size)}{Color.RESET}  {Color.DIM}{prefix}{conn}{Color.RESET}"
              f"{label}{_time_suffix(e.path, show_time, time_style)}")
        kids = children.get(e.path, [])
        child_prefix = prefix + ('    ' if is_last else '│   ')
        for i in range(len(kids) - 1, -1, -1):
            stack.append((kids[i], child_prefix, i == len(kids) - 1))

    _footer(res, 72)

# ── Output: JSON ──────────────────────────────────────────────────────────────

def to_json(res: ScanResult, entries: List[Entry], apparent_size: bool) -> str:
    return json.dumps({
        'root': res.root,
        'total': res.total,
        'unit': 'bytes',
        'apparent_size': apparent_size,
        'entries': [{'path': e.path, 'size': e.size, 'type': 'dir' if e.is_dir else 'file',
                     'depth': e.depth} for e in entries],
        'errors': res.errors,
    }, indent=2)

# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='dube',
        description='duBE — du But Easier: disk usage analyser with bars, tree view and filters',
        epilog='examples:  dube /var --top 10   ·   dube ~ --tree --max-depth 2   ·   dube . -a --threshold 100M',
    )
    p.add_argument('directory', nargs='?', default='.',
                   help='Directory to analyse (default: current directory)')
    p.add_argument('-d', '--max-depth', type=int, metavar='N',
                   help='Only show entries up to N levels deep (sizes still include everything)')
    p.add_argument('-a', '--all', action='store_true', help='Include individual files')
    p.add_argument('-t', '--tree', action='store_true', help='Display results as a tree')
    p.add_argument('-n', '--top', type=int, metavar='N', help='Show only the N largest entries')
    p.add_argument('--sort', choices=['asc', 'desc'], help='Sort by size (default: by path)')
    p.add_argument('--threshold', metavar='SIZE',
                   help='Only show entries ≥ SIZE (e.g. 100M, 1G); negative = ≤ |SIZE|. '
                        'Plain numbers are blocks of --block-size')
    p.add_argument('-z', '--exclude-zero', action='store_true', help='Hide zero-size entries')
    p.add_argument('--exclude', action='append', default=[], metavar='PATTERN',
                   help='Skip a path (/var/cache) or a name pattern (node_modules, *.iso). Repeatable')
    p.add_argument('--no-default-excludes', action='store_true',
                   help=f"Also scan {', '.join(DEFAULT_EXCLUDES)}")
    p.add_argument('--apparent-size', action='store_true',
                   help='Use file sizes instead of disk blocks used')
    p.add_argument('-L', '--follow-symlinks', action='store_true', help='Follow symbolic links')
    p.add_argument('-x', '--same-filesystem', action='store_true',
                   help='Stay on the filesystem of DIRECTORY')
    p.add_argument('--block-size', type=int, default=1024, metavar='BYTES',
                   help='Unit for plain --threshold numbers (default: 1024)')
    p.add_argument('--time', action='store_true', help='Show last modification time')
    p.add_argument('--time-style', default='iso', metavar='FMT',
                   help='iso, long-iso, full-iso or +strftime format')
    p.add_argument('--json', action='store_true', help='Machine-readable JSON output (sizes in bytes)')
    p.add_argument('-v', '--version', action='version', version=f'dube {VERSION}')
    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    Color.auto()

    def fail(msg: str) -> None:
        print(f"\n  {Color.RED}✖  {msg}{Color.RESET}\n", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.directory):
        fail(f"Not a directory: {args.directory}")
    if args.top is not None and args.top < 1:
        fail('--top must be a positive integer')
    if args.top is not None and args.tree:
        fail('--top cannot be combined with --tree (use --max-depth and --threshold instead)')
    if args.max_depth is not None and args.max_depth < 0:
        fail('--max-depth must be 0 or greater')
    threshold = None
    if args.threshold is not None:
        try:
            threshold = parse_size(args.threshold, args.block_size)
        except ValueError as e:
            fail(str(e))

    excludes = list(args.exclude)
    if not args.no_default_excludes:
        excludes += DEFAULT_EXCLUDES

    try:
        res = scan(args.directory, apparent_size=args.apparent_size,
                   follow_symlinks=args.follow_symlinks, same_filesystem=args.same_filesystem,
                   excludes=excludes, include_files=args.all)
        entries = select_entries(res, max_depth=args.max_depth, threshold=threshold,
                                 exclude_zero=args.exclude_zero, sort=args.sort, top=args.top)
    except KeyboardInterrupt:
        print(f"\n  {Color.RED}✖  Interrupted{Color.RESET}\n", file=sys.stderr)
        sys.exit(130)

    if args.json:
        print(to_json(res, entries, args.apparent_size))
    elif args.tree:
        print_tree(res, entries, args.sort, args.time, args.time_style)
    else:
        print_flat(res, entries, args.time, args.time_style)


def run() -> None:
    """Console entry point: like main(), but quiet when the output pipe is closed early (| head)."""
    try:
        main()
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(141)


if __name__ == '__main__':
    run()
