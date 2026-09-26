# Changelog

## 2.1.0

### Fixed
- Directory sizes were not cumulative: each directory only counted its own files, so parents looked
  almost empty. Sizes now include every descendant, exactly like `du` (totals match `du -s`).
- `--max-depth` skipped the contents of deeper directories, so totals shrank (`--max-depth 1` could report 0 B).
  It now only limits what is shown.
- `--threshold` removed small files from the totals instead of filtering the displayed entries.
- `--tree` printed an empty tree when the directory had a trailing slash (`dube dir/ --tree`).
- Hard-linked files were counted several times.
- `--follow-symlinks` could loop forever on symlink cycles.
- Default excludes (`/proc`, `/sys`…) were ignored when scanning with a relative path such as `.` from `/`.
- `--same-filesystem` could crash on unreadable directories; unreadable directories are now reported.
- Small files lost precision (sizes were truncated to whole blocks per file).
- The tree view was O(n²) on large directories.

### Added
- Percentage bars in the flat view.
- `--top N`, `--json`, `--no-default-excludes`, short flags `-t`, `-d`, `-n`, `-L`, `-x`.
- Human-friendly thresholds: `--threshold 100M`, `1.5G`, `-1G`.
- `--exclude` accepts name patterns (`node_modules`, `*.iso`) as well as paths.
- `--sort` and `-a` also apply to the tree view.
- Plain output when piped or when `NO_COLOR` is set.
- Test suite and GitHub Actions CI.

### Changed
- License metadata unified (MIT). Requires Python 3.9+.

## 2.0.0

- Tree view, visual redesign, pip-installable.
