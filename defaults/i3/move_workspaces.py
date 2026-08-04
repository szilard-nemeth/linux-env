import i3
import sys

activeOutputs = filter(lambda x: x["active"], i3.get_outputs())
try:
    primaryOutput = filter(lambda x: x["primary"], activeOutputs)[0]
except IndexError:
    primaryOutput = None
currentWorkspace = filter(lambda x: x["focused"], i3.get_workspaces())[0]
currentOutput = filter(lambda x: x["current_workspace"] == currentWorkspace["name"], activeOutputs)[0]
otherOutputs = filter(lambda x: x["name"] != currentOutput["name"], activeOutputs)

# if there is a primary screen move to it,
# else move to the first other output (if there is one)
if primaryOutput:
    i3.move("workspace to output", primaryOutput["name"])
elif len(otherOutputs) > 0:
    i3.move("workspace to output", otherOutputs[0]["name"])
