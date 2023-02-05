from sys import argv
from enum import Enum
import re

class ForwardFilesState(Enum):
    Sender = 0
    FirstRecipient = 1
    Recipient = 2
    Data = 3

def getPath(s):
    match = re.compile("<(.+)>").search(s)
    if match == None: return None
    return match.groups(1)

forwardFile = open(argv[1])
messages = []
currentMessage = -1
state = ForwardFilesState.Sender

for line in forwardFile:
    if line.startswith("From:"):
        state = ForwardFilesState.Sender
    if state == ForwardFilesState.Sender:
        currentMessage += 1
        messages.append({
            "sender" : getPath(line),
            "recipients" : [],
            "data" : []
        })
        state = ForwardFilesState.Recipient
    elif state == ForwardFilesState.Recipient:
        recipient = getPath(line)
        if recipient:
            messages[currentMessage]["recipients"].append(recipient)
        else:
            state = ForwardFilesState.Data
            messages[currentMessage]["data"].append(line)
    elif state == ForwardFilesState.Data:
        messages[currentMessage]["data"].append(line)

