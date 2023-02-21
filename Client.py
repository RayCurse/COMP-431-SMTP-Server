
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

class SMTPException(Exception):
    def __init__(self, code):
        self.code = code
    pass
def assertSMTPResponseCode(response, code):
    if not response.startswith(str(code)):
        raise SMTPException(response[:3])

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
inputFile = None
try:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    inputFile = clientSocket.makefile(mode="r", encoding="utf-8")
    clientSocket.connect((serverName, port))
    assertSMTPResponseCode(inputFile.readline(), 220)
    clientSocket.send(f"HELO {socket.gethostname()}\n".encode())
    assertSMTPResponseCode(inputFile.readline(), 250)
    clientSocket.send(f"MAIL FROM: <{sender}>\n".encode())
    assertSMTPResponseCode(inputFile.readline(), 250)
    for recipient in recipients:
        clientSocket.send(f"RCPT TO: <{recipient}>\n".encode())
        assertSMTPResponseCode(inputFile.readline(), 250)
    clientSocket.send(f"DATA\n".encode())
    assertSMTPResponseCode(inputFile.readline(), 354)
    clientSocket.send(f"From: <{sender}>\n".encode())
    clientSocket.send(f"To: ".encode())
    for i, recipient in enumerate(recipients):
        clientSocket.send(f"<{recipient}>".encode())
        if i < len(recipients) - 1:
            clientSocket.send(", ".encode())
    clientSocket.send(f"\nSubject: {subject}\n\n".encode())
    for dataLine in data:
        clientSocket.send(dataLine.encode())
    clientSocket.send(".\n".encode())
    assertSMTPResponseCode(inputFile.readline(), 250)
    clientSocket.send("QUIT\n".encode())
    assertSMTPResponseCode(inputFile.readline(), 221)
except socket.error:
    print("error: could not connect to server")
    sys.exit(1)
except SMTPException as e:
    print(f"error: SMTP protocol error {e.code}")
    sys.exit(1)
except Exception:
    print("error: unexpected error")
    sys.exit(1)
finally:
    if inputFile is not None:
        inputFile.close()
    if clientSocket is not None:
        clientSocket.close()
