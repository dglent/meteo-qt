from PyQt5.QtCore import (
    pyqtSignal, QSettings, QLocale, Qt, QSize, QCoreApplication
    )
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QLabel, QPushButton, QHBoxLayout,
    QDialogButtonBox, QCheckBox, QGridLayout, QColorDialog, QSpinBox
    )
import os
import logging

try:
    import citylistdlg
except:
    from meteo_qt import citylistdlg


class MeteoSettings(QDialog):
    applied_signal = pyqtSignal()

    def __init__(self, accurate_url, parent=None):
        super(MeteoSettings, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.accurate_url = accurate_url
        self.settings = QSettings()
        self.set_city = self.settings.value('City') or '?'
        locale = QLocale.system().name()
        locale_long = ['pt_BR', 'zh_CN', 'zh_TW']
        if locale not in locale_long:
            locale = locale[:2]
        self.interval_set = self.settings.value('Interval') or '30'
        self.temp_tray_color = self.settings.value('TrayColor') or ''
        # -----Cities comboBox--------------------------------
        self.first = True
        self.clear_combo = False
        self.city_list_before = []
        self.citylist = []
        self.city_combo = QComboBox()
        if self.set_city != '?':
            self.add_cities_incombo()
        self.city_combo.currentIndexChanged.connect(self.city_default)
        self.city_title = QLabel(self.tr('City'))
        self.city_button = QPushButton()
        self.city_button.setIcon(QIcon(':/configure'))
        self.city_button.setToolTip(self.tr('Click to edit the cities list'))
        self.city_button.clicked.connect(self.edit_cities_list)
        #------Language-----------------------------------------
        self.language_label = QLabel(self.tr('Language'))
        self.language_combo = QComboBox()
        self.language_combo.setToolTip(
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
                              'zh_TW': self.tr('Chinese Traditional'),
                              'zh_CN': self.tr('Chinese Simplified')
                               }
        lang_list = sorted(self.language_dico.values())
        # English as fallback language
        if locale not in self.language_dico:
            locale = 'en'
        self.setLanguage = self.settings.value('Language') or locale
        self.language_combo.addItems(lang_list)
        self.language_combo.setCurrentIndex(self.language_combo.findText
                                           (self.language_dico[self.setLanguage]))
        self.language_combo.currentIndexChanged.connect(self.language)
        self.lang_changed = False
        # Unit system
        self.units_changed = False
        self.temp_unit = self.settings.value('Unit')
        if self.temp_unit == None or self.temp_unit == '':
            self.temp_unit = 'metric'
            self.units_changed = True
        self.units_label = QLabel(self.tr('Temperature unit'))
        self.units_combo = QComboBox()
        self.units_dico = {'metric': '°C', 'imperial': '°F', ' ': '°K'}
        units_list = sorted(self.units_dico.values())
        self.units_combo.addItems(units_list)
        self.units_combo.setCurrentIndex(self.units_combo.findText(
            self.units_dico[self.temp_unit]))
        self.units_combo.currentIndexChanged.connect(self.units)

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
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.Ok|QDialogButtonBox.Apply|QDialogButtonBox.Cancel)
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
        self.temp_colorButton.setStyleSheet(
            'QWidget {{ background-color: {0} }}'.format(self.temp_tray_color))
        self.temp_colorButton.setMaximumSize(QSize(44, 24))
        self.temp_colorButton.clicked.connect(self.color_chooser)
        self.temp_color_resetButton = QPushButton(self.tr('Reset'))
        self.temp_color_resetButton.setToolTip(
            self.tr('Reset font colour to system default'))
        self.temp_color_resetButton.clicked.connect(self.color_reset)
        # Display notifications
        self.notifier_label = QLabel(self.tr('Notification on weather update'))
        self.notifier_checkbox = QCheckBox()
        notifier_bool = self.settings.value('Notifications') or 'True'
        notifier_bool = eval(notifier_bool)
        self.notifier_checkbox.setChecked(notifier_bool)
        self.notifier_checkbox.stateChanged.connect(self.notifier)
        self.notifier_changed = False
        # Font size
        fontsize = self.settings.value('FontSize') or '18'
        self.fontsize_label = QLabel(QCoreApplication.translate(
            "Settings dialog","Font size in tray",
            "Setting for the font size of the temperature in the tray icon"))
        self.fontsize_spinbox = QSpinBox()
        self.fontsize_spinbox.setRange(12, 25)
        self.fontsize_spinbox.setValue(int(fontsize))
        if fontsize == None or fontsize == '':
            self.settings.setValue('FontSize', '18')
        self.fontsize_changed = False
        self.fontsize_spinbox.valueChanged.connect(self.fontsize_change)
        #----------------------------------
        self.panel = QGridLayout()
        self.panel.addWidget(self.city_title, 0,0)
        self.panel.addWidget(self.city_combo, 0,1)
        self.panel.addWidget(self.city_button, 0,2)
        self.panel.addWidget(self.language_label, 1,0)
        self.panel.addWidget(self.language_combo, 1,1)
        self.panel.addWidget(self.units_label, 2,0)
        self.panel.addWidget(self.units_combo, 2,1)
        self.panel.addWidget(self.interval_label, 3,0)
        self.panel.addWidget(self.interval_combo, 3,1)
        self.panel.addWidget(self.interval_min, 3,2)
        self.panel.addWidget(self.autostart_label, 4,0)
        self.panel.addWidget(self.autostart_checkbox, 4,1)
        self.panel.addWidget(self.temp_colorLabel, 5,0)
        self.panel.addWidget(self.temp_colorButton, 5,1)
        self.panel.addWidget(self.temp_color_resetButton, 5,2)
        self.panel.addWidget(self.notifier_label, 6,0)
        self.panel.addWidget(self.notifier_checkbox, 6,1)
        self.panel.addWidget(self.fontsize_label, 7,0)
        self.panel.addWidget(self.fontsize_spinbox, 7,1)
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

    def city_default(self):
        allitems = [self.city_combo.itemText(i) for i in range(self.city_combo.count())]
        city_name = self.city_combo.currentText()
        citytosave = city_name.split('_')
        if len(citytosave) < 3:
            return
        self.id_before = citytosave[2]
        self.city_before = citytosave[0]
        self.country_before = citytosave[1]
        self.city_list_before = allitems[:]
        self.city_list_before.pop(self.city_list_before.index(city_name))
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def interval(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.interval_changed = True

    def edit_cities_list(self):
        dialog = citylistdlg.CityListDlg(self.citylist, self.accurate_url, self)
        dialog.citieslist_signal.connect(self.cities_list)
        dialog.exec_()

    def cities_list(self, cit_list):
        if len(cit_list) > 0:
            citytosave = cit_list[0].split('_')
            self.id_before = citytosave[2]
            self.city_before = citytosave[0]
            self.country_before = citytosave[1]
            if len(cit_list) > 1:
                self.city_list_before = cit_list[1:]
            else:
                self.city_list_before = str('')
        else:
            self.id_before = ''
            self.city_before = ''
            self.country_before = ''
            self.city_list_before = []
            self.clear_combo = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.first = False
        self.add_cities_incombo()

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
            logging.debug('Write desktop file in ~/.config/autostart')
        elif self.autostart_state == 0:
            if os.path.exists(total_path):
                os.remove(total_path)
            self.settings.setValue('Autostart', 'False')
            logging.debug('Remove desktop file from ~/.config/autostart')
        else:
            return

    def color_chooser(self):
        col = QColorDialog.getColor()
        if col.isValid():
            self.temp_colorButton.setStyleSheet(
                'QWidget {{ background-color: {0} }}'.format(col.name()))
            # focus to next elem to show immediatley the colour in the button (in some DEs)
            self.temp_color_resetButton.setFocus()
            self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
            self.color_before = col.name()
        else:
            logging.warn('Invalid color:', col)

    def color_reset(self):
        self.temp_colorButton.setStyleSheet(
                'QWidget { background-color:  }')
        self.color_before = ''
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def notifier(self, state):
        self.notifier_state = state
        self.notifier_changed = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def notifier_apply(self):
        if self.notifier_state == 2:
            self.settings.setValue('Notifications', 'True')
            logging.debug('Write: Notifications = True')
        elif self.notifier_state == 0:
            self.settings.setValue('Notifications', 'False')
            logging.debug('Write: Notifications = False')

    def fontsize_change(self, size):
        self.fontsize_changed = True
        self.fontsize_value = size
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def fontsize_apply(self):
        logging.debug('Apply fontsize: ' + str(self.fontsize_value))
        self.settings.setValue('FontSize', str(self.fontsize_value))

    def apply_settings(self):
        self.accepted()
        self.applied_signal.emit()
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(False)

    def accepted(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(False)
        if hasattr(self, 'id_before'):
            self.settings.setValue('ID', self.id_before)
            logging.debug('write ' + 'ID' + str(self.id_before))
        if hasattr(self, 'city_before'):
            self.settings.setValue('City', self.city_before)
            logging.debug('write ' + 'City' + str(self.city_before))
        if hasattr(self, 'country_before'):
            self.settings.setValue('Country', self.country_before)
            logging.debug('write ' + 'Country' + str(self.country_before))
        if hasattr(self, 'city_list_before'):
            self.settings.setValue('CityList', str(self.city_list_before))
            logging.debug('write ' + 'CityList' + str(self.city_list_before))
        if hasattr(self, 'color_before'):
            self.settings.setValue('TrayColor', self.color_before)
            if self.color_before == '':
                self.color_before = 'None'
            logging.debug('Write font color for temp in tray: {0}'.format(self.color_before))
        if self.autostart_changed:
            self.autostart_apply()
        if self.interval_changed:
            time = self.interval_combo.currentText()
            self.settings.setValue('Interval', time)
            logging.debug('Write ' + 'Interval' + str(time))
        if self.lang_changed:
            lang = self.language_combo.currentText()
            setlang = [key for key, value in self.language_dico.items() if value == lang]
            self.settings.setValue('Language', setlang[0])
            logging.debug('Write ' + 'Language' + str(setlang[0]))
        if self.units_changed:
            unit = self.units_combo.currentText()
            setUnit = [key for key, value in self.units_dico.items() if value == unit]
            self.settings.setValue('Unit', setUnit[0])
            logging.debug('Write ' + 'Unit ' + str(setUnit[0]))
        if self.notifier_changed:
            self.notifier_apply()
        if self.fontsize_changed:
            self.fontsize_apply()

    def accept(self):
        self.accepted()
        QDialog.accept(self)

    def add_cities_incombo(self):
        list_cities = ''
        self.city_combo.clear()
        if self.clear_combo:
            return
        if self.first:
            list_cities =  self.settings.value('CityList')
            if list_cities != None:
                self.city_list_before = list_cities[:]
            self.citylist = [self.set_city + '_' + self.settings.value('Country') +
                         '_' + self.settings.value('ID')]
        else:
            self.citylist = [self.city_before + '_' + self.country_before +
                             '_' + self.id_before]
            list_cities = self.city_list_before[:]
        if list_cities == None:
            list_cities = []
        if list_cities != '' and list_cities != None:
            if type(list_cities) is str:
                list_cities = eval(list_cities)
            self.citylist = self.citylist + list_cities
        duplicate = []
        for i in self.citylist:
            if i not in duplicate:
                duplicate.append(i)
        self.citylist = duplicate[:]
        self.city_combo.addItems(self.citylist)
        if len(list_cities) > 0:
            maxi = len(max(list_cities, key=len))
            self.city_combo.setMinimumSize(maxi*8,23)
