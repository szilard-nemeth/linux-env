import i3
import sys

activeOutputs = filter(
    lambda x: x[u'active'],
    i3.get_outputs())
try:
    primaryOutput = filter(
        lambda x: x[u'primary'],
        activeOutputs)[0]
except IndexError:
    primaryOutput = None
currentWorkspace = filter(
    lambda x: x[u'focused'],
    i3.get_workspaces())[0]
currentOutput = filter(
    lambda x: x[u'current_workspace'] == currentWorkspace[u'name'], 
    activeOutputs)[0]
otherOutputs = filter(
    lambda x: x[u'name'] != currentOutput[u'name'], 
    activeOutputs)

# if there is a primary screen move to it, 
# else move to the first other output (if there is one)
if primaryOutput:
    i3.move('workspace to output', primaryOutput[u'name']
elif len(otherOutputs) > 0:
    i3.move('workspace to output', otherOutputs[0][u'name']
