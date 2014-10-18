#!/usr/bin/env python3

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import searchcity


class MeteoSettings(QDialog):

    language_dico = {
        'en': 'English',
        'ru': 'Russian',
        'it': 'Italian',
        'es': 'Spanish',
        'uk': 'Ukrainian',
        'de': 'German',
        'pt': 'Portuguese',
        'ro': 'Romanian',
        'pl': 'Polish',
        'fi': 'Finnish',
        'nl': 'Dutch',
        'fr': 'French',
        'bg': 'Bulgarian',
        'sv': 'Swedish',
        'zh_tw': 'Chinese Traditional',
        'zh_cn': 'Chinese Simplified',
        'tr': 'Turkish',
        'hr': 'Croatian',
        'cd': 'Catalan'
    }

    unitsDico = {
        'metric': '°C',
        'imperial': '°F',
        ' ': '°K'
    }

    def __init__(self, accurate_url, parent=None):
        super(MeteoSettings, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.accurate_url = accurate_url
        self.settings = QSettings()
        self.setCity = self.settings.value('City') or '?'
        self.setLanguage = self.settings.value('Language') or 'en'
        self.tempUnit = self.settings.value('Unit') or 'metric'
        self.cityLabel = QLabel(self.setCity)
        self.cityTitle = QLabel('City :')
        self.cityButton = QPushButton()
        self.cityButton.setIcon(QIcon(':/configure'))
        self.cityButton.setToolTip('Click to modify the city')
        self.languageLabel = QLabel('Language :')
        self.languageCombo = QComboBox()
        self.languageCombo.setToolTip('The language for the weather descriptions')
        lang_list = list(c for l,c in self.language_dico.items())
        lang_list.sort()
        self.languageCombo.addItems(lang_list)
        self.languageCombo.setCurrentIndex(self.languageCombo.findText
                                           (self.language_dico[self.setLanguage]))
        self.connect(self.languageCombo, SIGNAL('currentIndexChanged(int)'), self.language)
        self.connect(self.cityButton, SIGNAL("clicked()"), self.searchcity)
        self.unitsLabel = QLabel('Temperature unit')
        self.unitsCombo = QComboBox()
        unitsList = list(t for l,t in self.unitsDico.items())
        self.unitsCombo.addItems(unitsList)
        self.unitsCombo.setCurrentIndex(self.unitsCombo.findText
                                        (self.unitsDico[self.tempUnit]))
        self.connect(self.unitsCombo, SIGNAL('currentIndexChanged(int)'), self.units)
        
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
        self.layout.addLayout(self.panel)
        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)
        self.setWindowTitle('Meteo-qt Configuration')

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

    def searchcity(self):
        dialog = searchcity.SearchCity(self.accurate_url, self)
        for e in 'id','city','country':
            self.connect(dialog, SIGNAL(e + '(PyQt_PyObject)'), self.savesettings)
        if dialog.exec_():
            self.setCity = self.settings.value('City') or '?'
            self.cityLabel.setText(self.setCity)

    def savesettings(self, what):
        self.settings.setValue(what[0], what[1])
        print('write ', what[0], what[1])
