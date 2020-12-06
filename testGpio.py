# Make sure you install pyusb and libusb on your system yo
import mcp2221a
import time
import customPrints

def testOutput(device):
    mcp2221a.setAllOutput(device)

    print("01 - Set pin 0 to 1")
    print("11 - Set pin 1 to 1")
    print("20 - Set pin 2 to 0")
    print("30 - Set pin 3 to 0")
    print("*************************************************************")
    while 1:
        gpioNumb = input("Set new pin value: ")
        if len(gpioNumb) == 2:
            mcp2221a.writeGP(device, int(gpioNumb[0]), int(gpioNumb[1]))
        else:
            print("2 characters to control GP:")
            print("    01 - Set pin 0 to 1")
            print("    11 - Set pin 1 to 1")
            print("    20 - Set pin 2 to 0")
            print("    30 - Set pin 3 to 0")

def testInput(device):
    mcp2221a.setAllInput(device)

    while 1:
        pinSt = mcp2221a.readGP(device)
        customPrints.printf("GP0: %u\n", pinSt[0])
        customPrints.printf("GP1: %u\n", pinSt[1])
        customPrints.printf("GP2: %u\n", pinSt[2])
        customPrints.printf("GP3: %u\n", pinSt[3])
        time.sleep(0.05)
        customPrints.cursorUpLines(4)

if __name__ == '__main__':
    device = mcp2221a.getDevice()

    print("*************************************************************")
    print("To finish gpio test press CTRL+C")
    print("*************************************************************")
    testInputOutput = input("Test GPIO as output or input? (I/O): ").lower()
    print("*************************************************************")
    if testInputOutput == "o":
        testOutput(device)
    elif testInputOutput == "i":
        testInput(device)
    else:
        print("Wrong character: " + testInputOutput)
