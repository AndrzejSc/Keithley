from datetime import datetime
from PyQt5.QtCore import QTimer
import serial
import os
import sys
from LIB import p755, keithley2000, fluke1595, measThread, vaisala, myTableModel as tableModel, TempMonitor_gui as MainWindow
import serial.tools.list_ports
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
import pandas as pd
# import time
from LIB.Dialogs import Dialogs

# pyside2-uic TempMonitor.ui -o TempMonitor_gui.py - nieuzywane

# pyuic5 TempMonitor.ui -o TempMonitor_gui.py
# Po wykonaniu komendy, w pliku /LIB/TempMonitor_gui.py zmienić linijkę: "import resources_rc"
# na "from LIB import resources_rc"
# BRAK IKON :
# w TempMonitor_gui.py Zmienić   icon8.addPixmap(QtGui.QPixmap(":/icons/disconnect.png"), ......
# na   icon8.addPixmap(QtGui.QPixmap("LIB/icons/disconnect.png"), .......
# TAK SAMO W OKNACH DIALOGÓW xxxGUI.py
#
# auto-py-to-exe  - Generator plików EXE
#

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
        # self.MeasureBtn.clicked.connect(self.measureBtnAction)
        self.autoSaveCheckBox.clicked.connect(self.changeAutoSaveCheckBox)
        # self.autoSaveCheckBox.changeEvent(self.autoSaveCheckBoxChanged)

        # Akcje paska przycisków (ToolBar)
        self.actionStartMeasurement.triggered.connect(self.measureStartAction)
        self.actionStopMeasurement.triggered.connect(self.measureStopAction)
        self.refreshCOM.triggered.connect(self.refreshCOMAction)
        self.actionDisconnectAll.triggered.connect(self.disconnectAll)
        self.actionSaveData.triggered.connect(self.saveFile)
        self.actionSaveAs.triggered.connect(self.saveAs)
        # self.actionSaveOptions.triggered.connect(self.showSaveOptionsWindow)

        # Akcje menu programu ikonki
        self.actionPomiar_rezystancji.triggered.connect(self.changeTempToRes)
        self.actionClearMeasurement.triggered.connect(self.clearMeasurement)
        self.actionRefreshProbesCoeff.triggered.connect(self.refreshProbesCoeff)
        self.actionZamknij.triggered.connect(self.exit_app)
        self.actionHelp.triggered.connect(self.showHelpWindow)
        self.actionO_programie.triggered.connect(self.showAboutWindow)
        # Inne kontrolki
        self.RefTempComboBox.currentIndexChanged.connect(self.changeRefComboBox)
        self.timeIntervalSpinBox.valueChanged.connect(self.changeTimeIntervalSpinBox)

        # Obiekty
        self.portsList = None  # Lista aktywnych portów COM
        self.gradConnection = None  # Obiekt do połączenia z multimetrem
        self.tempConnection = None  # Obiekt do połączenia z P-755
        self.vaisalaConnection = None  # Obiekt do połączenia z Vaisala
        self.measureThread = measThread.MeasThread()  # Wątek działający w tle
        self.helpDialog = Dialogs.HelpDialogWindow()  # Okno pomocy, pokazanie dopiero po przycisku
        self.aboutDialog = Dialogs.AboutDialogWindow()  # Okno O Programie

        # Połączenie sygnału emitowanego po zakończeniu pomiaru przez wątek w tle, z funkcją measDone
        self.measureThread.measDoneSignal.signal_str.connect(self.measDone)
        self.startMeasureTime = None

        # Obiekty do automatycznego zapisu
        self.autoSaveTimer = QTimer()
        self.autoSaveTimer.timeout.connect(self.checkIfIsMeasuringAndSave)

        # Zmienne
        self.isKeithleyConnected: bool = False  # Czy połączono z Keithleyem
        self.isVaisalaConnected: bool = False  # Czy połączono z Vaisala
        self.isThermometrConnected: bool = False  # Czy połączono z termometrem
        self.isMeasuring: bool = False  # Czy wykonywane są pomiary
        self.measNo = 0  # numer pomiaru
        self.gradMin: float = 0
        self.gradMax: float = 0
        self.gradDelta: float = 0
        self.unitChangedFlag = False  # Flaga, mówiąca o zmianie wyświetlanych jednostek
        self.filename: str = ""  # String, ścieżka i nazwa pliku do zapisu danych pomiarowych
        self.pathToDesktop: str = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop') + "\\" \
                                  + datetime.today().strftime("%d.%m.%Y")  # Ścieżka do pulpitu

        # Tablice, nagłówki itp
        # self.tableHeader = ['Time', 'P-755', 'HMT-Temp', 'HMT-RH', 'CH 1', 'CH 2', 'CH 3', 'CH 4', 'CH 5', 'CH 6', 'CH 7', 'CH 8', 'CH 9',
        #                    'CH 10', 'Gradient', 'Limit']
        # self.tableData = pd.DataFrame(columns=self.tableHeader)  # Obiekt do wyswietlenia danych w tabeli GUI
        self.tableHeader = []  # Nagłówek tabeli wyswietlanej w GUI
        self.tableData = pd.DataFrame()  # Obiekt do wyswietlenia danych w tabeli GUI
        self.rowToAdd = pd.DataFrame()  # Pojedynczy wiersz z aktualnymi pomiarami

        # Model do sterowania zawartością tabeli
        self.tableModel = tableModel.MyTableModel(self.tableData)

        # Init
        self.refreshCOMAction()
        self.RefGradientComboBox.addItem("Keithley 2000")
        self.RefHumidityComboBox.addItem("Vaisala HMT-337")
        self.RefTempComboBox.addItem("Dostmann P-755")
        self.RefTempComboBox.addItem("Fluke 1595A")
        self.Fluke1595ChannelComboBox.addItem("CH 1")
        self.Fluke1595ChannelComboBox.addItem("CH 2")
        self.Fluke1595ChannelComboBox.addItem("CH 3")
        self.Fluke1595ChannelComboBox.addItem("CH 4")

    # Menu -> Odśwież listę portów COM
    def refreshCOMAction(self):
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
            if not self.isThermometrConnected: self.ConnectTempBtn.setEnabled(True)
            if not self.isKeithleyConnected: self.ConnectGradBtn.setEnabled(True)
        else:
            self.ConnectRHBtn.setEnabled(False)
            self.ConnectTempBtn.setEnabled(False)
            self.ConnectGradBtn.setEnabled(False)

    # Przycisk "Połącz" (pomiar griadientu, Kiethley2000)
    def connectGradBtnAction(self):
        if self.isKeithleyConnected:
            # Przyrząd jest podłączony, rozłączanie
            if self.gradConnection.isConnected():
                if self.gradConnection.disconnect():
                    self.isKeithleyConnected = False
                    self.gradConnection = None
                    self.ConnectGradBtn.setText("Połącz")
                    self.logList.insertItem(0, getCurrentTime() + 'Rozłączono z Keithley2000')
                    self.LedGradStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))
                    self.PortListGradComboBox.setEnabled(True)
                    self.RefGradientComboBox.setEnabled(True)
                else:
                    print("Błąd rozłączenia" + self.gradConnection.errorMessage)
                self.measureStopAction()

        else:
            # ŁĄCZENIE PRZYRZĄDU
            self.gradConnection = keithley2000.Keithley2000(self.portsList[self.PortListGradComboBox.currentIndex()].device)
            self.gradConnection.connect()
            if self.gradConnection.isConnected():
                self.isKeithleyConnected = True
                self.measureThread.setKeithleyConnection(self.gradConnection)
                self.PortListGradComboBox.setEnabled(False)
                self.RefGradientComboBox.setEnabled(False)
                self.actionStartMeasurement.setEnabled(True)
                self.actionDisconnectAll.setEnabled(True)
                self.LedGradStatusLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
                self.ConnectGradBtn.setText("Rozłącz")
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

            # Jeśli nie udała sie próba połączenia
            else:
                self.isKeithleyConnected = False
                self.logList.insertItem(0,
                                        getCurrentTime() + 'Łączę z Keitley @ ' + self.PortListGradComboBox.currentText() + '... '
                                        + 'Połączenie nieudane! ' + self.gradConnection.errorMessage)
                self.warninngMessageBox(self.gradConnection.errorMessage, "Błąd połączenia z przyrządem pomiarowym!")
                self.gradConnection = None
                self.LedGradStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

    # Przycisk "Połącz" (pomiar Temperatury, P-755 lub Fluke)
    def connectTempBtnAction(self):
        if self.isThermometrConnected:
            # Rozłączanie
            if self.tempConnection.isConnected():
                if self.tempConnection.disconnect():
                    # Poprawnie rozlączono
                    self.isThermometrConnected = False
                    self.tempConnection = None
                    self.ConnectTempBtn.setText("Połącz")
                    self.logList.insertItem(0, getCurrentTime() + 'Rozłączono z termometrem')
                    self.LedTempStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))
                    self.PortListTempComboBox.setEnabled(True)
                    self.RefTempComboBox.setEnabled(True)
            else:
                print("Błąd rozłączenia" + self.tempConnection.errorMessage)
            self.measureStopAction()
        else:
            # Łączenie z termometrem
            if self.RefTempComboBox.currentIndex() == 0:
                self.tempConnection = p755.P755(self.portsList[self.PortListTempComboBox.currentIndex()].device)
            else:
                self.tempConnection = fluke1595.Fluke1595(self.portsList[self.PortListTempComboBox.currentIndex()].device,
                                                          self.Fluke1595ChannelComboBox.currentIndex() + 1)
            self.tempConnection.connect()
            if self.tempConnection.isConnected():
                # Połączenie się udało
                self.isThermometrConnected = True
                self.measureThread.setTemperatureConnection(self.tempConnection)
                self.PortListTempComboBox.setEnabled(False)
                self.RefTempComboBox.setEnabled(False)
                self.actionStartMeasurement.setEnabled(True)
                self.actionDisconnectAll.setEnabled(True)
                self.LedTempStatusLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
                self.ConnectTempBtn.setText("Rozłącz")
                self.logList.insertItem(0, getCurrentTime()
                                        + 'Połączono z termometrem: ' + self.RefTempComboBox.currentText() + ' '
                                        + str(self.tempConnection.baudrate) + " "
                                        + str(self.tempConnection.connection.bytesize) + " "
                                        + str(self.tempConnection.connection.parity) + " "
                                        + str(self.tempConnection.connection.stopbits) + " "
                                        + str(self.tempConnection.connection.xonxoff) + " ")
            else:
                # Jesli połączenie się nie udało
                self.isThermometrConnected = False
                self.logList.insertItem(0,
                                        getCurrentTime() + 'Połączenie z ' + self.RefTempComboBox.currentText()
                                        + ' @ ' + self.PortListTempComboBox.currentText() + '... '
                                        + ' nieudane! ' + self.tempConnection.errorMessage)
                self.warninngMessageBox(self.tempConnection.errorMessage, "Błąd połączenia z przyrządem pomiarowym!")
                self.tempConnection = None
                self.LedTempStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

    def connectRHBtnAction(self):
        if self.isVaisalaConnected:
            # Przyrząd jest podłączony, rozłączanie
            if self.vaisalaConnection.isConnected():
                if self.vaisalaConnection.disconnect():
                    self.isVaisalaConnected = False
                    self.vaisalaConnection = None
                    self.ConnectRHBtnBtn.setText("Połącz")
                    self.logList.insertItem(0, getCurrentTime() + 'Rozłączono z HMT 337')
                    self.LedRHStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))
                    self.PortListRHComboBox.setEnabled(True)
                    self.RefHumidityComboBox.setEnabled(True)
                else:
                    print("Błąd rozłączenia" + self.gradConnection.errorMessage)
                self.measureStopAction()

        else:
            # ŁĄCZENIE PRZYRZĄDU
            self.vaisalaConnection = vaisala.Vaisala(self.portsList[self.PortListGradComboBox.currentIndex()].device)
            self.vaisalaConnection.connect()
            if self.vaisalaConnection.isConnected():
                self.isVaisalaConnected = True
                self.measureThread.setVaisalaConnection(self.vaisalaConnection)
                self.PortListRHComboBox.setEnabled(False)
                self.RefHumidityComboBox.setEnabled(False)
                self.actionStartMeasurement.setEnabled(True)
                self.actionDisconnectAll.setEnabled(True)
                self.LedRHStatusLabel.setPixmap(QtGui.QPixmap(ICON_GREEN_LED))
                self.ConnectRHBtn.setText("Rozłącz")
                self.logList.insertItem(0, getCurrentTime()
                                        + 'Połączono z HMT 337: '
                                        + str(self.vaisalaConnection.baudrate) + " "
                                        + str(self.vaisalaConnection.connection.bytesize) + " "
                                        + str(self.vaisalaConnection.connection.parity) + " "
                                        + str(self.vaisalaConnection.connection.stopbits) + " "
                                        + str(self.vaisalaConnection.connection.xonxoff) + " ")
                # Jeśli nie udała sie próba połączenia
            else:
                self.isVaisalaConnected = False
                self.logList.insertItem(0,
                                        getCurrentTime() + 'Łączę z HMT-337 @ ' + self.PortListRHComboBox.currentText() + '... '
                                        + 'Połączenie nieudane! ' + self.vaisalaConnection.errorMessage)
                self.warninngMessageBox(self.vaisalaConnection.errorMessage, "Błąd połączenia z przyrządem pomiarowym!")
                self.vaisalaConnection = None
                self.LedRHStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

    def measureStopAction(self):
        self.isMeasuring = False
        # Zmiany wizualne w GUI
        self.devicesBox.setEnabled(True)

        if self.chceckAnyConnection():
            self.actionStartMeasurement.setEnabled(True)
            self.actionDisconnectAll.setEnabled(True)
        else:
            self.actionStartMeasurement.setEnabled(False)
            self.actionDisconnectAll.setEnabled(False)

        self.actionStopMeasurement.setEnabled(False)
        self.measureIntervalSpinBox.setEnabled(True)
        # print("STOP Action")

        # Zatrzymanie wątku
        print("STOPPING: " + str(self.measureThread))
        self.measureThread.setKeepRunning(False)
        self.measureThread.stop()
        # self.measureThread.terminate()
        # self.measureThread = None

    def measureStartAction(self):
        # Wyłączam przyciski "ROZLACZ" - jeśli jakieś urządzenie jest podłączone
        self.isMeasuring = True
        self.devicesBox.setEnabled(False)
        self.actionStartMeasurement.setEnabled(False)
        self.actionStopMeasurement.setEnabled(True)
        self.actionDisconnectAll.setEnabled(False)
        print("START Action")

        # self.startMeasureTime = datetime.now().time()
        # self.MeasureBtn.setText("STOP")
        # self.MeasureBtn.setStyleSheet("background-color: rgb(255,170,127)")
        self.measureIntervalSpinBox.setEnabled(False)

        # Tworze nowy wątek i przekazuje mu obiekty do komunikacji z urzadzeniami
        self.measureThread.setInterval(self.measureIntervalSpinBox.value() - 2)
        self.measureThread.setKeepRunning(True)
        self.measureThread.start()
        # startButtonTime = getCurrentTime()
        # self.doMeasurement()

    # Przycisk "Rozpocznij pomiary/STOP"
    def measureBtnAction(self):
        if self.isMeasuring:  # Jesli akutalnie wykonywane sa pomiary, to stopujemy i zmieniamy wyglad guzika
            # Zmiany wizualne w GUI
            self.isMeasuring = False
            # self.MeasureBtn.setText("Rozpocznij pomiary")
            # self.MeasureBtn.setStyleSheet("background-color: rgb(170, 255, 127)")
            self.measureIntervalSpinBox.setEnabled(True)

            # Zatrzymanie wątku
            print("STOPPING: " + str(self.measureThread))
            self.measureThread.setKeepRunning(False)
            self.measureThread.terminate()
            # self.measureThread = None

        else:  # Jesli nie są wykonywane pomiary- to je rozpoczynamy, lub kontynuujemy
            self.isMeasuring = True
            # self.startMeasureTime = datetime.now().time()
            # self.MeasureBtn.setText("STOP")
            # self.MeasureBtn.setStyleSheet("background-color: rgb(255,170,127)")
            self.measureIntervalSpinBox.setEnabled(False)

            # Tworze nowy wątek i przekazuje mu obiekty do komunikacji z urzadzeniami
            self.measureThread.setInterval(self.measureIntervalSpinBox.value() - 2)
            self.measureThread.setKeepRunning(True)
            self.measureThread.start()
            # startButtonTime = getCurrentTime()
            # sleep przez czas okreslony w kontrolce
            # print(time.sleep(float(self.spinBox.value()))
            # self.doMeasurement()

    # Przycisk przełączenia pomiarów temperatury/rezystancji
    def changeTempToRes(self):
        # Ustawiamy flagę odczytu rez/temp w wątku measureThread na przeciwna
        self.measureThread.setReadResistance(not self.measureThread.getReadResistance())
        if self.measureThread.getReadResistance():
            self.logList.insertItem(0, getCurrentTime() + 'Przełączono na pomiar rezystancji czujników PT-100.')
        else:
            self.logList.insertItem(0, getCurrentTime() + 'Przelączono na pomiar temperatury.')
        self.unitChangedFlag = True

    def measDone(self, data):
        # print("From signal MEAS DONE")
        # Po zakończeniu pomiarów pobieramy dane i zapisujemy do zmienniej rowToAdd
        self.rowToAdd = self.measureThread.getRowToAdd()
        # Obliczamy gradient i wpisujemy go do rowToAdd
        self.obliczGradient()

        # startTime = time.time()
        # self.refreshTable(data)
        self.refreshTable()
        # print("Refreshing table: " + str(time.time() - startTime))
        self.refreshGUI()

    def obliczGradient(self):
        """
        Funkcja z otrzymanych pomiarów temperatury oblicza maksymalny gradient. Modyfikuje wiersz "rowToAdd"
        """
        # Dodatkowe obliczenia i modyfikacja wiersza rowToAdd
        self.measNo += 1
        # Obliczenia wartosci min, max gradientu
        if self.isKeithleyConnected:
            gradMeasurement = self.rowToAdd[4:14]  # Tablica, z kótrej wyliczany jest min i max
            # print(self.rowToAdd)
            # print(gradMeasurement)
            self.gradMax = round(max(gradMeasurement), 3)
            self.gradMin = round(min(gradMeasurement), 3)
            self.gradDelta = round((self.gradMax - self.gradMin), 3)
            # self.rowToAdd.append(self.gradDelta)
        else:
            self.gradDelta = "-"
        self.rowToAdd.insert(14, self.gradDelta)  # Uzupełniamy wiersz o obliczony gradient
        self.rowToAdd.insert(15, round(self.maxAllowedGradSpinBox.value(), 3))  # uzupełniamy wiersz o ustawiony limit gradientu
        # Dodajemy wiersz do tabeli do wyświetlenia w GUI

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

    def refreshTable(self):
        # Aktualizacja tabeli w GUI
        # Tabela pokazuje wszystie wyniki, nawet te z przekroczonym gradientem
        self.tableData = self.tableData.append(pd.Series(self.rowToAdd, index=self.tableHeader), ignore_index=True)
        self.tableData.index = self.tableData.index + 1
        self.tableModel.setNewData(self.tableData)
        self.tableModel.layoutChanged.emit()
        self.tableView.setModel(self.tableModel)
        # Dopasowuje wysokość wiersza do zawartości
        self.tableView.resizeRowToContents(self.tableData.shape[0] - 1)
        # Dopasowuje szerokosc kolumn do zawartości, ale tylko przy pierwszym wykonanym pomiarze
        if self.tableData.shape[0] == 1:
            self.tableView.resizeColumnsToContents()
            self.tableView.resizeRowsToContents()

        # Dopasowujemy szerokosc kolumn po zmianie wyświetlanych wartości Temp/Rezystn
        if self.unitChangedFlag:
            self.tableView.resizeColumnsToContents()
            self.unitChangedFlag = False

        self.tableView.update()
        # self.tableView.resizeRowsToContents()
        self.tableView.scrollToBottom()

    # Funkcja w celu wskazania pliku do zapisu danych (Okno dialogowe)
    def saveToExcelWindow(self):
        if self.filename == '':
            temp = QFileDialog.getSaveFileName(self, "Zapisz dane pomiarowe...", self.pathToDesktop, "Excel Files (*.xlsx);;All Files (*)")[
                0]
        else:
            temp = QFileDialog.getSaveFileName(self, "Zapisz dane pomiarowe...", self.filename, "Excel Files (*.xlsx);;All Files (*)")[0]
        if temp == '':
            # self.logList.insertItem(0, getCurrentTime() + 'Nie wskazano pliku.')
            return 0
        else:
            self.filename = temp
            return 1

    def saveAs(self):
        if self.saveToExcelWindow():
            self.saveFile()

    def checkIfIsMeasuringAndSave(self):
        if self.isMeasuring:
            self.saveFile()
        else:
            self.logList.insertItem(0, getCurrentTime() + 'Rozpocznij pomiary aby uruchomić autozapis.')

    def saveFile(self):
        if self.filename == '':
            self.saveToExcelWindow()
        else:
            try:
                print("Zapisuje plik: " + self.filename)
                # print(self.tableData)
                self.tableData.to_excel(self.filename)
            except Exception as e:
                self.logList.insertItem(0, getCurrentTime() + 'Błąd zapisu do pliku: ' + str(e))
            else:
                self.logList.insertItem(0, getCurrentTime() + 'Zapisano dane do: ' + str(self.filename))

    def changeAutoSaveCheckBox(self):
        # print("Auto Save Box changed")
        if self.autoSaveCheckBox.isChecked():
            if self.filename == '':
                self.saveToExcelWindow()
            # Jeśli użytkownik nie wskazał pliku do zapisu
            if self.filename == '':
                self.autoSaveCheckBox.setChecked(False)
            else:
                self.timeIntervalSpinBox.setEnabled(True)
                self.saveFile()
                print("Autozapis co " + str(self.timeIntervalSpinBox.value()) + " min do: " + str(self.filename) + "")
                self.autoSaveTimer.start(self.timeIntervalSpinBox.value() * 60000)
        else:
            self.autoSaveCheckBox.setChecked(False)
            self.autoSaveTimer.stop()
            self.logList.insertItem(0, getCurrentTime() + 'Autozapis wyłączony.')

    def changeTimeIntervalSpinBox(self):
        self.autoSaveTimer.setInterval(self.timeIntervalSpinBox.value() * 60000)

    # Funkcja uruchamiana po zmianie urządzenia do pomiaru temperatury(changeRefComboBox),
    # jeśli wybrano FLUKE, aktywuj label i pole do wyboru kanału urządzenia.
    def changeRefComboBox(self):
        # Wybrano na liście P-755
        if self.RefTempComboBox.currentIndex() == 0:
            self.Fluke1595ChannelComboBox.setEnabled(False)
            self.tableHeader = ['Time', 'P-755', 'HMT-Temp', 'HMT-RH', 'CH 1', 'CH 2', 'CH 3', 'CH 4', 'CH 5', 'CH 6', 'CH 7', 'CH 8',
                                'CH 9', 'CH 10', 'Gradient', 'Limit']

        # Wybrano na liście urządzeń do podłączenia -FLuke
        if self.RefTempComboBox.currentIndex() == 1:
            self.Fluke1595ChannelComboBox.setEnabled(True)
            self.tableHeader = ['Time', '1595A', 'HMT-Temp', 'HMT-RH', 'CH 1', 'CH 2', 'CH 3', 'CH 4', 'CH 5', 'CH 6', 'CH 7', 'CH 8',
                                'CH 9', 'CH 10', 'Gradient', 'Limit']
        self.tableData = pd.DataFrame(columns=self.tableHeader)  # Obiekt do wyswietlenia danych w tabeli GUI

    # Funkcja czyści tabelę z wynikami, oraz pola w GUI
    def clearMeasurement(self):
        # Okno z ostrzeżeniem
        if self.measNo == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Brak pomiarów")
            dlg.setText("Brak wykonanych pomiarów")
            dlg.setStandardButtons(QMessageBox.Ok)
            dlg.setIcon(QMessageBox.Information)
            dlg.exec_()
        else:
            # print("Otwietam message box")
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Potwierdź usunięcie danych")
            dlg.setText("Czy na pewno wyczyścić dane pomiarowe ?")
            dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Abort)
            dlg.setIcon(QMessageBox.Warning)
            button = dlg.exec_()

            if button == QMessageBox.Yes:
                print("Klasuje dane pomiarowe")
                # print(self.tableData.shape[0])
                # self.tableData.drop([0,self.tableData.shape[0]],inplace=True)
                self.tableData.drop(self.tableData.index, inplace=True)

                # Odświerzam widok w GUI
                self.tableModel.setNewData(self.tableData)
                self.tableModel.layoutChanged.emit()
                self.tableView.setModel(self.tableModel)

                # Aktualizacja w GUI
                self.measNo = 0
                self.maxTempLineEdit.setText("")
                self.minTempLineEdit.setText("")
                self.countMeasLineEdit.setText(str(self.measNo))
                self.gradLineEdit.setText("")
                self.gradLineEdit.setStyleSheet("background-color: rgb(255, 255, 255)")

    # Powtórne wczytanie współczynników A,B, R0 sond pomiarowych
    def refreshProbesCoeff(self):
        if self.measureThread.refreshProbesCoeff():
            self.infoMessageBox("Wczytano współcznynniki", "Pobrano współczynniki PT-100 z pliku: \"ProbesCoeff\" ")
        else:
            self.warninngMessageBox("Nie wczytano współczynników.", "Dupa")

        # else:
        #    self.warninngMessageBox("Połącz z Keithley 2000", "Nie wczytano współczynników. Połącz z Keithley2000")

    # Sprawdzam czy jest podłączone jakieś urządzenie, jeśli tak, aktywuje przycisk DisconnectAll
    def chceckAnyConnection(self):
        # Jeśli którekolwiek urządzenie jest podłączone, aktywuj przycisk ToolBar>Disconnect All
        if self.isThermometrConnected or self.isVaisalaConnected or self.isKeithleyConnected:
            self.actionDisconnectAll.setEnabled(True)
            return True
        else:
            self.actionDisconnectAll.setEnabled(False)
            return False

    # Disconnect it All
    def disconnectAll(self):
        print("Rozłączam wszystko")
        if self.isKeithleyConnected:
            if self.gradConnection.disconnect():
                self.isKeithleyConnected = False
                self.LedGradStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

        if self.isThermometrConnected:
            if self.tempConnection.disconnect():
                self.isThermometrConnected = False
                self.LedTempStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

        if self.isVaisalaConnected:
            if self.vaisalaConnection.disconnect():
                self.isVaisalaConnected = False
                self.LedRHStatusLabel.setPixmap(QtGui.QPixmap(ICON_RED_LED))

        # Zmiany w głównej belce z przyciskami
        self.ConnectGradBtn.setText("Połącz")
        self.ConnectRHBtn.setText("Połącz")
        self.ConnectTempBtn.setText("Połącz")

        # Zatrzymujemy pomiary:
        self.measureStopAction()

    def showHelpWindow(self):
        self.helpDialog.show()

    def showAboutWindow(self):
        self.aboutDialog.show()

    def warninngMessageBox(self, errorMessage: str, errorTitle: str):
        if "PermissionError(13" in errorMessage:
            poz1 = errorMessage.find("'")
            poz2 = errorMessage.find("'", poz1 + 1)
            errorMessage = "Port " + errorMessage[poz1 + 1:poz2] + " jest zajęty. Wybierz inny port COM."

        dlg = QMessageBox(self)
        dlg.setWindowTitle(errorTitle)
        dlg.setText(errorMessage)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.setIcon(QMessageBox.Warning)
        dlg.exec_()
        return

    def infoMessageBox(self, title: str, infoMessage: str):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(infoMessage)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.setIcon(QMessageBox.Information)
        dlg.exec_()
        return

    def exit_app(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Zamknij program")
        dlg.setText("Czy na pewno zamknąć program?")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setIcon(QMessageBox.Warning)
        button = dlg.exec_()

        if button == QMessageBox.Yes:
            self.close()


# Funkcje poza główną klasa
def getCurrentTime():
    # return datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S ')
    return datetime.now().strftime('%H:%M:%S ')


def main():
    app = QApplication(sys.argv)
    mainWindow = ImageViewer()
    mainWindow.show()
    app.exec_()


if __name__ == '__main__':
    main()

# TODO
"""
 1. Weryfikacja połączenia COM, np. żeby termomentr P-755 nie łączył się z keitleyem itd    [ ]
    1.1 Aktualizacja CheckIDN - Keithley                                                    [X]
    1.2 Aktualizacja CheckIDN - P-755                                                       [ ] - Do aktualizacji, polecenie IDN? i odp
    1.3 Aktualizacja CheckIDN - Fluke                                                       [X]
    1.4 Aktualizacja CheckIDN - Vaisala                                                     [?] - Do sprawdzenia
 2. Dodać diody statusu RED/GREEN                                                           [X]
 3. Zatrzymanie pomiarów po utracie połączenia lub wyłączeniu urządzenia                    [ ]
 4. Przyciski "Rozłącz" dla każdego urządzenia                                              [?] - Do sprawdzenia
    4.1 Optymalizacja kodu dla termometrów P755/Fluke                                       [X]
    4.2 Aktualizacja plików .py przyrządów pod kątem rozłączenia                            [?] - Do sprawdzenia
 5. Wyświetlenie ilości wykonanaych pomiarów                                                [X]
 6. Poprawa zapisu danych w Excelu                                                          [X]
 7. Czyszczenie danych pomiarowych                                                          [X]
 8. Obsługa FLUKE 1595A                                                                     [X]
 9. Okno Warrning - wybierz inny port COM                                                   [X]
 10. Wczytaj ponownie współczynniki PT100                                                   [X]
 11. Symulacja Arduino                                                                      [-]
 12. Automatyczny zapis do pliku.                                                           [X]
   12.1 Menu + Automatyczny zapis, wybór pliku, czestotliwość zapisu.                       [X]
   12.2 Autozapis tylko gdy trwają pomiary.                                                 [X]
 13. Menu: Pomoc, Wersja + Autorzy                                                          [X]
 14. Okno (zakładka) Full LOG                                                               [ ]
 15. Menu: -> Nowe okno Edytuj współczynniki ABC - implementacja YAML                       [ ]
   15.1 Wczytanie współczynników ABC bez połączenia z Keithley                              [X]
   15.2 Dialog do wpisania ręcznego współcznników i wyboru plików                           [ ]
   15.3 Wskazanie pliku YAML z którego będzie odczyt ABC                                    [ ]
   15.3 Wskazanie pliku YAML do zapisu współczynników                                       [ ]
 16. Szybkie odczyty z Keithley - po powtórnym wcisnięciu "Pomiary" - WHY?                  [ ]

 -----     WYKRESY     -----
 1. Poprawa czasu na osi X                                                                  [ ]
 2. Czerwona linia maksymalnego dozwolonego gradientu                                       [ ]
 3. Poprawić oś y, od 0 do górny limit gradientu + offset                                   [ ]
"""
