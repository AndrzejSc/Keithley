import time
import serial


class Vaisala:
    def __init__(self, port, baudrate=19200, timeout=1):
        self.deviceIDN = ""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self._isVaisalaConnected: bool = False
        self.measurementTable: list = list()
        self.currentMeasurementRH: str = ""
        self.currentMeasurementTemp: str = ""
        self.errorMessage: str = ""
        self.deviceNameToCheck: str = "HMT"

    def connect(self) -> bool:
        try:
            self.connection = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        except serial.SerialTimeoutException:
            print('Błąd połączenia z Vaisala: Timeout')
            self._isVaisalaConnected = False
            return False
        except serial.SerialException as e:
            print('Błąd połączenia z Vaisala: ' + str(e))
            self.errorMessage = str(e)
            self._isVaisalaConnected = False
            return False
        else:
            if self.connection.isOpen():
                self.readIDN()
                if self.checkDeviceIDN():
                    print('Połączono z Vaisala!')
                    self._isVaisalaConnected = True
                    self.initDevice()
                return True
            else:
                print('Inny błąd połączenia!')
                self._isVaisalaConnected = False
                return False

    # Funkcja disconnect - NIE TESTOWANA
    def disconnect(self) -> bool:
        try:
            if self.connection.isOpen():
                self.connection.close()
                self._isVaisalaConnected = False
                print("Zamknięto poprawnie port Vaisala HMT")
                return True
            else:
                print("Błąd zamykania portu Vaisala HMT - port nie jest otwarty")
                self.errorMessage = "Błąd zamykania portu Vaisala HMT - port nie jest otwarty"
                return False
        except serial.SerialException as e:
            print('Błąd zamykania połaczenia Vaisala HMT: ' + str(e))
            self.errorMessage = str(e)
            return False

    def initDevice(self):
        # Ustawienia, które muszą być wykonane przed odczytem pomiarów
        self.connection.write("\r".encode())
        time.sleep(0.1)
        self.connection.write("ECHO=OFF\r".encode())
        time.sleep(0.1)
        self.connection.write("SMODE=STOP\r".encode())
        time.sleep(0.1)
        self.connection.readline()
        self.connection.readline()
        self.connection.readline()
        self.connection.flush()

    def readRH(self) -> str:
        self.currentMeasurementRH = ""
        self.connection.write("SEND\r".encode())
        time.sleep(0.1)
        while True:
            # print("Czytam 1 bajt!")
            char: bytes = self.connection.read()
            if char == ">".encode():
                break
            else:
                self.currentMeasurementRH += char.decode()
        self.currentMeasurementRH = self.currentMeasurementRH.strip()
        self.currentMeasurementRH = self.currentMeasurementRH.split()
        print(str(self.currentMeasurementRH))
        return self.currentMeasurementRH[2]

    def readTemp(self) -> str:
        self.currentMeasurementTemp = ""
        self.connection.write("SEND\r".encode())
        time.sleep(0.1)
        while True:
            # print("Czytam 1 bajt!")
            char: bytes = self.connection.read()
            if char == ">".encode():
                break
            else:
                self.currentMeasurementTemp += char.decode()
        self.currentMeasurementTemp = self.currentMeasurementTemp.strip()
        self.currentMeasurementTemp = self.currentMeasurementTemp.split()
        print(str(self.currentMeasurementTemp))
        return self.currentMeasurementTemp[4]

    def readIDN(self) -> str:
        self.connection.write("?\r".encode())
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

        if self.deviceIDN[0:2] == self.deviceNameToCheck:
            # print("Keithler checked")
            return self.deviceIDN
        else:
            return "Nieznane urządzenie"

    def checkDeviceIDN(self) -> bool:
        print(self.deviceIDN)
        if self.deviceIDN[0:2] == self.deviceNameToCheck:
            return True
        else:
            self.errorMessage = "Urządzenie nieznane lub nie odpowiada"
            return False

    def isConnected(self) -> bool:
        if self._isVaisalaConnected:
            return True
        else:
            return False