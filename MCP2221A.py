# Make sure you install pyusb and libusb on your system yo
import usb.core
import usb.util
import usb.control
import time
import ctypes
import traceback

HID_INTERFACE = 0x02
INPUT_ENDPOINT = 0x83
OUTPUT_ENDPOINT = 0x3
HID_PKT_SIZE = 64

STATUS_COMMAND = '\x10' + ('\x00' * 63)

CMD_WRITE = 0xB1
CMD_READ = 0xB0

WRITE_GP_SETTINGS = 0x01
WRITE_USB_MANUFACTURER_DESCRIPTOR_STRING = 0x02
WRITE_USB_PRODUCT_DESCRIPTOR_STRING = 0x03
WRITE_USB_SERIAL_NUMBER_DESCRIPTOR_STRING = 0x04

READ_CHIP_SETTINGS = 0x00
READ_GP_SETTINGS = 0x01
READ_USB_MANUFACTURER_DESCRIPTOR_STRING = 0x02
READ_USB_PRODUCT_DESCRIPTOR_STRING = 0x03
READ_USB_SERIAL_NUMBER_DESCRIPTOR_STRING = 0x04
READ_CHIP_FACTORY_SERIAL_NUMBER = 0x05

SET_GPIO_OUTPUT_VALUES = 0x50
GET_GPIO_VALUES = 0x51
SET_SRAM_SETTINGS = 0x60
GET_SRAM_SETTINGS = 0x61

CMD_RESET = 0x70

class FlashError(Exception):
    pass

class ByteDecoder(object):
    def __init__(self, b, multiplier):
        self.b = b
        self.multiplier = multiplier
    def value(self, data):
        return data[self.b] * self.multiplier

class HexDecoder(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
    def value(self, data):
        section = data[self.start:self.end]
        section.reverse()
        return ''.join('{:02x}'.format(x) for x in section)

class BitDecoder(object):
    def __init__(self, byte, bit):
        self.byte = byte
        self.bit = bit
    def value(self, data):
        return bool(data[self.byte] & (1 << self.bit))

class EnumDecoder(object):
    def __init__(self, byte, mask, opts):
        self.byte = byte
        self.mask = mask
        self.opts = opts
    def value(self, data):
        return self.opts[data[self.byte] & self.mask]

CHIP_SETTINGS_MAP = {
    'Provide serial number on enumeration': BitDecoder(4, 7),
    'USB vendorID': HexDecoder(8, 10),
    'USB productID': HexDecoder(10, 12),
    'USB power attributes': ByteDecoder(12, 1),
    'USB requested number of mA': ByteDecoder(13, 2),
    'Chip security': EnumDecoder(4, 0b11, {0: 'Unsecured', 1: 'Password-protected', 2: 'Permanently-locked', 3: 'Permanently-locked'})
}

class gpSetting_S(ctypes.LittleEndianStructure):
    __pack__ = 1
    _fields_ = [
        ("designation", ctypes.c_uint8, 3),  # 2-0   # 111-011 - Don't case, 010 - Dedicated function operation, 001 Alternate function, 000 - GPIO operation
        ("direction", ctypes.c_uint8, 1),    # 3     # 0 - Output mode, 1 - Input mode
        ("outputVal", ctypes.c_uint8, 1),    # 4     # This value will be present at the GPx pin at Power-up/Reset
        ("notUsed",  ctypes.c_uint8, 3),     # 7-5
    ]

class gpSetting_U(ctypes.Union):
    __pack__ = 1
    _fields_ = [
        ("B",  gpSetting_S),
        ("R",  ctypes.c_uint8),
    ]

class gpSettings_S(ctypes.LittleEndianStructure):
    __pack__ = 1
    _fields_ = [
        ("GP0",  gpSetting_U),
        ("GP1",  gpSetting_U),
        ("GP2",  gpSetting_U),
        ("GP3",  gpSetting_U),
    ]

class gpSettings_U(ctypes.Union):
    __pack__ = 1
    _fields_ = [
        ("B",  gpSettings_S),
        ("R",  ctypes.c_uint32),
    ]

def getManufacturer(device):
    try:
        return usb.util.get_string(device, device.iManufacturer)
    except ValueError:
        return ''

def getProduct(device):
    try:
        return usb.util.get_string(device, device.iProduct)
    except ValueError:
        return ''

class mcp2221a:


    def __init__(self):
        self.usbDevice = 0
        self.getUsbDevice()

    def getUsbDevice(self):
        self.usbDevice = usb.core.find(idVendor=0x4d8, idProduct=0xdd)
        if self.usbDevice is None:
            raise ValueError('No MCP2221A device found')
        # self.usbDevice.reset() # try this line if shiz isnt working

        # print(self.usbDevice)

        #tell the kernel to stop tracking it
        try:
            if self.usbDevice.is_kernel_driver_active(HID_INTERFACE) is True:
                # print("Detaching kernel driver")
                self.usbDevice.detach_kernel_driver(HID_INTERFACE)
        except usb.core.USBError:
            tracebackStr = traceback.format_exc()
            raise ValueError("Kernel driver won't give up control over device!")
            raise ValueError(tracebackStr)
        # self.usbDevice.set_configuration() #  try this line if shiz isnt working

    def resetChip(self):
        # Max power-up time 140ms
        buf = [0]*64
        buf[0] = CMD_RESET
        buf[1] = 0xAB
        buf[2] = 0xCD
        buf[3] = 0xEF
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        time.sleep(1)
        self.getUsbDevice()

    def writeFlash(self, data):
        buf = [0]*64
        buf[0] = CMD_WRITE
        for i in range(len(data)):
            buf[i+1] = data[i]
        # self.usbDevice.write(OUTPUT_ENDPOINT, '\xB1' + data)
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == CMD_WRITE
        if info[1] == 0x02:
            raise FlashError('Command not supported')
        if info[1] == 0x03:
            raise FlashError('Command not allowed')

    def writeDescriptor(self, name, descriptor):
        # Note that buf is sifted for 1 byte
        buf = [0]*63
        if descriptor == "Product":
            buf[0] = WRITE_USB_PRODUCT_DESCRIPTOR_STRING
        elif descriptor == "Manufacturer":
            buf[0] = WRITE_USB_MANUFACTURER_DESCRIPTOR_STRING
        elif descriptor == "Serial":
            buf[0] = WRITE_USB_SERIAL_NUMBER_DESCRIPTOR_STRING
        else:
            assert 0
        buf[1] = (2*len(name))+2  # Number of bytes + 2 in the provided USB Serial Number Descriptor String
        buf[2] = 0x03

        for i in range(len(name)):
            buf[i*2 + 0 + 3] = ord(name[i])  # ord() converts "A" to 'A' (from string to C like char)
            buf[i*2 + 1 + 3] = 0

        return self.writeFlash(buf)

    def writeFlashGpSettings(self, gpSettings):
        # First readFlashGpSettings() and than only set the GPx parameters you want to change

        # Note that buf is sifted for 1 byte
        buf = [0]*63
        buf[0] = WRITE_GP_SETTINGS
        buf[1] = gpSettings.B.GP0.R  # GP0 settings
        buf[2] = gpSettings.B.GP1.R  # GP1 settings
        buf[3] = gpSettings.B.GP2.R  # GP2 settings
        buf[4] = gpSettings.B.GP3.R  # GP3 settings

        return self.writeFlash(buf)

    def readFlash(self, section):
        # device.write(OUTPUT_ENDPOINT, '\xB0' + section + ('\x00' * 62))
        buf = [0]*64
        buf[0] = CMD_READ
        buf[1] = section
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == CMD_READ
        if info[1] != 0x00:
            raise FlashError('Command not supported')
        return info

    def readFlashGpSettings(self):
        response = self.readFlash(READ_GP_SETTINGS)

        gpSettings = gpSettings_U()
        gpSettings.B.GP0.R = response[4]
        gpSettings.B.GP1.R = response[5]
        gpSettings.B.GP2.R = response[6]
        gpSettings.B.GP3.R = response[7]

        return gpSettings

    def readChipSettings(self):
        chip_settings = self.readFlash(READ_CHIP_SETTINGS)
        output = dict()
        for attr in CHIP_SETTINGS_MAP:
            output[attr] = CHIP_SETTINGS_MAP[attr].value(chip_settings)
        return output

    def readUsbManufacturerDescriptorString(self):
        response = self.readFlash(READ_USB_MANUFACTURER_DESCRIPTOR_STRING)
        nameLen = int((response[2] - 2) / 2)
        assert response[3] == 0x03  # This value must always be 0x03
        usbManufacturerDescriptorString = ""
        for i in range(nameLen):
            usbManufacturerDescriptorString += chr(response[4 + i*2])

        return usbManufacturerDescriptorString

    def readUsbProductDescriptorString(self):
        response = self.readFlash(READ_USB_PRODUCT_DESCRIPTOR_STRING)
        nameLen = int((response[2] - 2) / 2)
        assert response[3] == 0x03  # This value must always be 0x03
        usbProductDescriptorString = ""
        for i in range(nameLen):
            usbProductDescriptorString += chr(response[4 + i*2])

        return usbProductDescriptorString

    def readUsbSerialNumberDescriptorString(self):
        response = self.readFlash(READ_USB_SERIAL_NUMBER_DESCRIPTOR_STRING)
        nameLen = int((response[2] - 2) / 2)
        assert response[3] == 0x03  # This value must always be 0x03
        usbSerialNumberDescriptorString = ""
        for i in range(nameLen):
            usbSerialNumberDescriptorString += chr(response[4 + i*2])

        return usbSerialNumberDescriptorString

    def readChipFactorySerialNumber(self):
        response = self.readFlash(READ_CHIP_FACTORY_SERIAL_NUMBER)
        structureLen = response[2]
        chipFactorySerialNumber = ""
        for i in range(structureLen):
            chipFactorySerialNumber += chr(response[4 + i])

        return chipFactorySerialNumber

    def getStatus(self):
        self.usbDevice.write(OUTPUT_ENDPOINT, STATUS_COMMAND)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == 0x10
        output = {
            'MCP2221A HW revision': chr(info[46]) + chr(info[47]),
            'MCP2221A Firmware revision': chr(info[48]) + chr(info[49]),
            'USB Manufacturer Descriptor String': self.readUsbManufacturerDescriptorString(),
            'USB Product Descriptor String': self.readUsbProductDescriptorString(),
            'USB Serial Number Descriptor String': self.readUsbSerialNumberDescriptorString(),
            'Chip factory serial number': self.readChipFactorySerialNumber()
        }

        chip_settings = self.readChipSettings()
        output.update(chip_settings)
        return output

    def getSramSettings(self):
        buf = [0]*64
        buf[0] = GET_SRAM_SETTINGS
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        print("GP0: " + hex(info[22]) + ", GP1: " + hex(info[23]) + ", GP2: " + hex(info[24]) + ", GP3: " + hex(info[25]))
        assert info[0] == GET_SRAM_SETTINGS
        return

    def setSramSettings(self):
        buf = [0]*64
        buf[0] = SET_SRAM_SETTINGS
        # buf[0] = 0x60
        buf[1] = 0x00  # Not care about this byte
        buf[7] = 0x80  # Alter GPIO configuration
        buf[8 + 0] = 0x10  # Alter GPx output (enable/disable)
        buf[8 + 1] = 0x10  # Alter GPx output (enable/disable)
        buf[8 + 2] = 0x17  # Alter GPx output (enable/disable)
        buf[8 + 3] = 0x17  # Alter GPx output (enable/disable)
        print("buf: " + str(buf))
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        print("info: " + str(info))
        assert info[0] == SET_SRAM_SETTINGS
        assert info[1] == 0x00  # Command completed successfully

    def setAllOutput(self):
        buf = [0]*64
        buf[0] = SET_SRAM_SETTINGS
        # buf[0] = 0x60
        buf[1] = 0x00  # Not care about this byte
        buf[7] = 0x80  # Alter GPIO configuration
        buf[8 + 0] = 0x00  # Alter GPx output (enable/disable)
        buf[8 + 1] = 0x00  # Alter GPx output (enable/disable)
        buf[8 + 2] = 0x00  # Alter GPx output (enable/disable)
        buf[8 + 3] = 0x00  # Alter GPx output (enable/disable)
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == SET_SRAM_SETTINGS
        assert info[1] == 0x00  # Command completed successfully

    def setAllInput(self):
        buf = [0]*64
        buf[0] = SET_SRAM_SETTINGS
        # buf[0] = 0x60
        buf[1] = 0x00  # Not care about this byte
        buf[7] = 0x80  # Alter GPIO configuration
        buf[8 + 0] = 0x08  # Alter GPx output (enable/disable)
        buf[8 + 1] = 0x08  # Alter GPx output (enable/disable)
        buf[8 + 2] = 0x08  # Alter GPx output (enable/disable)
        buf[8 + 3] = 0x08  # Alter GPx output (enable/disable)
        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == SET_SRAM_SETTINGS
        assert info[1] == 0x00  # Command completed successfully

    def writeGP(self, pin, st):
        # buf[0] = WRITE_GP_SETTINGS
        # Writing 0 means nothing changes
        buf = [0]*64
        buf[0] = SET_GPIO_OUTPUT_VALUES
        buf[1] = 0x00  # Not care about this byte
        buf[2+0 + pin*4] = 0xFF  # Alter GPx output (enable/disable)
        buf[2+1 + pin*4] = st  # GPx output value
        buf[2+2 + pin*4] = 0xFF  # Alter GPx pin direction (enable/disable)
        buf[2+3 + pin*4] = 0x00  # Set GPx as output

        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == SET_GPIO_OUTPUT_VALUES
        assert info[2+0 + pin] != 0xEE
        assert info[2+1 + pin] != 0xEE
        assert info[2+2 + pin] != 0xEE
        assert info[2+3 + pin] != 0xEE
        return

    def readGP(self):
        # buf[0] = WRITE_GP_SETTINGS
        # Writing 0 means nothing changes
        pinSt = [0]*4
        buf = [0]*64
        buf[0] = GET_GPIO_VALUES

        self.usbDevice.write(OUTPUT_ENDPOINT, buf)
        info = self.usbDevice.read(INPUT_ENDPOINT, HID_PKT_SIZE)
        assert info[0] == GET_GPIO_VALUES
        assert info[1] == 0x00  # Command completed successfully
        pinSt[0] = info[2 + 2*0]
        pinSt[1] = info[2 + 2*1]
        pinSt[2] = info[2 + 2*2]
        pinSt[3] = info[2 + 2*3]
        return pinSt

    def lsUSB(self):
        dev = usb.core.find(find_all=True)
        # print("Number of devices: " + str(dev.__sizeof__()))
        for device in dev:
            print('\033[92m ~=== ' + str(self.getProduct(device)) + ' ===~\033[0m')
            print('  \033[95m' + str(self.getManufacturer(device)) + '\033[0m')
            print('  productID=' + hex(device.idProduct) + ' vendorID=' + hex(device.idVendor))
            try:
                print(device.get_active_configuration())
            except:
                print("Access denied")

    def prettyPrint_GpSettings(self, gpSettings):
        print("GP0")
        print("  GPIO Output value: " + hex(gpSettings.B.GP0.B.outputVal))
        print("  GPIO Direction: "    + hex(gpSettings.B.GP0.B.direction))
        print("  GPIO Designation: "  + hex(gpSettings.B.GP0.B.designation))
        print("GP1")
        print("  GPIO Output value: " + hex(gpSettings.B.GP1.B.outputVal))
        print("  GPIO Direction: "    + hex(gpSettings.B.GP1.B.direction))
        print("  GPIO Designation: "  + hex(gpSettings.B.GP1.B.designation))
        print("GP2")
        print("  GPIO Output value: " + hex(gpSettings.B.GP2.B.outputVal))
        print("  GPIO Direction: "    + hex(gpSettings.B.GP2.B.direction))
        print("  GPIO Designation: "  + hex(gpSettings.B.GP2.B.designation))
        print("GP3")
        print("  GPIO Output value: " + hex(gpSettings.B.GP3.B.outputVal))
        print("  GPIO Direction: "    + hex(gpSettings.B.GP3.B.direction))
        print("  GPIO Designation:  " + hex(gpSettings.B.GP3.B.designation))

# end of class: mcp2221a

if __name__ == '__main__':
    mcp2221a = mcp2221a()

    print(mcp2221a.usbDevice)

    #start using the device with pre-determined endpoint numbers
    status = mcp2221a.getStatus()
    print(mcp2221a.getProduct() + ' found')
    for attr in status:
        print('\t %s => %s' % (attr, status[attr]))
    if input("Everything looks good. Write manufacturer/product strings? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(input('Product name: '), "Product")
        mcp2221a.writeDescriptor(input('Manufacturer name: '), "Manufacturer")
    else:
        print("USB device information:")
        mcp2221a.lsUSB()
