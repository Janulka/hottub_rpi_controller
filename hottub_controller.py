import time
import RPi.GPIO as io
import requests
import sys
import signal
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

class HotTubController(object):
    DWEET_URL_POST = "https://dweet.io:443/dweet/quietly/for/%s" % config['dweet']['thing'] 
    DWEET_URL_GET = "https://dweet.io:443/get/latest/dweet/for/%s" % config['dweet']['thing']
    MINIMUM_TEMPERATURE = int(config['temperature']['min'])
    MAXIMUM_TEMPERATURE = int(config['temperature']['max'])
    TEMPERATURE_FILE = config['temperature']['file']
    TEMPERATURE_CONTROL_BUTTON_PIN = int(config['temperature']['button_pin'])
    JETS_BUTTON_PIN = int(config['jets']['button_pin'])
    JET_CONTROLS = ['LOW', 'LOW+LIGHT', 'HIGH+LIGHT', 'HIGH', 'OFF']

    def __init__(self):
        def signal_handler(signal_number, frame):
            print('\nCaught signal %s, exiting HotTub Controller.' % signal_number)
            io.cleanup()
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        io.setmode(io.BCM)
        io.setup(self.JETS_BUTTON_PIN, io.OUT)
        io.setup(self.TEMPERATURE_CONTROL_BUTTON_PIN, io.OUT)
        io.output(self.JETS_BUTTON_PIN, io.HIGH)
        io.output(self.TEMPERATURE_CONTROL_BUTTON_PIN, io.HIGH)
        self._reset_hottub()
        print("Hottub controller is up.")

    def run(self):
        while True:
            jets = 0
            temp = 0
            get_request = requests.get(self.DWEET_URL_GET)

            try:
                content = get_request.json()['with'][0]['content']
                jets = int(content['jets'])
                temp = int(content['temp'])
            except Exception as e:
                if get_request.status_code != 200:
                    print("Caught exception:")
                    print(get_request.status_code, get_request.reason)
                    print(e)
                continue

            reset_dweet = False
            if jets > 0:
                self._set_jet_mode(jets)
                reset_dweet = True
            if temp > 0:
                self._set_temperature(temp)
                reset_dweet = True
            if jets == -1 and temp == -1:
                self._reset_hottub()
                reset_dweet = True
            if reset_dweet:
                requests.post(self.DWEET_URL_POST, data={'jets': 0, 'temp': 0})
            # Rate limit request.
            time.sleep(2)

    def _get_current_temperature(self):
        with open(self.TEMPERATURE_FILE, 'r') as f:
            return int(f.read().strip())

    def _get_current_desired_temperature(self):
        # This will make the display blink and show the current desired temperature.
        print("Toggle once.")
        self._toggle_once(self.TEMPERATURE_CONTROL_BUTTON_PIN)
        desired_temperature = self._get_current_temperature()
        print("Reading temperature %i." % desired_temperature)
        # Wait for the temperature display to stop blinking.
        time.sleep(3.0)
        print("Done reading.")
        return desired_temperature

    def _reset_hottub(self):
        self._temperature_toggle_direction_is_up = False
        self._jet_controls_index = 1

    def _set_jet_mode(self, jet_mode):
        if jet_mode >= len(self.JET_CONTROLS):
            jet_mode = len(self.JET_CONTROLS)
        print("Setting jets to %s." % self.JET_CONTROLS[jet_mode - 1])
        while jet_mode != self._jet_controls_index:
            self._toggle(self.JETS_BUTTON_PIN)
            self._jet_controls_index += 1
            if self._jet_controls_index > len(self.JET_CONTROLS):
                self._jet_controls_index = 1
            print("Jets now set to %s." % self.JET_CONTROLS[self._jet_controls_index - 1])

    def _switch_direction(self):
        self._temperature_toggle_direction_is_up = not self._temperature_toggle_direction_is_up
        if self._temperature_toggle_direction_is_up:
            print('Temperature direction now is UP.')
        else:
            print('Temperature direction now is DOWN.')

    def _set_temperature(self, desired_temperature):
        current_temperature = self._get_current_temperature()
        current_desired_temperature = self._get_current_desired_temperature()
        print('Current is %i, current desired is %i, desired is %i.' % (
            current_temperature, current_desired_temperature, desired_temperature))

        if desired_temperature == current_desired_temperature:
            print('Target already at desired temperature %i.' % desired_temperature)
            return

        if desired_temperature > self.MAXIMUM_TEMPERATURE:
            print('Clipping desired temperature %i to %i.' % (desired_temperature, self.MAXIMUM_TEMPERATURE))
            desired_temperature = self.MAXIMUM_TEMPERATURE
        elif desired_temperature < self.MINIMUM_TEMPERATURE:
            print('Clipping desired temperature %i to %i.' % (desired_temperature, self.MINIMUM_TEMPERATURE))
            desired_temperature = self.MINIMUM_TEMPERATURE

        ready_for_input = False
        while desired_temperature != current_desired_temperature:
            print('Temperature now at %i.' % current_desired_temperature)
            if desired_temperature > current_desired_temperature:
                print('Trying to increase temperature from %i to %i.' % (
                    current_desired_temperature, desired_temperature))
                if self._temperature_toggle_direction_is_up:
                    if not ready_for_input:
                        ready_for_input = True
                        # This will make the display blink and ready for input
                        self._toggle(self.TEMPERATURE_CONTROL_BUTTON_PIN)
                    self._toggle(self.TEMPERATURE_CONTROL_BUTTON_PIN)
                    current_desired_temperature += 1
                else:
                    self._toggle_temperature_direction()

            elif desired_temperature < current_desired_temperature:
                print('Trying to decrease temperature from %i to %i.' % (
                    current_desired_temperature, desired_temperature))
                if self._temperature_toggle_direction_is_up:
                    self._toggle_temperature_direction()
                else:
                    if not ready_for_input:
                        ready_for_input = True
                        # This will make the display blink and ready for input
                        self._toggle(self.TEMPERATURE_CONTROL_BUTTON_PIN)
                    self._toggle(self.TEMPERATURE_CONTROL_BUTTON_PIN)
                    current_desired_temperature -= 1

        # Once we are done, the direction has changed.
        self._switch_direction()

        print("Verifying the temperature.")
        # Wait for the temperature display to stop blinking.
        time.sleep(5.0)
        current_temperature = self._get_current_temperature()
        current_desired_temperature = self._get_current_desired_temperature()
        print("Current is %i, current desired is %i, desired is %i." % (
            current_temperature, current_desired_temperature, desired_temperature))
        if desired_temperature == current_desired_temperature:
            print('Target temperature succesfully set to %i.' % desired_temperature)
        else:
            self._switch_direction()
            self._set_temperature(desired_temperature)

    def _toggle_temperature_direction(self):
        io.output(self.TEMPERATURE_CONTROL_BUTTON_PIN, io.LOW)
        if self._temperature_toggle_direction_is_up:
            print('Waiting for temperature direction to change from up to down.')
        else:
            print('Waiting for temperature direction to change from down to up.')
        time.sleep(0.1)
        io.output(self.TEMPERATURE_CONTROL_BUTTON_PIN, io.HIGH)
        self._temperature_toggle_direction_is_up = not self._temperature_toggle_direction_is_up
        time.sleep(5.0)
        print('Temperature direction changed.')

    def _toggle(self, pin):
        io.output(pin, io.LOW)
        time.sleep(0.1)
        io.output(pin, io.HIGH)
        time.sleep(0.9)

    def _toggle_once(self, pin):
        self._toggle(pin)
        time.sleep(3.0)
        self._temperature_toggle_direction_is_up = not self._temperature_toggle_direction_is_up
        if self._temperature_toggle_direction_is_up:
            print('Temperature direction now is UP.')
        else:
            print('Temperature direction now is DOWN.')

if __name__ == "__main__":
    hot_tub_controller = HotTubController()
    hot_tub_controller.run()
