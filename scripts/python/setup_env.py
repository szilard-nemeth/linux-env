import os
import logging
from dataclasses import dataclass, field
from typing import List

import sh

LOG = logging.getLogger(__name__)


@dataclass
class InstallableProgram:
    name: str
    checker_cmd: str
    install_cmd: str
    ignore_stdout: bool = True
    ignore_stderr: bool = True
    additional_commands: List[str] = field(default_factory=list)


class LinuxEnvSetup:
    def run_process(self, command, log=True, log_result=True):
        if log:
            LOG.info("executing: {}".format(command))
        pipe = os.popen(command)
        result = pipe.read()
        if log_result:
            logging.info(result)
        return result

    def ensure_program_installed(self, program):
        # TODO use program.ignore_stdout, program._ignore_stderr
        LOG.info("Checking whether %s is installed...", program.name)
        res = sh.bash(c=program.checker_cmd)
        LOG.debug("process result: %s", res)
        if res.exit_code != 0:
            LOG.info("%s not found! Installing %s", program.name)
            sh.bash(c=program.install_cmd)
        else:
            LOG.info("%s already installed.")

    def initial_setup_macos(self):
        LOG.info("=== Running initial macOS setup ===")
        programs = [
            InstallableProgram(
                "Homebrew",
                "hash brew",
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"',
                ignore_stderr=True,
            ),
            InstallableProgram(
                "GNU sed",
                "echo \"123 abc\" | sed -r 's/[0-9]+/& &/'",
                "brew install gnu-sed --with-default-names",
                ignore_stderr=True,
            ),
            InstallableProgram(
                "npm",
                "hash node",
                "brew install node",
                additional_commands=["which node # => /usr/local/bin/node", 'mkdir "${HOME}/.npm-packages"'],
            ),
            InstallableProgram(
                "figlet", "npm list -g figlet-cli", "npm install -g figlet-cli", ignore_stderr=True, ignore_stdout=True
            ),
            InstallableProgram(
                "gettext",
                "brew list gettext",
                "brew install gettext",
                ignore_stdout=True,
                ignore_stderr=True,
                additional_commands=["brew link --force gettext"],
            ),
        ]
        for p in programs:
            self.ensure_program_installed(p)

    # TODO how to source scripts? https://unix.stackexchange.com/questions/246813/unable-to-use-source-command-within-python-script

    def logging_setup(self):
        # set up logging to file
        logging.basicConfig(
            filename="log_file_name.log",
            level=logging.INFO,
            format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )

        # set up logging to console
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        # set a format which is simpler for console use
        formatter = logging.Formatter("%(message)s")
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.getLogger("").addHandler(console)

    def do_setup(self):
        self.logging_setup()
        self.initial_setup_macos()


if __name__ == "__main__":
    setup = LinuxEnvSetup()
    setup.do_setup()
