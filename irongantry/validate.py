"""Input validation for IronGantry — all user-supplied data is validated here."""

import re

# PEP 508 package name: letter/digit, may contain hyphens/underscores/dots internally
_PKG_NAME_RE = re.compile(
    r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)"  # name
    r"(\[([A-Za-z0-9._-]+(,[A-Za-z0-9._-]+)*)\])?"   # optional extras
    r"([!<>=~].+)?$"                                    # optional version spec
)

_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_PYTHON_VERSION_RE = re.compile(r"^\d+\.\d+$")

_ALLOWED_MANIFEST_KEYS = {"project", "python", "packages", "entrypoint"}


def validate_project_name(name: str) -> str:
    """Validate project name: alphanumeric, underscore, hyphen only."""
    if not isinstance(name, str) or not name:
        raise ValueError("Project name must be a non-empty string.")
    if not _PROJECT_NAME_RE.match(name):
        raise ValueError(
            f"Invalid project name {name!r}: "
            "only letters, digits, underscores, and hyphens are allowed."
        )
    return name


def validate_package(pkg: str) -> str:
    """Validate a single pip package specifier against PEP 508 naming rules."""
    if not isinstance(pkg, str) or not pkg.strip():
        raise ValueError("Package specifier must be a non-empty string.")
    pkg = pkg.strip()
    if not _PKG_NAME_RE.match(pkg):
        raise ValueError(f"Invalid package specifier: {pkg!r}")
    return pkg


def validate_entrypoint(entry: str) -> str:
    """Validate entrypoint: must start with 'python' or 'python3'."""
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError("Entrypoint must be a non-empty string.")
    entry = entry.strip()
    first_token = entry.split()[0]
    if first_token not in ("python", "python3"):
        raise ValueError(
            f"Entrypoint must start with 'python' or 'python3', got {first_token!r}."
        )
    return entry


def validate_python_version(ver: str) -> str:
    """Validate python version string: must be major.minor format."""
    if not isinstance(ver, str) or not ver.strip():
        raise ValueError("Python version must be a non-empty string.")
    ver = ver.strip()
    if not _PYTHON_VERSION_RE.match(ver):
        raise ValueError(
            f"Invalid python version {ver!r}: expected 'major.minor' (e.g. '3.12')."
        )
    return ver


def validate_manifest(config: dict) -> dict:
    """Validate a parsed IronGantryfile manifest.

    Returns the validated config dict (values may be stripped/normalized).
    Raises ValueError on any validation failure.
    """
    if not isinstance(config, dict):
        raise ValueError("Manifest must be a TOML table (dict), not a bare value.")

    # Reject unknown keys
    unknown = set(config.keys()) - _ALLOWED_MANIFEST_KEYS
    if unknown:
        raise ValueError(f"Unknown manifest keys: {', '.join(sorted(unknown))}")

    # project — required
    if "project" not in config:
        raise ValueError("Manifest must contain a 'project' key.")
    validate_project_name(config["project"])

    # entrypoint — required
    if "entrypoint" not in config:
        raise ValueError("Manifest must contain an 'entrypoint' key.")
    config["entrypoint"] = validate_entrypoint(config["entrypoint"])

    # python — optional
    if "python" in config:
        config["python"] = validate_python_version(config["python"])

    # packages — optional
    if "packages" in config:
        pkgs = config["packages"]
        if not isinstance(pkgs, list):
            raise ValueError("'packages' must be a list of strings.")
        config["packages"] = [validate_package(p) for p in pkgs]

    return config
