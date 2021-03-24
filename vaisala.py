import time
import serial


class Vaisala:
    def __init__(self, port, baudrate=19200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self._isVaisalaConnected: bool = False
        self.measurementTable: list = list()
        self.currentMeasurementRH: str = ""
        self.currentMeasurementTemp: str = ""
        self.errorMessage: str =""

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
                print('Połączono z Vaisala!')
                self._isVaisalaConnected = True
                self.initDevice()
                return True
            else:
                print('Inny błąd połączenia!')
                self._isVaisalaConnected = False
                return False

    def initDevice(self):
        # Ustawienia, które muszą być wykonane przed odczytem pomiarów
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

    def isConnected(self) -> bool:
        if self._isVaisalaConnected:
            return True
        else:
            return False
