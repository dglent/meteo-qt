#!/usr/bin/env python3

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import searchcity


class MeteoSettings(QDialog):

    def __init__(self, accurate_url, parent=None):
        super(MeteoSettings, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.accurate_url = accurate_url
        self.settings = QSettings()
        self.set_city = self.settings.value('City') or '?'
        self.setLanguage = self.settings.value('Language') or 'en'
        self.tempUnit = self.settings.value('Unit') or 'metric'
        self.interval_set = self.settings.value('Interval') or '30'
        self.cityLabel = QLabel(self.set_city)
        self.cityTitle = QLabel(self.tr('City'))
        self.cityButton = QPushButton()
        self.cityButton.setIcon(QIcon(':/configure'))
        self.cityButton.setToolTip(self.tr('Click to modify the city'))
        self.languageLabel = QLabel(self.tr('Language'))
        self.languageCombo = QComboBox()
        self.languageCombo.setToolTip(self.tr('The language for the weather descriptions'))
        self.language_dico = {'en': self.tr('English'), 'ru': self.tr('Russian'),
                              'it': self.tr('Italian'), 'es': self.tr('Spanish'),
                              'uk': self.tr('Ukrainian'), 'de': self.tr('German'),
                              'pt': self.tr('Portuguese'), 'ro': self.tr('Romanian'),
                              'pl': self.tr('Polish'), 'fi': self.tr('Finnish'),
                              'nl': self.tr('Dutch'), 'fr': self.tr('French'),
                              'bg': self.tr('Bulgarian'), 'sv': self.tr('Swedish'),
                              'zh_tw': self.tr('Chinese Traditional'),
                              'zh_cn': self.tr('Chinese Simplified'),
                              'tr': self.tr('Turkish'), 'hr': self.tr('Croatian'),
                              'cd': self.tr('Catalan'), 'el': self.tr('Greek')}
        lang_list = list(c for l,c in self.language_dico.items())
        lang_list.sort()
        self.languageCombo.addItems(lang_list)
        self.languageCombo.setCurrentIndex(self.languageCombo.findText
                                           (self.language_dico[self.setLanguage]))
        self.connect(self.languageCombo, SIGNAL('currentIndexChanged(int)'), self.language)
        self.connect(self.cityButton, SIGNAL("clicked()"), self.searchcity)
        self.unitsLabel = QLabel(self.tr('Temperature unit'))
        self.unitsCombo = QComboBox()
        self.unitsDico = {'metric': '°C', 'imperial': '°F', ' ': '°K'}
        unitsList = list(t for l,t in self.unitsDico.items())
        self.unitsCombo.addItems(unitsList)
        self.unitsCombo.setCurrentIndex(self.unitsCombo.findText(
            self.unitsDico[self.tempUnit]))
        self.connect(self.unitsCombo, SIGNAL('currentIndexChanged(int)'), self.units)
        self.interval_label = QLabel(self.tr('Update interval'))
        self.interval_min = QLabel(self.tr('minutes'))
        self.interval_combo = QComboBox()
        self.interval_list = ['15','30','45','60','90','120']
        self.interval_combo.addItems(self.interval_list)
        self.interval_combo.setCurrentIndex(self.interval_combo.findText(
            self.interval_list[self.interval_list.index(self.interval_set)]))
        self.connect(self.interval_combo, SIGNAL('currentIndexChanged(int)'), self.interval)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttonLayout.addWidget(buttonBox)
        self.connect(buttonBox, SIGNAL("rejected()"), self.reject)
        self.panel = QGridLayout()
        self.panel.addWidget(self.cityTitle, 0,0)
        self.panel.addWidget(self.cityLabel, 0,1)
        self.panel.addWidget(self.cityButton, 0,2)
        self.panel.addWidget(self.languageLabel, 1,0)
        self.panel.addWidget(self.languageCombo, 1,1)
        self.panel.addWidget(self.unitsLabel, 2,0)
        self.panel.addWidget(self.unitsCombo, 2,1)
        self.panel.addWidget(self.interval_label, 3,0)
        self.panel.addWidget(self.interval_combo, 3,1)
        self.panel.addWidget(self.interval_min, 3,2)
        self.layout.addLayout(self.panel)
        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)
        self.setWindowTitle(self.tr('Meteo-qt Configuration'))

    def units(self):
        unit = self.unitsCombo.currentText()
        setUnit = [key for key, value in self.unitsDico.items() if value == unit]
        self.settings.setValue('Unit', setUnit[0])
        print('Write ', 'Unit', setUnit[0])

    def language(self):
        lang = self.languageCombo.currentText()
        setlang = [key for key, value in self.language_dico.items() if value == lang]
        self.settings.setValue('Language', setlang[0])
        print('Write ', 'Language', setlang[0])

    def interval(self):
        time = self.interval_combo.currentText()
        self.settings.setValue('Interval', time)
        print('Write ', 'Interval', time)

    def searchcity(self):
        dialog = searchcity.SearchCity(self.accurate_url, self)
        for e in 'id','city','country':
            self.connect(dialog, SIGNAL(e + '(PyQt_PyObject)'), self.savesettings)
        if dialog.exec_():
            self.set_city = self.settings.value('City') or '?'
            self.cityLabel.setText(self.set_city)

    def savesettings(self, what):
        self.settings.setValue(what[0], what[1])
        print('write ', what[0], what[1])


