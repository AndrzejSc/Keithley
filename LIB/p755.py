import time
import serial


class P755:
    def __init__(self, port, baudrate=2400, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self._isP755Connected: bool = False
        self.currentMeasurement: float = 0.0
        self.deviceIDN: str = ""
        self.errorMessage: str = ""
        self.deviceNameToCheck: str = "P-755"

    def connect(self) -> bool:
        try:
            self.connection = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        except serial.SerialTimeoutException as e:
            print('Błąd połączenia z P-755: Timeout')
            self.errorMessage = str(e)
            self._isP755Connected = False
            return False
        except serial.SerialException as e:
            print('Błąd połączenia z P-755: ' + str(e))
            self.errorMessage = str(e)
            self._isP755Connected = False
            return False
        else:
            if self.connection.isOpen():
                print("Połączenie z P-755 - nie sprawdzono poprawności urządzenia")
                # TODO Sprawdzenie IDN - do zaimplementowania. Komenda? Odpowiedź?
                # self.readIDN()
                # if self.checkDeviceIDN():
                #     print('Połączono z P-755!')
                #     self._isP755Connected = True
                #     self.initDevice()
                #     return True
                # else:
                #     self.errorMessage = "Urządzenie nieznane lub nie odpowiada"
                #     return False
            else:
                print('Inny błąd połączenia!')
                self._isP755Connected = False
                self.errorMessage = "Nie otwarto połączenia z portem COM"
                return False

    # Funkcja disconnect - NIE TESTOWANA
    def disconnect(self) -> bool:
        try:
            if self.connection.isOpen():
                self.connection.close()
                self._isP755Connected = False
                print("Zamknięto poprawnie port P755")
                return True
            else:
                print("Błąd zamykania portu P755 - port nie jest otwarty")
                self.errorMessage = "Błąd zamykania portu P755 - port nie jest otwarty"
                return False
        except serial.SerialException as e:
            print('Błąd zamykania połaczenia P755: ' + str(e))
            self.errorMessage = str(e)
            return False

    def initDevice(self):
        # Ustawienia, które muszą być wykonane przed odczytem pomiarów
        pass

    def read(self) -> str:
        self.currentMeasurement = ""
        self.connection.flush()
        self.connection.write(b'\xFC')
        time.sleep(0.1)
        while True:
            # print("Czytam 1 bajt!")
            char: bytes = self.connection.read()
            if char == "\n".encode():
                break
            else:
                self.currentMeasurement += char.decode()
        self.currentMeasurement = self.currentMeasurement.strip()
        self.currentMeasurement = self.currentMeasurement.split()
        # print(str(self.currentMeasurement[0]))
        return self.currentMeasurement[0]

    def isConnected(self) -> bool:
        if self._isP755Connected:
            return True
        else:
            return False

    # TODO zmienić funkję na sprawdzającą czy połączono z prawidlowym urządzeniem
    def readIDN(self) -> str:
        self.deviceIDN = ""
        self.connection.write("*IDN?\n".encode())
        time.sleep(0.1)
        while True:
            try:
                char: bytes = self.connection.read()
                if char == ("\r".encode() or "\n".encode()):
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
        if self.deviceIDN[0:8] == "KEITHLEY":
            # print("Keithler checked")
            return self.deviceIDN
        else:
            return "Nieznane urządzenie"

    def checkDeviceIDN(self) -> bool:
        print(self.deviceIDN)
        # TODO - Sprawdzić nazwę i funkcję ReadIDN
        if self.deviceIDN[0:8] == self.deviceNameToCheck:
            return True
        else:
            self.errorMessage = "Urządzenie nieznane lub nie odpowiada"
            return False