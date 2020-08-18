from os import path
from io import open
import re
from setuptools import setup, find_packages

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(this_directory, "version.py")) as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    version = version_match.group(1)

with open('LICENSE') as f:
    license = f.read()

setup(
    name="yarn-dev-func",
    version=version,
    author="Szilard Nemeth",
    author_email="szilard.nemeth88@gmail.com",
    description="YARN and git developer functions / helper scripts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/szilard-nemeth/linux-env",
    packages=find_packages(exclude=["tests"]),
    tests_require=["pytest"],
    install_requires=[],
    extras_require={
        "myst": ["myst-parser~=0.8; python_version >= '3.6'"],
        "toml": ["toml"],
    },
    license=license,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Topic :: Developer helper scripts",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
    ],
)