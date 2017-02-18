import logging
import sys
import threading
import time

# using hidapi Cython interface from https://github.com/trezor/cython-hidapi using BSD license
import hid

class Powermate(object):

    VENDOR_ID = 0x077d
    PRODUCT_ID = 0x0410

    _REPORT_ID = 0
    _REPORT_LENGTH = 9

    _SET_STATIC_BRIGHTNESS = 1
    _SET_PULSE_ASLEEP = 2
    _SET_PULSE_AWAKE = 3
    _SET_PULSE_MODE = 4    

    _WHEEL = intern("wheel")
    _BUTTON = intern("button")
    _UP = intern("up")
    _DOWN = intern("down")

    def __init__(self):

        self.__button_state = None      # unknown
        self.__callbacks = []
        self.__dev = hid.device()
        try:
            self.__dev.open(self.VENDOR_ID, self.PRODUCT_ID)
        except:
            raise Exception("Could not find the PowerMate")

        logging.debug("Manufacturer: %s, product: %s",
                      self.__dev.get_manufacturer_string(),
                      self.__dev.get_product_string())

        self.__dev.set_nonblocking(1)

    def __command(self, command, *args):
        featureReport = [self._REPORT_ID, 0x41, 1, command, 0, 0, 0, 0, 0]
        for i in range(len(args)):
            featureReport[i + 4] = args[i]
        self.__dev.send_feature_report(featureReport)

    def __inspect(self):
        report = self.__dev.get_feature_report(self._REPORT_ID, self._REPORT_LENGTH)
        return report

    @property
    def brightness(self):
        report = self.__inspect()
        # brightness is third byte
        return report[3]

    @brightness.setter
    def brightness(self, brightness):
        """Sets the brightness of the PowerMate's LED
             brightness: A value from 0 (darkest) to 255 (brightest), inclusive
        """
        self.__command(self._SET_STATIC_BRIGHTNESS, brightness)

    @property
    def pulsing(self):
        report = self.__inspect()
        return True if (report[4] & 0x01) else False

    @pulsing.setter
    def pulsing(self, pulse):
        """Sets whether or not to pulse constantly
             pulse: A boolean value indicating whether to pulse (True), or not
             (False)
        """
        self.__command(self._SET_PULSE_AWAKE, 1 if pulse else 0)

    @property
    def pulsing_when_asleep(self):
        report = self.__inspect()
        return True if (report[4] & 0x04) else False

    @pulsing_when_asleep.setter
    def pulsing_when_asleep(self, pulse):
        """Sets whether or not to pulse when the computer is asleep
             pulse: A boolean value indicating whether to pulse (True), or not
             (False)
        """
        self.__command(self._SET_PULSE_ASLEEP, 1 if pulse else 0)

    @property
    def pulse_speed(self):
        report = self.__inspect()
        speed = report[5]
        if report[4] & 0x20:        # fast
            speed += 255
        elif report[4] & 0x10:      # normal
            speed = 255
        else:
            speed = (254 - speed)
        return speed

    @pulse_speed.setter
    def pulse_speed(self, speed):
        """Sets the pulse speed of the PowerMate's LED
             speed: A value from -255 to 255 (inclusive). Lower values are
               slower, higher values are faster
        """
        if speed < 255:
            ptable = 0;
            speed = 254 - speed
        elif pulseSpeed == 255:
            ptable = 1;
            speed = 0;
        else:
            ptable = 2;
            speed -= 255;

        self.__command(self._SET_PULSE_MODE, ptable, speed);

    @property
    def button_state(self):
        report = self.__inspect()
        return response[0]

    def register_callback(self, callback):
        self.__callbacks.append(callback)

    def unregister_callback(self, callback):
        if callback in self.__callbacks:
            self.__callbacks.remove(callback)

    def notify(self, event):
        for callback in self.__callbacks:
            callback(event)

    def __parse_event(self, data):
        button_state = data[0]
        if button_state != self.__button_state:
            self.__button_state = button_state
            self.notify((self._BUTTON, self._DOWN if button_state else self._UP))

        wheel_delta = data[1]
        if wheel_delta > 0:
            if wheel_delta & 0x80:
                wheel_delta -= 256
            self.notify((self._WHEEL, wheel_delta))

    def __watch(self):
        while True:
            try:
                data = self.__dev.read(60, timeout_ms=100)
                if data:
                    self.__parse_event(data)
            except Exception as x:
                logging.warn("exception '%s' on Powermate watch loop", x)            

    def watch(self):
        self.__event_thread = threading.Thread(target=self.__watch)
        self.__event_thread.daemon = True
        self.__event_thread.start()


if __name__ == "__main__":

    p = Powermate()
    p.brightness = 100
    print p.brightness, p.pulse_speed
    p.register_callback(lambda event: sys.stdout.write(str(event) + "\n"))
    p.watch()
    time.sleep(1000)
