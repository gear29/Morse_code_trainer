
from machine import Pin, I2C
import time
import framebuf

# =====================================
# PIN SETUP
# =====================================

# 74HC595 shift registers
DATA = Pin(18, Pin.OUT)
CLOCK = Pin(19, Pin.OUT)
LATCH = Pin(21, Pin.OUT)

# Button
button = Pin(10, Pin.IN, Pin.PULL_UP)

# OLED screen: I2C0
i2c = I2C(
    0,
    sda=Pin(4),
    scl=Pin(5),
    freq=400000
)

# =====================================
# OLED DRIVER
# =====================================

class SSD1306:

    def __init__(self, i2c, address):
        self.i2c = i2c
        self.address = address
        self.width = 128
        self.height = 64

        self.buffer = bytearray(1024)

        self.frame = framebuf.FrameBuffer(
            self.buffer,
            128,
            64,
            framebuf.MONO_VLSB
        )

        commands = [
            0xAE, 0x20, 0x00,
            0x40, 0xA1, 0xC8,
            0xA8, 0x3F, 0xD3,
            0x00, 0xDA, 0x12,
            0x81, 0x7F, 0xD9,
            0xF1, 0xDB, 0x40,
            0xA4, 0xA6, 0xD5,
            0x80, 0x8D, 0x14,
            0xAF
        ]

        for command in commands:
            self.i2c.writeto(
                self.address,
                bytes([0x00, command])
            )

    def fill(self, color):
        self.frame.fill(color)

    def text(self, message, x, y):
        self.frame.text(message, x, y)

    def show(self):
        for page in range(8):
            self.i2c.writeto(
                self.address,
                bytes([0x00, 0xB0 + page])
            )

            start = page * 128
            end = start + 128

            self.i2c.writeto(
                self.address,
                b'\x40' + bytes(self.buffer[start:end])
            )


# Find OLED address
devices = i2c.scan()

if 0x3C in devices:
    oled_address = 0x3C
elif 0x3D in devices:
    oled_address = 0x3D
else:
    raise RuntimeError("OLED not found!")

oled = SSD1306(i2c, oled_address)


# =====================================
# LED CONTROL
# =====================================

LED_COUNT = 30
CHIP_COUNT = 4

def set_led(led_number):

    # Four bytes, one per chip
    outputs = [0, 0, 0, 0]

    if 0 <= led_number < LED_COUNT:

        chip = led_number // 8
        bit = led_number % 8

        outputs[chip] |= (1 << bit)

    # Send data to shift registers
    LATCH.value(0)

    # Send last chip first
    for value in reversed(outputs):

        # Send most significant bit first
        for bit in range(7, -1, -1):

            DATA.value((value >> bit) & 1)

            CLOCK.value(1)
            CLOCK.value(0)

    # Update outputs
    LATCH.value(1)
    LATCH.value(0)


# =====================================
# LETTER SYSTEM
# =====================================

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "

current_letter = 0

def update_screen():

    oled.fill(0)

    oled.text("MORSE TRAINER", 0, 0)
    oled.text("----------------", 0, 10)

    letter = LETTERS[current_letter]

    if letter == " ":
        name = "SPACE"
    else:
        name = letter

    oled.text("Letter: " + name, 0, 24)

    oled.text(
        "LED: " + str(current_letter + 1) + " / 27",
        0, 36
    )

    oled.text("Press to advance", 0, 52)

    oled.show()


# =====================================
# BUTTON SETUP
# =====================================

last_raw = button.value()
stable_state = last_raw
last_change = time.ticks_ms()


# =====================================
# STARTUP
# =====================================

set_led(current_letter)
update_screen()

print("Morse trainer started")


# =====================================
# MAIN LOOP
# =====================================

while True:

    raw = button.value()
    now = time.ticks_ms()

    # Detect a change in button state
    if raw != last_raw:
        last_raw = raw
        last_change = now

    # Wait for button debounce
    if time.ticks_diff(now, last_change) > 30:

        if raw != stable_state:

            stable_state = raw

            # Button pressed
            if stable_state == 0:

                # Advance to next letter
                current_letter = (
                    current_letter + 1
                ) % len(LETTERS)

                # Update LEDs and screen
                set_led(current_letter)
                update_screen()

                print(
                    "Current letter:",
                    LETTERS[current_letter]
                )

    time.sleep_ms(5)
