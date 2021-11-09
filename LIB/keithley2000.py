import time
from datetime import datetime

import serial


class Keithley2000:
    def __init__(self, port, baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self._isKeithleyConnected: bool = False
        self.measurementTable: list = list()
        self.currentMeasurement: str = ""
        self.deviceIDN: str = ""
        self.errorMessage: str = ""
        self.deviceNameToCheck: str = "KEITHLEY"

    def connect(self) -> bool:
        try:
            self.connection = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        except serial.SerialTimeoutException as e:
            print('Błąd połączenia z Keithley: Timeout')
            self.errorMessage = str(e)
            self._isKeithleyConnected = False
            return False
        except serial.SerialException as e:
            print('Błąd połączenia z Keithley2000: ' + str(e))
            self.errorMessage = str(e)
            self._isKeithleyConnected = False
            return False
        else:
            if self.connection.isOpen():
                self.readIDN()
                # Jeśli połączone urządzenie to KEITHLEY
                if self.checkDeviceIDN():
                    self._isKeithleyConnected = True
                    self.initDevice()
                    return True
                else:
                    self.errorMessage = "Urządzenie nieznane lub nie odpowiada"
                    return False
            else:
                print('Inny błąd połączenia!')
                self._isKeithleyConnected = False
                self.errorMessage = "Nie otwarto połączenia z portem COM"
                return False

    def disconnect(self) -> bool:
        try:
            if self.connection.isOpen():
                self.connection.close()
                self._isKeithleyConnected = False
                print("Zamknięto poprawnie port Keithley")
                return True
            else:
                print("Błąd zamykania portu Keithley - port nie jest otwarty")
                self.errorMessage = "Błąd zamykania portu Keithley - port nie jest otwarty"
                return False
        except serial.SerialException as e:
            print('Błąd zamykania połaczenia Keithley: ' + str(e))
            self.errorMessage = str(e)
            return False

    def initDevice(self):
        # Ustawienia, które muszą być wykonane przed odczytem pomiarów
        self.connection.write("*RST\n".encode())
        time.sleep(0.1)
        self.connection.write("INIT\n".encode())
        time.sleep(0.1)
        # self.connection.write("ROUT:OPEN:ALL\n".encode())
        self.connection.write(":FUNC 'FRES'\n".encode())
        time.sleep(0.1)
        self.changeChannel(1)
        self.connection.write("RES:RANG 1000\n".encode())
        time.sleep(0.1)
        # TODO Zmiana formatu danych na rs

    def readAllChannels(self) -> list:
        startTime = time.time()
        for i in range(1, 11):
            self.changeChannel(i)
            self.measurementTable[i] = (self.connection.read())
            print("CH " + str(i) + ":" + str(self.measurementTable[i]))
        print("Keithley czas pomiarów seriipip install auto-py-to-exe: " + str(time.time() - startTime))
        return self.measurementTable

    def readChannel(self, channel) -> str:
        self.changeChannel(channel)
        self.currentMeasurement = self.read()
        return self.currentMeasurement

    def read(self) -> str:
        self.currentMeasurement = ""
        self.connection.write(":READ?\n".encode())
        #time.sleep(0.05)

        while True:
            tstart = time.time()
            char: bytes = self.connection.read(1)
            #print(char)
            t = time.time() - tstart
            #print(t)

            if char == "\r".encode():
                break
            else:
                self.currentMeasurement += char.decode()
        # print(self.currentMeasurement)
        return self.currentMeasurement

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
        if self.deviceIDN[0:8] == self.deviceNameToCheck:
            return True
        else:
            self.errorMessage = "Urządzenie nieznane lub nie odpowiada"
            return False

    def changeChannel(self, channel):
        tempCommand: bytes = ("ROUT:CLOS (@" + str(channel) + ")\n").encode()
        self.connection.write(tempCommand)
        time.sleep(0.05)

    def isConnected(self) -> bool:
        if self._isKeithleyConnected:
            return True
        else:
            return False
