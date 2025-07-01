"""Cleanup tool for removing unnecessary temporary files from the MCP server."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


async def cleanup_server(
    remove_logs: bool = True,
    remove_caches: bool = True,
    remove_backups: bool = True,
    dry_run: bool = False,
) -> str:
    """
    Clean up unnecessary temporary files from the MCP server.

    This tool removes files that are NOT necessary for MCP server operations:
    - Log files (*.log)
    - Cache directories (.mypy_cache, .pytest_cache, __pycache__)
    - Backup files (*.backup, *.bak, *~)
    - PID files (*.pid)
    - Temporary files (*.tmp, *.temp)

    PRESERVES essential files:
    - State files in monitoring_data/
    - Alert history in monitoring_data/alerts/
    - Configuration files
    - All source code and tools

    Args:
        remove_logs: Remove all log files (default: True)
        remove_caches: Remove cache directories (default: True)
        remove_backups: Remove backup files (default: True)
        dry_run: Only show what would be deleted without actually deleting (default: False)

    Returns:
        Detailed report of cleanup operations
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent

    files_to_delete: list[Path] = []
    dirs_to_delete: list[Path] = []
    preserved_files: list[str] = []

    # Define patterns for files to remove
    if remove_logs:
        log_patterns = ["*.log"]
        for pattern in log_patterns:
            files_to_delete.extend(project_root.glob(pattern))
            files_to_delete.extend(project_root.glob(f"**/{pattern}"))

    if remove_backups:
        backup_patterns = ["*.backup", "*.bak", "*~", "*.swp"]
        for pattern in backup_patterns:
            files_to_delete.extend(project_root.glob(pattern))
            files_to_delete.extend(project_root.glob(f"**/{pattern}"))

    # Always remove these temporary files
    temp_patterns = ["*.pid", "*.tmp", "*.temp", ".DS_Store"]
    for pattern in temp_patterns:
        files_to_delete.extend(project_root.glob(pattern))
        files_to_delete.extend(project_root.glob(f"**/{pattern}"))

    if remove_caches:
        # Cache directories to remove
        cache_dirs = [".mypy_cache", ".pytest_cache", "__pycache__", ".coverage", "htmlcov", ".tox"]
        for cache_dir in cache_dirs:
            dirs_to_delete.extend(project_root.glob(f"**/{cache_dir}"))

    # Filter out files in .venv and .git directories
    files_to_delete = [f for f in files_to_delete if ".venv" not in str(f) and ".git" not in str(f)]
    dirs_to_delete = [d for d in dirs_to_delete if ".venv" not in str(d) and ".git" not in str(d)]

    # Identify files to preserve
    preserve_patterns = [
        "monitoring_data/*.json",
        "monitoring_data/**/*.json",
        "monitoring_data/**/*.jsonl",
        "config/*.json",
        "**/*.py",  # All Python source files
    ]

    for pattern in preserve_patterns:
        preserved_files.extend(project_root.glob(pattern))

    # Remove duplicates and sort
    files_to_delete = sorted(set(files_to_delete))
    dirs_to_delete = sorted(set(dirs_to_delete))

    # Calculate sizes
    total_size = 0
    file_details = []

    for file_path in files_to_delete:
        if file_path.exists():
            size = file_path.stat().st_size
            total_size += size
            file_details.append((file_path, size))

    dir_details = []
    for dir_path in dirs_to_delete:
        if dir_path.exists():
            dir_size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
            total_size += dir_size
            dir_details.append((dir_path, dir_size))

    # Sort by size
    file_details.sort(key=lambda x: x[1], reverse=True)
    dir_details.sort(key=lambda x: x[1], reverse=True)

    # Perform cleanup if not dry run
    deleted_files = 0
    deleted_dirs = 0
    errors = []

    if not dry_run:
        # Delete files
        for file_path, size in file_details:
            try:
                if file_path.exists():
                    file_path.unlink()
                    deleted_files += 1
            except Exception as e:
                errors.append(f"Error deleting {file_path}: {str(e)}")

        # Delete directories
        for dir_path, size in dir_details:
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    deleted_dirs += 1
            except Exception as e:
                errors.append(f"Error deleting {dir_path}: {str(e)}")

    # Format size
    def format_size(size_bytes: int) -> str:
        size_float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f}{unit}"
            size_float /= 1024.0
        return f"{size_float:.1f}TB"

    # Generate report
    mode_text = "DRY RUN - No files were actually deleted" if dry_run else "CLEANUP COMPLETED"

    report = f"""# 🧹 MCP Server Cleanup Report

**Mode:** {mode_text}
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Space {'To Be Freed' if dry_run else 'Freed'}:** {format_size(total_size)}

## 📊 Summary
- **Files {'to delete' if dry_run else 'deleted'}:** {len(file_details)} files
- **Directories {'to delete' if dry_run else 'deleted'}:** {len(dir_details)} directories
- **Errors:** {len(errors)}

## 🗑️ Files {'To Delete' if dry_run else 'Deleted'} (Top 10 by size)
"""

    for i, (file_path, size) in enumerate(file_details[:10], 1):
        rel_path = file_path.relative_to(project_root)
        report += f"{i}. `{rel_path}` - {format_size(size)}\n"

    if len(file_details) > 10:
        report += f"\n... and {len(file_details) - 10} more files\n"

    if dir_details:
        report += f"\n## 📁 Directories {'To Delete' if dry_run else 'Deleted'}\n"
        for dir_path, size in dir_details:
            rel_path = dir_path.relative_to(project_root)
            report += f"- `{rel_path}/` - {format_size(size)}\n"

    report += "\n## ✅ Preserved Files\n"
    report += "- All state files in `monitoring_data/`\n"
    report += "- Alert history in `monitoring_data/alerts/`\n"
    report += "- All configuration files\n"
    report += "- All Python source code\n"

    if errors:
        report += "\n## ❌ Errors\n"
        for error in errors:
            report += f"- {error}\n"

    report += "\n## 🔧 Options Used\n"
    report += f"- Remove logs: {'Yes' if remove_logs else 'No'}\n"
    report += f"- Remove caches: {'Yes' if remove_caches else 'No'}\n"
    report += f"- Remove backups: {'Yes' if remove_backups else 'No'}\n"
    report += f"- Dry run: {'Yes' if dry_run else 'No'}\n"

    if dry_run:
        report += "\n**Note:** Run without `dry_run=True` to actually delete files.\n"

    return report


async def list_cleanup_candidates() -> str:
    """
    List all files that would be cleaned up without deleting them.

    This is equivalent to cleanup_server(dry_run=True) but with a simpler interface.

    Returns:
        Report of files that can be cleaned up
    """
    return await cleanup_server(dry_run=True)
