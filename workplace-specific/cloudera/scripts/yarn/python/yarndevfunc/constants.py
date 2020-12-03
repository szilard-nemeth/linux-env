APACHE = "apache"
HEAD = "HEAD"
ORIGIN_TRUNK = "origin/trunk"
ORIGIN = "origin"
FETCH_HEAD = "FETCH_HEAD"
TRUNK = "trunk"
BRANCH_3_1 = "branch-3.1"
GERRIT_REVIEWER_LIST = "r=shuzirra,r=pbacsko,r=kmarton,r=gandras,r=bteke"
ENV_CLOUDERA_HADOOP_ROOT = "CLOUDERA_HADOOP_ROOT"
ENV_HADOOP_DEV_DIR = "HADOOP_DEV_DIR"

# Do not leak bad ENV variable namings into the python code
LOADED_ENV_UPSTREAM_DIR = "upstream-hadoop-dir"
LOADED_ENV_DOWNSTREAM_DIR = "downstream-hadoop-dir"
PROJECT_NAME = "yarn_dev_func"
DEST_DIR_PREFIX = "test"
HADOOP_REPO_TEMPLATE = "https://github.com/{user}/hadoop.git"
HADOOP_REPO_APACHE = HADOOP_REPO_TEMPLATE.format(user=APACHE)
COMMIT_FIELD_SEPARATOR = " "

# Patch constants
YARN_PATCH_FILENAME_REGEX = ".*(YARN-[0-9]+).*\\.patch"
PATCH_FILE_REGEX = "\\.\\d.*\\.patch$"
PATCH_EXTENSION = ".patch"
FIRST_PATCH_NUMBER = "001"
