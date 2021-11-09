import time
import serial


class Fluke1595:
    def __init__(self, port, channel, baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._channel = channel
        self.connection = None
        self._isFlukeConnected: bool = False
        self.currentMeasurement: float = 0.0
        self.deviceIDN: str = ""
        self.errorMessage: str = ""
        self.deviceNameToCheck: str = "FLUKE"

    def connect(self) -> bool:
        try:
            self.connection = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        except serial.SerialTimeoutException as e:
            print('Błąd połączenia z Fluke 1595A: Timeout')
            self.errorMessage = str(e)
            self._isFlukeConnected = False
            return False
        except serial.SerialException as e:
            print('Błąd połączenia z Fluke 1595A: ' + str(e))
            self.errorMessage = str(e)
            self._isFlukeConnected = False
            return False
        else:
            # Jeśli połączono, sprawdz IDN urządzenia. Jeśli to FLUKE to True
            if self.connection.isOpen():
                self.readIDN()
                # Sprawdzamy czy połączyliśmy się z FLUKE
                if self.checkDeviceIDN():
                    print('Połączono z Fluke')
                    self._isFlukeConnected = True
                    self.initDevice()
                    return True
                else:
                    self.errorMessage = "Urządzenie nieznane lub nie odpowiada."
                    return False
            else:
                print('Inny błąd połączenia!')
                self._isFlukeConnected = False
                self.errorMessage = "Nie otwarto połączenia z portem COM. Nieznany błąd."
                return False

    # Funkcja disconnect - NIE TESTOWANA
    def disconnect(self) -> bool:
        try:
            if self.connection.isOpen():
                self.connection.close()
                self._isFlukeConnected = False
                print("Zamknięto poprawnie port Fluke")
                return True
            else:
                print("Błąd zamykania portu Fluke - port nie jest otwarty")
                self.errorMessage = "Błąd zamykania portu Fluke - port nie jest otwarty"
                return False
        except serial.SerialException as e:
            print('Błąd zamykania połaczenia Fluke: ' + str(e))
            self.errorMessage = str(e)
            return False

    def initDevice(self):
        # Ustawienia, które muszą być wykonane przed odczytem pomiarów
        self.connection.write(":INIT:CONT\n".encode())
        time.sleep(0.05)
        pass

    def read(self) -> str:
        self.currentMeasurement = ""

        self.connection.write((":FETC?" + str(self._channel) + "\n").encode())
        time.sleep(0.05)
        while True:
            char: bytes = self.connection.read()
            if char == "\r".encode():
                break
            else:
                self.currentMeasurement += char.decode()
        # print(float(self.currentMeasurement[0:9]))
        return self.currentMeasurement[0:9]

    def isConnected(self) -> bool:
        if self._isFlukeConnected:
            return True
        else:
            return False

    def readIDN(self) -> str:
        self.deviceIDN = ""
        self.connection.write("*IDN?\n".encode())
        time.sleep(0.1)
        while True:
            try:
                char: bytes = self.connection.read()
                if char == ("\r".encode() or "\n".encode()):
                    # print("BREAK")
                    break
                if char == b'':
                    # print("DIPA")
                    break
                else:
                    self.deviceIDN += char.decode()
            except serial.SerialTimeoutException:
                self.errorMessage = "Serial Timeout Exception"
                print("Serial Timeout Exception")
                break
            except:
                self.errorMessage = "Can't decode received bytes"
                print("Can't decode received bytes")
                break
        if self.deviceIDN[0:5] == "FLUKE":
            # print("FLUKE checked")
            return self.deviceIDN
        else:
            return "Nieznane urządzenie"

    def checkDeviceIDN(self) -> bool:
        print(self.deviceIDN)
        if self.deviceIDN[0:5] == self.deviceNameToCheck:
            return True
        else:
            self.errorMessage = "Urządzenie nieznane lub nie odpowiada"
