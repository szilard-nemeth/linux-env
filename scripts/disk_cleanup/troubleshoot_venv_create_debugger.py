import os
import venv
import subprocess
import tempfile
from pathlib import Path


def create_and_diagnose():
    temp_path = tempfile.mkdtemp(prefix="venv_diag_")
    venv_dir = Path(temp_path) / "test_venv"

    # 1. Scrub the environment
    clean_env = os.environ.copy()
    # These are the usual suspects that break venv creation in debuggers
    blocked_keys = ["PYTHONPATH", "PYTHONHOME", "PYDEVD_USE_CYTHON", "LIBRARY_PATH"]

    print("📋 Current environment status (subset):")
    for key in blocked_keys:
        val = os.environ.get(key, "NOT SET")
        print(f"  {key}: {val}")
        clean_env.pop(key, None)

    print(f"\n🛠 Attempting to create venv at: {venv_dir}")

    try:
        # Fixed: Removed the non-existent 'with_scm'
        builder = venv.EnvBuilder(with_pip=False)
        builder.create(venv_dir)

        # Determine the python path inside the new venv
        python_exe = venv_dir / "bin" / "python"

        # _call_ensurepip1(clean_env, python_exe)
        _call_ensurepip2(python_exe)

    except Exception as e:
        print(f"\n❌ Builder failed during creation: {e}")
        import traceback

        traceback.print_exc()


def _call_ensurepip1(clean_env: dict[str, str], python_exe: Path):
    print(f"🔍 Running manual ensurepip via {python_exe}...")

    # 2. Run ensurepip with the scrubbed environment
    result = subprocess.run(
        [str(python_exe), "-Im", "ensurepip", "--upgrade", "--default-pip"],
        env=clean_env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("\n❌ ENSUREPIP FAILED")
        print("--- STDOUT ---")
        print(result.stdout if result.stdout else "(empty)")
        print("--- STDERR ---")
        print(result.stderr if result.stderr else "(empty)")
    else:
        print("\n✅ Success! Pip installed correctly.")


def _call_ensurepip2(python_exe: Path):
    # 1. Create a truly minimal environment
    # We only keep PATH so the system knows where basic commands are
    minimal_env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # Needed for Windows
        "HOME": os.environ.get("HOME", ""),  # Needed for macOS/Linux
    }

    # 2. Use the -I flag (Isolated mode)
    # This ignores all PYTHON* environment variables and user site-packages
    _ = subprocess.run(
        [str(python_exe), "-I", "-m", "ensurepip", "--upgrade", "--default-pip"],
        env=minimal_env,
        capture_output=True,
        text=True,
    )


if __name__ == "__main__":
    create_and_diagnose()
