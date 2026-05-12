# duBE — du But Easier

[![PyPI version](https://badge.fury.io/py/dube.svg)](https://badge.fury.io/py/dube)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/serber1990/duBE?style=social)](https://github.com/serber1990/duBE/stargazers)

Enhanced disk usage analyser — a cleaner, more powerful `du` replacement with tree view, sorting, filters and readable output.

---

## ✨ Features

- 🌲 **Tree view** (`--tree`) — visual directory hierarchy with cumulative sizes per branch
- 📊 **Sort by size** — `--sort asc` / `--sort desc`
- 🕐 **Modification time** — `--time` shows last-modified date alongside each entry
- 🚫 **Smart exclusions** — skip directories, zero-size entries, or entries below a threshold
- 📏 **Apparent size** — actual file content vs. disk blocks
- 🌈 **Clean, color-coded output** — readable at a glance without visual noise

---

## 📥 Installation

```bash
pip install dube
```

Or clone locally:

```bash
git clone https://github.com/serber1990/duBE.git
cd duBE
pip install -e .
```

---

## 🛠 Usage

```bash
dube [directory] [options]
```

| Option | Description |
|--------|-------------|
| `directory` | Directory to analyse (default: `.`) |
| `--tree` | Show results as a directory tree with cumulative sizes |
| `--max-depth N` | Limit recursion depth |
| `-a`, `--all` | Include individual files |
| `--sort asc\|desc` | Sort by size |
| `--time` | Show last modification time per entry |
| `--time-style FMT` | Date format: `iso`, `long-iso`, `full-iso`, or strftime string |
| `--apparent-size` | Show apparent size instead of disk blocks |
| `--follow-symlinks` | Follow symbolic links |
| `--same-filesystem` | Restrict to one filesystem |
| `--exclude DIR` | Exclude a directory (repeatable) |
| `-z`, `--exclude-zero` | Hide zero-size entries |
| `--threshold N` | Show entries ≥ N blocks (negative = ≤ \|N\|) |
| `-v`, `--version` | Show version |

---

## 🎨 Examples

```bash
# Analyse current directory
dube .

# Tree view, 2 levels deep
dube /home/user --tree --max-depth 2

# Largest directories first, show modification dates
dube /var/log --sort desc --time

# Include individual files, skip empty entries
dube /etc -a -z

# Only show entries bigger than 100 blocks
dube /home --threshold 100
```

---

## 📝 License

MIT — see [LICENSE](LICENSE).

---

## 💬 Feedback

Open an issue or reach out via GitHub.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-@serber1990-181717?style=flat-square&logo=github)](https://github.com/serber1990)
