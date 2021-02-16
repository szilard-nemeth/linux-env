import logging
import shlex
import subprocess

from pythoncommons.file_utils import FileUtils
from pythoncommons.string_utils import auto_str, StringUtils

LOG = logging.getLogger(__name__)


@auto_str
class RegularCommandResult:
    def __init__(self, cli_cmd, args, stdout, stderr, exit_code):
        self.cli_cmd = cli_cmd
        self.args = args
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code


class CommandRunner:
    @staticmethod
    def run(command, shell=False, shlex_split=True):
        if shlex_split:
            args = shlex.split(command)
        else:
            args = command
        proc = subprocess.run(
            args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell
        )
        args2 = str(proc.args)
        return RegularCommandResult(command, args2, proc.stdout, proc.stderr, proc.returncode)

    @staticmethod
    def getoutput(command, raise_on_error=True):
        statusoutput = subprocess.getstatusoutput(command)
        if raise_on_error and statusoutput[0] != 0:
            raise ValueError("Command failed with exit code %d. Command was: %s", statusoutput[0], command)
        return statusoutput[1]

    @staticmethod
    def egrep_with_cli(git_log_result, file, piped_jira_ids):
        FileUtils.save_to_file(file, StringUtils.list_to_multiline_string(git_log_result))
        cli_command = f"cat {file} | egrep '{piped_jira_ids}'"
        return CommandRunner.run_cli_command(cli_command)

    @staticmethod
    def run_cli_command(cli_command, fail_on_empty_output=True, print_command=True, fail_on_error=True):
        if print_command:
            LOG.info("Running CLI command: %s", cli_command)
        output = CommandRunner.getoutput(cli_command, raise_on_error=fail_on_error)
        if fail_on_empty_output and not output:
            raise ValueError("Command failed: %s", cli_command)
        return output
