## API Reference

### Python

#### Module: termux_cli_manager.py

termux_cli_manager.py
Unified manager + fixer for Gemini CLI and Qwen CLI on Termux (Android).

Features:
- Install / update / uninstall @google/gemini-cli and @qwen-code/qwen-code using npm
- Optionally build ripgrep from source (Rust) OR use Termux `pkg install ripgrep`
- Patch Gemini's downloadRipGrep.js to support android by short-circuiting to system `rg`
- Create qwen-rg-wrapper.js and inject into Qwen's dist/index.js
- Create gemini-auto-patch.js and qwen-auto-patch.js and set them as postinstall hooks
- Atomic writes with timestamped backups
- Safe postinstall script merging
- Idempotent; safe; logs clearly
- Interactive menu and CLI flags support
- File-based logging
- Configuration file support
- Dependency checking
- Enhanced error handling
- Non-interactive mode with --yes and --dry-run flags

Usage:
  pkg install python nodejs npm ripgrep  # recommended prerequisites
  Save script and run: python3 termux_cli_manager.py

##### Functions

**`get_npm_prefix()`**

Dynamically detect npm prefix

**`setup_logging(verbose)`**

Setup logging to file and console

**`load_config()`**

Load configuration from file

**`save_config(config)`**

Save configuration to file

**`echo(s, color)`**

Print with optional color

**`run(cmd, check, capture, dry_run, shell)`**

Run shell command with dry-run support. Accepts cmd as string or list.

**`get_timestamp()`**

Get current timestamp for backup files

**`safe_write(path, content, make_backup, dry_run)`**

Write content to file with atomic operation and timestamped backup

**`backup_file(path, dry_run)`**

Create timestamped backup of file if it exists

**`is_termux()`**

Check if running in Termux environment

**`check_dependencies()`**

Check if required dependencies are installed

**`find_all_ripgrep_files(gemini_dir)`**

Find all downloadRipGrep.js files in gemini directory recursively

**`is_installed(pkg_dir)`**

Check if package is installed

**`get_current_version(pkg_dir, version_cmd)`**

Get current version of installed package

**`fetch_available_versions(pkg_name)`**

Fetch available versions from npm registry

**`select_version(pkg_name, current_version)`**

Interactive version selection

**`fix_node_gyp_on_android(dry_run)`**

Fixes node-gyp issue on Termux by creating a gypi file
that defines android_ndk_path.

**`ensure_system_ripgrep(auto_install, dry_run)`**

Ensure ripgrep is installed via pkg

**`build_ripgrep_from_source(target_arch, dry_run)`**

Attempt to compile ripgrep with cargo for Android. Heavy and requires Rust.
Returns True if built and installed to ~/.local/bin or similar.

**`npm_install_global(pkg_name, version, ignore_scripts, dry_run)`**

Install npm package globally

**`npm_uninstall_global(pkg_name, dry_run)`**

Uninstall npm package globally

**`npm_update_global(pkg_name, dry_run)`**

Update npm package globally

**`npm_rebuild_global(pkg_names, dry_run)`**

Rebuild npm packages globally

**`find_gemini_ripgrep_files()`**

Find all Gemini ripgrep files to patch

**`patch_gemini_download_ripgrep(dry_run)`**

Patch all Gemini ripgrep download files

**`write_gemini_autopatch(dry_run)`**

Write auto-patch script for Gemini

**`patch_qwen_wrapper_and_index(dry_run)`**

Patch Qwen to use system ripgrep

**`write_qwen_autopatch(dry_run)`**

Write auto-patch script for Qwen

**`merge_postinstall_hook(pkg_dir, script_path, dry_run)`**

Safely merge postinstall hook to package.json, preserving existing scripts

**`remove_postinstall_hook(pkg_dir, script_path, dry_run)`**

Remove postinstall hook from package.json, preserving other scripts

**`get_latest_backup(path)`**

Get the latest backup file for a given path

**`rollback_gemini_patches(dry_run)`**

Rollback all Gemini patches

**`rollback_qwen_patches(dry_run)`**

Rollback all Qwen patches

**`install_gemini_flow(config, dry_run, yes)`**

Install Gemini CLI flow

**`update_gemini_flow(config, dry_run, yes)`**

Update Gemini CLI flow

**`uninstall_gemini_flow(config, dry_run, yes)`**

Uninstall Gemini CLI flow

**`install_qwen_flow(config, dry_run, yes)`**

Install Qwen CLI flow

**`update_qwen_flow(config, dry_run, yes)`**

Update Qwen CLI flow

**`uninstall_qwen_flow(config, dry_run, yes)`**

Uninstall Qwen CLI flow

**`verify_gemini()`**

Verify Gemini installation with detailed error reporting

**`verify_qwen()`**

Verify Qwen installation with detailed error reporting

**`show_logo()`**

Displays the TCM ASCII art logo.

**`get_manager_version()`**

Get current version of the tool

**`check_for_updates()`**

Check for updates to the tool itself

**`show_menu(config, yes, dry_run)`**

Show interactive menu

**`parse_args()`**

Parse command line arguments

**`main()`**

Main function

### JavaScript

### Java

### C++

### Go

