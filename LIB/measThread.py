import datetime
import math

from PyQt5.QtCore import pyqtSignal, QThread, QObject
import pandas as pd
import LIB.vaisala as vaisala
import LIB.keithley2000 as keithley2000
import LIB.p755 as p755


class MySignal(QObject):
    signal_str = pyqtSignal(str)


class MeasThread(QThread):
    def __init__(self, keithley2000connection: keithley2000 = None,TemperatureConnection = None, vaisalaConnection: vaisala = None,
                 interval=3, parent=None):
        super(MeasThread, self).__init__()

        # Zmienne proste
        self._interval = interval
        self._keepRunning = False
        #self.isCalibUnitConnected = False  # Zmienna do podłączenia urzadzenia kalibrowanego
        self._gettingProbeCoeffStatus = None  # bool, zmienna określająca czy udało się pobrać współcznynniki PT100
        self._readResistance = False # Gdy True- odczytujemy z Keithley rezystancję, false - przeliczamy na temperature

        # Obiekty
        self.rowToAdd = pd.DataFrame()

        # # Pobieramy współczyniki do PT100 i ustawiamy odpowiednią zmienną na success/fail (true,false)
        # self.getPorbesResultTouple = getProbesCoeff()  # Pobieramy dane z funkcji getProblesCoeff() w formacie bool, lub bool+df
        # if self.getPorbesResultTouple[0]:  # Jeżeli pierwsza zwrócona z getProbesCoeff(), wartość to true, czyli success
        #     self.probesCoeff = self.getPorbesResultTouple[1]
        #     self._gettingProbeCoeffStatus = True
        # else:
        #     self._gettingProbeCoeffStatus = False
        self.refreshProbesCoeff()

        self._keithley2000connection: keithley2000 = keithley2000connection
        self._temperatureConnection = TemperatureConnection
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

    def setTemperatureConnection(self, temperatureConnection):
        self._temperatureConnection = temperatureConnection

    def setGettingProbeCoeffStatus(self, state: bool):
        self._gettingProbeCoeffStatus = state

    def setReadResistance (self, state:bool):
        self._readResistance = state

    def getGettingProbeCoeffStatus(self):
        return self._gettingProbeCoeffStatus

    def getRowToAdd(self):
        return self.rowToAdd

    def getReadResistance(self):
        return self._readResistance

    def refreshProbesCoeff(self):
        # Pobieramy współczyniki do PT100 i ustawiamy odpowiednią zmienną na success/fail (true,false)
        self.getPorbesResultTouple = getProbesCoeff()  # Pobieramy dane z funkcji getProblesCoeff() w formacie bool, lub bool+df
        if self.getPorbesResultTouple[0]:  # Jeżeli pierwsza zwrócona z getProbesCoeff(), wartość to true, czyli success
            self.probesCoeff = self.getPorbesResultTouple[1]
            self._gettingProbeCoeffStatus = True
            return 1
        else:
            self._gettingProbeCoeffStatus = False
            return 0

    def run(self):
        print("Wykonuje pomiary z measThread, Interval: " + str(self._interval) + ", keepRunning: " + str(self._keepRunning))
        while self._keepRunning:
            self.doMeasurement()
            self.sleep(self._interval)

    def doMeasurement(self):
        tempTime = getCurrentTime()
        # print("RUN@: " + tempTime)

        # Step 1 - pobieranie godziny
        self.rowToAdd = [tempTime]  # tablica bedzie zawierać tylko 1 element (tempTime), później dołożymy pomiary

        # Step 2 - Odczyt temp z Termometru
        if self._temperatureConnection is not None:
            # self.logList.insertItem(0, getCurrentTime() + 'TempConnection: ' + str(self.tempConnection.read()))
            self.rowToAdd.append(float(self._temperatureConnection.read()))
        else:
            # Jeśli nie mamy połączenia z termometrem to wpisujemy '-'
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
            #print("START: " + str(datetime.datetime.now().time()))
            for i in range(1, 11):
                tstart = datetime.datetime.now()
                # calculateTemp(współcznniki dla sondy, rezystancja, kanał pomiarowy)

                # W zależności od ustawienia odczytujemy rezystancję lub przeliczamy na temperaturę.
                if self._readResistance:
                    tempMeasurement = self._keithley2000connection.readChannel(i)
                else:
                    tempMeasurement = calculateTemp(self.probesCoeff, self._keithley2000connection.readChannel(i), i - 1)

                # print(str(i) + " " + str(tempMeasurement))
                t = datetime.datetime.now() - tstart
                self.rowToAdd.append(round(float(tempMeasurement), 4))  # Dodajemy do tablicy kolejne odczytane pomiary
                #print(t)

        else:
            for i in range(1, 11):
                self.rowToAdd.append("-")
        # Step 5 - Odczyt z przyrządu kalibrowanego
        # NOT_TODO -całość- W tej wersji nie obslugujemy przyrządów kalibrowanych
        # if self.isCalibUnitConnected:
        #     self.rowToAdd.append("-")
        #     self.rowToAdd.append("-")
        # else:
        #     self.rowToAdd.append("-")
        #     self.rowToAdd.append("-")
        # print(self.rowToAdd)

        # Signal emit
        self.measDoneSignal.signal_str.emit('OK')

    def stop(self):
        self.terminate()


def getCurrentTime():
    # return datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S ')
    return datetime.datetime.now().strftime('%H:%M:%S ')


def getProbesCoeff():
    """
    Funkcja pobiera z pliku 'ProbesCoeff.xlsx' parametry R0, A, B, C dla poszczególnych sond multimetru Keithley2000
    :return: DataFrame: Kolumny: ProbeNo, R0, A, B,C.
    Dla wiersza 0 -Ro = 100, parametry ABC z normy.
    """
    # tempData = pd.read_csv(r'C:\Users\Milenka\PycharmProjects\Keithley\ProbesCoeff.csv')
    try:
        tempData = pd.read_excel(r'ProbesCoeff.xlsx')
        probesCoeff = pd.DataFrame(tempData)
        result = True
        print("Pobrano współczynniki PT100")
        print(probesCoeff)
        return result, probesCoeff
    except:
        result = False
        print("Błąd pobierania współczynników PT100")
        return result




def calculateTemp(coeffTable: pd.DataFrame, Rt: float, channel: int = 0) -> float:
    """
    :param coeffTable:  Tablica z parametrami dla wszystkich sond pomiarowych
    :param Rt:          Rezystancja odczytana z multimetru
    :param channel:     Kanał z którego odczytano rezystancję
    :return:            Temperatura dla danego kanału
    Do funkcji przekazywana jest Tablica z parametrami, ponieważ nie funkcja nie jest częścią klsasy ImageViewer
    """
    R0 = float(coeffTable.loc[channel, 'R0'])
    A = float(coeffTable.loc[channel, 'A'])
    B = float(coeffTable.loc[channel, 'B'])
    C = float(coeffTable.loc[channel, 'C'])
    wspC = 1 - (float(Rt) / float(R0))
    delta = math.sqrt(A * A - (4 * B * wspC))
    temp = (A * (-1) + delta) / (2 * B)
    return temp

# Funkcja obliczająca temperaturę. Parametry obliczane w inny sposób.
def calculateTemp2(coeffTable: pd.DataFrame, Rt: float, channel: int = 0) -> float:
    """
    :param coeffTable:  Tablica z parametrami dla wszystkich sond pomiarowych
    :param Rt:          Rezystancja odczytana z multimetru
    :param channel:     Kanał z którego odczytano rezystancję
    :return:            Temperatura dla danego kanału
    Do funkcji przekazywana jest Tablica z parametrami, ponieważ nie funkcja nie jest częścią klsasy ImageViewer
    """
    R0 = float(coeffTable.loc[channel, 'R0'])
    A = float(coeffTable.loc[channel, 'A'])
    B = float(coeffTable.loc[channel, 'B'])
    C = float(coeffTable.loc[channel, 'C'])
    #wspC = 1 - (float(Rt) / float(R0))
    #delta = math.sqrt(A * A - (4 * B * wspC))
    Rt=float(Rt)
    temp = A*Rt*Rt+B*Rt+C
    return temp
