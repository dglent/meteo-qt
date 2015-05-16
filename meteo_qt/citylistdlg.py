from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDialog, QListWidget, QVBoxLayout, QHBoxLayout, QDialogButtonBox,
    QPushButton, QLabel
    )

try:
    import searchcity
except:
    from meteo_qt import searchcity


class CityListDlg(QDialog):
    citieslist_signal = pyqtSignal([list])

    def __init__(self, citylist, accurate_url, parent=None):
        super(CityListDlg, self).__init__(parent)
        self.citylist = citylist
        self.accurate_url = accurate_url
        self.listWidget = QListWidget()
        self.listWidget.addItems(self.citylist)
        buttonLayout = QVBoxLayout()
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.accept)
        layoutT = QVBoxLayout()
        layout = QHBoxLayout()
        layout.addWidget(self.listWidget)
        layout.addLayout(buttonLayout)
        for text, slot in ((self.tr("&Add..."), self.add),
                           (self.tr("&Remove..."), self.remove),
                           (self.tr("&Up"), self.up),
                           (self.tr("&Down"), self.down),
                           (self.tr("De&fault"), self.default),
                           (self.tr("&Sort"), self.listWidget.sortItems)):
            button = QPushButton(text)
            buttonLayout.addWidget(button)
            button.clicked.connect(slot)
        buttonLayout.addWidget(self.buttonBox)
        self.status = QLabel()
        layoutT.addLayout(layout)
        layoutT.addWidget(self.status)
        self.setLayout(layoutT)
        self.checklength()

    def add(self):
        self.status.setText('')
        lista = []
        newitem=''
        self.citytoadd = ''
        self.countrytoadd = ''
        self._idtoadd = ''
        dialog = searchcity.SearchCity(self.accurate_url, self)
        dialog.id_signal.connect(self.addcity)
        dialog.city_signal.connect(self.addcity)
        dialog.country_signal.connect(self.addcity)
        if dialog.exec_() == 1:
            newitem = self.citytoadd + '_' + self.countrytoadd + '_' + self._idtoadd
            for row in range(self.listWidget.count()):
                lista.append(self.listWidget.item(row).text())
            if newitem in lista:
                self.status.setText(self.tr('The city already exists in the list'))
                return
            else:
                self.listWidget.addItem(newitem)
                self.checklength()

    def addcity(self, what):
        self.status.setText('')
        if what[0] == 'ID':
            self._idtoadd = what[1]
        elif what[0] == 'City':
            self.citytoadd = what[1]
        elif what[0] == 'Country':
            self.countrytoadd = what[1]

    def remove(self):
        self.status.setText('')
        if self.listWidget.count() == 0:
            self.status.setText(self.tr('The list is empty'))
            return
        row = self.listWidget.currentRow()
        item = self.listWidget.item(row)
        if item is None:
            return
        message = self.tr('The city "{0}" has been removed').format(
            self.listWidget.item(row).text())
        item = self.listWidget.takeItem(row)
        del item
        self.status.setText(message)

    def up(self):
        self.status.setText('')
        row = self.listWidget.currentRow()
        if row >= 1:
            item = self.listWidget.takeItem(row)
            self.listWidget.insertItem(row - 1, item)
            self.listWidget.setCurrentItem(item)

    def down(self):
        self.status.setText('')
        row = self.listWidget.currentRow()
        if row < self.listWidget.count() - 1:
            item = self.listWidget.takeItem(row)
            self.listWidget.insertItem(row + 1, item)
            self.listWidget.setCurrentItem(item)

    def default(self):
        self.status.setText('')
        row = self.listWidget.currentRow()
        if row >= 1:
            item = self.listWidget.takeItem(row)
            self.listWidget.insertItem(0, item)
            self.listWidget.setCurrentItem(item)

    def checklength(self):
        listtosend = []
        for row in range(self.listWidget.count()):
            listtosend.append(self.listWidget.item(row).text())
        if len(listtosend) == 0:
            return
        maxi = len(max(listtosend, key=len))
        self.listWidget.setMinimumWidth(self.listWidget.sizeHintForColumn(0))

    def accept(self):
        listtosend = []
        for row in range(self.listWidget.count()):
            listtosend.append(self.listWidget.item(row).text())
        self.citieslist_signal[list].emit(listtosend)
        QDialog.accept(self)
