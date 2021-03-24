from datetime import datetime
import serial
import sys
import numpy as np
import keithley2000
import p755
import vaisala
import serial.tools.list_ports
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QFileDialog
import TempMonitor_gui as MainWindow
import pandas as pd
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import math
import measThread
import myTableModel as tableModel
import time

matplotlib.use("Qt5Agg")

# pyside2-uic TempMonitor.ui -o TempMonitor_gui.py - nieuzywane
# pyuic5 TempMonitor.ui -o TempMonitor_gui.py

# Definiuje ikony statusu połączenia
ICON_RED_LED = ":/icons/led-red-on.png"
ICON_GREEN_LED = ":/icons/green-led-on.png"


class ImageViewer(QtWidgets.QMainWindow, MainWindow.Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # Połączenia przycisków z funkcjami - WAŻNE - Nazwy funkcji wpisujemy bez ()
        self.ConnectGradBtn.clicked.connect(self.connectGradBtnAction)
        self.ConnectTempBtn.clicked.connect(self.connectTempBtnAction)
        self.ConnectRHBtn.clicked.connect(self.connectRHBtnAction)
        # self.RefreshBtn.clicked.connect(self.refreshBtnAction)
        self.MeasureBtn.clicked.connect(self.measureBtnAction)
        self.refreshMenu.triggered.connect(self.refreshBtnAction)
        self.actionZapiszDane.triggered.connect(self.saveToExcelWindow)

        # Obiekty
        self.portsList = None  # Lista aktywnych portów COM
        self.gradConnection = None  # Obiekt do połączenia z multimetrem
        self.tempConnection = None  # Obiekt do połączenia z P-755
        self.vaisalaConnection = None  # Obiekt do połączenia z Vaisala
        self.measureThread = measThread.MeasThread()
        # self.measureThread.measDoneSignal.signal_str.connect(self.refreshTable)
        self.measureThread.measDoneSignal.signal_str.connect(self.measDone)
        self.startMeasureTime = None

        # Zmienne
        self.isKeithleyConnected: bool = False  # Czy połączono z Keithleyem
        self.isVaisalaConnected: bool = False  # Czy połączono z Vaisala
        self.isP755Connected: bool = False  # Czy połączono z P-755
        self.isCalibUnitConnected: bool = False  # Czy połączono z P-755
        self.isMeasuring: bool = False  # Czy wykonywane są pomiary
        self.measNo = 0  # numer pomiaru
        self.gradMin: float = 0
        self.gradMax: float = 0
        self.gradDelta: float = 0
        self.iloscProbek: int = int(5 * 60 / self.spinBox.value())  # Ilosc probek do wyswietlenia na wykresie. Domyslnie wykres 5 min

        # Tablice itp
        self.tableHeader = ['Time', 'P-755', 'HMT-Temp', 'HMT-RH', 'CH 1', 'CH 2', 'CH 3', 'CH 4', 'CH 5', 'CH 6', 'CH 7', 'CH 8', 'CH 9',
                            'CH 10', 'Gradient', 'Limit', 'KalibTemp', 'KalibRH']
        self.tableHeaderToExcel = ['Date', 'Time', 'P-755', 'HMT-Temp', 'HMT-RH', 'CH 1', 'CH 2', 'CH 3', 'CH 4', 'CH 5', 'CH 6', 'CH 7',
                                   'CH 8', 'CH 9', 'CH 10', 'Gradient', 'Limit', 'KalibTemp', 'KalibRH']
        self.tableData = pd.DataFrame(columns=self.tableHeader)  # Obiekt do wyswietlenia danych w tabeli GUI
        self.dataToExcel = pd.DataFrame(columns=self.tableHeaderToExcel)  # Obiekt z danymi do exportu do excela
        self.rowToAdd = pd.DataFrame()
        self.excelFileName = "TEST3.xlsx"
        self.excelSheetName = "Sheet1"
        #self.appendToExcel = appendToExcel.AppendToExcel("test9.xlsx")
        # self.myWorkbook = Workbook()
        # self.myWorksheet = self.myWorkbook.active
        self.writer = pd.ExcelWriter(self.excelFileName, engine='openpyxl')

        # self.columnsDataLabels = []
        # self.rowsDataLabels = []
        # self.probesCoeff = getProbesCoeff()
        self.saveExcelException = None  # Przechowuje wynik operacji zapisu danych do excela
        self.dataToPlot = pd.DataFrame()  # Tablica zawierająca dane liczbowe do wyświetlenia na wykresie

        # Model do sterowania zawartością tabeli
        self.tableModel = tableModel.MyTableModel(self.tableData)

        # Obiekty do wyświetlenia wykresu
        self.fig = Figure(facecolor=(1, 1, 1), edgecolor=(0, 0, 0))
        self.canvas = FigureCanvas(self.fig)
        self.ax1f3 = self.fig.add_subplot(111)
        self.plotTimeInterval = ['5 min', '15 min', '30 min', '1 h', '2 h', '4 h', '6 h']
        self.PlotTimeComboBox.addItems(self.plotTimeInterval)
        self.PlotTimeComboBox.currentIndexChanged.connect(self.refreshDataToPlot)
        self.plotMinutesLocator = mdates.MinuteLocator()
        self.plotHoursLocator = mdates.HourLocator()

        # Init
        self.refreshBtnAction()
        # self.appendToExcel.append(self.rowToAdd)

    # TODO ALL PLOTTING!!!
    def updatePlot(self):
        # print("Updating plot")
        # Odświeżam wykres w stary sposób
        self.refreshDataToPlot()

    def plotting(self):
        # fig = Figure(facecolor=(1, 1, 1), edgecolor=(0, 0, 0))
        # ax1f3 = self.fig.add_subplot(111)

        # print(self.dataToPlot.iloc[:,0],self.dataToPlot.iloc[:,1])
        # print(self.dataToPlot.iloc[:,0])    # cały wiersz z timesepami
        # print(self.dataToPlot[0:,0])    # pierwszy element wiersz z timesepami
        # print(self.dataToPlot.iloc[len(self.dataToPlot):,0])    # ostatni element wiersz z timesepami
        # print(self.dataToPlot.iloc[:,1])    # cały wiersz z wartosciami
        print(self.dataToPlot.iat[0, 0])
        print(self.dataToPlot.iat[len(self.dataToPlot) - 1, 0])
        # self.ax1f3.set_xdata(self.dataToPlot.iloc[:, 0])
        # self.ax1f3.set_ydata(self.dataToPlot.iloc[:, 1])
        self.ax1f3.draw()
        # xData = pd.date_range(self.dataToPlot.iloc[:0],self.dataToPlot.iloc[:])
        # self.ax1f3.plot(self.dataToPlot.iloc[:, 0], self.dataToPlot.iloc[:, 1])
        # ax1f3.autofmt_xdate()
        # ax1f3.set_x
        # ax1f3.xaxis.set_major_locator(self.plotHoursLocator)
        # ax1f3.xaxis.set_minor_locator(self.plotMinutesLocator)
        # self.canvas = FigureCanvas(fig)

        # if self.mplvl.isEmpty():
        #     print("Plot container is empty")
        #     self.mplvl.addWidget(self.canvas)
        #     self.canvas.draw()
        # else:
        #     self.clearPlot(self.mplvl)
        #     self.mplvl.addWidget(self.canvas)
        #     self.canvas.draw()

    def updatePlotNew(self):
        pass

    def clearPlot(self, layout):
        while self.mplvl.count():
            child = self.mplvl.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                self.clearPlot(child.layout())

    def refreshDataToPlot(self):
        # Odświerzam tabele zawierająca dane do wykresu
        if self.startMeasureTime is None:
            self.startMeasureTime = self.tableData.iloc[0, 0]  # Czas rozpoczęcia pomiarów

        # Obliczamy ilosc potrzebnych probek do wyswietlenia odpowieniego wykresu
        if self.PlotTimeComboBox.currentIndex() == 0:  # Wybrano wykres 5 min
            # obliczamy ilosc probek do wyswietlenia: 5 min * 60s / czas pomiedzy pomiarami
            self.iloscProbek = int(5 * 60 / self.spinBox.value())
            # self.iloscProbek = int(1 * 60 / self.spinBox.value())
        elif self.PlotTimeComboBox.currentIndex() == 1:  # Wybrano wykres 15 min
            self.iloscProbek = int(15 * 60 / self.spinBox.value())
        elif self.PlotTimeComboBox.currentIndex() == 2:  # Wybrano wykres 30 min
            self.iloscProbek = int(30 * 60 / self.spinBox.value())
            pass
        elif self.PlotTimeComboBox.currentIndex() == 3:  # Wybrano wykres 1h
            self.iloscProbek = int(60 * 60 / self.spinBox.value())
            pass
        elif self.PlotTimeComboBox.currentIndex() == 4:  # Wybrano wykres 2h
            self.iloscProbek = int(120 * 60 / self.spinBox.value())
            pass
        elif self.PlotTimeComboBox.currentIndex() == 5:  # Wybrano wykres 4h
            self.iloscProbek = int(240 * 60 / self.spinBox.value())
            pass
        elif self.PlotTimeComboBox.currentIndex() == 6:  # Wybrano wykres 6h
            self.iloscProbek = int(360 * 60 / self.spinBox.value())

        # Tworzymy tabelę z danymi do wykresu, jeśli mamy za mało próbek na wyświetlenie danego czasu
        # wyświetlamy tylko to co jest już zebrane
        if self.tableData['Gradient'].count() <= self.iloscProbek:
            # print("Potrzeba: " + str(self.iloscProbek) + " mamy: " + str(self.tableData['Gradient'].count()))
            self.dataToPlot = self.tableData.iloc[:, [0, 14]]  # Series
            # print(self.dataToPlot)
            self.plotting()
        else:
            self.dataToPlot = self.tableData.iloc[-self.iloscProbek:, [0, 14]]  # Series
            # print(self.dataToPlot)
            self.plotting()

        self.updatePlotNew()
    # TODO --- END

    def exit_app(self):
        print("EXIT function")  # verification of shortcut press
        self.close()

    # Menu -> Odśwież listę portów COM
    def refreshBtnAction(self):
        self.portsList = serial.tools.list_ports.comports()
        self.PortListTempComboBox.clear()
        self.PortListRHComboBox.clear()
        self.PortListGradComboBox.clear()
        for port in self.portsList:
            self.PortListTempComboBox.addItem(port.device)
            self.PortListRHComboBox.addItem(port.device)
            self.PortListGradComboBox.addItem(port.device)
        self.logList.insertItem(0, getCurrentTime() + "Zaktualizowano listę portów COM")
        if self.PortListRHComboBox.count():
            if not self.isVaisalaConnected: self.ConnectRHBtn.setEnabled(True)
            if not self.isP755Connected: self.ConnectTempBtn.setEnabled(True)
            if not self.isKeithleyConnected: self.ConnectGradBtn.setEnabled(True)
        else:
            self.ConnectRHBtn.setEnabled(False)
            self.ConnectTempBtn.setEnabled(False)
            self.ConnectGradBtn.setEnabled(False)

        # Jeśli nie jest połączone żadne urządzenia, wyłączam guzik rozpoczęcia pomiaru
        if self.isKeithleyConnected or self.isP755Connected or self.isVaisalaConnected:
            self.MeasureBtn.setEnabled(True)
        else:
            self.MeasureBtn.setEnabled(False)

    # Przycisk "Połącz" (pomiar griadientu, Kiethley2000)
    def connectGradBtnAction(self):
        # if self.PortListGradComboBox.
        # self.logList.insertItem(0, getCurrentTime() + 'Łączę z Keitley @ ' + self.PortListGradComboBox.currentText() + '...')
        # Wyświetl port COM urządzenia wybranego na liście
        # print('Łączę na: ' + str(self.portsList[self.PortListGradComboBox.currentIndex()].device))
        # Tworze obiekt typu Keithley2000 o zadanych w oknie parametrach
        self.gradConnection = keithley2000.Keithley2000(self.portsList[self.PortListGradComboBox.currentIndex()].device)
        self.gradConnection.connect()
        if self.gradConnection.isConnected():
            self.isKeithleyConnected = True
            self.measureThread.setKeithleyConnection(self.gradConnection)
            self.ConnectGradBtn.setEnabled(False)
            ## TODO Zmiana przycisku na "rozłącz"
            self.PortListGradComboBox.setEnabled(False)
            self.MeasureBtn.setEnabled(True)
            self.logList.insertItem(0, getCurrentTime()
                                    + 'Połączono z Keithley2000: '
                                    + str(self.gradConnection.baudrate) + " "
                                    + str(self.gradConnection.connection.bytesize) + " "
                                    + str(self.gradConnection.connection.parity) + " "
                                    + str(self.gradConnection.connection.stopbits) + " "
                                    + str(self.gradConnection.connection.xonxoff) + " ")
            # Sprawdzamy czy pobrano z sukcesem współczynniki dla PT100
            if self.measureThread.getGettingProbeCoeffStatus():
                self.logList.insertItem(0, getCurrentTime() + 'Pobrano współczynniki PT100')
            else:
                self.logList.insertItem(0, getCurrentTime() + 'Błąd pobierania współczynników PT100')
            # Zmieniam dane w oknie głównym
            # self.ConnectionStatusGradLabel.setText(
            #     "<html><head/><body><p><span style=""color:#00aa00;"">Połączono</span></p></body></html>")
            self.LedGradStatusLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
        else:
            self.isKeithleyConnected = False
            self.logList.insertItem(0,
                                    getCurrentTime() + 'Łączę z Keitley @ ' + self.PortListGradComboBox.currentText() + '... '
                                    + 'Połączenie nieudane! ' + self.gradConnection.errorMessage)
            self.gradConnection = None
            # self.ConnectionStatusGradLabel.setText(
            #     "<html><head/><body><p><span style=""color:#ff0000;"">Rozłączono</span></p></body></html>")
            self.LedGradStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

    # Przycisk "Połącz" (pomiar RH, Vaisala)
    def connectTempBtnAction(self):
        # self.logList.insertItem(0, getCurrentTime() + "Łączę z P-755 @...")
        self.tempConnection = p755.P755(self.portsList[self.PortListTempComboBox.currentIndex()].device)
        self.tempConnection.connect()
        if self.tempConnection.isConnected():
            self.isP755Connected = True
            self.measureThread.setP755Connection(self.tempConnection)
            self.ConnectTempBtn.setEnabled(False)
            self.MeasureBtn.setEnabled(True)
            self.logList.insertItem(0, getCurrentTime()
                                    + 'Połączono z P-755: '
                                    + str(self.tempConnection.baudrate) + " "
                                    + str(self.tempConnection.connection.bytesize) + " "
                                    + str(self.tempConnection.connection.parity) + " "
                                    + str(self.tempConnection.connection.stopbits) + " "
                                    + str(self.tempConnection.connection.xonxoff) + " ")

            # Zmieniam dane w oknie głównym
            # self.ConnectionStatusTempLabel.setText(
            #     "<html><head/><body><p><span style=""color:#00aa00;"">Połaczono</span></p></body></html>")
            self.LedTempStatusLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
        else:
            self.isP755Connected = False
            self.logList.insertItem(0,
                                    getCurrentTime() + 'Łączę z P-755 @ ' + self.PortListTempComboBox.currentText() + '... '
                                    + 'Połączenie nieudane! ' + self.tempConnection.errorMessage)
            self.tempConnection = None

            # self.ConnectionStatusTempLabel.setText(
            #     "<html><head/><body><p><span style=""color:#ff0000;"">Rozłączono</span></p></body></html>")
            self.LedTempStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

    # Przycisk "Połącz" (pomiar temperatury, P-755)
    def connectRHBtnAction(self):
        # self.logList.insertItem(0, getCurrentTime() + 'Łączę z Vaisala...')
        self.vaisalaConnection = vaisala.Vaisala(self.portsList[self.PortListRHComboBox.currentIndex()].device)
        self.vaisalaConnection.connect()
        if self.vaisalaConnection.isConnected():
            self.isVaisalaConnected = True
            self.measureThread.setVaisalaConnection(self.vaisalaConnection)
            self.ConnectRHBtn.setEnabled(False)
            self.MeasureBtn.setEnabled(True)
            self.logList.insertItem(0, getCurrentTime()
                                    + 'Połączono z HMT: '
                                    + str(self.vaisalaConnection.baudrate) + " "
                                    + str(self.vaisalaConnection.connection.bytesize) + " "
                                    + str(self.vaisalaConnection.connection.parity) + " "
                                    + str(self.vaisalaConnection.connection.stopbits) + " "
                                    + str(self.vaisalaConnection.connection.xonxoff) + " ")
            # Zmieniam dane w oknie głównym
            # self.ConnectionStatusRHLabel.setText(
            #     "<html><head/><body><p><span style=""color:#00aa00;"">Połaczono</span></p></body></html>")
            self.LedRHStatusLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
            # self.StateVaisalaDescLabel.setText(self.vaisalaConnection.connection.port + " "
            #                                    + str(self.vaisalaConnection.baudrate) + " "
            #                                    + str(self.vaisalaConnection.connection.bytesize) + " "
            #                                    + str(self.vaisalaConnection.connection.parity) + " "
            #                                    + str(self.vaisalaConnection.connection.stopbits) + " "
            #                                    + str(self.vaisalaConnection.connection.xonxoff))
        else:
            self.isVaisalaConnected = False
            self.logList.insertItem(0,
                                    getCurrentTime() + 'Łączę z Vaisala @ ' + self.PortListRHComboBox.currentText() + '... '
                                    + 'Połączenie nieudane! ' + self.vaisalaConnection.errorMessage)
            self.vaisalaConnection = None
            # self.ConnectionStatusRHLabel.setText(
            #     "<html><head/><body><p><span style=""color:#ff0000;"">Rozłączono</span></p></body></html>")
            self.LedRHStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

    # Przycisk "Rozpocznij pomiarty/STOP"
    def measureBtnAction(self):
        if self.isMeasuring:  # Jesli akutalnie wykonywane sa pomiary, to stopujemy i zmieniamy wyglad guzika
            # TODO Zatrzymanie threadu
            # print("From Main: "+str(self.measureThread.rowToAdd))

            # Zmiany wizualne w GUI
            self.isMeasuring = False
            self.measureStatusLedLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))
            self.MeasureBtn.setText("Rozpocznij pomiary")
            self.MeasureBtn.setStyleSheet("background-color: rgb(170, 255, 127)")
            self.spinBox.setEnabled(True)

            # Zatrzymanie wątku
            print("STOPPING: " + str(self.measureThread))
            self.measureThread.setKeepRunning(False)
            self.measureThread.terminate()
            # self.measureThread = None

        else:  # Jesli nie są wykonywane pomiary- to je rozpoczynamy
            self.isMeasuring = True
            # self.startMeasureTime = datetime.now().time()
            self.measureStatusLedLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
            self.MeasureBtn.setText("STOP")
            self.MeasureBtn.setStyleSheet("background-color: rgb(255,170,127)")
            self.spinBox.setEnabled(False)

            # TODO Rozpoczęcie threadu

            # Tworze nowy wątek i przekazuje mu obiekty do komunikacji z urzadzeniami
            self.measureThread.setInterval(self.spinBox.value() - 2)
            self.measureThread.setKeepRunning(True)
            self.measureThread.start()
            # startButtonTime = getCurrentTime()
            # sleep przez czas okreslony w kontrolce
            # print(time.sleep(float(self.spinBox.value()))
            # self.doMeasurement()

    def measDone(self, data):
        # Po zakończeniu pomiarów pobieramy dane i zapisujemy do zmienniej rowToAdd
        self.rowToAdd = self.measureThread.getRowToAdd()
        # Obliczamy gradient i wpisujemy go do rowToAdd
        self.obliczGradient()

        startTime =time.time()
        self.refreshTable(data)
        print ("\nRefreshing table: " + str(time.time()-startTime))

        # TODO Na później do zrobienia cały plotting
        # self.updatePlot()

        #startTime = time.time()
        self.refreshGUI()
        #print("Refreshing GUI: " + str(time.time() - startTime))

        startTime =time.time()
        #self.saveToExcel()
        #print("Saving Excel table: " + str(time.time() - startTime))

        if self.saveExcelException:
            self.logList.insertItem(0, getCurrentTime() + "Błąd zapisu do excela: " + str(self.saveExcelException))
            print("Błąd zapisu do excela: " + str(self.saveExcelException))

    def obliczGradient(self):
        '''
        Funkcja z otrzymanych pomiarów temperatury oblicza maksymalny gradient. Modyfikuje wiersz "rowToAdd"
        '''
        # Dodatkowe obliczenia i modyfikacja wiersza rowToAdd
        self.measNo += 1
        # Obliczenia wartosci min, max gradientu
        self.gradMeasurement = self.rowToAdd[4:14]  # Tablica, z kótrej wyliczany jest min i max
        # print(self.gradMeasurement)
        self.gradMax = round(max(self.gradMeasurement), 3)
        self.gradMin = round(min(self.gradMeasurement), 3)
        self.gradDelta = round((self.gradMax - self.gradMin), 3)
        # self.rowToAdd.append(self.gradDelta)
        self.rowToAdd.insert(14, self.gradDelta)  # Uzupełniamy wiersz o obliczony gradient
        self.rowToAdd.insert(15, round(self.maxAllowedGradSpinBox.value(), 3))  # uzupełniamy wiersz o ustawiony limit gradientu

    def refreshGUI(self):
        # Wyświetlenie wyników max i min w LineEdit GUI
        self.maxTempLineEdit.setText(str(self.gradMax))
        self.minTempLineEdit.setText(str(self.gradMin))
        self.countMeasLineEdit.setText(str(self.measNo))

        # Sprawdzam wartość gradientu zmieniam kolor pola LineEdit
        self.gradLineEdit.setText(str(self.gradDelta))
        if self.gradDelta > self.maxAllowedGradSpinBox.value():
            self.gradLineEdit.setStyleSheet("background-color: rgb(255,170,127)")
            # self.logList.insertItem(0, getCurrentTime() + 'Przekroczona maksymalna wartość gradientu temperatury w komorze')
            # print("Wartosc przekroczona")
        else:
            self.gradLineEdit.setStyleSheet("background-color: rgb(170, 255, 127)")

    def refreshTable(self, data):

        # Aktualizacja tabeli w GUI
        # Tabela pokazuje wszystie wyniki, nawet te z przekroczonym gradientem
        self.tableData = self.tableData.append(pd.Series(self.rowToAdd, index=self.tableHeader), ignore_index=True)
        self.tableData.index = self.tableData.index + 1
        self.tableModel.setNewData(self.tableData)
        self.tableModel.layoutChanged.emit()
        self.tableView.setModel(self.tableModel)
        self.tableView.resizeRowToContents(self.tableData.shape[0]-1)
        if self.tableData.shape[0]==1:
            self.tableView.resizeColumnsToContents()
            self.tableView.resizeRowsToContents()

        self.tableView.update()
        # self.tableView.resizeRowsToContents()
        self.tableView.scrollToBottom()

    # Slot do uruchomienia z menu
    def saveToExcelWindow(self):
        filename = QFileDialog.getSaveFileName(self,"Zapisz dane pomiarowe",'',"Excel Files (*.xlsx);;All Files (*)")
        if filename[0]=='':
            print("Nie wybrano żadnego pliku do zapisu")
            #print(filename[1])
            return 0
        else:
            print("Zapisuje plik: " + filename[0])
            # Dodajemy datę do tabeli
            print(self.tableData)
            self.tableData.to_excel(filename[0])

    # Nieużywane
    def doMeasurement(self):
        print("Doing measurement...")
        # W poszczególnych krokach generujemy wiersz, który następnie w step 6 dodajemy do DataFrame
        #
        # Step 1 - pobieranie godziny
        tempTime = getCurrentTime()
        self.rowToAdd = [tempTime]  # tablica bedzie zawierać tylko 1 element (tempTime), później dołożymy pomiary

        # Step 2 - Odczyt temp z P-755
        if self.isP755Connected:
            # self.logList.insertItem(0, getCurrentTime() + 'P-755: ' + str(self.tempConnection.read()))
            self.rowToAdd.append(self.tempConnection.read())
        else:
            # Jeśli nie mamy połączenia z P-755 to wpisujemy '-'
            self.rowToAdd.append("-")

        # Step 3 - Odczyt z HMT (Vaisala)
        if self.isVaisalaConnected:
            self.rowToAdd.append(self.vaisalaConnection.readTemp())
            self.rowToAdd.append(self.vaisalaConnection.readRH())
        else:
            self.rowToAdd.append("-")
            self.rowToAdd.append("-")

        # Step 4 - Odczyt z 10 termometrów Keithley
        if self.isKeithleyConnected:
            for i in range(1, 11):
                # tempMeasurement = self.gradConnection.readChannel(i)
                tempMeasurement = calculateTemp(self.probesCoeff, self.gradConnection.readChannel(i), i - 1)
                # Dodajemy do tablicy kolejne odczytane pomiary
                # print(str(i) + " " + str(tempMeasurement))
                self.rowToAdd.append(round(tempMeasurement, 3))
        else:
            for i in range(1, 11):
                self.rowToAdd.append("-")

        # Step 5 - Odczyt z przyrządu kalibrowanego
        # TODO -całość
        if self.isCalibUnitConnected:
            self.rowToAdd.append(np.nan)
            self.rowToAdd.append(np.nan)
        else:
            self.rowToAdd.append("-")
            self.rowToAdd.append("-")

        # Step 6 - dodajemy wiersz rowToAdd do DataFrame
        self.tableData = self.tableData.append(pd.Series(self.rowToAdd, index=self.tableHeader), ignore_index=True)
        self.tableData.index = self.tableData.index + 1
        # print(self.rowToAdd)
        # print(self.tableData)

        # TODO: Eksport danych do Excela
        # with xlsxwriter.Workbook('Dane.xlsx') as workbook:
        #    workbook.shee.write_row(self.measNo, 0, self.rowToAdd)

        # print(str(columns=('Time', 'CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7', 'CH8', 'CH9', 'CH10').size))
        # Convert data to export
        # self.dataToExcel = pd.DataFrame(self.tableData)
        # columns=['Time', 'CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7', 'CH8', 'CH9', 'CH10'])
        # Save to excel
        # self.dataToExcel.to_excel(self.pathToExcel)

        # Aktualizacja modelu obiektu tabeli
        self.measNo += 1
        print(self.tableData)

        # Update TableModel
        # self.tableModel = MyTableModel(self.tableData)
        # self.tableView.setModel(self.tableModel)
        # # self.tableView.clearSpans()
        # self.tableView.resizeColumnsToContents()
        # self.tableView.resizeRowsToContents()
        # self.tableView.scrollToBottom()



# Funkcje poza główną aplikacją
def getCurrentTime():
    # return datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S ')
    return datetime.now().strftime('%H:%M:%S ')


def getProbesCoeff():
    '''
    Funkcja pobiera z pliku 'ProbesCoeff.csv' parametry R0, A, B, C dla poszczególnych sond multimetru Keithley2000
    :return: DataFrame: Kolumny: ProbeNo, R0, A, B,C.
    Dla wiersza 0 -Ro = 100, parametry ABC z normy.
    '''
    # tempData = pd.read_csv(r'C:\Users\Milenka\PycharmProjects\Keithley\ProbesCoeff.csv')
    tempData = pd.read_excel(r'C:\Users\Milenka\PycharmProjects\Keithley\ProbesCoeff.xlsx')
    probesCoeff = pd.DataFrame(tempData)
    return probesCoeff


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


def main():
    app = QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    app.exec_()


if __name__ == '__main__':
    main()

# TODO
# 1. Weryfikacja połączenia COM, żeby termomentr P-755 nie łączył się z keitleyem itd       [ ]
# 2. Dodać diody statusu RED/GREEN                                                          [X]
# 3. Zatrzymanie pomiarów po utracie połączenia lub wyłączeniu urządzenia                   [ ]
# 4. Przycisk "Rozłącz"                                                                     [ ]
# 5. Wyświetlenie ilości wykonanaych pomiarów                                               [X]
# 6. Poprawa zapisu danych w Excelu                                                         [ ]
#
# -----     WYKRESY     -----
# 1. Poprawa czasu na osi X                                                                 [ ]
# 2. Czerwona linia maksymalnego dozwolonego gradientu                                      [ ]
# 3. Poprawić oś y, od 0 do górny limit gradientu + offset                                  [ ]
