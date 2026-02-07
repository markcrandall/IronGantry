"""Core engine for IronGantry — build, run, and ship Python projects."""

import os
import shlex
import shutil
import subprocess
import sys
import venv
import zipfile

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    raise SystemExit("IronGantry requires Python 3.11+ (for tomllib).")

from irongantry.validate import validate_manifest, validate_project_name

MANIFEST = "IronGantryfile"
ENV_DIR = ".irongantry_env"


class IronGantryEngine:
    """Security-hardened Python container engine."""

    def __init__(self) -> None:
        self.manifest_path = MANIFEST
        self.env_dir = ENV_DIR

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------
    def _load_manifest(self) -> dict:
        """Read and validate the IronGantryfile."""
        if not os.path.isfile(self.manifest_path):
            raise FileNotFoundError(
                f"Manifest not found: {self.manifest_path}\n"
                "Run 'irongantry init' first."
            )
        with open(self.manifest_path, "rb") as f:
            config = tomllib.load(f)
        return validate_manifest(config)

    # ------------------------------------------------------------------
    # Path helpers (cross-platform)
    # ------------------------------------------------------------------
    def _bin_dir(self) -> str:
        """Return the venv bin/Scripts directory name."""
        return "Scripts" if os.name == "nt" else "bin"

    def _pip_path(self) -> str:
        """Return absolute path to pip inside the venv."""
        pip_name = "pip.exe" if os.name == "nt" else "pip"
        return os.path.join(os.path.abspath(self.env_dir), self._bin_dir(), pip_name)

    def _python_path(self) -> str:
        """Return absolute path to python inside the venv."""
        py_name = "python.exe" if os.name == "nt" else "python"
        return os.path.join(os.path.abspath(self.env_dir), self._bin_dir(), py_name)

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------
    def init(self, name: str = "my_app") -> None:
        """Create a new IronGantryfile. Raises FileExistsError if one exists."""
        name = validate_project_name(name)

        if os.path.exists(self.manifest_path):
            raise FileExistsError(
                f"{self.manifest_path} already exists. "
                "Remove it first if you want to reinitialize."
            )

        content = (
            f'project = "{name}"\n'
            f'python = "{sys.version_info.major}.{sys.version_info.minor}"\n'
            f'packages = []\n'
            f'entrypoint = "python main.py"\n'
        )
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Created {self.manifest_path} for project '{name}'.")

    def build(self) -> None:
        """Create venv and install packages from the manifest."""
        config = self._load_manifest()

        # Clean previous environment
        if os.path.isdir(self.env_dir):
            shutil.rmtree(self.env_dir)

        # Create fresh venv
        print("Creating virtual environment...")
        venv.create(self.env_dir, with_pip=True, symlinks=False)

        # Install packages
        packages = config.get("packages", [])
        if packages:
            pip = self._pip_path()
            # Security fix #5: use -- separator so package names can't be
            # interpreted as pip flags, and shell=False with explicit arg list.
            cmd = [pip, "install", "--"] + packages
            print(f"Installing {len(packages)} package(s)...")
            subprocess.run(cmd, check=True, shell=False)

        print("Build complete.")

    def run(self) -> None:
        """Execute the manifest entrypoint using the venv Python."""
        config = self._load_manifest()
        entry = config["entrypoint"]

        abs_python = self._python_path()
        if not os.path.isfile(abs_python):
            raise FileNotFoundError(
                f"Venv Python not found at {abs_python}.\n"
                "Run 'irongantry build' first."
            )

        # Security fix #6: use shlex.split then replace only the first token
        # instead of substring .replace("python", ...).
        tokens = shlex.split(entry)
        tokens[0] = abs_python  # replace 'python'/'python3' with venv path

        # Build clean environment
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = os.path.abspath(self.env_dir)
        bin_dir = os.path.join(os.path.abspath(self.env_dir), self._bin_dir())
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

        # Security fix #1: shell=False with argument list
        subprocess.run(tokens, env=env, check=False, shell=False)

    def ship(self) -> str:
        """Zip the project into a portable <project>_shipped.zip.

        The zip excludes the venv and caches, bundles the IronGantry
        package itself, and generates a bootstrap.py so the recipient
        only needs Python 3.11+ to build and run.
        """
        config = self._load_manifest()
        project_name = config["project"]
        filename = f"{project_name}_shipped.zip"

        # Directories/patterns to exclude
        exclude_dirs = {self.env_dir, "__pycache__", ".irongantry_env"}
        exclude_suffixes = (".pyc", ".pyo")

        # Locate the irongantry package from this running installation
        import irongantry as _ig_pkg
        ig_pkg_dir = os.path.dirname(os.path.abspath(_ig_pkg.__file__))
        ig_entry = os.path.join(os.path.dirname(ig_pkg_dir), "irongantry.py")

        bundle_files = {
            "irongantry/__init__.py": os.path.join(ig_pkg_dir, "__init__.py"),
            "irongantry/validate.py": os.path.join(ig_pkg_dir, "validate.py"),
            "irongantry/engine.py": os.path.join(ig_pkg_dir, "engine.py"),
            "irongantry/cli.py": os.path.join(ig_pkg_dir, "cli.py"),
            "irongantry.py": ig_entry,
        }

        bootstrap_src = (
            '"""Bootstrap: build environment and run the app. Requires Python 3.11+."""\n'
            "import subprocess, sys, os\n"
            "os.chdir(os.path.dirname(os.path.abspath(__file__)))\n"
            'subprocess.run([sys.executable, "irongantry.py", "build"], check=True)\n'
            'subprocess.run([sys.executable, "irongantry.py", "run"], check=True)\n'
        )

        with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add user project files
            for root, dirs, files in os.walk("."):
                # Prune excluded directories in-place
                dirs[:] = [
                    d for d in dirs
                    if d not in exclude_dirs and not d.startswith(".")
                ]
                for f in files:
                    if f.endswith(exclude_suffixes):
                        continue
                    if f.endswith("_shipped.zip"):
                        continue
                    filepath = os.path.join(root, f)
                    arcname = os.path.normpath(filepath)
                    zf.write(filepath, arcname)

            # Bundle IronGantry package
            for arcname, src_path in bundle_files.items():
                if os.path.isfile(src_path):
                    zf.write(src_path, arcname)

            # Generate bootstrap.py
            zf.writestr("bootstrap.py", bootstrap_src)

        print(f"Shipped: {filename}")
        return filename
