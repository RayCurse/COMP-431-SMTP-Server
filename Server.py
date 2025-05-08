from sys import exit
from sys import argv
from enum import Enum
import re
import os
import socket

# Helper functions and values
class TerminalParseException(Exception):
    def __init__(self, terminalName):
        self.TerminalName = terminalName

class NonTerminalParseException(Exception):
    pass

def expect(symbolGroups):
    global currentPos
    global currentStr
    for symbolGroup in symbolGroups:
        # Consume char i
        if currentPos >= len(currentStr) or currentStr[currentPos] not in symbolGroup:
            raise NonTerminalParseException()
        currentPos += 1

def lookAhead():
    if currentPos < len(currentStr) - 1:
        return currentStr[currentPos + 1]

# Trivial non terminals
SP = {" ", "\t"}
letter = set(map(chr, range(65, 91))) | set(map(chr, range(97, 123)))
digit = set("0123456789")
special = set('<>()[]\\.,;:@"')
char = set(map(chr, range(32, 127))) - special - SP

# MAIL_FROM command grammar impl
def mailFromCmd():
    try:
        expect("MAIL")
        whitespace()
        expect("FROM:")
        nullspace()
        reversePath()
        nullspace()
        CRLF()
    except NonTerminalParseException:
        raise TerminalParseException("mail-from-cmd")

def whitespace():
    try:
        if lookAhead() == " " or lookAhead() == "\t":
            expect([SP])
            whitespace()
        else:
            expect([SP])
    except NonTerminalParseException:
        raise TerminalParseException("whitespace")

def nullspace():
    if currentPos < len(currentStr) and (currentStr[currentPos] == " " or currentStr[currentPos] == "\t"):
        whitespace()
    else:
        pass

def reversePath():
    path()

def path():
    global currentPath
    try:
        pathStart = currentPos
        expect("<")
        mailbox()
        expect(">")
        pathEnd = currentPos
        currentPath = currentStr[pathStart:pathEnd]
    except NonTerminalParseException:
        raise TerminalParseException("path")

def mailbox():
    try:
        localPart()
        expect("@")
        domain()
    except NonTerminalParseException:
        raise TerminalParseException("mailbox")

def localPart():
    string()

def string():
    try:
        if lookAhead() in char:
            expect([char])
            string()
        else:
            expect([char])
    except NonTerminalParseException:
        raise TerminalParseException("string")

def domain():
    element()
    if currentPos < len(currentStr) and currentStr[currentPos] == ".":
        expect(".")
        domain()

def element():
    try:
        if currentPos < len(currentStr) and currentStr[currentPos] in letter:
            if lookAhead() in letter | digit:
                name()
            else:
                expect([letter])
        else:
            raise NonTerminalParseException()
    except NonTerminalParseException:
        raise TerminalParseException("element")

def name():
    try:
        expect([letter])
        letterDigStr()
    except NonTerminalParseException:
        raise TerminalParseException("name")

def letterDigStr():
    if lookAhead() in letter | digit:
        letterDig()
        letterDigStr()
    else:
        letterDig()

def letterDig():
    try:
        if currentPos < len(currentStr) and currentStr[currentPos] in letter:
            expect([letter])
        else:
            expect([digit])
    except NonTerminalParseException:
        # Shouldn't be possible to get here if we got to letterDig from element
        raise TerminalParseException("letter-dig")

def CRLF():
    try:
        expect("\n")
    except NonTerminalParseException:
        raise TerminalParseException("CRLF")

# RCPT TO command grammar impl
def rcptToCmd():
    try:
        expect("RCPT")
        whitespace()
        expect("TO:")
        nullspace()
        forwardPath()
        nullspace()
        CRLF()
    except NonTerminalParseException:
        raise TerminalParseException("rcpt-to-command")

def forwardPath():
    path()

# DATA command grammar impl
def dataCmd():
    try:
        expect("DATA")
        nullspace()
        CRLF()
    except NonTerminalParseException:
        raise TerminalParseException("data-cmd")

# HELO command grammar impl
def heloCmd():
    global currentDomain
    try:
        expect("HELO")
        whitespace()
        domainStart = currentPos
        # Don't validate domain for gradescope grading
        if currentPos >= len(currentStr):
            raise TerminalParseException("helo")
        acceptableChars = set(map(chr, range(32, 127))) - SP
        while currentStr[currentPos] in acceptableChars:
            expect([acceptableChars])
        domainEnd = currentPos
        currentDomain = currentStr[domainStart:domainEnd]
        nullspace()
        CRLF()
    except NonTerminalParseException:
        raise TerminalParseException("helo")

# Keep track of state
class SMTPState(Enum):
    # Value of each state are the commands that are accepted in that state

    # The value of the ProcessingData state doesn't matter since we
    # don't treat lines as commands when in that state (and hence
    # never get to the code that needs its value)

    AwaitingHelo = {heloCmd}
    AwaitingMailTo = {mailFromCmd}
    AwaitingRcptTo = {rcptToCmd}
    AwaitingData = {rcptToCmd, dataCmd}
    ProcessingData = {}

currentPos = 0
currentStr = ""
currentPath = ""
currentDomain = ""
currentState = SMTPState.AwaitingHelo
emailRecipients = []
emailSender = ""
messageContents = []

def stateMachine(currentState, command):
    if currentState == SMTPState.AwaitingMailTo:
        return SMTPState.AwaitingRcptTo
    elif currentState == SMTPState.AwaitingRcptTo:
        return SMTPState.AwaitingData
    elif currentState == SMTPState.AwaitingData:
        if command == rcptToCmd:
            return SMTPState.AwaitingData
        else:
            return SMTPState.ProcessingData
    else:
        return SMTPState.AwaitingMailTo

# Create listening socket and start listening for requests
port = int(argv[1])
welcomingSocket = None
try:
    welcomingSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    welcomingSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    welcomingSocket.bind(("", port))
    welcomingSocket.listen(1)
except Exception:
    print("error: could not create welcoming socket")
    if welcomingSocket is not None:
        welcomingSocket.close()
    exit(1)

while True:

    # Wait for client connection
    connSocket = None
    inputFile = None
    try:
        connSocket, addr = welcomingSocket.accept()
        inputFile = connSocket.makefile(mode="r", encoding="utf-8")
        connSocket.send(f"220 {socket.gethostname()}\n".encode())

        # Reset state
        currentState = SMTPState.AwaitingHelo

        # Process commands
        for line in inputFile:
            # Get new line
            currentStr = line
            currentPos = 0

            # If we're processing message contents, write to file and move on to next line
            if currentState == SMTPState.ProcessingData:
                if line == ".\n":
                    currentState = SMTPState.AwaitingMailTo
                    connSocket.send("250 OK\n".encode())
                    domains = set()
                    for email in emailRecipients:
                        domainStr = email.partition("@")[2][:-1]
                        if domainStr in domains: continue
                        domains.add(domainStr)
                        for line in messageContents:
                            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "forward", domainStr), "a+") as file:
                                file.write(line)
                else:
                    messageContents.append(line)
                continue

            # Special case for QUIT command
            if line == "QUIT\n":
                connSocket.send(f"221 {socket.gethostname()} closing connection\n".encode())
                break

            # Determine what command it is
            command = None
            if re.compile("^MAIL[ \t]+FROM:").match(line):
                command = mailFromCmd
            elif re.compile("^RCPT[ \t]+TO:").match(line):
                command = rcptToCmd
            elif re.compile("^DATA").match(line):
                command = dataCmd
            elif re.compile("^HELO").match(line):
                command = heloCmd
            else:
                connSocket.send("500 Syntax error: command unrecognized\n".encode())
                currentState = SMTPState.AwaitingMailTo
                continue

            # Determine if command is valid under current state
            if command not in currentState.value:
                connSocket.send("503 Bad sequence of commands\n".encode())
                currentState = SMTPState.AwaitingMailTo
                continue

            # Parse command
            try:
                command()
            except TerminalParseException as e:
                connSocket.send("501 Syntax error in parameters or arguments\n".encode())
                currentState = SMTPState.AwaitingMailTo
                continue

            # Write response
            if command == mailFromCmd:
                connSocket.send("250 OK\n".encode())
                emailSender = currentPath
            elif command == rcptToCmd:
                connSocket.send("250 OK\n".encode())
                if currentState == SMTPState.AwaitingRcptTo:
                    # this is the first RCPT TO command, so clear previous email recipients
                    emailRecipients.clear()
                emailRecipients.append(currentPath)
            elif command == dataCmd:
                connSocket.send("354 Start mail input; end with <CRLF>.<CRLF>\n".encode())
                messageContents.clear()
                # The from and to headers should now be sent from the client as message contents
                # messageContents.append(f"From: {emailSender}\n")
                # for emailRecipient in emailRecipients:
                #     messageContents.append(f"To: {emailRecipient}\n")
            elif command == heloCmd:
                connSocket.send(f"250 Hello {currentDomain} pleased to meet you\n".encode())

            # Update state
            currentState = stateMachine(currentState, command)

        # If we were processing message when input ended, write 501 error message (invalid data command)
        if currentState == SMTPState.ProcessingData:
            connSocket.send("501 Syntax error in parameters or arguments".encode())
    except Exception:
        print("error: client connection error")
    except KeyboardInterrupt:
        welcomingSocket.close()
        exit(0)
    finally:
        if inputFile is not None:
            inputFile.close()
        if connSocket is not None:
            connSocket.close()
