import datetime
import math
from PySide2.QtCore import Signal, QThread, QObject
import pandas as pd
import vaisala
import keithley2000
import p755
from PySide2.QtCore import QThreadPool


class MySignal(QObject):
    signal_str = Signal(str)


class MeasThread(QThread):
    def __init__(self, keithley2000connection: keithley2000 = None, P755connection: p755 = None, vaisalaConnection: vaisala = None,
                 interval=3, parent=None):
        super(MeasThread, self).__init__()
        # self.exiting = False

        # Zmienne proste
        self._interval = interval
        self._keepRunning = False
        self.isCalibUnitConnected = False  # Zmienna do podłączenia urzadzenia kalibrowanego
        self._gettingProbeCoeffStatus = None  # bool, zmienna określająca czy udało się pobrać współcznynniki PT100

        # Obiekty
        self.rowToAdd = pd.DataFrame()
        # TODO, obsługa 'return result' lub 'return result, probesCoeff'
        getPorbesResultTouple = getProbesCoeff()  # Pobieramy dane z funkcji getProblesCoeff() w formacie bool, lub bool+df
        if getPorbesResultTouple[0]:  # Jeżeli pierwsza zwrócona z getProbesCoeff(), wartość to true
            self.probesCoeff = getPorbesResultTouple[1]
            self._gettingProbeCoeffStatus = True
        else:
            self._gettingProbeCoeffStatus = False

        self._keithley2000connection: keithley2000 = keithley2000connection
        self._P755connection: p755 = P755connection
        self._vaisalaConnection: vaisala = vaisalaConnection

        # Signals
        self.measDoneSignal = MySignal()
        # self.measDoneSignal.signal_str.connect(parent.refreshTable)

        # print("MeasThread instance created!" + str(self))

    def setInterval(self, interval):
        self._interval = interval

    def setKeepRunning(self, state: bool):
        self._keepRunning = state

    def setKeithleyConnection(self, keithleyConnection: keithley2000):
        self._keithley2000connection = keithleyConnection

    def setVaisalaConnection(self, vaisalaConnection: vaisala):
        self._vaisalaConnection = vaisalaConnection

    def setP755Connection(self, p755Connection: p755):
        self._P755connection = p755Connection

    def setGettingProbeCoeffStatus(self, state: bool):
        self._gettingProbeCoeffStatus = state

    def getGettingProbeCoeffStatus(self):
        return self._gettingProbeCoeffStatus

    def getRowToAdd(self):
        return self.rowToAdd

    def run(self):
        print("Wykonuje pomiary z measThread, Interval: " + str(self._interval) + ", keep: " + str(self._keepRunning))
        while self._keepRunning:
            self.doMeasurement()
            self.sleep(self._interval)

    def doMeasurement(self):
        tempTime = getCurrentTime()
        # print("RUN@: " + tempTime)

        # Step 1 - pobieranie godziny
        self.rowToAdd = [tempTime]  # tablica bedzie zawierać tylko 1 element (tempTime), później dołożymy pomiary

        # Step 2 - Odczyt temp z P-755
        if self._P755connection is not None:
            # self.logList.insertItem(0, getCurrentTime() + 'P-755: ' + str(self.tempConnection.read()))
            self.rowToAdd.append(self._P755connection.read())
        else:
            # Jeśli nie mamy połączenia z P-755 to wpisujemy '-'
            self.rowToAdd.append("-")

        # Step 3 - Odczyt z HMT (Vaisala)
        if self._vaisalaConnection is not None:
            self.rowToAdd.append(self._vaisalaConnection.readTemp())
            self.rowToAdd.append(self._vaisalaConnection.readRH())
        else:
            self.rowToAdd.append("-")
            self.rowToAdd.append("-")

        # Step 4 - Odczyt z 10 kanałów Keithley 2000
        # Sprawdzamy, czy obiekt do połączenia z urządzeniem został przesłany z programu głównego
        if self._keithley2000connection is not None:
            for i in range(1, 11):
                tempMeasurement = calculateTemp(self.probesCoeff, self._keithley2000connection.readChannel(i), i - 1)
                # print(str(i) + " " + str(tempMeasurement))
                self.rowToAdd.append(round(float(tempMeasurement), 3))  # Dodajemy do tablicy kolejne odczytane pomiary
        else:
            for i in range(1, 11):
                self.rowToAdd.append("-")

        # Step 5 - Odczyt z przyrządu kalibrowanego
        # TODO -całość
        if self.isCalibUnitConnected:
            self.rowToAdd.append("-")
            self.rowToAdd.append("-")
        else:
            self.rowToAdd.append("-")
            self.rowToAdd.append("-")
        # print(self.rowToAdd)
        # Signal emit
        self.measDoneSignal.signal_str.emit('OK')


def getCurrentTime():
    # return datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S ')
    return datetime.datetime.now().strftime('%H:%M:%S ')


def getProbesCoeff():
    '''
    Funkcja pobiera z pliku 'ProbesCoeff.csv' parametry R0, A, B, C dla poszczególnych sond multimetru Keithley2000
    :return: DataFrame: Kolumny: ProbeNo, R0, A, B,C.
    Dla wiersza 0 -Ro = 100, parametry ABC z normy.
    '''
    # tempData = pd.read_csv(r'C:\Users\Milenka\PycharmProjects\Keithley\ProbesCoeff.csv')
    try:
        tempData = pd.read_excel(r'C:\Users\Milenka\PycharmProjects\Keithley\ProbesCoeff.xlsx')
        probesCoeff = pd.DataFrame(tempData)
        result = True
        print("Pobrano współczynniki PT100")
        return result, probesCoeff
    except:
        result = False
        print("Błąd pobierania współczynników PT100")
        return result


def calculateTemp(coeffTable: pd.DataFrame, Rt: float, channel: int = 0) -> float:
    '''
    :param coeffTable:  Tablica z parametrami dla wszystkich sond pomiarowych
    :param Rt:          Rezystancja odczytana z multimetru
    :param channel:     Kanał z którego odczytano rezystancję
    :return:            Temperatura dla danego kanału
    Do funkcji przekazywana jest Tablica z parametrami, ponieważ nie funkcja nie jest częścią klsasy ImageViewer
    '''
    R0 = float(coeffTable.loc[channel, 'R0'])
    A = float(coeffTable.loc[channel, 'A'])
    B = float(coeffTable.loc[channel, 'B'])
    C = float(coeffTable.loc[channel, 'C'])
    wspC = 1 - (float(Rt) / float(R0))
    delta = math.sqrt(A * A - (4 * B * wspC))
    temp = (A * (-1) + delta) / (2 * B)

    return temp
