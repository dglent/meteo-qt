#!/usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import os

try:
    import searchcity
except:
    from meteo_qt import searchcity


class MeteoSettings(QDialog):
    applied_signal = pyqtSignal()

    def __init__(self, accurate_url, parent=None):
        super(MeteoSettings, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.accurate_url = accurate_url
        self.settings = QSettings()
        self.set_city = self.settings.value('City') or '?'
        locale = QLocale.system().name().lower()
        locale_long = ['pt_BR', 'zh_CN', 'zh_TW']
        if locale not in locale_long:
            locale = locale[:2]
        self.tempUnit = self.settings.value('Unit') or 'metric'
        self.interval_set = self.settings.value('Interval') or '30'
        self.temp_tray_color = self.settings.value('TrayColor') or ''
        self.city_label = QLabel(self.set_city)
        self.cityTitle = QLabel(self.tr('City'))
        self.cityButton = QPushButton()
        self.cityButton.setIcon(QIcon(':/configure'))
        self.cityButton.setToolTip(self.tr('Click to modify the city'))
        self.cityButton.clicked.connect(self.searchcity)
        # language
        self.languageLabel = QLabel(self.tr('Language'))
        self.languageCombo = QComboBox()
        self.languageCombo.setToolTip(
            self.tr('The application has to be restared to apply the language setting'))
        self.language_dico = {'bg': self.tr('Bulgarian'),
                              'ca': self.tr('Catalan'),
                              'cs': self.tr('Czech'),
                              'da': self.tr('Danish'),
                              'de': self.tr('German'),
                              'el': self.tr('Greek'),
                              'en': self.tr('English'),
                              'es': self.tr('Spanish'),
                              'fi': self.tr('Finnish'),
                              'fr': self.tr('French'),
                              'he': self.tr('Hebrew'),
                              'hr': self.tr('Croatian'),
                              'hu': self.tr('Hungarian'),
                              'it': self.tr('Italian'),
                              'ja': self.tr('Japanese'),
                              'lt': self.tr('Lithuanian'),
                              'nb': self.tr('Norwegian (Bokmaal)'),
                              'nl': self.tr('Dutch'),
                              'pl': self.tr('Polish'),
                              'pt': self.tr('Portuguese'),
                              'pt_BR': self.tr('Brazil Portuguese'),
                              'ro': self.tr('Romanian'),
                              'ru': self.tr('Russian'),
                              'sk': self.tr('Slovak'),
                              'sv': self.tr('Swedish'),
                              'tr': self.tr('Turkish'),
                              'uk': self.tr('Ukrainian'),
                              'zh_tw': self.tr('Chinese Traditional'),
                              'zh_cn': self.tr('Chinese Simplified')
                               }
        lang_list = sorted(self.language_dico.values())
        # English as fallback language
        if locale not in self.language_dico:
            locale = 'en'
        self.setLanguage = self.settings.value('Language') or locale
        self.languageCombo.addItems(lang_list)
        self.languageCombo.setCurrentIndex(self.languageCombo.findText
                                           (self.language_dico[self.setLanguage]))
        self.languageCombo.currentIndexChanged.connect(self.language)
        self.lang_changed = False
        # Unit system
        self.unitsLabel = QLabel(self.tr('Temperature unit'))
        self.unitsCombo = QComboBox()
        self.unitsDico = {'metric': '°C', 'imperial': '°F', ' ': '°K'}
        unitsList = sorted(self.unitsDico.values())
        self.unitsCombo.addItems(unitsList)
        self.unitsCombo.setCurrentIndex(self.unitsCombo.findText(
            self.unitsDico[self.tempUnit]))
        self.unitsCombo.currentIndexChanged.connect(self.units)
        self.units_changed = False
        # Interval of updates
        self.interval_label = QLabel(self.tr('Update interval'))
        self.interval_min = QLabel(self.tr('minutes'))
        self.interval_combo = QComboBox()
        self.interval_list = ['15','30','45','60','90','120']
        self.interval_combo.addItems(self.interval_list)
        self.interval_combo.setCurrentIndex(self.interval_combo.findText(
            self.interval_list[self.interval_list.index(self.interval_set)]))
        self.interval_combo.currentIndexChanged.connect(self.interval)
        self.interval_changed = False
        # OK Cancel Apply Buttons
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch()
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Apply|QDialogButtonBox.Cancel)
        self.buttonBox.setContentsMargins(0,30,0,0)
        self.buttonLayout.addWidget(self.buttonBox)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(False)
        # Autostart
        self.autostart_label = QLabel(self.tr('Launch at startup'))
        self.autostart_checkbox = QCheckBox()
        autostart_bool = self.settings.value('Autostart') or 'False'
        autostart_bool = eval(autostart_bool)
        self.autostart_checkbox.setChecked(autostart_bool)
        self.autostart_checkbox.stateChanged.connect(self.autostart)
        self.autostart_changed = False
        # Tray temp° color
        self.temp_colorLabel=QLabel(self.tr('Font colour in the tray'))
        self.temp_colorButton = QPushButton()
        self.temp_colorButton.setStyleSheet('QWidget {{ background-color: {0} }}'.format(self.temp_tray_color))
        self.temp_colorButton.setMaximumSize(QSize(44, 24))
        self.temp_colorButton.clicked.connect(self.color_chooser)
        self.temp_color_resetButton = QPushButton(self.tr('Reset'))
        self.temp_color_resetButton.setToolTip(self.tr('Reset font colour to system default'))
        self.temp_color_resetButton.clicked.connect(self.color_reset)
        #----
        self.panel = QGridLayout()
        self.panel.addWidget(self.cityTitle, 0,0)
        self.panel.addWidget(self.city_label, 0,1)
        self.panel.addWidget(self.cityButton, 0,2)
        self.panel.addWidget(self.languageLabel, 1,0)
        self.panel.addWidget(self.languageCombo, 1,1)
        self.panel.addWidget(self.unitsLabel, 2,0)
        self.panel.addWidget(self.unitsCombo, 2,1)
        self.panel.addWidget(self.interval_label, 3,0)
        self.panel.addWidget(self.interval_combo, 3,1)
        self.panel.addWidget(self.interval_min, 3,2)
        self.panel.addWidget(self.autostart_label, 4,0)
        self.panel.addWidget(self.autostart_checkbox, 4,1)
        self.panel.addWidget(self.temp_colorLabel, 5,0)
        self.panel.addWidget(self.temp_colorButton, 5,1)
        self.panel.addWidget(self.temp_color_resetButton, 5,2)
        self.layout.addLayout(self.panel)
        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)
        self.setWindowTitle(self.tr('Meteo-qt Configuration'))

    def units(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.units_changed = True

    def language(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.lang_changed = True

    def interval(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.interval_changed = True

    def searchcity(self):
        dialog = searchcity.SearchCity(self.accurate_url, self)
        dialog.id_signal.connect(self.store_before_save_settings)
        dialog.city_signal.connect(self.store_before_save_settings)
        dialog.country_signal.connect(self.store_before_save_settings)
        dialog.exec_()

    def store_before_save_settings(self, what):
        if what[0] == 'ID':
            self.id_before = what[1]
        elif what[0] == 'City':
            self.city_before = what[1]
            self.city_label.setText(self.city_before)
        elif what[0] == 'Country':
            self.country_before = what[1]
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def autostart(self, state):
        self.autostart_state = state
        self.autostart_changed = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def autostart_apply(self):
        dir_auto = '/.config/autostart/'
        d_file = 'meteo-qt.desktop'
        home = os.getenv('HOME')
        total_path = home + dir_auto + d_file
        if self.autostart_state == 2:
            desktop_file = ['[Desktop Entry]\n',
                            'Exec=meteo-qt\n',
                            'Name=meteo-qt\n',
                            'Type=Application\n',
                            'Version=1.0\n',
                            'X-LXQt-Need-Tray=true\n']
            if not os.path.exists(home + dir_auto):
                os.system('mkdir -p {}'.format(os.path.dirname(total_path)))
            with open(total_path, 'w') as out_file:
                out_file.writelines(desktop_file)
            self.settings.setValue('Autostart', 'True')
            print('Write desktop file in ~/.config/autostart')
        elif self.autostart_state == 0:
            if os.path.exists(total_path):
                os.remove(total_path)
            self.settings.setValue('Autostart', 'False')
            print('Remove desktop file from ~/.config/autostart')
        else:
            return

    def color_chooser(self):
        col = QColorDialog.getColor()
        if col.isValid():
            self.temp_colorButton.setStyleSheet(
                'QWidget {{ background-color: {0} }}'.format(col.name()))
            self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
            self.color_before = col.name()

    def color_reset(self):
        self.temp_colorButton.setStyleSheet(
                'QWidget { background-color:  }')
        self.color_before = ''
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def apply_settings(self):
        self.accepted()
        self.applied_signal.emit()
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(False)

    def accepted(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(False)
        if hasattr(self, 'id_before'):
            self.settings.setValue('ID', self.id_before)
            print('write ', 'ID', self.id_before)
        if hasattr(self, 'city_before'):
            self.settings.setValue('City', self.city_before)
            print('write ', 'City', self.city_before)
        if hasattr(self, 'country_before'):
            self.settings.setValue('Country', self.country_before)
            print('write ', 'Country', self.country_before)
        if hasattr(self, 'color_before'):
            self.settings.setValue('TrayColor', self.color_before)
            if self.color_before == '':
                self.color_before = 'None'
            print('Write font color for temp in tray: {0}'.format(self.color_before))
        if self.autostart_changed:
            self.autostart_apply()
        if self.interval_changed:
            time = self.interval_combo.currentText()
            self.settings.setValue('Interval', time)
            print('Write ', 'Interval', time)
        if self.lang_changed:
            lang = self.languageCombo.currentText()
            setlang = [key for key, value in self.language_dico.items() if value == lang]
            self.settings.setValue('Language', setlang[0])
            print('Write ', 'Language', setlang[0])
        if self.units_changed:
            unit = self.unitsCombo.currentText()
            setUnit = [key for key, value in self.unitsDico.items() if value == unit]
            self.settings.setValue('Unit', setUnit[0])
            print('Write ', 'Unit', setUnit[0])

    def accept(self):
        self.accepted()
        QDialog.accept(self)



