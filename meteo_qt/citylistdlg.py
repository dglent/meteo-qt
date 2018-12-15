from PyQt5.QtCore import QCoreApplication, Qt, QSettings, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                             QListWidget, QPushButton, QVBoxLayout)

try:
    import searchcity
    import citytranslate
except ImportError:
    from meteo_qt import searchcity
    from meteo_qt import citytranslate


class CityListDlg(QDialog):
    citieslist_signal = pyqtSignal([list])
    citiesdict_signal = pyqtSignal([dict])

    def __init__(self, citylist, accurate_url, appid, trans_cities_dict, parent=None):
        super(CityListDlg, self).__init__(parent)
        self.settings = QSettings()
        self.citylist = citylist
        self.trans_cities_dict = trans_cities_dict
        self.accurate_url = accurate_url
        self.appid = appid
        self.listWidget = QListWidget()
        self.listWidget.itemDoubleClicked.connect(self.translate)
        cities_list = []
        for i in self.citylist:
            cities_list.append(self.trans_cities_dict.get(i, i))
        self.listWidget.addItems(cities_list)
        buttonLayout = QVBoxLayout()
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
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
        self.translate_button = QPushButton(
            QCoreApplication.translate(
                'Button',
                '&Translate',
                'Edit cities name'
            )
        )
        buttonLayout.addWidget(self.translate_button)
        self.translate_button.clicked.connect(self.translate)
        buttonLayout.addWidget(self.buttonBox)
        self.status = QLabel()
        layoutT.addLayout(layout)
        layoutT.addWidget(self.status)
        self.setLayout(layoutT)
        self.setWindowTitle(
            QCoreApplication.translate(
                'Window title',
                'Cities',
                'Cities list dialogue'
            )
        )
        self.checklength()

    def add(self):
        self.status.setText('')
        lista = []
        newitem = ''
        self.citytoadd = ''
        self.countrytoadd = ''
        self._idtoadd = ''
        dialog = searchcity.SearchCity(self.accurate_url, self.appid, self)
        dialog.id_signal.connect(self.addcity)
        dialog.city_signal.connect(self.addcity)
        dialog.country_signal.connect(self.addcity)
        if dialog.exec_() == 1:
            newitem = (
                self.citytoadd + '_' + self.countrytoadd
                + '_' + self._idtoadd
            )
            for row in range(self.listWidget.count()):
                lista.append(self.listWidget.item(row).text())
            if newitem in lista:
                self.status.setText(
                    QCoreApplication.translate(
                        'Status bar message',
                        'The city already exists in the list',
                        'Cities list dialogue'
                    )
                )
                return
            else:
                self.listWidget.addItem(newitem)
                self.checklength()
                self.status.setText(
                    QCoreApplication.translate(
                        'Status bar message',
                        'ℹ ' + 'Toggle cities with mouse scroll on the weather window',
                        'Cities list dialogue'
                    )
                )

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
        if self.listWidget.count() == 1:
            self.status.setText(
                QCoreApplication.translate(
                    'Message when trying to remove the'
                    'last and unique city in the list',
                    'This is the default city !',
                    'Cities list dialogue'
                )
            )
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
        if self.listWidget.count() == 1:
            # After adding the first city the entry is not activated
            self.listWidget.setCurrentRow(0)
        if self.listWidget.count() > 0:
            self.translate_button.setEnabled(True)
            self.listWidget.setMinimumWidth(self.listWidget.sizeHintForColumn(0))
        else:
            self.translate_button.setEnabled(False)

    def translate(self):
        city = self.listWidget.currentItem().text()
        dialog = citytranslate.CityTranslate(city, self.trans_cities_dict, self)
        dialog.city_signal.connect(self.current_translation)
        if dialog.exec_() == 1:
            row = self.listWidget.currentRow()
            item = self.listWidget.takeItem(row)
            del item
            self.listWidget.insertItem(row, self.current_translated_city)
            self.listWidget.setCurrentRow(row)

    def current_translation(self, translated_city):
        for city,translated in translated_city.items():
            if translated == '':
                translated = city
            self.trans_cities_dict[city] = translated
            self.current_translated_city = translated

    def accept(self):
        listtosend = []
        for row in range(self.listWidget.count()):
            city = self.find_city_key(self.listWidget.item(row).text())
            listtosend.append(city)
        if self.listWidget.count() == 0:
            return
        self.citieslist_signal[list].emit(listtosend)
        self.citiesdict_signal[dict].emit(self.trans_cities_dict)
        QDialog.accept(self)

    def find_city_key(self, city):
        for key,value in self.trans_cities_dict.items():
            if value == city:
                return key
        return city
