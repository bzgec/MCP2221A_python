import sys

def printf(format, *args):
  sys.stdout.write(format % args)

def clearLine():
  sys.stdout.write("\033[K") # Clear to the end of line

def cursorUpOneLine():
  sys.stdout.write("\033[F") # Cursor up one line

def cursorUpLines(n):
  while n > 0:
    clearLine()
    cursorUpOneLine()
    n -= 1