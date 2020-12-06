## MCP2221A python test
- Really simple python scripts to test MCP2221A
- Tested with `Python 3.8.5`
- Starting point of this code was taken from [twitchyliquid64 - mcp2221a_set_strings.py](https://gist.github.com/twitchyliquid64/a093ce11245274a2adeb631ccd2ba7eb)

### Implemented
- [x] Setting USB descriptor strings
- [x] Controlling GP as outputs/inputs (for now only one option is possible for all pins)
- [ ] DAC
- [ ] ADC
- [ ] I2C

### Dependencies
- pyusb
- libusb
### testGpio.py
- Test GP as input or output
- [Open file](./testGpio.py)
### setDescriptorStrings.py
- Print some MCP2221A parameters
- Set USB Manufacturer, Product and Serial Descriptor Strings (they are used during the USB enumeration)
- [Open file](./setDescriptorStrings.py)
### mcp2221a.py
- Main library
- [Open file](./mcp2221a.py)
