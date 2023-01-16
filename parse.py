from sys import stdin

currentPost = 0
currentStr = ""

# Helper functions
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

# Trivial non terminals
SP = {" ", "\t"}
letter = set(map(chr, range(65, 91))) | set(map(chr, range(97, 123)))
digit = set("0123456789")
special = set('<>()[]\\.,;:@"')
char = set(map(chr, range(32, 127))) - special - SP
null = set()

# Grammar impl
def mailFromCmd():
    try:
        expect("MAIL\n")
    except NonTerminalParseException:
        raise TerminalParseException("mail-from-cmd")

# Main loop
for line in stdin:
    currentStr = line
    currentPos = 0
    try:
        mailFromCmd()
        print("Sender ok")
    except TerminalParseException as e:
        print(f"ERROR -- {e.TerminalName}")
