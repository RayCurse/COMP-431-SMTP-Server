



from sys import stdin
import re
from enum import Enum

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
    try:
        expect("<")
        mailbox()
        expect(">")
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

# Keep track of state
class SMTPState(Enum):
    AwaitingMailTo = {mailFromCmd}
    AwaitingRcptTo = {rcptToCmd}
    AwaitingData = {rcptToCmd, dataCmd}
    ProcessingData = {}

currentPos = 0
currentStr = ""
currentState = SMTPState.AwaitingMailTo

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
    elif currentState == SMTPState.ProcessingData:
        return SMTPState.AwaitingMailTo
    else:
        return SMTPState.AwaitingMailTo

# Main loop
for line in stdin:

    # Get new line
    currentStr = line
    currentPos = 0
    print(line, end="")

    # Determine what command it is
    command = None
    if re.compile("^MAIL[ \t]+FROM:").match(line):
        command = mailFromCmd
    elif re.compile("^RCPT[ \t]+TO:").match(line):
        command = rcptToCmd
    elif re.compile("^DATA").match(line):
        command = dataCmd
    else:
        print("500 Syntax error: command unrecognized")
        currentState = SMTPState.AwaitingMailTo
        continue

    # Determine if command is valid under current state
    if command not in currentState.value:
        currentState = SMTPState.AwaitingMailTo
        print("503 Bad sequence of commands")
        continue

    # Update state
    currentState = stateMachine(currentState, command)

    # Parse command
    try:
        command()
        print("250 OK")
    except TerminalParseException as e:
        print("501 Syntax error in parameters or arguments")
        currentState = SMTPState.AwaitingMailTo
        continue
