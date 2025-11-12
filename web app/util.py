"""
Utility Functions
Common utilities for the RFP Analysis System.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Union
import hashlib


def ensure_dir(directory: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        directory: Directory path
        
    Returns:
        Path object
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_hash(file_path: Union[str, Path]) -> str:
    """
    Get MD5 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def save_json(data: Union[Dict, List], file_path: Union[str, Path], indent: int = 2):
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_json(file_path: Union[str, Path]) -> Union[Dict, List]:
    """
    Load data from JSON file.
    
    Args:
        file_path: Input file path
        
    Returns:
        Loaded data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    return Path(file_path).stat().st_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def list_files(directory: Union[str, Path], 
               extensions: Optional[List[str]] = None,
               recursive: bool = False) -> List[Path]:
    """
    List files in a directory.
    
    Args:
        directory: Directory to search
        extensions: File extensions to filter (e.g., ['.pdf', '.docx'])
        recursive: Search recursively
        
    Returns:
        List of file paths
    """
    path = Path(directory)
    
    if not path.exists():
        return []
    
    if recursive:
        files = path.rglob("*")
    else:
        files = path.glob("*")
    
    files = [f for f in files if f.is_file()]
    
    if extensions:
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                     for ext in extensions]
        files = [f for f in files if f.suffix.lower() in extensions]
    
    return sorted(files)


def count_tokens_estimate(text: str) -> int:
    """
    Rough estimate of token count.
    
    Args:
        text: Text to count
        
    Returns:
        Estimated token count (rough: words * 1.3)
    """
    words = len(text.split())
    return int(words * 1.3)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_file_type(file_path: Union[str, Path], 
                       allowed_extensions: List[str]) -> bool:
    """
    Validate file extension.
    
    Args:
        file_path: Path to file
        allowed_extensions: List of allowed extensions
        
    Returns:
        True if valid, False otherwise
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    
    allowed = [e.lower() if e.startswith('.') else f'.{e.lower()}' 
              for e in allowed_extensions]
    
    return ext in allowed


def create_backup(file_path: Union[str, Path], backup_suffix: str = ".bak") -> Path:
    """
    Create a backup copy of a file.
    
    Args:
        file_path: Path to file
        backup_suffix: Suffix for backup file
        
    Returns:
        Path to backup file
    """
    path = Path(file_path)
    backup_path = path.with_suffix(path.suffix + backup_suffix)
    
    if path.exists():
        import shutil
        shutil.copy2(path, backup_path)
    
    return backup_path


def merge_dicts(*dicts: Dict) -> Dict:
    """
    Merge multiple dictionaries.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def flatten_list(nested_list: List) -> List:
    """
    Flatten a nested list.
    
    Args:
        nested_list: Nested list
        
    Returns:
        Flattened list
    """
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def get_project_root() -> Path:
    """
    Get project root directory.
    
    Returns:
        Path to project root
    """
    current = Path(__file__).resolve()
    # Go up until we find a marker file (like README.md or .git)
    while current.parent != current:
        if (current / "README.md").exists() or (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def print_progress_bar(iteration: int, 
                       total: int, 
                       prefix: str = '', 
                       suffix: str = '', 
                       length: int = 50):
    """
    Print progress bar to console.
    
    Args:
        iteration: Current iteration
        total: Total iterations
        prefix: Prefix string
        suffix: Suffix string
        length: Bar length
    """
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='')
    if iteration == total:
        print()


class Timer:
    """Simple timer context manager."""
    
    def __init__(self, name: str = "Operation"):
        """
        Initialize timer.
        
        Args:
            name: Name of the operation
        """
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timer."""
        import time
        self.start_time = time.time()
        print(f"⏱️  Starting {self.name}...")
        return self
    
    def __exit__(self, *args):
        """Stop timer and print elapsed time."""
        import time
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        print(f"✅ {self.name} completed in {elapsed:.2f} seconds")


if __name__ == "__main__":
    # Test utilities
    print("Testing utilities...")
    
    # Test directory creation
    test_dir = ensure_dir("test_output")
    print(f"✅ Created directory: {test_dir}")
    
    # Test timer
    with Timer("Test operation"):
        import time
        time.sleep(1)
    
    # Test file size formatting
    sizes = [500, 5000, 50000, 500000, 5000000]
    for size in sizes:
        print(f"{size} bytes = {format_file_size(size)}")
    
    print("\n✅ All utility tests passed!")