#!/usr/bin/env python3
"""
Compare multiple directories and show unique files side-by-side in columns,
grouped alphabetically for easy visual comparison.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path
import hashlib
import argparse

def calculate_file_hash(file_path, chunk_size=8192, hash_algo='md5'):
    """Calculate hash of a file."""
    hash_obj = hashlib.new(hash_algo)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return None

def get_all_files_recursive(directories):
    """Return dict: directory -> set of filenames (recursive, no hidden)"""
    files_in_dir = {}
    for dir_path in directories:
        dir_path = Path(dir_path).resolve()
        if not dir_path.is_dir():
            print(f"Error: '{dir_path}' is not a directory.", file=sys.stderr)
            continue
        files = set()
        for file_path in dir_path.rglob('*'):
            if file_path.name.startswith('.') or not file_path.is_file():
                continue
            files.add(file_path.name)
        files_in_dir[dir_path] = files
    return files_in_dir

def get_unique_files_by_content(directories):
    """Return dict: directory -> set of filenames unique by content"""
    content_map = defaultdict(list)  # hash -> list of (path, dir)
    
    # First pass: build hash map
    for dir_path in directories:
        dir_path = Path(dir_path).resolve()
        if not dir_path.is_dir():
            continue
        for file_path in dir_path.rglob('*'):
            if file_path.name.startswith('.') or not file_path.is_file():
                continue
            file_hash = calculate_file_hash(file_path)
            if file_hash:
                content_map[file_hash].append((file_path, dir_path))
    
    # Determine which files are unique by content
    unique_in_dir = {d: set() for d in directories}
    
    for file_hash, locations in content_map.items():
        dirs_present = {dir_path for _, dir_path in locations}
        if len(dirs_present) == 1:
            unique_dir = dirs_present.pop()
            for file_path, _ in locations:
                if file_path.parent.resolve() in [d.resolve() for d in directories]:
                    unique_in_dir[unique_dir].add(file_path.name)
    
    return unique_in_dir

def print_side_by_side_comparison(directories, unique_files_per_dir):
    """Print all unique files grouped alphabetically in neat columns."""
    if not directories:
        print("No valid directories to compare.")
        return
    
    # Sort directories by name for consistent left-to-right order
    sorted_dirs = sorted(directories, key=lambda x: x.name)
    dir_names = [d.name + "/" for d in sorted_dirs]
    
    # Find all unique filenames across all dirs
    all_unique_files = sorted({
        fname for fileset in unique_files_per_dir.values()
        for fname in fileset
    })
    
    if not all_unique_files:
        print("No unique files found in any directory.")
        return
    
    # Determine column widths
    col_widths = [max(len(name), 20) for name in dir_names]  # min 20
    header = " │ ".join(f"{name:<{w}}" for name, w in zip(dir_names, col_widths))
    separator = "─" * len(header)
    
    print("\nUnique files comparison (grouped alphabetically):\n")
    print(header)
    print(separator)
    
    current_letter = ''
    for filename in all_unique_files:
        letter = filename[0].upper()
        if letter != current_letter:
            current_letter = letter
            if letter.isalpha():
                print(f"\n{current_letter}")
            else:
                print(f"\n# (non-letter)")
        
        row = []
        for dir_path in sorted_dirs:
            marker = "✓" if filename in unique_files_per_dir.get(dir_path, set()) else " "
            row.append(f"{marker} {filename}")
        
        line = " │ ".join(f"{cell:<{w}}" for cell, w in zip(row, col_widths))
        print(line)
    
    print(f"\n{separator}")
    counts = [len(unique_files_per_dir.get(d, set())) for d in sorted_dirs]
    footer = " │ ".join(f"{c} files" for c in counts)
    print(footer.rjust(len(footer) + len(" │ ".join(["" for _ in counts])) - len(footer)))

def main():
    parser = argparse.ArgumentParser(
        description="Compare directories and show unique files side-by-side, grouped alphabetically."
    )
    parser.add_argument('directories', nargs='+', help='Directories to compare')
    parser.add_argument('--by-content', action='store_true',
                        help='Compare by file content (detects same files with different names)')
    
    args = parser.parse_args()
    
    if len(args.directories) < 2:
        print("Error: At least 2 directories required.", file=sys.stderr)
        sys.exit(1)
    
    directories = [Path(d).resolve() for d in args.directories]
    valid_dirs = [d for d in directories if d.is_dir()]
    
    if len(valid_dirs) < 2:
        print("Error: At least 2 valid directories are required.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Comparing {len(valid_dirs)} directories recursively (skipping hidden files)...")
    if args.by_content:
        print("Mode: Unique by content (hash) ─ detects renamed duplicates")
        unique_files = get_unique_files_by_content(valid_dirs)
    else:
        print("Mode: Unique by filename only")
        all_files = get_all_files_recursive(valid_dirs)
        # Compute unique per dir
        unique_files = {}
        for dir_path, files in all_files.items():
            others = set()
            for other_dir, other_files in all_files.items():
                if other_dir != dir_path:
                    others.update(other_files)
            unique_files[dir_path] = files - others
    
    print_side_by_side_comparison(valid_dirs, unique_files)

if __name__ == "__main__":
    main()
