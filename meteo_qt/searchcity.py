#!/usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import urllib.request
from lxml import etree

class SearchCity(QDialog):
    id_signal = pyqtSignal([tuple])
    city_signal = pyqtSignal([tuple])
    country_signal = pyqtSignal([tuple])

    def __init__(self, accurate_url, parent=None):
        super(SearchCity, self).__init__(parent)
        self.delay = 1000
        self.timer = QTimer()
        self.accurate_url = accurate_url
        self.suffix = '&type=like&mode=xml'
        self.layout = QVBoxLayout()
        self.lineLayout = QHBoxLayout()
        self.buttonSearch = QPushButton()
        self.buttonSearch.setIcon(QIcon(':/find'))
        self.buttonSearch.clicked.connect(self.search)
        self.line_search = QLineEdit(self.tr('Type the name of the city and press Enter'))
        self.line_search.selectAll()
        self.listWidget = QListWidget()
        self.status = QLabel()
        self.lineLayout.addWidget(self.line_search)
        self.lineLayout.addWidget(self.buttonSearch)
        self.layout.addLayout(self.lineLayout)
        self.layout.addWidget(self.listWidget)
        self.layout.addWidget(self.status)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch()
        self.buttonOk = QPushButton(self.tr('&Ok'))
        self.buttonOk.setEnabled(False)
        self.buttonCancel = QPushButton(self.tr('&Cancel'))
        self.buttonLayout.addWidget(self.buttonOk)
        self.buttonLayout.addWidget(self.buttonCancel)
        self.layout.addLayout(self.buttonLayout)
        self.setMinimumWidth(int(len(self.line_search.text())*10))
        self.setLayout(self.layout)
        self.line_search.returnPressed.connect(self.search)
        self.buttonOk.clicked.connect(self.accept)
        self.buttonCancel.clicked.connect(self.reject)
        self.listWidget.itemSelectionChanged.connect(self.buttonCheck)
        self.listWidget.itemDoubleClicked['QListWidgetItem *'].connect(self.accept)
        self.status.setText(self.tr('Tip: Type the first three letters to search by substring'))

    def buttonCheck(self):
        '''Enable OK button if an item is selected'''
        row = self.listWidget.currentRow()
        item = self.listWidget.item(row)
        if item != None:
            self.buttonOk.setEnabled(True)

    def accept(self):
        row = self.listWidget.currentRow()
        item = self.listWidget.item(row)
        if item != None:
            selected_city = item.text()
            city_list = selected_city.split(' - ')
            for c in range(len(city_list)):
                city_list[c] = city_list[c].strip()
            id_ = 'ID', city_list[0]
            city = 'City', city_list[1]
            country = 'Country', city_list[2]
            self.id_signal[tuple].emit(id_)
            self.city_signal[tuple].emit(city)
            self.country_signal[tuple].emit(country)
        QDialog.accept(self)

    def search(self):
        try:
            if self.workThread.isRunning():
                return
        except AttributeError:
            pass
        self.lista=[]
        self.dico={}
        self.errorStatus = False
        self.buttonOk.setEnabled(False)
        self.listWidget.clear()
        self.city = (self.line_search.text())
        self.status.setText(self.tr('Searching...'))
        self.workThread = WorkThread(self.accurate_url, self.city, self.suffix)
        self.workThread.city_signal['QString'].connect(self.addlist)
        self.workThread.finished.connect(self.result)
        self.workThread.error['QString'].connect(self.error)
        self.timer.singleShot(self.delay, self.threadstart)

    def threadstart(self):
        self.workThread.start()

    def addlist(self, city):
        print('Found: ', city)
        self.lista.append(city)

    def error(self, e):
        self.delay = 5000
        print(e)
        self.status.setText(e)
        self.adjustSize()
        self.errorStatus = True

    def result(self):
        if self.errorStatus:
            return
        self.delay = 1000
        self.listWidget.addItems(self.lista)
        number_cities = len(self.lista)
        cities_text = ''
        if number_cities == 0:
            cities_text = self.tr('No results')
        elif number_cities == 1:
            cities_text = self.tr('Found {0} city').format(number_cities)
        elif number_cities > 1:
            cities_text = self.tr('Found {0} cities').format(number_cities)
        self.status.setText(cities_text)


class WorkThread(QThread):
    error = pyqtSignal(['QString'])
    city_signal = pyqtSignal(['QString'])

    def __init__(self, accurate_url, city, suffix):
        QThread.__init__(self)
        self.accurate_url = accurate_url
        # Search in any language
        self.city = repr(city.encode('utf-8')).replace("b'","").replace("\\x","%").replace("'","")
        self.suffix = suffix
        self.tentatives = 1

    def __del__(self):
        self.wait()

    def run(self):
        error_message = self.tr('Data error, please try again later\nor modify the name of the city')
        self.lista = []
        if self.city == '':
            return
        try:
            req = urllib.request.urlopen(self.accurate_url + self.city + self.suffix)
            page = req.read()
            tree = etree.fromstring(page)
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            code = ''
            if hasattr(error, 'code'):
                code = str(error.code)
            m_error = (self.tr('Error: ') + code + ' ' + str(error.reason) +
                       self.tr('\nTry again later'))
            self.error['QString'].emit(m_error)
            return
        # No result
        if int(tree[1].text) == 0:
            print('Number of cities: 0')
            return
        for i in range(int(tree[1].text)):
            city = tree[3][i][0].get('name')
            country = tree[3][i][0][1].text
            id_ = tree[3][i][0].get('id')
            if int(id_) == 0:
                print('Error ID: ',id_)
                self.error['QString'].emit(error_message)
                return
            if city == '' or country == None:
                print('Tries: ',self.tentatives)
                if self.tentatives == 10:
                    self.error['QString'].emit(error_message)
                    return
                else:
                    self.tentatives += 1
                    self.run()
                    print('Try to retreive city information...')
            try:
                self.lista.append(id_ + ' - ' + city + ' - ' + country)
            except:
                print('An error has occured:\n')
                print('ID', id_)
                print('City',city)
                print('Country', country)
                return
        for i in self.lista:
            self.city_signal['QString'].emit(i)
        print('City thread done')
        return

