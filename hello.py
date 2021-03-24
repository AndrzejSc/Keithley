import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QTableView

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("Monitor temperatury komory klimatycznej")
window.setGeometry(100, 100, 600, 600)
window.move(60, 15)
helloMsg = QLabel('<h1>Hello World!</h1>', parent=window)
helloMsg.move(60, 15)
tempTable = QTableView(parent=window)

#dane do tabeli

window.show()

sys.exit(app.exec_())
