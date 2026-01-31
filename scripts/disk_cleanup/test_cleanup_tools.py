from typing import List

from generate_dummy_data import create_real_test_env
from scripts.disk_cleanup.cleanup_disk import CleanupTool, AsdfGolangCleanup, DiscoveryCleanup


def main():
    base_dir = create_real_test_env()

    tools: List[CleanupTool] = [
        # MavenCleanup(), # (From your original code)
        # AsdfGolangCleanup(keep_versions=["1.24.11"]),
        # DockerCleanup(),
        DiscoveryCleanup("Python Venvs", base_dir, ["venv", ".venv"]),
        # DiscoveryCleanup("Terraform", DEVELOPMENT_ROOT, [".terraform"]),
        # DiscoveryCleanup("Pip Cache", "~/Library/Caches/pip", ["*"]),
        # PoetryCacheCleanup()
    ]
    for tool in tools:
        tool.prepare()
        tool.execute()
        _ = tool.verify()
        tool.print_summary()
        print("-" * 30)


if __name__ == "__main__":
    main()
