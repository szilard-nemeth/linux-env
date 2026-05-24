if [ -n "${ZSH_VERSION:-}" ]; then
    _GIT_SH_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
else
    _GIT_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

function test_zsh_source {
    echo "dir: $_GIT_SH_DIR"
}
