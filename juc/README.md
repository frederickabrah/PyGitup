# Termux CLI Manager

A comprehensive manager and fixer for Gemini CLI (@google/gemini-cli) and Qwen CLI (@qwen-code/qwen-code) on Termux (Android).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Node.js Version](https://img.shields.io/badge/Node.js-12%2B-green.svg)](https://nodejs.org/)

## Table of Contents

- [Overview](#overview)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Interactive Mode](#interactive-mode)
  - [Command-Line Interface](#command-line-interface)
- [How It Works](#how-it-works)
  - [Gemini CLI Fix](#gemini-cli-fix)
  - [Qwen CLI Fix](#qwen-cli-fix)
- [Configuration](#configuration)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Changelog](#changelog)

## Overview

The **Termux CLI Manager (TCM)** provides a unified and robust solution for managing both Google's Gemini CLI and Alibaba's Qwen CLI on Android devices running Termux. It addresses critical compatibility issues that prevent these powerful AI command-line interfaces from functioning correctly in the Termux environment. TCM handles installation, updates, uninstallation, patching, and verification, ensuring a seamless experience for developers and users leveraging AI on their mobile devices.

## The Problem

Both `@google/gemini-cli` and `@qwen-code/qwen-code` are designed to enhance development workflows with AI capabilities. However, their installation process on Termux often fails due to a common dependency: `ripgrep`. Specifically, the build process for `ripgrep` within these CLI packages does not recognize `android` as a valid platform. This leads to compilation errors and prevents successful installation, typically manifesting as errors similar to:

```
gyp: Undefined variable android_ndk_path in binding.gyp while trying to load binding.gyp
gyp ERR! stack Error: gyp failed with exit code: 1
...
VError: Unknown platform: android at getTarget (.../downloadRipGrep.js:60:13)
```

These errors effectively block users from installing and utilizing Gemini CLI and Qwen CLI on their Termux setups.

## The Solution

The Termux CLI Manager comprehensively addresses these issues through targeted modifications and intelligent dependency management:

1.  **For Gemini CLI**: It intelligently modifies the `downloadRipGrep.js` file within the Gemini CLI package. This modification enables `android` to be recognized as a valid platform and directs the system to use a pre-installed `ripgrep` instance, bypassing the problematic internal download process.
2.  **For Qwen CLI**: It creates a sophisticated wrapper mechanism. This involves generating a `qwen-rg-wrapper.js` file that transparently redirects all `ripgrep` calls from the Qwen CLI to the system-installed `ripgrep` binary, ensuring smooth operation without internal modifications to core Qwen CLI files.
3.  **Auto-patching**: Both solutions are implemented with "auto-patch" scripts designed to persist through future package updates, minimizing the need for manual intervention.
4.  **Dependency Management**: TCM ensures that all necessary system dependencies, including `python`, `nodejs`, `npm`, and `ripgrep`, are correctly installed and configured.

This integrated approach provides a robust and long-term solution, enabling the full functionality of Gemini CLI and Qwen CLI on Termux.

## Features

TCM is packed with features designed for ease of use and reliability:

-   ✅ **Comprehensive Management**: Install, update, and uninstall both Gemini CLI and Qwen CLI with simple commands or an interactive menu.
-   ✅ **Automatic Patching**: Seamlessly applies patches to fix Android compatibility issues for both CLIs, ensuring they run flawlessly.
-   ✅ **Dual Interface Support**: Offers both an intuitive interactive menu and a powerful command-line interface (CLI) for flexible operation.
-   ✅ **Backup System**: Automatically creates backups of original files before applying patches, allowing for safe rollbacks.
-   ✅ **Persistent Patches**: Utilizes auto-patch scripts designed to survive subsequent package updates, reducing maintenance effort.
-   ✅ **Dependency Checking**: Verifies and assists with the installation of all required system dependencies.
-   ✅ **Detailed Logging**: Implements file-based logging to aid in troubleshooting and monitoring operations.
-   ✅ **Configuration Management**: Supports a configuration file for customizing tool behavior (details in `USAGE_GUIDE.md`).
-   ✅ **Version Selection**: Provides options for installing specific versions of the CLIs.
-   ✅ **Installation Verification**: Includes a mechanism to verify the successful installation and patching of both CLIs.
-   ✅ **Rollback Capabilities**: Allows users to revert patches for Gemini and Qwen CLI if needed.
-   ✅ **"Do Everything" Mode**: A convenient option to automate the entire setup process, from installation to patching.
-   ✅ **Self-Update Mechanism**: The tool itself can be updated, ensuring you always have the latest fixes and features.

## Installation

To install Termux CLI Manager and prepare your Termux environment, follow these steps:

1.  **Install Termux**: Ensure you have the Termux application installed on your Android device from F-Droid or Google Play Store.
2.  **Install Core Dependencies**: Open Termux and install the necessary system packages:
    ```bash
    pkg update && pkg upgrade
    pkg install python nodejs npm ripgrep
    ```
3.  **Download TCM**: Fetch the main script from the official repository:
    ```bash
    curl -O https://raw.githubusercontent.com/frederickabrah/TCM/main/termux_cli_manager.py
    chmod +x termux_cli_manager.py
    ```

After these steps, TCM is ready to use! You can run it directly or move it to a directory in your `$PATH` for global access (e.g., `mv termux_cli_manager.py ~/.local/bin/tcm`).

Alternatively, you can clone the repository for full access:
```bash
git clone https://github.com/frederickabrah/TCM.git
cd TCM
# Then install dependencies as above, and run python3 termux_cli_manager.py
```

## Usage

Termux CLI Manager offers both an interactive menu for guided operations and a command-line interface for scripting and automation.

### Interactive Mode

For a guided experience, simply run the script without any arguments:

```bash
python3 termux_cli_manager.py
```

This will present an interactive menu, allowing you to choose actions like installing, updating, patching, or uninstalling Gemini and Qwen CLIs:

```
Welcome to Termux CLI Manager!
Please select an option:
---------------------------------------------
1) Install Gemini
2) Update Gemini
3) Uninstall Gemini
4) Install Qwen
5) Update Qwen
6) Uninstall Qwen
7) Patch Gemini
8) Patch Qwen
9) Patch both
10) Ensure ripgrep (pkg install)
11) Rollback Gemini patches
12) Rollback Qwen patches
13) Do everything (install both -> ripgrep -> patch -> rebuild)
14) Verify installations
15) Show log file
0) Exit
---------------------------------------------
Enter your choice:
```

### Command-Line Interface

For advanced users and automation scripts, TCM supports various command-line flags:

```bash
# Install both CLIs
python3 termux_cli_manager.py --install-gemini --install-qwen

# Update both CLIs
python3 termux_cli_manager.py --update-gemini --update-qwen

# Patch both CLIs
python3 termux_cli_manager.py --patch-both

# Ensure ripgrep is installed
python3 termux_cli_manager.py --ensure-rg

# Perform a full setup (install, ensure ripgrep, patch, rebuild)
python3 termux_cli_manager.py --do-everything

# Verify installations
python3 termux_cli_manager.py --verify

# Enable verbose logging for detailed output during an operation
python3 termux_cli_manager.py --verbose --install-gemini

# View all available CLI options
python3 termux_cli_manager.py --help
```

For more detailed CLI examples and options, please refer to the [USAGE_GUIDE.md](USAGE_GUIDE.md).

## How It Works

TCM implements specific strategies to overcome the `ripgrep` compatibility issues for each CLI.

### Gemini CLI Fix

The fix for Gemini CLI involves a direct modification to its source code responsible for `ripgrep` detection and download:

1.  **Platform Recognition**: The script locates the `downloadRipGrep.js` file within the Gemini CLI package.
2.  **Code Modification**: It injects logic to explicitly add `android` as a recognized platform, instructing it to use `system-installed` `ripgrep`.
3.  **Download Bypass**: When the target platform is identified as `system-installed`, the modified script bypasses the problematic internal `ripgrep` binary download process.
4.  **System `ripgrep` Usage**: Gemini CLI is then configured to utilize the `ripgrep` binary already installed on the Termux system via `pkg install ripgrep`.

This ensures that the Gemini CLI's dependency resolution for `ripgrep` is handled correctly by the Termux environment.

### Qwen CLI Fix

The approach for Qwen CLI is different, focusing on creating a seamless wrapper:

1.  **Wrapper Creation**: The script generates a dedicated JavaScript file, `qwen-rg-wrapper.js`, designed to act as an intermediary. This wrapper's sole purpose is to execute the system-installed `rg` (ripgrep) command with all passed arguments.
2.  **Main File Modification**: It then modifies Qwen CLI's main execution file, `dist/index.js`, to import and utilize this newly created `qwen-rg-wrapper.js`.
3.  **Redirection**: All internal `ripgrep` calls made by the Qwen CLI are transparently redirected to this wrapper, which in turn invokes the functional system `ripgrep`.

This method avoids deep alterations to Qwen CLI's core logic while ensuring its `ripgrep` dependencies are satisfied correctly.

## Configuration

TCM supports a configuration file (`config.json` in the project root or `~/.config/tcm/config.json`) for persistent settings. This allows you to customize default installation paths, logging levels, and other preferences.

For detailed information on configuring TCM, please refer to the [USAGE_GUIDE.md](USAGE_GUIDE.md).

## Logging

All operations performed by TCM are logged to a file (`tcm.log` by default, located in the project root or `~/.cache/tcm/tcm.log`). This log file is invaluable for debugging issues, tracking actions, and reviewing execution details. You can view the log directly through the interactive menu or by accessing the file. Verbose logging can be enabled with the `--verbose` flag for more detailed output.

## Troubleshooting

Should you encounter any issues:
1.  **Check Dependencies**: Ensure all required packages (`python`, `nodejs`, `npm`, `ripgrep`) are installed and up-to-date.
2.  **Review Log File**: Examine the `tcm.log` file for error messages or clues about what went wrong.
3.  **Rollback Patches**: If a patch causes unexpected behavior, use the rollback options in the interactive menu or CLI flags.
4.  **Verify Installations**: Use the `--verify` flag to check the status of your Gemini and Qwen CLI installations.

If problems persist, please refer to the [USAGE_GUIDE.md](USAGE_GUIDE.md) for a dedicated troubleshooting section or open an issue on the GitHub repository.

## Contributing

We welcome contributions to Termux CLI Manager! If you have ideas for improvements, bug fixes, or new features, please feel free to:

1.  **Fork the repository**.
2.  **Create a new branch** (`git checkout -b feature/your-feature-name`).
3.  **Make your changes**.
4.  **Write clear commit messages**.
5.  **Submit a Pull Request** explaining your changes.

Please ensure your code adheres to the existing style and includes relevant tests if applicable.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Changelog

For a detailed history of changes, new features, and bug fixes, please refer to the [CHANGELOG.md](CHANGELOG.md) file.