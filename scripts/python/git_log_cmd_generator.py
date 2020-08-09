#!/usr/bin/python
import argparse

__author__ = 'Szilard Nemeth'

####TEST COMMANDS & RESULTS
# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --grep grepas "Gergo Repas" --oneline --count
# git log --grep grepas --grep Gergo Repas --oneline | wc -l

# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --grep snemeth Szilard  'Szilard Nemeth' --oneline --count --final-grep 'YARN\|SUBMARINE\|HADOOP'
# git log --grep snemeth --grep Szilard --grep Szilard Nemeth --oneline | grep YARN\|SUBMARINE\|HADOOP | wc -l

# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --grep snemeth Szilard  'Szilard Nemeth' --oneline --final-grep 'YARN\|SUBMARINE\|HADOOP'
# git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | grep YARN\|SUBMARINE\|HADOOP

# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --grep snemeth Szilard  'Szilard Nemeth' --oneline --count
# git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | wc -l

# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --authors "snemeth@apache.org" --oneline --count
# git log --author snemeth@apache.org --oneline | wc -l


# alias upstream-yarn2="echo $(($(git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | grep YARN | wc -l | tr -s ' ' | cut -d ' ' -f2) + $(git log --author=snemeth --oneline | wc -l | tr -s ' ' | cut -d ' ' -f2)))"
# THIS IS A COMBINED COMMAND:
# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --grep snemeth Szilard  'Szilard Nemeth' --oneline --count --trim-count
# git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | wc -l | tr -s ' ' | cut -d ' ' -f2
# ++ 
# python3 /Users/szilardnemeth/development/my-repos/linux-env/scripts/git_log_cmd_generator.py --author snemeth --oneline --count --trim-count
# git log --author snemeth --oneline | wc -l | tr -s ' ' | cut -d ' ' -f2

def parse_args():
    """This function parses and return arguments passed in"""

    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--grep", nargs='+', type=str, dest='grep', help="Grep for these strings", required=False)
    parser.add_argument("-o", "--oneline", dest='oneline', action='store_true', required=False, default=True, help="Whether to use git log --oneline",)
    parser.add_argument("-a", "--author", dest='author', type=str, required=False, default=False, help="Grep for authors")
    parser.add_argument("-c", "--committer", dest='committer', type=str, required=False, default=False, help="Grep for committers")
    parser.add_argument("-C", "--count", dest='count', action='store_true', required=False, default=False, help="Whether to return count of commits")
    parser.add_argument("-tc", "--trim-count", dest='trim_count', action='store_true', required=False, default=False, help="Whether to trim whitespaces from count output")
    parser.add_argument("-fg", "--final-grep", dest='final_grep', type=str, required=False, help="Whether to apply a final grep for the command")
    parser.add_argument("-v", "--verbose", dest='verbose', action='store_true', required=False, help="Verbose logging")

    args = parser.parse_args()
    if not args.grep and not args.author and not args.committer:
        raise ValueError("Either grep, committer or author must be specified as argument!")
    if not args.count and args.trim_count:
        raise ValueError("--trim-count can only be used if --count is specified!")

    if args.verbose:
        print("args: " + str(args))
    return args


def convert_args(option, list):
    def put_to_string(s):
        if " " in s:
            return "'" + s + "'"
        return s
    if not list:
        return ''
    if isinstance(list, str):
        list = [list]

    result = ' '.join(["--" + option + " " + put_to_string(g) for g in list])

    if args.verbose:
        print("Converted args for option '{}': '{}'".format(option, list))
    return result


if __name__ == '__main__':
    args = parse_args()
    
    cmd = "git log "
    cmd += convert_args("grep", args.grep)
    cmd += convert_args("author", args.author)
    cmd += " --oneline" if args.oneline else ""
    cmd += " | grep {}".format("'" + args.final_grep + "'") if args.final_grep else ""
    cmd += " | wc -l" if args.count else ""
    cmd += " | tr -s ' ' | cut -d ' ' -f2" if args.trim_count else ""
    print(cmd)
