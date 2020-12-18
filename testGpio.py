# Make sure you install pyusb and libusb on your system yo
import MCP2221A
import time
import customPrints

def testOutput(mcp2221a):
    mcp2221a.setAllOutput()

    print("01 - Set pin 0 to 1")
    print("11 - Set pin 1 to 1")
    print("20 - Set pin 2 to 0")
    print("30 - Set pin 3 to 0")
    print("*************************************************************")
    while 1:
        gpioNumb = input("Set new pin value: ")
        if len(gpioNumb) == 2:
            mcp2221a.writeGP(int(gpioNumb[0]), int(gpioNumb[1]))
        else:
            print("2 characters to control GP:")
            print("    01 - Set pin 0 to 1")
            print("    11 - Set pin 1 to 1")
            print("    20 - Set pin 2 to 0")
            print("    30 - Set pin 3 to 0")

def testInput(mcp2221a):
    mcp2221a.setAllInput()

    while 1:
        pinSt = mcp2221a.readGP()
        customPrints.printf("GP0: %u\n", pinSt[0])
        customPrints.printf("GP1: %u\n", pinSt[1])
        customPrints.printf("GP2: %u\n", pinSt[2])
        customPrints.printf("GP3: %u\n", pinSt[3])
        time.sleep(0.05)
        customPrints.cursorUpLines(4)

if __name__ == '__main__':
    mcp2221a = MCP2221A.mcp2221a()

    print("*************************************************************")
    print("To finish gpio test press CTRL+C")
    print("*************************************************************")
    testInputOutput = input("Test GPIO as output or input? (I/O): ").lower()
    print("*************************************************************")
    if testInputOutput == "o":
        testOutput(mcp2221a)
    elif testInputOutput == "i":
        testInput(mcp2221a)
    else:
        print("Wrong character: " + testInputOutput)
