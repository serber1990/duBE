#!/usr/bin/env python3

import argparse
import os
import sys
import signal
from datetime import datetime
from shellcolorize import Color

EXCLUDE_DIRS = ['/proc', '/sys', '/dev', '/run', '/mnt', '/media', '/lost+found']

def get_size(start_path='.', max_depth=None, follow_symlinks=False, same_filesystem=True, 
             block_size=1024, threshold=None, show_all=False, apparent_size=False):
    total_size = 0
    base_dev = os.stat(start_path).st_dev if same_filesystem else None
    depth = start_path.rstrip(os.path.sep).count(os.path.sep)
    sizes = {}

    for dirpath, dirnames, filenames in os.walk(start_path, followlinks=follow_symlinks):
        current_depth = dirpath.count(os.path.sep) - depth
        if max_depth is not None and current_depth >= max_depth:
            dirnames[:] = []
            continue

        dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in EXCLUDE_DIRS]
        if same_filesystem:
            dirnames[:] = [d for d in dirnames if os.stat(os.path.join(dirpath, d)).st_dev == base_dev]

        dir_size = 0
        for file in filenames:
            fp = os.path.join(dirpath, file)
            try:
                if not os.path.islink(fp) or follow_symlinks:
                    if apparent_size:
                        file_size = os.path.getsize(fp) // block_size
                    else:
                        file_size = (os.stat(fp).st_blocks * 512) // block_size

                    if threshold is None or (threshold > 0 and file_size >= threshold) or (threshold < 0 and file_size <= threshold):
                        dir_size += file_size
                        if show_all:
                            sizes[fp] = file_size
            except (FileNotFoundError, OSError):
                continue

        sizes[dirpath] = dir_size
        total_size += dir_size

    return total_size, sizes

def format_size(size, block_size=1024):
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    size *= block_size
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}"

def get_modified_time(path, time_format="iso"):
    time = datetime.fromtimestamp(os.path.getmtime(path))
    if time_format.startswith('+'):
        return time.strftime(time_format[1:])
    elif time_format == "full-iso":
        return time.strftime('%Y-%m-%d %H:%M:%S.%f')
    elif time_format == "long-iso":
        return time.strftime('%Y-%m-%d %H:%M')
    elif time_format == "iso":
        return time.strftime('%Y-%m-%d')
    else:
        return time.strftime(time_format)

def print_tree(sizes, root_dir, block_size=1024):
    def print_dir_tree(path, prefix=""):
        size = sizes.get(path, 0)
        print(f"{Color.BLUE}{format_size(size, block_size)}{Color.RESET} {prefix}{os.path.basename(path)}")
        subdirs = [d for d in sizes if os.path.dirname(d) == path]
        for i, subdir in enumerate(sorted(subdirs)):
            if i == len(subdirs) - 1:
                print_dir_tree(subdir, prefix + "    ")
            else:
                print_dir_tree(subdir, prefix + "│   ")

    print(f"{Color.MAGENTA}\n[*] Disk usage analysis in tree format for directory: {root_dir}\n{Color.RESET}")
    print_dir_tree(root_dir)

def analyze_disk_usage(directory='.', max_depth=None, follow_symlinks=False, same_filesystem=True, 
                       block_size=1024, threshold=None, show_time=False, time_style="iso", 
                       sort_order=None, show_all=False, exclude_zero=False, apparent_size=False):
    total_size, folder_sizes = get_size(directory, max_depth, follow_symlinks, same_filesystem, 
                                        block_size, threshold, show_all, apparent_size)
    
    if exclude_zero:
        folder_sizes = {path: size for path, size in folder_sizes.items() if size > 0}
    
    sorted_sizes = sorted(folder_sizes.items(), key=lambda x: x[1], reverse=(sort_order == "desc"))

    print(f"{Color.MAGENTA}\n[*] Disk usage analysis for directory: {directory}\n{Color.RESET}")
    for path, size in sorted_sizes:
        formatted_size = format_size(size, block_size)
        if show_time:
            mod_time = get_modified_time(path, time_style)
            print(f"{Color.BLUE}{formatted_size}{Color.RESET} {path}  {Color.YELLOW}[Modified: {mod_time}]{Color.RESET}")
        else:
            print(f"{Color.BLUE}{formatted_size}{Color.RESET} {path}")

    print(f"{Color.GREEN}\n[+] Total size: {format_size(total_size, block_size)}{Color.RESET}")

def handle_sigint(signum, frame):
    print(f"\n{Color.RED}[!] Exiting now{Color.RESET}")
    sys.exit(1)

def main():
    signal.signal(signal.SIGINT, handle_sigint)

    parser = argparse.ArgumentParser(description='Enhanced disk usage analyzer with additional features.')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to analyze (default: current directory)')
    parser.add_argument('--max-depth', type=int, help='Maximum depth to recurse')
    parser.add_argument('-a', '--all', action='store_true', help='Include individual files in output')
    parser.add_argument('--block-size', type=int, default=1024, help='Block size for disk usage (default: 1024 bytes)')
    parser.add_argument('--apparent-size', action='store_true', help='Show apparent size instead of disk usage')
    parser.add_argument('--follow-symlinks', action='store_true', help='Follow symbolic links')
    parser.add_argument('--exclude', action='append', help='Exclude specific directories or patterns')
    parser.add_argument('--same-filesystem', action='store_true', help='Restrict to a single filesystem')
    parser.add_argument('-z', '--exclude-zero', action='store_true', help='Exclude files and directories with 0.00 B size')
    parser.add_argument('--threshold', type=int, help='Exclude entries smaller/larger than threshold (use positive/negative value)')
    parser.add_argument('--time', action='store_true', help='Show last modification time of each directory')
    parser.add_argument('--time-style', help='Date format for --time (default: iso)', default="iso")
    parser.add_argument('--sort', choices=['asc', 'desc'], help='Sort by size in ascending or descending order')

    args = parser.parse_args()
    directory = args.directory

    if args.exclude:
        EXCLUDE_DIRS.extend(args.exclude)

    analyze_disk_usage(
        directory,
        max_depth=args.max_depth,
        follow_symlinks=args.follow_symlinks,
        same_filesystem=args.same_filesystem,
        block_size=args.block_size,
        threshold=args.threshold,
        show_time=args.time,
        time_style=args.time_style,
        sort_order=args.sort,
        show_all=args.all,
        exclude_zero=args.exclude_zero,
        apparent_size=args.apparent_size
    )

if __name__ == "__main__":
    main()

