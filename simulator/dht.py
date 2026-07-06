class DHT11:
    def __init__(self, pin):
        self.pin = pin
        self._temperature = 24
        self._humidity = 55

    def measure(self):
        return None

    def temperature(self):
        return self._temperature

    def humidity(self):
        return self._humidity
