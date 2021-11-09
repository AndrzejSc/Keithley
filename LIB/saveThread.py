# NIEUŻYWANY - Jeśli Qtimer nie da rady, trzeba wrócić do tematu na Threadach
import datetime

from PyQt5.QtCore import pyqtSignal, QThread, QObject


class MySignal(QObject):
    signal_str = pyqtSignal(str)


class SaveThread(QThread):
    def __init__(self, interval=10, parent=None):
        super(SaveThread, self).__init__()

        # Zmienne proste
        self._interval = interval * 60
        self._keepRunning = False

        # Signals
        self.saveNowSignal = MySignal()
        # self.measDoneSignal.signal_str.connect(parent.refreshTable)
        # print("MeasThread instance created!" + str(self))

    def setInterval(self, interval):
        self._interval = interval*60
        print("Zmieniam interwał na: "+str(self._interval)+"s")

    def setKeepRunning(self, state: bool):
        self._keepRunning = state

    def run(self):
        print("Automatyczny zapis:, Interval: " + str(self._interval) + "s, keepRunning: " + str(self._keepRunning))
        # while self._keepRunning:
        # self.emitSignal()
        self.sleep(self._interval)
        print("Emisja SaveNowSignal @ " + datetime.datetime.today().strftime("%H:%M:%S"))
        self.saveNowSignal.signal_str.emit('SAVE')
        self.exec_()

    def exec_(self) -> int:
        print("EXEC_")
        self.sleep(1)
        return 0

    def emitSignal(self):
        self.saveNowSignal.signal_str.emit('SAVE')
