
import sys
import re

# Helper functions
def isPath(s):
    localPartRegularExpr = r'((?![<>()[\]\\.,:;@"\s\t])[ -~])+'
    domainRegularExpr = r'([a-zA-Z][a-zA-Z0-9]*\.)*[a-zA-Z][a-zA-Z0-9]*'
    pathRegularExpr = localPartRegularExpr + "@" + domainRegularExpr
    return re.fullmatch(pathRegularExpr, s) is not None

def getPaths(s):
    paths = re.split(r",[\s]?", s)
    for path in paths:
        if not isPath(path): return None
    return paths

# Get user input
sender = input("From:\n")
while not isPath(sender):
    print("invalid sender")
    sender = input("From:\n")

recipients = getPaths(input("To:\n"))
while recipients is None:
    print("invalid list of recipients")
    recipients = getPaths(input("To:\n"))

subject = input("Subject:\n")
print("Message:")
data = []
while True:
    line = sys.stdin.readline()
    if line == ".\n": break
    data.append(line)

# Write commands to SMTP server
print(f'MAIL FROM: <{sender}>')
for recipient in recipients:
    print(f'RCPT TO: <{recipient}>')
print(f'DATA')
for dataLine in data:
    print(dataLine, end="")
print(".")
print("QUIT")
