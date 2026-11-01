# Recovery safety boundary. Keep independent from editable application config.
from machine import Pin


def safe_outputs():
    # Physical installation: six active-low relays. High means OFF.
    for number in (19, 5, 18, 25, 26, 27):
        Pin(number, Pin.OUT, value=1)


safe_outputs()
