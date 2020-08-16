import shlex
import subprocess

from utils import auto_str


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
        proc = subprocess.run(args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        args2 = str(proc.args)
        return RegularCommandResult(command, args2, proc.stdout, proc.stderr, proc.returncode)

    @staticmethod
    def getoutput(command, raise_on_error=True):
        statusoutput = subprocess.getstatusoutput(command)
        if raise_on_error and statusoutput[0] != 0:
            raise ValueError("Command failed with exit code %d. Command was: %s", statusoutput[0], command)
        return statusoutput[1]
