import os
import subprocess
import tempfile
import venv
from pathlib import Path
from typing import Any, Union


def create_real_test_env(venv=True, terraform=True):
    results = {}
    if venv:
        results["venv_basedir"] = _create_venvs()
    if terraform:
        results["terraform_basedir"] = _create_terraform_test_setup()
    return results


def _create_venvs() -> Path:
    # Create a persistent temp directory
    temp_path = tempfile.mkdtemp(prefix="venv_real_test_")
    base_dir = Path(temp_path)
    print(f"🚀 Creating real environments in: {base_dir}")

    # Configuration: folder_name -> list of packages to pip install
    test_setups = {
        "project_alpha/venv": ["requests", "flask"],
        "data_science_project/venv": ["numpy"],
        "data_science_project2/.venv": ["numpy"],
        "micro_service/test_env": [],  # Empty venv (only pip/setuptools)
    }

    for folder, packages in test_setups.items():
        venv_dir = base_dir / folder
        print(f"📦 Setting up {folder}...")
        # _create_venv(packages, venv_dir)
        _create_venv_debugger_compatible(packages, venv_dir)

    # 4. Create a "fake" one that should NOT be deleted
    fake_path = base_dir / "user_documents/not_a_venv"
    fake_path.mkdir(parents=True, exist_ok=True)
    (fake_path / "important.txt").write_text("Don't delete me!")

    print(f"\n✅ Done! Your test sandbox is ready at: {base_dir}")
    print(f"Total environments created: {len(test_setups)}")
    return base_dir


def _create_venv(packages: Union[list[str], list[Any]], venv_dir: Path):
    # 1. Create the actual virtual environment
    venv.create(venv_dir, with_pip=True)

    # 2. Determine the path to the pip executable (Windows vs Unix)
    pip_exe = _determine_pip_executable(venv_dir)

    # Fix for debugger
    minimal_env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # Needed for Windows
        "HOME": os.environ.get("HOME", ""),  # Needed for macOS/Linux
    }

    # 3. Install packages if any are listed
    if packages:
        subprocess.check_call([str(pip_exe), "install"] + packages, stdout=subprocess.DEVNULL, env=minimal_env)


def _determine_pip_executable(venv_dir: Path) -> Path:
    if os.name == "nt":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"
    return pip_exe


class IsolatedEnvBuilder(venv.EnvBuilder):
    def __init__(self, custom_env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_env = custom_env

    def post_setup(self, context):
        """
        This is called after the venv is created.
        We manually trigger ensurepip here with the clean environment.
        """
        print(f"DEBUG: Bootstrapping pip for {context.env_dir}")
        # -I ignores all PYTHON environment variables and parent flags
        cmd = [context.env_exe, "-I", "-m", "ensurepip", "--upgrade", "--default-pip"]

        result = subprocess.run(cmd, env=self.custom_env, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Pip install failed: {result.stderr}")


def _create_venv_debugger_compatible(packages: Union[list[str], list[Any]], venv_dir: Path):
    # 1. Define the minimal environment
    minimal_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    }

    # 2. Initialize with with_pip=False because we handle it in post_setup
    builder = IsolatedEnvBuilder(custom_env=minimal_env, with_pip=False)

    # 3. Create the venv
    builder.create(venv_dir)

    pip_exe = _determine_pip_executable(venv_dir)

    if packages:
        subprocess.check_call([str(pip_exe), "install"] + packages, stdout=subprocess.DEVNULL, env=minimal_env)


def _create_terraform_test_setup():
    temp_path = tempfile.mkdtemp(prefix="tf_cleanup_test_")
    base_dir = Path(temp_path)

    # Structure: Project Folder -> Hidden Dir -> Dummy Files (with simulated sizes)
    tf_projects = {
        "infra_production": {
            ".terraform/providers/registry.terraform.io/hashicorp/aws/5.0.0/darwin_arm64/terraform-provider-aws_v5.0.0_x5": 250,  # MB
            ".terraform/modules/vpc/main.tf": 0.01,
            "main.tf": 0.01,
            ".terraform.lock.hcl": 0.01,
        },
        "dev_sandbox": {
            ".terraform/providers/registry.terraform.io/hashicorp/random/3.5.1/darwin_arm64/terraform-provider-random_v3.5.1_x5": 20,  # MB
            "main.tf": 0.01,
        },
        "archive_project_2024": {
            ".terraform/providers/registry.terraform.io/hashicorp/google/4.0.0/darwin_arm64/terraform-provider-google_v4.0.0_x5": 180,  # MB
            "main.tf": 0.01,
        },
    }

    for project, files in tf_projects.items():
        for file_path, size_mb in files.items():
            full_path = base_dir / project / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Create a "heavy" file to test disk space reporting
            with open(full_path, "wb") as f:
                f.seek(int(size_mb * 1024 * 1024) - 1)
                f.write(b"\0")

    print(f"🏗️ Terraform sandbox created at: {base_dir}")
    return base_dir


if __name__ == "__main__":
    create_real_test_env()
