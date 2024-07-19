# MUST RUN WITH SUDO

# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# Simple test for NeoPixels on Raspberry Pi
import time
import board
import neopixel

class LedController:
    def __init__(self, pixel_pin, num_pixels, brightness=0.2, order=neopixel.GRB):
        self.pixel_pin = pixel_pin
        self.num_pixels = num_pixels
        self.ORDER = order
        self.pixels = neopixel.NeoPixel(
            self.pixel_pin, self.num_pixels, brightness=brightness, auto_write=False, pixel_order=self.ORDER
        )

    def wheel(self, pos):
        # Input a value 0 to 255 to get a color value.
        # The colours are a transition r - g - b - back to r.
        if pos < 0 or pos > 255:
            r = g = b = 0
        elif pos < 85:
            r = int(pos * 3)
            g = int(255 - pos * 3)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int(255 - pos * 3)
            g = 0
            b = int(pos * 3)
        else:
            pos -= 170
            r = 0
            g = int(pos * 3)
            b = int(255 - pos * 3)
        return (r, g, b) if self.ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

    def rainbow_cycle(self, wait):
        for j in range(255):
            for i in range(self.num_pixels):
                pixel_index = (i * 256 // self.num_pixels) + j
                self.pixels[i] = self.wheel(pixel_index & 255)
            self.pixels.show()
            time.sleep(wait)

    def solid_color(self, color):
        self.pixels.fill(color)
        self.pixels.show()

    def show_white(self):
        white_color = (255, 255, 255) if self.ORDER in (neopixel.RGB, neopixel.GRB) else (255, 255, 255, 255)
        self.solid_color(white_color)

    def run(self):
        while True:
            # Uncomment the line below to keep showing white color only
            self.show_white()

            # The following lines are for other color cycles. Comment them out if showing white color only.
            # self.solid_color((255, 0, 0))
            # time.sleep(1)
            # self.solid_color((0, 255, 0))
            # time.sleep(1)
            # self.solid_color((0, 0, 255))
            # time.sleep(1)
            # self.rainbow_cycle(0.001)  # rainbow cycle with 1ms delay per step

if __name__ == "__main__":
    pixel_pin = board.D18
    num_pixels = 16
    led_controller = LedController(pixel_pin, num_pixels)
    led_controller.run()
