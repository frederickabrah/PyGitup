"""
PyGitUp UX Utilities
=====================
Common UX improvements across all features:
- Progress tracking with time estimates
- Ctrl+C handling
- Session-level caching
- Default values management
"""

import os
import signal
import time
from datetime import datetime
from .ui import print_info, print_warning, print_success

# Session-level cache for repo names and user preferences
_session_cache = {
    'last_repo': None,
    'last_url': None,
    'last_patterns': None,
    'start_time': None
}

def get_session_cache(key):
    """Get value from session cache."""
    return _session_cache.get(key)

def set_session_cache(key, value):
    """Set value in session cache."""
    _session_cache[key] = value

def start_timer():
    """Start operation timer."""
    _session_cache['start_time'] = time.time()

def get_elapsed_time():
    """Get elapsed time since start_timer was called."""
    if _session_cache['start_time']:
        return time.time() - _session_cache['start_time']
    return 0

def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m {int(seconds%60)}s"
    else:
        return f"{int(seconds/3600)}h {int((seconds%3600)/60)}m"

def estimate_remaining(current, total, elapsed):
    """Estimate remaining time based on progress."""
    if current == 0:
        return "calculating..."
    rate = current / elapsed if elapsed > 0 else 0
    remaining_items = total - current
    remaining_time = remaining_items / rate if rate > 0 else 0
    return format_duration(remaining_time)

def setup_ctrl_c_handler(cleanup_func=None):
    """Setup Ctrl+C handler with optional cleanup."""
    def handler(signum, frame):
        print_warning("\n\n⚠️  Operation cancelled by user")
        if cleanup_func:
            cleanup_func()
        exit(0)
    
    signal.signal(signal.SIGINT, handler)

def clear_ctrl_c_handler():
    """Restore default Ctrl+C handler."""
    signal.signal(signal.SIGINT, signal.default_int_handler)

def get_default_repo_name():
    """Get default repo name from session cache or current directory."""
    if _session_cache.get('last_repo'):
        return _session_cache['last_repo']
    # Use current directory name as fallback
    return os.path.basename(os.getcwd())

def get_default_patterns(pattern_type='file'):
    """Get default patterns for various operations."""
    defaults = {
        'file': ['*.py', '*.js', '*.md'],
        'squash': ['typo', 'fix', 'update', 'WIP'],
        'todo': ['*.py', '*.js', '*.md', '*.ts', '*.jsx', '*.tsx']
    }
    return defaults.get(pattern_type, ['*'])

def confirm_proceed(operation_name, warnings=None):
    """Generic confirmation prompt with optional warnings."""
    if warnings:
        print_warning("\n⚠️  WARNINGS:")
        for w in warnings:
            print_warning(f"  • {w}")
    
    confirm = input(f"\nType 'YES' to proceed with {operation_name}: ").strip()
    return confirm == 'YES'

def with_progress(iterable, desc="Processing", unit="items"):
    """Wrapper for tqdm progress with error handling."""
    try:
        from tqdm import tqdm
        return tqdm(iterable, desc=desc, unit=unit)
    except ImportError:
        # Fallback if tqdm not available
        return iterable
