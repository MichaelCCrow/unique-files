#!/usr/bin/env python3
"""
Compare multiple directories and list files that are unique to each directory.
Files are considered the same if they have the same name (case-sensitive).
Optionally, you can compare by file content (hash) to detect duplicates with different names.
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

def get_files_by_name(directories, follow_symlinks=False):
    """Return a dict mapping filename -> list of directories containing it."""
    file_locations = defaultdict(list)
    
    for dir_path in directories:
        dir_path = Path(dir_path).resolve()
        if not dir_path.is_dir():
            print(f"Error: '{dir_path}' is not a directory or does not exist.", file=sys.stderr)
            continue
        
        for file_path in dir_path.rglob('*'):
            if file_path.name.startswith('.'):
                continue
            if file_path.is_file() or (follow_symlinks and file_path.is_symlink()):
                file_locations[file_path.name].append(dir_path)
    
    return file_locations

def get_files_by_content(directories, chunk_size=8192):
    """Return a dict mapping file hash -> list of (path, directory) tuples."""
    content_map = defaultdict(list)
    
    for dir_path in directories:
        dir_path = Path(dir_path).resolve()
        if not dir_path.is_dir():
            continue
            
        for file_path in dir_path.rglob('*'):
            if file_path.name.startswith('.'):
                continue
            if not file_path.is_file():
                continue
            file_hash = calculate_file_hash(file_path, chunk_size)
            if file_hash:
                content_map[file_hash].append((file_path, dir_path))
    
    return content_map

def print_unique_by_name(directories):
    file_locations = get_files_by_name(directories)
    
    # Invert to get files unique to each directory
    unique_files = defaultdict(list)
    
    for filename, dirs_containing in file_locations.items():
        if len(dirs_containing) == 1:
            unique_dir = dirs_containing[0]
            unique_files[unique_dir].append(filename)
    
    # Print results
    print("Files unique to each directory (by filename):\n")
    for dir_path in sorted(unique_files.keys(), key=lambda x: x.name):
        files = sorted(unique_files[dir_path])
        print(f"{dir_path}/  ({len(files)} unique files)")
        for f in files[:50]:  # limit preview
            print(f"   - {f}")
        #if len(files) > 50:
        #    print(f"   ... and {len(files) - 50} more")
        print()

def main():
    parser = argparse.ArgumentParser(description="Find files unique to each directory.")
    parser.add_argument('directories', nargs='+', help='Directories to compare')
    parser.add_argument('--by-content', action='store_true',
                        help='Compare by file content (hash) instead of just filename (slower but more accurate)')
    parser.add_argument('--follow-symlinks', action='store_true',
                        help='Include symlinked files when comparing by name')
    
    args = parser.parse_args()
    
    if len(args.directories) < 2:
        print("Error: Please provide at least 2 directories to compare.", file=sys.stderr)
        sys.exit(1)
    
    directories = [Path(d) for d in args.directories]
    
    if args.by_content:
        print("Comparing files by content (this may take a while)...")
        content_map = get_files_by_content(directories)
        
        # Track which files have duplicates across directories
        seen_in_multiple = set()
        for locations in content_map.values():
            dirs = {path.parent for path, _ in locations}
            if len(dirs) > 1:
                for file_path, _ in locations:
                    seen_in_multiple.add(file_path)
        
        print("\nFiles unique to each directory (by content):\n")
        for dir_path in directories:
            unique_files = []
            for file_path in dir_path.rglob('*'):
                if file_path.name.startswith('.'):
                    continue
                if not file_path.is_file():
                    continue
                if file_path not in seen_in_multiple:
                    file_hash = calculate_file_hash(file_path)
                    # Double-check this file isn't duplicated under different name
                    if file_hash and len({p.parent for p, _ in content_map[file_hash]}) == 1:
                        unique_files.append(file_path.name)
            
            if unique_files:
                print(f"{dir_path}/  ({len(unique_files)} unique files by content)")
                for f in sorted(unique_files)[:50]:
                    print(f"   - {f}")
                if len(unique_files) > 50:
                    print(f"   ... and {len(unique_files) - 50} more")
                print()
            else:
                print(f"{dir_path}/  (no unique files by content)")
                print()
    else:
        print_unique_by_name(directories)

if __name__ == "__main__":
    main()
