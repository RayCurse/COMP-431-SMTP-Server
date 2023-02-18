
from sys import argv
from sys import stderr
from enum import Enum
import os
import re

class ForwardFilesState(Enum):
    Sender = 0
    FirstRecipient = 1
    Recipient = 2
    Data = 3

def getPath(s):
    match = re.compile("(<.+>)").search(s)
    if match == None: return None
    return match.groups(0)[0]

def sendReq(req, kwargs):
    print(req, kwargs)
    res = input()
    print(res, file=stderr)

    if not (res.startswith("250") or res.startswith("354")):
        print("QUIT")
        exit()

# Parse forward file
path = argv[1]
if not os.path.isabs(path):
    path = os.path.join(os.path.dirname(__file__), path)
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

# Write commands to SMTP server
for message in messages:
    sendReq(f'MAIL FROM: {message["sender"]}')
    for recipient in message["recipients"]:
        sendReq(f'RCPT TO: {recipient}')
    sendReq(f'DATA')
    for dataLine in message["data"]:
        print(dataLine, end="")
    sendReq(".")
print("QUIT")
