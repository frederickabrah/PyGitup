
import argparse

def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="PyGitUp - Effortless GitHub Uploads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pygitup.py --mode file --repo myrepo --file myfile.py
  python pygitup.py --mode project --path ./myproject --private
  python pygitup.py --mode batch --repo myrepo --files file1.py,file2.py
  python pygitup.py --mode template --template web-app --repo mywebsite
  python pygitup.py --mode release --repo myproject --version v1.0.0
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["project", "file", "batch", "template", "release", "multi-repo", "scan-todos", "offline-queue", "process-queue", "request-review", "smart-push", "generate-docs", "analytics", "configure", "branch", "stash", "tag", "cherry-pick", "gist", "webhook", "actions", "pr", "audit", "visibility", "repo-info", "delete-repo", "bulk-mgmt"],
        help="Operation mode"
    )

    # Create subparsers for modes that have sub-commands
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-command help")

    # Branch sub-parser
    parser_branch = subparsers.add_parser("branch", help="Manage branches")
    branch_subparsers = parser_branch.add_subparsers(dest="action", help="Branch action")
    branch_subparsers.add_parser("list", help="List all branches")
    parser_branch_create = branch_subparsers.add_parser("create", help="Create a new branch")
    parser_branch_create.add_argument("branch_name", help="The name of the branch to create")
    parser_branch_delete = branch_subparsers.add_parser("delete", help="Delete a branch")
    parser_branch_delete.add_argument("branch_name", help="The name of the branch to delete")
    parser_branch_switch = branch_subparsers.add_parser("switch", help="Switch to a different branch")
    parser_branch_switch.add_argument("branch_name", help="The name of the branch to switch to")

    # Stash sub-parser
    parser_stash = subparsers.add_parser("stash", help="Manage stashes")
    stash_subparsers = parser_stash.add_subparsers(dest="action", help="Stash action")
    parser_stash_save = stash_subparsers.add_parser("save", help="Save a new stash")
    parser_stash_save.add_argument("message", nargs="?", help="Optional message for the stash")
    stash_subparsers.add_parser("list", help="List all stashes")
    stash_subparsers.add_parser("apply", help="Apply the latest stash")
    stash_subparsers.add_parser("pop", help="Apply the latest stash and drop it")
    stash_subparsers.add_parser("drop", help="Drop the latest stash")

    # Tag sub-parser
    parser_tag = subparsers.add_parser("tag", help="Manage tags")
    tag_subparsers = parser_tag.add_subparsers(dest="action", help="Tag action")
    tag_subparsers.add_parser("list", help="List all tags")
    parser_tag_create = tag_subparsers.add_parser("create", help="Create a new tag")
    parser_tag_create.add_argument("tag_name", help="The name of the tag to create")
    parser_tag_create.add_argument("-m", "--message", help="Annotation message for the tag")
    parser_tag_delete = tag_subparsers.add_parser("delete", help="Delete a tag")
    parser_tag_delete.add_argument("tag_name", help="The name of the tag to delete")

    # Cherry-pick argument
    parser.add_argument("--commit-hash", help="The hash of the commit to cherry-pick")

    # Gist sub-parser
    parser_gist = subparsers.add_parser("gist", help="Manage Gists")
    gist_subparsers = parser_gist.add_subparsers(dest="action", help="Gist action")
    parser_gist_create = gist_subparsers.add_parser("create", help="Create a new Gist")
    parser_gist_create.add_argument("filename", help="The filename for the Gist")
    parser_gist_create.add_argument("content", help="The content of the Gist")
    parser_gist_create.add_argument("--description", help="Optional description for the Gist")
    parser_gist_create.add_argument("--public", action="store_true", help="Make the Gist public")
    gist_subparsers.add_parser("list", help="List your Gists")

    # Webhook sub-parser
    parser_webhook = subparsers.add_parser("webhook", help="Manage repository webhooks")
    webhook_subparsers = parser_webhook.add_subparsers(dest="action", help="Webhook action")
    webhook_subparsers.add_parser("list", help="List webhooks for a repository")
    parser_webhook_create = webhook_subparsers.add_parser("create", help="Create a new webhook")
    parser_webhook_create.add_argument("url", help="The URL for the webhook")
    parser_webhook_create.add_argument("--events", nargs="+", default=["push"], help="A list of events to subscribe to")
    parser_webhook_delete = webhook_subparsers.add_parser("delete", help="Delete a webhook")
    parser_webhook_delete.add_argument("hook_id", help="The ID of the webhook to delete")

    # Actions sub-parser
    parser_actions = subparsers.add_parser("actions", help="Manage GitHub Actions")
    actions_subparsers = parser_actions.add_subparsers(dest="action", help="Actions action")
    parser_actions_trigger = actions_subparsers.add_parser("trigger", help="Trigger a workflow")
    parser_actions_trigger.add_argument("workflow_id", help="The ID of the workflow to trigger")
    parser_actions_trigger.add_argument("--ref", default="main", help="The ref to trigger the workflow on")
    actions_subparsers.add_parser("monitor", help="Monitor workflow runs")

    # PR sub-parser
    parser_pr = subparsers.add_parser("pr", help="Manage Pull Requests")
    pr_subparsers = parser_pr.add_subparsers(dest="action", help="PR action")
    parser_pr_merge = pr_subparsers.add_parser("merge", help="Merge a pull request")
    parser_pr_merge.add_argument("pr_number", type=int, help="The number of the pull request to merge")
    parser_pr_close = pr_subparsers.add_parser("close", help="Close a pull request")
    parser_pr_close.add_argument("pr_number", type=int, help="The number of the pull request to close")
    parser_pr_comment = pr_subparsers.add_parser("comment", help="Add a comment to a pull request")
    parser_pr_comment.add_argument("pr_number", type=int, help="The number of the pull request to comment on")
    parser_pr_comment.add_argument("comment", help="The comment to add")
    
    # Common arguments
    parser.add_argument("--repo", help="Target GitHub repository name")
    parser.add_argument("--file", help="Local file to upload")
    parser.add_argument("--path", help="Path in repository for file upload or base path for batch upload")
    parser.add_argument("--message", help="Commit message")
    parser.add_argument("--url", help="URL of the repository (for repo-info mode)")
    
    # Project mode arguments
    parser.add_argument("--description", help="Repository description (for project mode)")
    parser.add_argument("--private", action="store_true", help="Make repository private (for project mode)")
    parser.add_argument("--public", action="store_true", help="Make repository public (for project mode)")
    
    # Batch mode arguments
    parser.add_argument("--files", help="Comma-separated list of files to upload (for batch mode)")
    
    # Template mode arguments
    parser.add_argument("--template", help="Template name for project creation")
    parser.add_argument("--variables", help="Template variables (key=value,key2=value2)")
    
    # Release mode arguments
    parser.add_argument("--version", help="Version tag for release")
    parser.add_argument("--name", help="Release name")
    parser.add_argument("--generate-changelog", action="store_true", help="Generate changelog from commit history")
    
    # Multi-repo mode arguments
    parser.add_argument("--multi-repo", help="Comma-separated list of repositories")
    
    # TODO scan mode arguments
    parser.add_argument("--pattern", help="File patterns to scan for TODOs")
    parser.add_argument("--assign", help="Assignees for created issues")
    parser.add_argument("--no-assign", action="store_true", help="Don't assign issues")
    
    # Code review mode arguments
    parser.add_argument("--reviewers", help="Reviewers for code review request")
    
    # Smart push mode arguments
    parser.add_argument("--squash-pattern", help="Patterns to squash in commit messages")
    
    # Documentation mode arguments
    parser.add_argument("--output", help="Output directory for generated documentation")
    
    # Analytics mode arguments
    parser.add_argument("--period", help="Period for analytics report")
    
    # Configuration arguments
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--batch", action="store_true", help="Run in batch mode (used internally)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the execution of the command without making any changes.")
    
    return parser
