# Make sure you install pyusb and libusb on your system yo
import usb.core
import usb.util
import usb.control
import time

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

def writeFlash(device, data):
    buf = [0]*64
    buf[0] = CMD_WRITE
    for i in range(len(data)):
        buf[i+1] = data[i]
    # device.write(OUTPUT_ENDPOINT, '\xB1' + data)
    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == CMD_WRITE
    if info[1] == 0x02:
        raise FlashError('Command not supported')
    if info[1] == 0x03:
        raise FlashError('Command not allowed')

def writeDescriptor(device, name, descriptor):
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

    return writeFlash(device, buf)

def readFlash(device, section):
    # device.write(OUTPUT_ENDPOINT, '\xB0' + section + ('\x00' * 62))
    buf = [0]*64
    buf[0] = CMD_READ
    buf[1] = section
    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == CMD_READ
    if info[1] != 0x00:
        raise FlashError('Command not supported')
    return info

def readChipSettings(device):
    chip_settings = readFlash(device, READ_CHIP_SETTINGS)
    output = dict()
    for attr in CHIP_SETTINGS_MAP:
        output[attr] = CHIP_SETTINGS_MAP[attr].value(chip_settings)
    return output

def readUsbManufacturerDescriptorString(device):
    response = readFlash(device, READ_USB_MANUFACTURER_DESCRIPTOR_STRING)
    nameLen = int((response[2] - 2) / 2)
    assert response[3] == 0x03  # This value must always be 0x03
    usbManufacturerDescriptorString = ""
    for i in range(nameLen):
        usbManufacturerDescriptorString += chr(response[4 + i*2])

    return usbManufacturerDescriptorString

def readUsbProductDescriptorString(device):
    response = readFlash(device, READ_USB_PRODUCT_DESCRIPTOR_STRING)
    nameLen = int((response[2] - 2) / 2)
    assert response[3] == 0x03  # This value must always be 0x03
    usbProductDescriptorString = ""
    for i in range(nameLen):
        usbProductDescriptorString += chr(response[4 + i*2])

    return usbProductDescriptorString

def readUsbSerialNumberDescriptorString(device):
    response = readFlash(device, READ_USB_SERIAL_NUMBER_DESCRIPTOR_STRING)
    nameLen = int((response[2] - 2) / 2)
    assert response[3] == 0x03  # This value must always be 0x03
    usbSerialNumberDescriptorString = ""
    for i in range(nameLen):
        usbSerialNumberDescriptorString += chr(response[4 + i*2])

    return usbSerialNumberDescriptorString

def readChipFactorySerialNumber(device):
    response = readFlash(device, READ_CHIP_FACTORY_SERIAL_NUMBER)
    structureLen = response[2]
    chipFactorySerialNumber = ""
    for i in range(structureLen):
        chipFactorySerialNumber += chr(response[4 + i])

    return chipFactorySerialNumber

def getStatus(device):
    device.write(OUTPUT_ENDPOINT, STATUS_COMMAND)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == 0x10
    output = {
        'MCP2221A HW revision': chr(info[46]) + chr(info[47]),
        'MCP2221A Firmware revision': chr(info[48]) + chr(info[49]),
        'USB Manufacturer Descriptor String': readUsbManufacturerDescriptorString(device),
        'USB Product Descriptor String': readUsbProductDescriptorString(device),
        'USB Serial Number Descriptor String': readUsbSerialNumberDescriptorString(device),
        'Chip factory serial number': readChipFactorySerialNumber(device)
    }

    chip_settings = readChipSettings(device)
    output.update(chip_settings)
    return output

def getSramSettings(device):
    buf = [0]*64
    buf[0] = GET_SRAM_SETTINGS
    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    print("GP0: " + hex(info[22]) + ", GP1: " + hex(info[23]) + ", GP2: " + hex(info[24]) + ", GP3: " + hex(info[25]))
    assert info[0] == GET_SRAM_SETTINGS
    return

def setSramSettings(device):
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
    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    print("info: " + str(info))
    assert info[0] == SET_SRAM_SETTINGS
    assert info[1] == 0x00  # Command completed successfully

def setAllOutput(device):
    buf = [0]*64
    buf[0] = SET_SRAM_SETTINGS
    # buf[0] = 0x60
    buf[1] = 0x00  # Not care about this byte
    buf[7] = 0x80  # Alter GPIO configuration
    buf[8 + 0] = 0x00  # Alter GPx output (enable/disable)
    buf[8 + 1] = 0x00  # Alter GPx output (enable/disable)
    buf[8 + 2] = 0x00  # Alter GPx output (enable/disable)
    buf[8 + 3] = 0x00  # Alter GPx output (enable/disable)
    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == SET_SRAM_SETTINGS
    assert info[1] == 0x00  # Command completed successfully

def setAllInput(device):
    buf = [0]*64
    buf[0] = SET_SRAM_SETTINGS
    # buf[0] = 0x60
    buf[1] = 0x00  # Not care about this byte
    buf[7] = 0x80  # Alter GPIO configuration
    buf[8 + 0] = 0x08  # Alter GPx output (enable/disable)
    buf[8 + 1] = 0x08  # Alter GPx output (enable/disable)
    buf[8 + 2] = 0x08  # Alter GPx output (enable/disable)
    buf[8 + 3] = 0x08  # Alter GPx output (enable/disable)
    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == SET_SRAM_SETTINGS
    assert info[1] == 0x00  # Command completed successfully

def writeGP(device, pin, st):
    # buf[0] = WRITE_GP_SETTINGS
    # Writing 0 means nothing changes
    buf = [0]*64
    buf[0] = SET_GPIO_OUTPUT_VALUES
    buf[1] = 0x00  # Not care about this byte
    buf[2+0 + pin*4] = 0xFF  # Alter GPx output (enable/disable)
    buf[2+1 + pin*4] = st  # GPx output value
    buf[2+2 + pin*4] = 0xFF  # Alter GPx pin direction (enable/disable)
    buf[2+3 + pin*4] = 0x00  # Set GPx as output

    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == SET_GPIO_OUTPUT_VALUES
    assert info[2+0 + pin] != 0xEE
    assert info[2+1 + pin] != 0xEE
    assert info[2+2 + pin] != 0xEE
    assert info[2+3 + pin] != 0xEE
    return

def readGP(device):
    # buf[0] = WRITE_GP_SETTINGS
    # Writing 0 means nothing changes
    pinSt = [0]*4
    buf = [0]*64
    buf[0] = GET_GPIO_VALUES

    device.write(OUTPUT_ENDPOINT, buf)
    info = device.read(INPUT_ENDPOINT, HID_PKT_SIZE)
    assert info[0] == GET_GPIO_VALUES
    assert info[1] == 0x00  # Command completed successfully
    pinSt[0] = info[2 + 2*0]
    pinSt[1] = info[2 + 2*1]
    pinSt[2] = info[2 + 2*2]
    pinSt[3] = info[2 + 2*3]
    return pinSt

def lsUSB():
    dev = usb.core.find(find_all=True)
    # print("Number of devices: " + str(dev.__sizeof__()))
    for device in dev:
        print('\033[92m ~=== ' + str(getProduct(device)) + ' ===~\033[0m')
        print('  \033[95m' + str(getManufacturer(device)) + '\033[0m')
        print('  productID=' + hex(device.idProduct) + ' vendorID=' + hex(device.idVendor))
        try:
            print(device.get_active_configuration())
        except:
            print("Access denied")

def getDevice():
    device = usb.core.find(idVendor=0x4d8, idProduct=0xdd)
    if device is None:
        raise ValueError('No MCP2221A device found')
    # device.reset() # try this line if shiz isnt working

    # print(device)

    #tell the kernel to stop tracking it
    try:
        if device.is_kernel_driver_active(HID_INTERFACE) is True:
            print("Detaching kernel driver")
            device.detach_kernel_driver(HID_INTERFACE)
    except usb.core.USBError as e:
        raise ValueError("Kernel driver won't give up control over device: " + str(e))
    # device.set_configuration() #  try this line if shiz isnt working
    return device

if __name__ == '__main__':
    # lsUSB()

    device = usb.core.find(idVendor=0x4d8, idProduct=0xdd)
    if device is None:
        raise ValueError('No MCP2221A device found')
    # device.reset() # try this line if shiz isnt working

    print(device)

    #tell the kernel to stop tracking it
    try:
        if device.is_kernel_driver_active(HID_INTERFACE) is True:
            print("Detaching kernel driver")
            device.detach_kernel_driver(HID_INTERFACE)
    except usb.core.USBError as e:
        raise ValueError("Kernel driver won't give up control over device: " + str(e))
    # device.set_configuration() #  try this line if shiz isnt working

    writeGP(device, 0, 0)
    # writeGP(device, 1, 0)
    # writeGP(device, 2, 0)
    # writeGP(device, 3, 0)

    #start using the device with pre-determined endpoint numbers
    status = getStatus(device)
    print(getProduct(device) + ' found')
    for attr in status:
        print('\t %s => %s' % (attr, status[attr]))
    if input("Everything looks good. Write manufacturer/product strings? (y/N): ").lower() == 'y':
        writeDescriptor(device, input('Product name: '), "Product")
        writeDescriptor(device, input('Manufacturer name: '), "Manufacturer")
    else:
        print("USB device information:")
        lsUSB()