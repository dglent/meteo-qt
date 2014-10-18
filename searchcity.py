#!/usr/bin/env python3

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import urllib.request
from lxml import etree

class SearchCity(QDialog):
    
    def __init__(self, accurate_url, parent=None):
        super(SearchCity, self).__init__(parent)
        self.delay = 1000
        self.timer = QTimer()
        self.accurate_url = accurate_url
        self.suffix = '&type=accurate&mode=xml'
        self.layout = QVBoxLayout()
        self.line_search = QLineEdit('Type the name of the city and press Enter')
        self.line_search.selectAll()
        self.listWidget = QListWidget()
        self.status = QLabel()
        self.layout.addWidget(self.line_search)
        self.layout.addWidget(self.listWidget)
        self.layout.addWidget(self.status)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch()
        self.buttonOk = QPushButton('&Ok')
        self.buttonOk.setEnabled(False)
        self.buttonCancel = QPushButton('&Cancel')
        self.buttonLayout.addWidget(self.buttonOk)
        self.buttonLayout.addWidget(self.buttonCancel)
        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)
        self.connect(self.line_search, SIGNAL("returnPressed()"), self.search)
        self.connect(self.buttonOk, SIGNAL("clicked()"), self.accept)
        self.connect(self.buttonCancel, SIGNAL("clicked()"), self.reject)
        self.connect(self.listWidget, SIGNAL("itemSelectionChanged()"), self.buttonCheck)
        self.connect(self.listWidget, SIGNAL("itemDoubleClicked(QListWidgetItem *)"), self.accept)
        self.status.setText('')
        
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
            city_list = selected_city.split('-')
            for c in range(len(city_list)):
                city_list[c] = city_list[c].strip()
            self.emit(SIGNAL('id(PyQt_PyObject)'), ('ID', city_list[0]))
            self.emit(SIGNAL('city(PyQt_PyObject)'), ('City', city_list[1]))
            self.emit(SIGNAL('country(PyQt_PyObject)'), ('Country', city_list[2]))
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
        self.status.setText('Searching...')
        self.workThread = WorkThread(self.accurate_url, self.city, self.suffix)
        self.connect(self.workThread, SIGNAL('city(QString)'), self.addlist)
        self.connect(self.workThread, SIGNAL('finished()'), self.result)
        self.connect(self.workThread, SIGNAL('error(QString)'), self.error)
        self.timer.singleShot(self.delay, self.threadstart)
    
    def threadstart(self):
        self.workThread.start()
        
    def addlist(self, city):
        self.lista.append(city)
        
    def error(self, e):
        self.delay = 5000
        print(e)
        self.status.setText(e)
        self.errorStatus = True
        
    def result(self):
        if self.errorStatus:
            return
        self.delay = 1000
        self.listWidget.addItems(self.lista)
        number_cities = len(self.lista)
        cities_text = ''
        if number_cities == 0:
            cities_text = 'No results'
        elif number_cities == 1:
            cities_text = 'Found {0} city'.format(number_cities)
        elif number_cities > 1:
            cities_text = 'Found {0} cities'.format(number_cities)
        self.status.setText(cities_text)
        
        
class WorkThread(QThread):
    def __init__(self, accurate_url, city, suffix):
        QThread.__init__(self)
        self.accurate_url = accurate_url
        # Search in any language
        self.city = repr(city.encode('utf-8')).replace("b'","").replace("\\x","%").replace("'","")
        self.suffix = suffix

    def __del__(self):
        self.wait()
 
    def run(self):
        self.lista = []
        if self.city == '':
            return
        try:
            req = urllib.request.urlopen(self.accurate_url + self.city + self.suffix)
            page = req.read()
            tree = etree.fromstring(page)
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            error = 'Error ' + str(error.code) + ' ' + str(error.reason + '\nTry again later')
            self.emit(SIGNAL('error(QString)'), error)
            return
        if int(tree[1].text) == 0:
            return
        for i in range(int(tree[1].text)):
            city = tree[3][i][0].get('name')
            if city == '':
                return
            country = tree[3][i][0][1].text
            id_ = tree[3][i][0].get('id')
            if int(id_) == 0:
                error = ('Data error, please try again later\nor modify the name of the city')
                self.emit(SIGNAL('error(QString)'), error)
                return
            self.lista.append(id_ + ' - ' + city + ' - ' + country)        
        for i in self.lista:
            self.emit(SIGNAL('city(QString)'), i)
        print('City thread done')
        return  
        
