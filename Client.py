
import socket
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
serverName = sys.argv[1]
port = int(sys.argv[2])
clientSocket = None
try:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((serverName, port))
    clientSocket.send(f"MAIL FROM: <{sender}>\n".encode())
    for recipient in recipients:
        clientSocket.send(f"RCPT TO: <{recipient}>\n".encode())
    clientSocket.send(f"DATA\n".encode())
    for dataLine in data:
        clientSocket.send(dataLine.encode())
    clientSocket.send(".\n".encode())
    clientSocket.send("QUIT\n".encode())
except socket.error:
    print("error: could not connect to server")
    sys.exit(1)
finally:
    if clientSocket is not None:
        clientSocket.close()
