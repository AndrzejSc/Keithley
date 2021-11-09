# Zapis ciągły, po wykonaniu każdej serii pomiarowej. W aktualnej wersji nieużywany.
# Funkcja z głównej klasy MainWindow.
# Wymaga biblioteki AppendToExcel
def saveToExcel(self):
    # Dodajemy datę do tabeli
    self.rowToAdd.insert(0, datetime.now().strftime('%d.%m.%Y'))
    self.dataToExcel = self.dataToExcel.append(pd.Series(self.rowToAdd, index=self.tableHeaderToExcel), ignore_index=True)
    self.dataToExcel.index = self.dataToExcel.index + 1

    # Przy okazji sprawdzamy czas wykonania zapisu
    startTime = time.time()
    # Jeśli to pierwszy wiersz do zapisania  to
    if self.measNo == 1:
        self.appendToExcel.append(self.dataToExcel)
    else:
        # Jeśli nie, to do excela dopisujemy wiersz, ale bez nagłówka
        temp = pd.DataFrame(self.rowToAdd).T
        temp.index = temp.index + self.measNo
        # print(temp.index)
        self.appendToExcel.append(temp, header=False)
        # print(self.rowToAdd)
        # print(temp)
    print("\tSaving to file: " + str(time.time() - startTime))


# MainClass :
#     # self.appendToExcel = appendToExcel.AppendToExcel("test9.xlsx")
#     self.writer = pd.ExcelWriter(self.excelFileName, engine='openpyxl')