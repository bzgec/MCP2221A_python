# Make sure you install pyusb and libusb on your system yo
import MCP2221A
import time
import customPrints

def setConfig(mcp2221a, pin):
    # First settings must be read from flash (in order to keep settings from other pins after writing)
    gpSettings = mcp2221a.readFlashGpSettings()

    outputVal = int(input("Output value (0-1): "))
    direction = int(input("Direction (0-1): "))
    designation = int(input("Designation: "))
    print("*************************************************************")

    if pin == 0:
        gpSettings.B.GP0.B.outputVal = outputVal
        gpSettings.B.GP0.B.direction = direction
        gpSettings.B.GP0.B.designation = designation
    elif pin == 1:
        gpSettings.B.GP1.B.outputVal = outputVal
        gpSettings.B.GP1.B.direction = direction
        gpSettings.B.GP1.B.designation = designation
    elif pin == 2:
        gpSettings.B.GP2.B.outputVal = outputVal
        gpSettings.B.GP2.B.direction = direction
        gpSettings.B.GP2.B.designation = designation
    elif pin == 3:
        gpSettings.B.GP3.B.outputVal = outputVal
        gpSettings.B.GP3.B.direction = direction
        gpSettings.B.GP3.B.designation = designation


    mcp2221a.writeFlashGpSettings(gpSettings)

def resetAndReadGpSettings(mcp2221a):

    customPrints.printf("Resetting the IC...")
    mcp2221a.resetChip()
    customPrints.printf(" done\r\n")
    print("*************************************************************")

    gpSettings = mcp2221a.readFlashGpSettings()
    mcp2221a.prettyPrint_GpSettings(gpSettings)


if __name__ == '__main__':
    print("*************************************************************")
    print("To finish setting default GPIO configuration press CTRL+C")
    print("*************************************************************")

    mcp2221a = MCP2221A.mcp2221a()

    resetAndReadGpSettings(mcp2221a)


    while(1):
        print("*************************************************************")
        pin = input("Set default value for pin (0-3): ")
        print("*************************************************************")
        if pin == "0":
            setConfig(mcp2221a, 0)
        elif pin == "1":
            setConfig(mcp2221a, 1)
        elif pin == "2":
            setConfig(mcp2221a, 2)
        elif pin == "3":
            setConfig(mcp2221a, 3)
        else:
            print("Wrong character: " + pin)

        resetAndReadGpSettings(mcp2221a)
