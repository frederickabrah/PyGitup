"""
PyGitUp UX Helpers
===================
Common utilities for better user experience:
- Progress tracking with time estimates
- Retry logic with exponential backoff
- Accessible output (colorblind-friendly)
- Help text and examples
- Error recovery helpers
"""

import time
import sys
from datetime import datetime
from typing import Callable, Optional, Any, Dict
from .ui import print_info, print_success, print_error, print_warning


def with_progress(
    operation: Callable,
    description: str = "Processing",
    total: Optional[int] = None,
    unit: str = "items"
) -> Any:
    """
    Execute an operation with progress indicator.
    
    Args:
        operation: Function to execute
        description: What to display
        total: Total items (if known)
        unit: Unit of measurement
        
    Returns:
        Result from operation
    """
    start_time = datetime.now()
    print_info(f"{description}...")
    print_info("Press Ctrl+C to cancel")
    
    try:
        result = operation()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print_success(f"✓ Completed in {elapsed:.1f}s")
        return result
        
    except KeyboardInterrupt:
        elapsed = (datetime.now() - start_time).total_seconds()
        print_info(f"\n⚠️  Cancelled after {elapsed:.1f}s")
        raise
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print_error(f"✗ Failed after {elapsed:.1f}s: {e}")
        raise


def with_retry(
    operation: Callable,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    error_messages: Optional[Dict[str, str]] = None
) -> Any:
    """
    Execute an operation with automatic retry on failure.
    
    Args:
        operation: Function to execute
        max_retries: Maximum retry attempts
        backoff_factor: Exponential backoff multiplier
        error_messages: Custom error messages for known errors
        
    Returns:
        Result from operation
        
    Raises:
        Exception: If all retries fail
    """
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            return operation()
            
        except Exception as e:
            last_exception = e
            error_str = str(e)
            
            # Check for known errors with custom messages
            if error_messages:
                for pattern, message in error_messages.items():
                    if pattern.lower() in error_str.lower():
                        print_warning(f"Attempt {attempt}/{max_retries}: {message}")
                        break
                else:
                    print_warning(f"Attempt {attempt}/{max_retries}: {error_str}")
            else:
                print_warning(f"Attempt {attempt}/{max_retries}: {error_str}")
            
            # Don't retry on last attempt
            if attempt < max_retries:
                wait_time = backoff_factor ** attempt
                print_info(f"Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
    
    # All retries failed
    raise last_exception


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def estimate_time(total_items: int, processed_items: int, elapsed_seconds: float) -> Optional[float]:
    """
    Estimate remaining time based on progress.
    
    Args:
        total_items: Total items to process
        processed_items: Items processed so far
        elapsed_seconds: Time elapsed so far
        
    Returns:
        Estimated remaining seconds, or None if can't estimate
    """
    if processed_items == 0 or elapsed_seconds == 0:
        return None
    
    rate = processed_items / elapsed_seconds
    remaining_items = total_items - processed_items
    remaining_seconds = remaining_items / rate
    
    return remaining_seconds


def estimate_file_operation_time(file_size_bytes: int, operation_type: str = "upload") -> Optional[str]:
    """
    Estimate time for file operations based on size.
    
    Args:
        file_size_bytes: Size of file in bytes
        operation_type: Type of operation (upload, download, scan)
        
    Returns:
        Human-readable time estimate
    """
    # Rough estimates based on typical speeds
    speeds = {
        "upload": 1024 * 1024,  # ~1 MB/s average
        "download": 2 * 1024 * 1024,  # ~2 MB/s average
        "scan": 10 * 1024 * 1024,  # ~10 MB/s for local scans
    }
    
    speed = speeds.get(operation_type, 1024 * 1024)
    estimated_seconds = file_size_bytes / speed
    
    if estimated_seconds < 60:
        return f"~{int(estimated_seconds)}s"
    elif estimated_seconds < 3600:
        return f"~{int(estimated_seconds / 60)}m"
    else:
        return f"~{int(estimated_seconds / 3600)}h"


def estimate_repo_operation_time(repo_size_mb: float, operation_type: str = "clone") -> Optional[str]:
    """
    Estimate time for repository operations.
    
    Args:
        repo_size_mb: Repository size in MB
        operation_type: Type (clone, push, pull, migrate)
        
    Returns:
        Human-readable time estimate
    """
    speeds = {
        "clone": 2.0,  # ~2 MB/s
        "push": 1.0,  # ~1 MB/s
        "pull": 2.0,  # ~2 MB/s
        "migrate": 1.5,  # ~1.5 MB/s average
    }
    
    speed = speeds.get(operation_type, 1.0)
    estimated_seconds = repo_size_mb / speed
    
    if estimated_seconds < 60:
        return f"~{int(estimated_seconds)}s"
    elif estimated_seconds < 3600:
        return f"~{int(estimated_seconds / 60)}m {int((estimated_seconds % 60))}s"
    else:
        hours = estimated_seconds / 3600
        return f"~{int(hours)}h {int((estimated_seconds % 3600) / 60)}m"


def accessible_success(message: str) -> None:
    """Print success message with accessibility in mind."""
    # Use both color and symbols for colorblind users
    print_success(f"✓ {message}")


def accessible_error(message: str, hint: Optional[str] = None) -> None:
    """Print error message with accessibility and helpful hints."""
    print_error(f"✗ {message}")
    if hint:
        print_info(f"💡 Hint: {hint}")


def accessible_warning(message: str, action: Optional[str] = None) -> None:
    """Print warning message with suggested action."""
    print_warning(f"⚠️  {message}")
    if action:
        print_info(f"→ Suggested action: {action}")


def confirm_action(prompt: str, require_type: str = "YES") -> bool:
    """
    Require explicit confirmation for dangerous actions.
    
    Args:
        prompt: What to confirm
        require_type: What text user must type (YES, DELETE, etc.)
        
    Returns:
        True if confirmed, False otherwise
    """
    print_warning(f"\n{prompt}")
    user_input = input(f"Type '{require_type}' to confirm: ").strip()
    return user_input == require_type


def safe_input(prompt: str, default: Optional[str] = None, validator: Optional[Callable] = None) -> str:
    """
    Safe input with validation and default value.
    
    Args:
        prompt: Input prompt
        default: Default value if user presses Enter
        validator: Function to validate input
        
    Returns:
        Validated input string
    """
    while True:
        user_input = input(f"{prompt} [{default}]: " if default else f"{prompt}: ")
        
        if not user_input:
            if default:
                return default
            print_error("Input required")
            continue
        
        if validator:
            is_valid, error_msg = validator(user_input)
            if not is_valid:
                print_error(f"Invalid: {error_msg}")
                continue
        
        return user_input
