"""
PyGitUp Automation Module
==========================
AI-powered automation features for GitHub workflows.
"""

from .release_notes import generate_ai_release_notes, generate_release_notes_from_commits
from .issue_triage import ai_label_issues, ai_prioritize_issues, auto_label_and_triage
from .commit_suggestions import suggest_commit_message, enhance_commit_message
from .dependency_updates import check_dependency_updates, create_dependency_update_pr
from .todo_prioritizer import scan_and_prioritize_todos, get_todo_priority_report

__all__ = [
    'generate_ai_release_notes',
    'generate_release_notes_from_commits',
    'ai_label_issues',
    'ai_prioritize_issues',
    'auto_label_and_triage',
    'suggest_commit_message',
    'enhance_commit_message',
    'check_dependency_updates',
    'create_dependency_update_pr',
    'scan_and_prioritize_todos',
    'get_todo_priority_report',
]
