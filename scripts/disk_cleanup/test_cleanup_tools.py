import os
from pathlib import Path
from typing import List

from generate_dummy_data import create_real_test_env
from scripts.disk_cleanup.cleanup_disk import (
    CleanupTool,
    AsdfGolangCleanup,
    DiscoveryCleanup,
    PoetryCacheCleanup,
    MavenCleanup,
    DockerCleanup,
    ToolRunner,
)

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))


def main():
    results = create_real_test_env(venv=True, terraform=True)

    tools: List[CleanupTool] = [
        MavenCleanup(),  # (From your original code)
        AsdfGolangCleanup(keep_versions=["1.24.11"]),
        DockerCleanup(),
        DiscoveryCleanup("Python Venvs", results["venv_basedir"], ["venv", ".venv"]),
        DiscoveryCleanup("Terraform", results["terraform_basedir"], [".terraform"], age_days=-1),
        # DiscoveryCleanup("Terraform", results["terraform_basedir"], [".terraform"], age_days=30),
        # DiscoveryCleanup("Pip Cache", "~/Library/Caches/pip", ["*"]),
        PoetryCacheCleanup(),
    ]
    ToolRunner.run_tools(tools)


if __name__ == "__main__":
    main()
