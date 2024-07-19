###
### ls /dev/spi*
### cat /proc/cpuinfo

### sudo /opt/nvidia/jetson-io/jetson-io.py 
### docker build --network="host" -t led .
### sudo modprobe spidev && docker run --privileged -it --entrypoint /bin/bash led
###
### led_controller_spi1 = LEDController(spi_bus=1)  # For SPI 1
### led_controller_spi2 = LEDController(spi_bus=2)  # For SPI 2
###

'''
System Initializing: blinking yellow light
System Ready: gentle pulsing blue light
User Match: blinking green light
User Not Match: blinking red light
Face Too Far Left: blue light moving from left to center
Face Too Far Right: blue light moving from right to center
Face Too Small: blue light moving from both sides towards the center
Device Not Found: steady orange light
Network Connectivity Issues: steady yellow light
General System Error: steady pink light
'''

from __future__ import annotations

import time
import board
import busio
import neopixel_spi as neopixel
import threading
import datetime

class LEDController(threading.Thread):
    def __init__(self, spi_bus=1):
        super(LEDController, self).__init__()
        # Configuration:
        self.NUM_PIXELS = 8
        self.PIXEL_ORDER = neopixel.GRB
        self.DELAY = 0.1  # Adjusted for quicker animations
        self.current_state = None
        self.running = False
        self.lock = threading.Lock()
        self.expected_state = None
        self.state_start_time = datetime.datetime.now()
        self.current_state_min_duration_ms = 0  # Store minimum duration in milliseconds for the current state

        # Theme and Configuration Settings:
        self.THEME_COLORS = {
            'initializing': (255, 150, 0),  # blinking yellow
            'ready_idle': (0, 0, 255),  # Blue
            'detecting_presence': (0, 255, 255),  # Cyan
            'authentication_in_progress': (0, 0, 255),  # Blue for processing
            'access_granted': (0, 255, 0),  # Green
            'access_denied': (255, 0, 0),  # Red
            'device_not_found': (255, 50, 0),  # Orange
            'general_system_error': (128, 0, 128),  # Pink
            'network_issues': (255, 150, 0),  # Yellow color
            'face_position': (0, 255, 255),  # Cyan for face positioning
            'secondary': (0, 0, 128),  # Secondary color, darker shade for gradients
            # Alexa light ring colors
            'alexa_listening': (0, 0, 255),  # Directional blue
            'alexa_thinking': (0, 0, 255),  # Alternating blue
            'alexa_responding': (0, 0, 255),  # Pulsing blue
            'alexa_setup': (255, 165, 0),  # Cycling orange
            'alexa_mic_muted': (255, 0, 0),  # Solid red
            'alexa_notification': (255, 255, 0),  # Pulsing yellow
            'alexa_incoming_call': (0, 255, 0),  # Pulsing green
            'alexa_active_call': (0, 255, 0),  # Cycling green
            'alexa_volume': (255, 255, 255),  # Contextual white
            'alexa_error': (128, 0, 128),  # Quickly pulsing purple
            'alexa_do_not_disturb': (128, 0, 128),  # Slowly pulsing purple
            'alexa_away_mode': (255, 255, 255),  # Cycling white
        }

        self.BRIGHTNESS = 1.0  # Overall brightness of the LEDs
        self.ANIMATION_SPEED = 0.3  # General speed for animations

        # Setup SPI and pixels based on the selected SPI bus:
        if spi_bus == 1:
            spi = board.SPI()  # Default SPI interface
        elif spi_bus == 2:
            spi = busio.SPI("GP36_SPI3_CLK", MISO="GP37_SPI3_MISO", MOSI="GP38_SPI3_MOSI")
        else:
            raise ValueError("Invalid SPI bus specified")

        self.pixels = neopixel.NeoPixel_SPI(spi, self.NUM_PIXELS, pixel_order=self.PIXEL_ORDER, auto_write=False)
        self.pixels.brightness = self.BRIGHTNESS

    # Function Definitions:
    def interruptible_sleep(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            with self.lock:
                if self.expected_state != self.current_state:
                    return False  # Indicates the sleep was interrupted
            time.sleep(min(0.1, duration - (time.time() - start_time)))  # Sleep for short intervals
        return True  # Indicates the sleep completed normally


    def pulse(self, led_indices, color, steps, state_name):
        for step in range(steps):
            with self.lock:
                # Check if the state has changed or the controller has stopped
                if self.current_state != state_name or not self.running:
                    return
            if step <= steps // 2:
                brightness = step / (steps // 2)
            else:
                brightness = (steps - step) / (steps // 2)
            adjusted_color = (int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness))
            for led_index in led_indices:
                self.pixels[led_index] = adjusted_color
            self.pixels.show()
            if not self.interruptible_sleep(self.DELAY):
                break;


    def clear_pixels(self, execute=False):
        if execute:
            for i in range(self.NUM_PIXELS):
                self.pixels[i] = (0, 0, 0)
            self.pixels.show()

    def flow(self, color, steps):
        """Creates a flowing light effect across the LEDs."""
        for step in range(steps):
            with self.lock:
                if self.current_state != 'authentication_in_progress':
                    return  # Exit if the state has changed
            for i in range(self.NUM_PIXELS):
                # Calculate the position for each step
                position = abs((step % (self.NUM_PIXELS * 2)) - i)

                # Fade color based on distance from the center
                fade = max(0, (self.NUM_PIXELS/2 - position) / (self.NUM_PIXELS/2))
                adjusted_color = (int(color[0] * fade), int(color[1] * fade), int(color[2] * fade))

                self.pixels[i] = adjusted_color

            self.pixels.show()
            if not self.interruptible_sleep(self.DELAY):
                break;

    def directional_gradient(self, start_side, primary_color, secondary_color):
        steps = self.NUM_PIXELS // 2
        range_func = range(steps) if start_side == 'left' else reversed(range(steps))
        for step in range_func:
            for i in range(self.NUM_PIXELS):
                distance = min(abs(i - step), abs(self.NUM_PIXELS - 1 - i - step))
                if i == step or i == self.NUM_PIXELS - 1 - step:
                    color = primary_color
                elif i == 0 or i == self.NUM_PIXELS - 1:
                    color = secondary_color
                else:
                    color = secondary_color if distance > 1 else primary_color
                self.pixels[i] = color
            self.pixels.show()
            # Check if the state has changed
            with self.lock:
                if self.current_state != 'directional_gradient':
                    return
            if not self.interruptible_sleep(self.ANIMATION_SPEED):
                break;

    def set_face_position_indicator(self, position, primary_color, secondary_color):
        self.clear_pixels()
        for i in range(self.NUM_PIXELS):
            if position == 'left' and i < self.NUM_PIXELS // 3:
                self.pixels[i] = primary_color
            elif position == 'right' and i > 2 * self.NUM_PIXELS // 3:
                self.pixels[i] = primary_color
            elif position == 'center' and self.NUM_PIXELS // 3 <= i <= 2 * self.NUM_PIXELS // 3:
                self.pixels[i] = primary_color
            else:
                self.pixels[i] = secondary_color
        self.pixels.show()

    # State Functions:
    
    '''
    def system_ready_idle(self):
        self.clear_pixels()
        self.pulse([i for i in range(self.NUM_PIXELS)], self.THEME_COLORS['ready_idle'], 60, 'system_ready_idle')
    '''

    def system_ready_idle(self):
        """Displays an LED pattern to indicate that the device is initializing."""
        self.clear_pixels()
        # Example pattern: A gentle pulsing light with minimum brightness
        steps = 15
        min_brightness = 0.2  # Minimum brightness level (30%)
        max_brightness = 1.0  # Maximum brightness level (100%)

        for _ in range(1):  # Repeat the pattern a few times
            for step in range(steps):
                # Adjust brightness between min_brightness and max_brightness
                brightness = min_brightness + (max_brightness - min_brightness) * (step / (steps - 1))
                color = [int(c * brightness) for c in self.THEME_COLORS['ready_idle']]
                for i in range(self.NUM_PIXELS):
                    self.pixels[i] = tuple(color)
                self.pixels.show()
                if not self.interruptible_sleep(0.08):
                    break
            
            for step in reversed(range(steps)):
                # Adjust brightness between max_brightness and min_brightness
                brightness = min_brightness + (max_brightness - min_brightness) * (step / (steps - 1))
                color = [int(c * brightness) for c in self.THEME_COLORS['ready_idle']]
                for i in range(self.NUM_PIXELS):
                    self.pixels[i] = tuple(color)
                self.pixels.show()
                if not self.interruptible_sleep(0.08):
                    break
            

    def detecting_presence(self):
        self.clear_pixels()
        self.directional_gradient('center', self.THEME_COLORS['detecting_presence'], self.THEME_COLORS['secondary'])

    def authentication_in_progress(self):
        self.clear_pixels()
        self.flow(self.THEME_COLORS['authentication_in_progress'], 100)

    def access_granted(self):
        self.clear_pixels()
        for _ in range(3):
            self.pulse([i for i in range(self.NUM_PIXELS)], self.THEME_COLORS['access_granted'], 10, 'access_granted')
            if not self.interruptible_sleep(0.1):
                break

    def access_denied(self):
        self.clear_pixels()
        for _ in range(5):
            self.pulse([i for i in range(self.NUM_PIXELS)], self.THEME_COLORS['access_denied'], 5, 'access_denied')
            if not self.interruptible_sleep(0.1):
                break

    def system_error_or_malfunction(self):
        """Displays a fixed color pattern to indicate a system error or malfunction."""
        error_color = self.THEME_COLORS['general_system_error']  # Color for system error
        self.clear_pixels()
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = error_color
        self.pixels.show()
        if not self.interruptible_sleep(0.5):  # Stay on for half a second
            return
    
    def device_not_found(self):
        """Displays a fixed color pattern to indicate a system error or malfunction."""
        error_color = self.THEME_COLORS['device_not_found']  # Color for system error
        self.clear_pixels()
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = error_color
        self.pixels.show()
        if not self.interruptible_sleep(0.5):  # Stay on for half a second
            return

    def network_connectivity_issues(self):
        """Displays a fixed color pattern to indicate a system error or malfunction."""
        error_color = self.THEME_COLORS['network_issues']  # Color for system error
        self.clear_pixels()
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = error_color
        self.pixels.show()
        if not self.interruptible_sleep(0.5):  # Stay on for half a second
            return
    
    '''
    def network_connectivity_issues(self):
        """Displays a blinking yellow pattern to indicate network connectivity issues."""
        steps = 10  # Number of steps in the blink cycle
        for _ in range(5):  # Number of blinking cycles
            # Blink on
            for i in range(self.NUM_PIXELS):
                self.pixels[i] = self.THEME_COLORS['network_issues']  # Yellow
            self.pixels.show()
            if not self.interruptible_sleep(0.5):  # Stay on for half a second
                break

            # Blink off
            self.clear_pixels()
            if not self.interruptible_sleep(0.5):  # Off for half a second
                break
    '''

    def face_too_left(self):
        self.clear_pixels()
        # Set all LEDs to blue initially
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = self.THEME_COLORS['secondary']  # Assuming 'secondary' is blue
        self.pixels.show()

        # Move a cyan light from left to center
        for i in range(self.NUM_PIXELS // 2):
            with self.lock:
                if self.current_state != 'face_too_left':
                    return
            self.pixels[i] = self.THEME_COLORS['face_position']  # Set to cyan
            if i > 0:
                self.pixels[i - 1] = self.THEME_COLORS['secondary']  # Set the previous one back to blue
            self.pixels.show()
            if not self.interruptible_sleep(self.ANIMATION_SPEED):
                break

    def face_too_right(self):
        self.clear_pixels()
        # Set all LEDs to blue initially
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = self.THEME_COLORS['secondary']  # Assuming 'secondary' is blue
        self.pixels.show()

        # Move a cyan light from right to center
        for i in reversed(range(self.NUM_PIXELS // 2, self.NUM_PIXELS)):
            with self.lock:
                if self.current_state != 'face_too_right':
                    return
            self.pixels[i] = self.THEME_COLORS['face_position']  # Set to cyan
            if i < self.NUM_PIXELS - 1:
                self.pixels[i + 1] = self.THEME_COLORS['secondary']  # Set the next one back to blue
            self.pixels.show()
            if not self.interruptible_sleep(self.ANIMATION_SPEED):
                break

    def face_not_clear(self):
        self.clear_pixels()
        # Set all LEDs to blue initially
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = self.THEME_COLORS['secondary']  # Assuming 'secondary' is blue
        self.pixels.show()

        # Move cyan lights from both sides towards the center
        for i in range(self.NUM_PIXELS // 2):
            with self.lock:
                if self.current_state != 'face_not_clear':
                    return
            # Move the left cyan light towards the center
            self.pixels[i] = self.THEME_COLORS['face_position']  # Set to cyan
            if i > 0:
                self.pixels[i - 1] = self.THEME_COLORS['secondary']  # Set the previous one back to blue

            # Move the right cyan light towards the center
            right_index = self.NUM_PIXELS - 1 - i
            self.pixels[right_index] = self.THEME_COLORS['face_position']  # Set to cyan
            if right_index < self.NUM_PIXELS - 1:
                self.pixels[right_index + 1] = self.THEME_COLORS['secondary']  # Set the next one back to blue

            self.pixels.show()
            if not self.interruptible_sleep(self.ANIMATION_SPEED):
                break

    def initializing(self):
        """Displays an LED pattern to indicate that the device is initializing."""
        self.clear_pixels()
        # Example pattern: A blinking orange light
        steps = 5
        for _ in range(3):  # Repeat the pattern a few times
            for brightness in [i/steps for i in range(steps)] + [i/steps for i in reversed(range(steps))]:
                color = [int(c * brightness) for c in self.THEME_COLORS['initializing']]  # Use orange for initializing
                for i in range(self.NUM_PIXELS):
                    self.pixels[i] = tuple(color)
                self.pixels.show()
                if not self.interruptible_sleep(self.DELAY):
                    break

    def run(self):
        self.running = True
        while self.running:
            if self.current_state or self.expected_state:
                self.current_state = self.expected_state
                # Call the method corresponding to the current_state
                getattr(self, self.current_state)()
                
    
    def change_state(self, new_state, min_duration_ms=None, force=False):
        '''
        min_duration_ms (int, optional): The minimum duration in milliseconds that the current state must be maintained 
                                        before transitioning to the new state. Defaults to None, which means no minimum duration is enforced.
        force (bool, optional): If True, the state change will occur immediately, bypassing the minimum duration check. Defaults to False.
        '''
        with self.lock:
            if self.current_state != new_state:
                current_time = datetime.datetime.now()

                # Calculate the elapsed time in milliseconds
                elapsed_time_ms = (current_time - self.state_start_time).total_seconds() * 1000

                # Check if minimum time has elapsed for the current state, unless force is True
                if not force and elapsed_time_ms < self.current_state_min_duration_ms:
                    return  # Do not change state if minimum duration has not elapsed and not forced

                # Proceed with changing the state
                self.clear_pixels()  # Clear the pixels upon state change
                #self.current_state = new_state  # Update the current_state
                self.expected_state = new_state  # Update the expected_state
                self.state_start_time = current_time  # Update the start time of the new state

                # Update the minimum duration for the new state
                self.current_state_min_duration_ms = min_duration_ms if min_duration_ms is not None else 0


    def stop(self):
        with self.lock:
            self.clear_pixels(execute=True)
            self.running = False
            self.current_state = None

    # Alexa Light Ring Animations

    def alexa_listening(self):
        # Directional blue light
        self.clear_pixels()
        for i in range(self.NUM_PIXELS):
            self.pixels[i] = self.THEME_COLORS['alexa_listening']
            if i != 0:
                self.pixels[i - 1] = (0, 0, 0)
            self.pixels.show()
            if not self.interruptible_sleep(0.1):
                break

    def alexa_thinking(self):
        # Alternating blue light
        self.clear_pixels()
        for _ in range(10):  # Repeat the pattern
            for i in range(0, self.NUM_PIXELS, 2):
                self.pixels[i] = self.THEME_COLORS['alexa_thinking']
                if i != 0:
                    self.pixels[i - 1] = (0, 0, 0)
                self.pixels.show()
            self.interruptible_sleep(0.1)
            for i in range(1, self.NUM_PIXELS, 2):
                self.pixels[i] = self.THEME_COLORS['alexa_thinking']
                if i != 1:
                    self.pixels[i - 1] = (0, 0, 0)
                self.pixels.show()
            self.interruptible_sleep(0.1)

    def alexa_responding(self):
        # Pulsing blue light
        self.clear_pixels()
        steps = 10
        for _ in range(5):  # Number of pulsing cycles
            for brightness in [i/steps for i in range(steps)] + [i/steps for i in reversed(range(steps))]:
                color = [int(c * brightness) for c in self.THEME_COLORS['alexa_responding']]
                for i in range(self.NUM_PIXELS):
                    self.pixels[i] = tuple(color)
                self.pixels.show()
                if not self.interruptible_sleep(self.DELAY):
                    break
            if not self.interruptible_sleep(self.ANIMATION_SPEED):
                break

    def alexa_error(self):
        # Quickly pulsing purple light
        self.clear_pixels()
        steps = 15
        for _ in range(5):
            for brightness in [i/steps for i in range(steps)] + [i/steps for i in reversed(range(steps))]:
                color = [int(c * brightness) for c in self.THEME_COLORS['alexa_error']]
                for i in range(self.NUM_PIXELS):
                    self.pixels[i] = tuple(color)
                self.pixels.show()
                if not self.interruptible_sleep(self.DELAY / 2):  # Faster pulsing
                    break
            if not self.interruptible_sleep(self.ANIMATION_SPEED):
                break

def main_menu():
    while True:
        print("\nNeopixel LED Control:")
        print("1. System Ready/Idle")
        print("2. Detecting Presence")
        print("3. Authentication in Progress")
        print("4. Access Granted")
        print("5. Access Denied")
        print("6. General System Error or Malfunction")
        print("7. Network/Connectivity Issues")
        print("8. Face Too Far Left")
        print("9. Face Too Far Right")
        print("10. Face Not Clear Enough")
        print("11. Alexa Listening")
        print("12. Alexa Responding")
        print("13. Alexa Error")
        print("14. Alexa Error for minimum 5 seconds")
        print("15. Initializing")
        print("16. Initializing with Forced State Change")
        print("17. Device Not Found")
        print("0. Exit")
        choice = input("Enter choice: ")
        if choice == '1':
            led_controller.change_state('system_ready_idle')
        elif choice == '2':
            led_controller.change_state('detecting_presence')
        elif choice == '3':
            led_controller.change_state('authentication_in_progress')
        elif choice == '4':
            led_controller.change_state('access_granted')
        elif choice == '5':
            led_controller.change_state('access_denied')
        elif choice == '6':
            led_controller.change_state('system_error_or_malfunction')
        elif choice == '7':
            led_controller.change_state('network_connectivity_issues')
        elif choice == '8':
            led_controller.change_state('face_too_left')
        elif choice == '9':
            led_controller.change_state('face_too_right')
        elif choice == '10':
            led_controller.change_state('face_not_clear')
        elif choice == '11':
            led_controller.change_state('alexa_listening')
        elif choice == '12':
            led_controller.change_state('alexa_responding')
        elif choice == '13':
            led_controller.change_state('alexa_error')
        elif choice == '14':
            led_controller.change_state('alexa_error', min_duration_ms=5000)
        elif choice == '15':
            led_controller.change_state('initializing')
        elif choice == '16':
            led_controller.change_state('initializing', force=True)
        elif choice == '17':
            led_controller.change_state('device_not_found')
        elif choice == '0':
            led_controller.stop()
            break
        else:
            print("Invalid choice. Please enter a number from 0 to 10.")

if __name__ == "__main__":
    # Test code when running this file directly
    # Initialize the LEDController as a thread
    led_controller = LEDController()
    led_controller.start()

    # Run the main menu in the main thread
    main_menu()

    # Stop the LED controller and wait for the thread to finish
    led_controller.stop()
    led_controller.join()  # Wait for the LED controller thread to finish before exiting
