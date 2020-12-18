import MCP2221A

if __name__ == '__main__':
    mcp2221a = MCP2221A.mcp2221a()
    print("*************************************************************")

    status = mcp2221a.getStatus()
    for attr in status:
        print('%s: %s' % (attr, status[attr]))

    print("*************************************************************")
    if input("Write new USB Manufacturer Descriptor String? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(input('Manufacturer name: '), "Manufacturer")
    if input("Write new USB Product Descriptor String? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(input('Product name: '), "Product")
    if input("Write new USB Serial Number Descriptor String? (y/N): ").lower() == 'y':
        mcp2221a.writeDescriptor(input('Serial: '), "Serial")