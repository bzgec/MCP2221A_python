import mcp2221a

if __name__ == '__main__':
    device = mcp2221a.getDevice()
    print("*************************************************************")

    status = mcp2221a.getStatus(device)
    for attr in status:
        print('%s: %s' % (attr, status[attr]))

    print("*************************************************************")
    if input("Write new USB Manufacturer Descriptor String? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(device, input('Manufacturer name: '), "Manufacturer")
    if input("Write new USB Product Descriptor String? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(device, input('Product name: '), "Product")
    if input("Write new USB Serial Number Descriptor String? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(device, input('Serial: '), "Serial")