# duBE — du But Easier

[![CI](https://github.com/serber1990/duBE/actions/workflows/ci.yml/badge.svg)](https://github.com/serber1990/duBE/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/dube.svg)](https://badge.fury.io/py/dube)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/serber1990/duBE?style=social)](https://github.com/serber1990/duBE/stargazers)

**Find what is eating your disk in one command.** duBE is a friendlier `du`: cumulative sizes,
percentage bars, a tree view, top-N, human-friendly filters and JSON output — with the same totals as `du`.

<p align="center">
  <img src="https://raw.githubusercontent.com/serber1990/duBE/main/docs/demo.gif" alt="dube demo: largest directories with percentage bars and tree view" width="820">
</p>

---

## ✨ Features

- 📊 **Percentage bars** — see at a glance which directory dominates
- 🏆 **Top-N** — `dube / --top 10` lists the biggest offenders, nothing else
- 🌲 **Tree view** — directory hierarchy with cumulative sizes per branch
- 🎯 **Human filters** — `--threshold 100M`, `--exclude node_modules`, `--exclude '*.iso'`, `-z`
- ✅ **Accurate like `du`** — cumulative sizes, hard links counted once, symlink loops detected
- 🧭 **Depth control** — `--max-depth` limits what is *shown*, never what is *counted*
- 🤖 **JSON output** — sizes in bytes for scripts and monitoring
- 🔇 **Script-friendly** — plain output when piped, warnings on stderr, `NO_COLOR` support

---

## 📥 Installation

```bash
pip install dube
```

Or from source:

```bash
git clone https://github.com/serber1990/duBE.git
cd duBE
pip install -e .
```

---

## 🎨 Examples

### Biggest entries

```bash
dube project --top 5
```

```
  ╔══════════════════════════════════════════════╗
  ║  duBE  ·  /home/user/project                 ║
  ╚══════════════════════════════════════════════╝

      1.3 GB  ████████░░░░  66.0%  project/logs/
    479.0 MB  ███░░░░░░░░░  24.3%  project/node_modules/
    312.0 MB  ██░░░░░░░░░░  15.8%  project/node_modules/typescript/
    188.0 MB  █░░░░░░░░░░░   9.5%  project/.git/
    188.0 MB  █░░░░░░░░░░░   9.5%  project/.git/objects/
  ────────────────────────────────────────────────────────────────────────
      1.9 GB  Total  project
```

### Tree view

```bash
dube project --tree --max-depth 2
```

```
  ╔══════════════════════════════════════════════╗
  ║  duBE  ·  /home/user/project  ·  tree        ║
  ╚══════════════════════════════════════════════╝

      1.9 GB  project
    188.0 MB  ├── .git/
    188.0 MB  │   └── objects/
      2.3 MB  ├── dist/
      1.3 GB  ├── logs/
    479.0 MB  ├── node_modules/
     21.0 MB  │   ├── react/
    312.0 MB  │   ├── typescript/
    146.0 MB  │   └── webpack/
    730.1 KB  └── src/
    640.1 KB      └── components/
  ────────────────────────────────────────────────────────────────────────
      1.9 GB  Total  project
```

### More

```bash
dube /var/log --sort desc --time          # largest first, with modification dates
dube /home -a --threshold 1G              # every file or directory of 1 GB or more
dube / -x --top 20                        # stay on the root filesystem
dube . --exclude node_modules --exclude .git
dube /srv --json | jq '.entries[] | select(.size > 1e9) | .path'
```

---

## 🛠 Options

| Option | Description |
|--------|-------------|
| `directory` | Directory to analyse (default: `.`) |
| `-n`, `--top N` | Show only the N largest entries |
| `-t`, `--tree` | Show a tree with cumulative sizes |
| `-d`, `--max-depth N` | Only show entries up to N levels deep (totals still include everything) |
| `-a`, `--all` | Include individual files |
| `--sort asc\|desc` | Sort by size (default: by path) |
| `--threshold SIZE` | Only entries ≥ SIZE (`100M`, `1.5G`); negative = ≤ \|SIZE\| |
| `-z`, `--exclude-zero` | Hide zero-size entries |
| `--exclude PATTERN` | Skip a path (`/var/cache`) or name pattern (`node_modules`, `*.iso`). Repeatable |
| `--no-default-excludes` | Also scan `/proc`, `/sys`, `/dev`, `/run`, `/mnt`, `/media`, `/lost+found` |
| `--apparent-size` | Use file sizes instead of disk blocks used |
| `-L`, `--follow-symlinks` | Follow symbolic links (loops are detected) |
| `-x`, `--same-filesystem` | Do not cross into other mounted filesystems |
| `--time` / `--time-style FMT` | Show modification time (`iso`, `long-iso`, `full-iso`, `+%d/%m/%Y`) |
| `--json` | JSON output, sizes in bytes |
| `--block-size BYTES` | Unit for plain `--threshold` numbers (default 1024) |
| `-v`, `--version` | Show version |

Directories that cannot be read are counted and reported on stderr — run with `sudo` for complete totals.

---

## 🧪 Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

See [CHANGELOG.md](CHANGELOG.md) for release notes.

---

## 📝 License

MIT — see [LICENSE](LICENSE).

---

## 💬 Feedback

Open an issue or reach out via GitHub.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-@serber1990-181717?style=flat-square&logo=github)](https://github.com/serber1990)
