
# duBE (du But Easier)

**duBE** is a Python command-line tool that provides an enhanced, user-friendly alternative to the `du` command, but easier. It offers additional options such as directory exclusion, depth limits, apparent size, tree format analysis, and more. Ideal for those seeking a flexible and detailed way to analyze disk usage on their systems.

---

## ✨ Features

- 🔢 **Disk Usage Analysis**: Provides the size of each file or folder within a directory.
- 🎛 **Advanced Options**: Allows limiting search depth, excluding specific directories, showing modification times, and more just like du.
- 🌲 **Tree Format**: Displays results in a tree structure for easy visualization and colorized.
- 📏 **Apparent Size**: Option to show apparent size instead of actual disk usage.

---

## 📥 Installation

1. Clone this repository to your local machine:

   ```bash
   git clone https://github.com/serber1990/duBE.git
   cd duBE
   ```

2. Ensure Python and the `shellcolorize` library are installed.

   ```bash
   pip install shellcolorize
   ```

---

## 🛠 Usage

To run the script and analyze disk usage of a directory, use the following command:

```bash
python3 duBE.py [options]
```

Basic usage example:

```bash
python3 duBE.py /path/to/directory
```

---

## 🔧 Available Options

Here is a list of options you can use to customize the analysis:

- `directory`: Directory to analyze (default: current directory).
- `--max-depth <N>`: Maximum depth to search in subdirectories.
- `-a`, `--all`: Include individual files in the output.
- `--block-size <N>`: Block size for disk usage (default: 1024 bytes).
- `--apparent-size`: Show apparent size instead of actual disk usage.
- `--follow-symlinks`: Follow symbolic links.
- `--exclude <DIR>`: Exclude specific directories or patterns.
- `--same-filesystem`: Limit the analysis to a single filesystem.
- `-z`, `--exclude-zero`: Exclude files and directories with 0.00 B size.
- `--threshold <N>`: Exclude entries smaller/larger than threshold (positive/negative value).
- `--time`: Show last modification time of each file/folder.
- `--time-style <FORMAT>`: Date format for `--time` (default: iso).
- `--sort <asc|desc>`: Sort by size in ascending or descending order.

---

## 🎨 Usage Examples

### Basic Analysis of the Current Directory

```bash
python3 duBE.py .
```

### Analysis with Depth Limit

```bash
python3 duBE.py /home/user --max-depth 2
```

### Exclude Specific Directories or Empty Files

```bash
python3 duBE.py /home/user --exclude /home/user/Downloads --exclude /home/user/tmp
```

```bash
python3 duBE.py /home/user --exclude-zero (or -z)
```

### Show Apparent Size and Modification Dates

```bash
python3 duBE.py /home/user --apparent-size --time
```

### Tree Format Analysis

```bash
python3 duBE.py /home/user --max-depth 3 --all
```

---

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 💬 Feedback

If you have any questions, suggestions, or would like to contribute, feel free to open an issue or pull request.

## 🌐 Connect with Me

[![GitHub](https://img.shields.io/badge/GitHub-@serber1990-181717?style=flat-square&logo=github)](https://github.com/serber1990)

---

### 🚀 Easily analyze disk usage with **duBE** (du But Easier)!
