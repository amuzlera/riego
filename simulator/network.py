STA_IF = 0


class WLAN:
    def __init__(self, interface):
        self.interface = interface
        self._active = False
        self._connected = False
        self._ssid = None
        self._password = None
        self._ifconfig = ("127.0.0.1", "255.255.255.0", "127.0.0.1", "127.0.0.1")

    def active(self, value=None):
        if value is None:
            return self._active
        self._active = bool(value)
        return self._active

    def connect(self, ssid, password):
        self._ssid = ssid
        self._password = password
        self._connected = True

    def isconnected(self):
        return self._connected

    def ifconfig(self, cfg=None):
        if cfg is None:
            return self._ifconfig
        self._ifconfig = tuple(cfg)
        return self._ifconfig

    def status(self):
        return 3 if self._connected else 1
