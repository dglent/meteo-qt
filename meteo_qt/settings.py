import logging
import os
import glob

from PyQt5.QtCore import (
    QCoreApplication, QLocale, QSettings, QSize, Qt, pyqtSignal
)
from PyQt5.QtGui import QIcon, QColor, QFont
from PyQt5.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QVBoxLayout, QFontDialog
)

try:
    import citylistdlg
    import proxydlg
except ImportError:
    from meteo_qt import citylistdlg
    from meteo_qt import proxydlg


class MeteoSettings(QDialog):
    applied_signal = pyqtSignal()

    def __init__(self, accurate_url, appid, parent=None):
        super(MeteoSettings, self).__init__(parent)
        self.settings = QSettings()
        trans_cities_dict = self.settings.value('CitiesTranslation') or '{}'
        self.trans_cities_dict = eval(trans_cities_dict)
        self.layout = QVBoxLayout()
        self.accurate_url = accurate_url
        self.appid = appid
        self.set_city = self.settings.value('City') or '?'
        locale = QLocale.system().name()
        locale_long = ['pt_BR', 'zh_CN', 'zh_TW']
        if locale not in locale_long:
            locale = locale[:2]
        self.interval_set = self.settings.value('Interval') or '30'
        self.temp_tray_color = self.settings.value('TrayColor') or ''
        # -----Cities comboBox------------------------
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
        # ------Language------------------------------
        self.language_label = QLabel(self.tr('Language'))
        self.language_combo = QComboBox()
        self.language_combo.setToolTip(
            QCoreApplication.translate(
                'Tooltip',
                'The application has to be restared to apply the language setting',
                'Settings dialogue'
            )
        )
        self.language_dico = {
            'bg': self.tr('Bulgarian'),
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
        self.language_combo.setCurrentIndex(
            self.language_combo.findText(self.language_dico[self.setLanguage])
        )
        self.language_combo.currentIndexChanged.connect(self.language)
        self.lang_changed = False
        # Unit system
        self.units_changed = False
        self.temp_unit = self.settings.value('Unit')
        if self.temp_unit is None or self.temp_unit == '':
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
        # Wind unit
        self.wind_unit_changed = False
        self.wind_unit = self.settings.value('Wind_unit')
        if self.wind_unit is None or self.wind_unit == '':
            self.wind_unit = 'df'
            self.wind_unit_changed = True
        self.wind_unit_label = QLabel(
            QCoreApplication.translate(
                'Label of the checkbox',
                'Wind speed unit',
                'Settings dialogue'
            )
        )
        self.wind_unit_combo = QComboBox()
        wind_units_list = [
            QCoreApplication.translate(
                'Option to choose the default wind speed unit',
                'Default',
                'Settings diaogue'
            ),
            QCoreApplication.translate(
                'Option to choose wind speed unit',
                'Beaufort',
                'Settings dialogue'
            ),
            QCoreApplication.translate(
                'Option to choose wind speed unit',
                'Km/h',
                'Settings dialogue'
            )
        ]
        self.wind_unit_dico = {
            'df': wind_units_list[0],
            'bf': wind_units_list[1],
            'km': wind_units_list[2]
        }

        self.wind_unit_combo.addItems(wind_units_list)
        self.wind_unit_combo.setCurrentIndex(
            self.wind_unit_combo.findText(self.wind_unit_dico[self.wind_unit])
        )
        self.wind_unit_combo.currentIndexChanged.connect(self.wind_unit_change_apply)
        self.wind_unit_combo.model().item(2).setEnabled(False)
        if self.temp_unit == 'metric':
            self.wind_unit_combo.model().item(2).setEnabled(True)
        # Decimal in trayicon
        self.temp_decimal_label = QLabel(
            QCoreApplication.translate(
                'If the temperature will be shown with a decimal or rounded in tray icon',
                'Temperature accuracy in system tray',
                'Settings dialogue'
            )
        )
        self.temp_decimal_combo = QComboBox()
        temp_decimal_combo_dico = {'False': '0°', 'True': '0.1°'}
        temp_decimal_combo_list = [
            temp_decimal_combo_dico['False'], temp_decimal_combo_dico['True']
        ]
        self.temp_decimal_combo.addItems(temp_decimal_combo_list)
        temp_decimal_bool_str = self.settings.value('Decimal') or 'False'
        self.temp_decimal_combo.setCurrentIndex(
            self.temp_decimal_combo.findText(
                temp_decimal_combo_dico[temp_decimal_bool_str]
            )
        )
        self.temp_decimal_combo.currentIndexChanged.connect(self.temp_decimal)
        self.temp_decimal_changed = False
        # Interval of updates
        self.interval_label = QLabel(self.tr('Update interval'))
        self.interval_min = QLabel(self.tr('minutes'))
        self.interval_combo = QComboBox()
        self.interval_list = ['15', '30', '45', '60', '90', '120']
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
            QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        self.buttonBox.setContentsMargins(0, 30, 0, 0)
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
        self.temp_colorLabel = QLabel(self.tr('Font colour in the tray'))
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
        # Icon & Temp
        self.tray_icon_temp_label = QLabel(
            QCoreApplication.translate(
                'Settings dialogue',
                'System tray icon',
                'Setting to choose the type of the icon on the tray'
                '(only icon only text, icon&text'
            )
        )
        self.tray_icon_combo = QComboBox()
        tray_icon_temp = QCoreApplication.translate(
            'Settings dialogue',
            'Icon & temperature',
            'Setting to choose the type of the icon on the tray'
        )
        tray_icon = QCoreApplication.translate(
            'Settings dialogue',
            'Icon',
            'Setting to choose the type of the icon on the tray'
        )
        tray_temp = QCoreApplication.translate(
            'Settings dialogue',
            'Temperature',
            'Setting to choose the type of the icon on the tray'
        )
        tray_icon_feels_like = QCoreApplication.translate(
            'Settings dialogue',
            'Icon & Feels like temperature',
            'Setting to choose the type of the icon on the tray'
        )
        tray_feels_like = QCoreApplication.translate(
            'Settings dialogue',
            'Feels like temperature',
            'Setting to choose the type of the icon on the tray'
        )
        self.tray_dico = {
            'icon&temp': tray_icon_temp,
            'icon': tray_icon,
            'temp': tray_temp,
            'icon&feels_like': tray_icon_feels_like,
            'feels_like_temp': tray_feels_like,
        }
        set_tray_icon = self.settings.value('TrayType') or 'icon&temp'
        tray_icon_list = sorted(self.tray_dico.values())
        self.tray_icon_combo.addItems(tray_icon_list)
        self.tray_icon_combo.setCurrentIndex(
            self.tray_icon_combo.findText(self.tray_dico[set_tray_icon])
        )
        self.tray_icon_combo.currentIndexChanged.connect(self.tray)
        self.tray_changed = False
        # Weather icons
        self.comboBox_icons_theme = QComboBox()
        thema_list = ['OpenWeatherMap']
        self.system_default_theme_translated = {
            'System default': QCoreApplication.translate(
                'Settings dialogue',
                'System default',
                'ComboBox to choose the system default icons theme'
            )
        }
        self.comboBox_icons_theme.setToolTip(
            QCoreApplication.translate(
                'Settings dialogue',
                'Icons theme',
                'Tooltip of the ComboBox to choose the icons theme'
            )
        )
        thema_list.append(self.system_default_theme_translated['System default'])
        logging.debug('Icons theme paths : ' + str(QIcon.themeSearchPaths()))
        for themedir in QIcon.themeSearchPaths():
            for dirpath in glob.glob(themedir + '/*/'):
                for path in glob.glob(dirpath + '/*'):
                    if path.count('index.theme'):
                        thema = os.path.basename(os.path.dirname(path))
                        if thema not in thema_list:
                            thema_list.append(thema)

        thema_list = sorted(thema_list, key=str.casefold)
        logging.debug('Found themes : ' + str(thema_list))
        self.comboBox_icons_theme.addItems(thema_list)

        icontheme_conf = self.settings.value('IconsTheme') or 'System default'
        if icontheme_conf == 'System default':
            self.comboBox_icons_theme.setCurrentIndex(
                self.comboBox_icons_theme.findText(self.system_default_theme_translated['System default'])
            )
        else:
            self.comboBox_icons_theme.setCurrentIndex(
                self.comboBox_icons_theme.findText(icontheme_conf)
            )

        self.comboBox_icons_theme.currentIndexChanged.connect(self.system_theme_icons)
        self.comboBox_icons_theme_changed = False

        # Tray icon initialization size and temp position
        self.tray_icon_init_label = QLabel(
            QCoreApplication.translate(
                'Settings dialogue',
                'Tray icon size and text position',
                'This option concernes 2 dropdown lists'
                'to define the size to initialize the tray icon'
                'and the position of the temperature text in the icon'
            )
        )
        self.tray_icon_init_label.setToolTip(
            QCoreApplication.translate(
                'Settings dialogue',
                'Changing this setting you can improve the displaying of the temperature in the tray icon',
                'ToolTip of the label "Tray icon size and text position"'
            )
        )

        self.tray_icon_init_cmb = QComboBox()
        self.tray_icon_init_cmb.setToolTip(
            QCoreApplication.translate(
                'Settings dialogue',
                'Tray icon initialization size (default size: 64x64)',
                'Tooltip of the drowndrop list with icon sizes'
            )
        )
        self.tray_icon_init_cmb.addItems(["16x16", "24x24", "32x32", "64x64"])
        icon_init_size = self.settings.value('Tray_icon_init_size') or '64x64'
        self.tray_icon_init_cmb.setCurrentText(icon_init_size)
        self.tray_icon_init_cmb.currentIndexChanged.connect(self.tray_icon_init_size_change)
        self.tray_icon_init_cmb_changed = False

        self.tray_icon_temp_pos_spinbox = QSpinBox()
        self.tray_icon_temp_pos_spinbox.setRange(-20, 20)
        temp_pos_in_icon = self.settings.value('Tray_icon_temp_position') or '-12'
        self.tray_icon_temp_pos_spinbox.setValue(int(temp_pos_in_icon))
        self.tray_icon_temp_pos_spinbox_changed = False
        self.tray_icon_temp_pos_spinbox.valueChanged.connect(self.tray_icon_temp_pos_change)
        self.tray_icon_temp_pos_spinbox.setToolTip(
            QCoreApplication.translate(
                'Settings dialogue',
                'Temperature position in the icon (vertically) (default value: -12)',
                'ToolTip of the widget (a spinbox) to define the position of the temperature paint in the tray icon'
            )
        )

        # Toggle icon Temp
        self.toggle_tray_label = QLabel(
            QCoreApplication.translate(
                'Settings dialogue',
                'Toggle tray icon interval',
                'Label for the option of the checkbox to '
                'activate the toggle of the tray icon and temperature'
            )
        )
        toggle_interval = self.settings.value('Toggle_tray_interval') or '0'
        self.toggle_tray_spinbox = QSpinBox()
        self.toggle_tray_spinbox.setRange(0, 100000)
        self.toggle_tray_spinbox_changed = False
        self.toggle_tray_spinbox.valueChanged.connect(self.toggle_tray_interval_change)
        self.toggle_tray_spinbox.setValue(int(toggle_interval))
        self.toggle_tray_interval_label = QLabel(
            QCoreApplication.translate(
                'Settings dialogue',
                'seconds. Set to 0 to deactivate',
                'Label after the spinbox to choose the interval '
                'to toggle the tray icon and temperature'
            )
        )
        self.activate_toggle_check()
        # Font of temperature in tray
        self.font_tray_changed = False
        self.font_tray_conf_new = ''
        self.font_tray_conf = self.settings.value('FontTray') or False
        if not self.font_tray_conf:
            self.font_tray_conf = 'Sans Serif,18,-1,5,50,0,0,0,0,0'
            self.settings.setValue('FontTray', self.font_tray_conf)
        self.font_tray_label = QLabel(
            QCoreApplication.translate(
                'Settings dialogue',
                'Temperature font in system tray',
                'Setting for the font size of the temperature in the tray icon'
            )
        )
        font_tray_btn_label = (
            f"{self.font_tray_conf.split(',')[0]} - "
            f"{self.font_tray_conf.split(',')[1]} - "
            f"{self.font_tray_conf.split(',')[-1]}"
        )
        self.font_tray_btn = QPushButton(font_tray_btn_label)
        self.font_tray_btn.clicked.connect(self.getfont)
        # Proxy
        self.proxy_label = QLabel(
            QCoreApplication.translate(
                'Checkbox',
                'Connection by proxy',
                'Settings dialogue'
            )
        )
        self.proxy_chbox = QCheckBox()
        proxy_bool = self.settings.value('Proxy') or 'False'
        self.proxy_bool = eval(proxy_bool)
        self.proxy_chbox.setChecked(self.proxy_bool)
        self.proxy_chbox.stateChanged.connect(self.proxy)
        self.proxy_changed = False
        self.proxy_button = QPushButton(
            QCoreApplication.translate(
                'Label of button to open the proxy dialogue',
                'Settings',
                'Settings dialogue'
            )
        )
        self.proxy_button.clicked.connect(self.proxy_settings)
        self.proxy_button.setEnabled(self.proxy_bool)
        # Openweathermap key
        self.owmkey_label = QLabel(
            QCoreApplication.translate(
                'The key that user can generate in his OpenWeatherMap profile',
                'OpenWeatherMap key',
                'Settings dialogue'
            )
        )
        self.owmkey_create = QLabel(
            QCoreApplication.translate(
                'Link to create a profile in OpenWeatherMap',
                "<a href=\"http://home.openweathermap.org/users/sign_up\">Create key</a>",
                'Settings dialogue'
            )
        )
        self.owmkey_create.setOpenExternalLinks(True)
        apikey = self.settings.value('APPID') or '4f086d061c620924f6389f7e7cf0ec6d'
        self.owmkey_text = QLineEdit()
        self.owmkey_text.setText(apikey)
        self.owmkey_text.textChanged.connect(self.apikey_changed)

        self.start_minimized_label = QLabel(
            QCoreApplication.translate(
                'Checkable option to show or not the window at startup',
                'Start minimized',
                'Settings dialogue'
            )
        )
        self.start_minimized_chbx = QCheckBox()
        start_minimized_bool = self.settings.value('StartMinimized') or 'True'
        self.start_minimized_bool = eval(start_minimized_bool)
        self.start_minimized_chbx.setChecked(self.start_minimized_bool)
        self.start_minimized_chbx.stateChanged.connect(self.start_minimized)
        self.start_minimized_changed = False

        self.logging_label = QLabel(
            QCoreApplication.translate(
                'Option for logging level',
                'Logging level',
                'Settings window'
            )
        )
        self.logging_level_combo = QComboBox()
        logging_levels = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
        self.logging_level_combo.addItems(logging_levels)
        level = self.settings.value('Logging/Level') or 'INFO'
        self.logging_level_combo.setCurrentIndex(
            self.logging_level_combo.findText(level)
        )
        self.logging_level_combo.currentIndexChanged.connect(self.logging_set)
        self.logging_changed = False

        # ----------
        self.panel = QGridLayout()
        self.panel.addWidget(self.city_title, 0, 0)
        self.panel.addWidget(self.city_combo, 0, 1)
        self.panel.addWidget(self.city_button, 0, 2)
        self.panel.addWidget(self.language_label, 1, 0)
        self.panel.addWidget(self.language_combo, 1, 1)
        self.panel.addWidget(self.units_label, 2, 0)
        self.panel.addWidget(self.units_combo, 2, 1)
        self.panel.addWidget(self.wind_unit_label, 3, 0)
        self.panel.addWidget(self.wind_unit_combo, 3, 1)
        self.panel.addWidget(self.temp_decimal_label, 4, 0)
        self.panel.addWidget(self.temp_decimal_combo, 4, 1)
        self.panel.addWidget(self.interval_label, 5, 0)
        self.panel.addWidget(self.interval_combo, 5, 1)
        self.panel.addWidget(self.interval_min, 5, 2)
        self.panel.addWidget(self.autostart_label, 6, 0)
        self.panel.addWidget(self.autostart_checkbox, 6, 1)
        self.panel.addWidget(self.temp_colorLabel, 7, 0)
        self.panel.addWidget(self.temp_colorButton, 7, 1)
        self.panel.addWidget(self.temp_color_resetButton, 7, 2)
        self.panel.addWidget(self.notifier_label, 8, 0)
        self.panel.addWidget(self.notifier_checkbox, 8, 1)
        self.panel.addWidget(self.tray_icon_temp_label, 9, 0)
        self.panel.addWidget(self.tray_icon_combo, 9, 1)
        self.panel.addWidget(self.comboBox_icons_theme, 9, 2)
        self.panel.addWidget(self.tray_icon_init_label, 10, 0)
        self.panel.addWidget(self.tray_icon_init_cmb, 10, 1)
        self.panel.addWidget(self.tray_icon_temp_pos_spinbox, 10, 2)
        self.panel.addWidget(self.toggle_tray_label, 11, 0)
        self.panel.addWidget(self.toggle_tray_spinbox, 11, 1)
        self.panel.addWidget(self.toggle_tray_interval_label, 11, 2)
        self.panel.addWidget(self.font_tray_label, 12, 0)
        self.panel.addWidget(self.font_tray_btn, 12, 1)
        self.panel.addWidget(self.proxy_label, 13, 0)
        self.panel.addWidget(self.proxy_chbox, 13, 1)
        self.panel.addWidget(self.proxy_button, 13, 2)
        self.panel.addWidget(self.owmkey_label, 14, 0)
        self.panel.addWidget(self.owmkey_text, 14, 1)
        self.panel.addWidget(self.owmkey_create, 14, 2)
        self.panel.addWidget(self.start_minimized_label, 15, 0)
        self.panel.addWidget(self.start_minimized_chbx, 15, 1)
        self.panel.addWidget(self.logging_label, 16, 0)
        self.panel.addWidget(self.logging_level_combo, 16, 1)

        self.layout.addLayout(self.panel)
        self.layout.addLayout(self.buttonLayout)
        self.statusbar = QLabel()
        self.layout.addWidget(self.statusbar)
        self.nokey_message = QCoreApplication.translate(
            'Warning message after pressing Ok',
            'Please enter your OpenWeatherMap key',
            'Settings dialogue'
        )
        self.nocity_message = QCoreApplication.translate(
            'Warning message after pressing OK',
            'Please add a city',
            'Settings dialogue'
        )
        self.setLayout(self.layout)
        self.setWindowTitle(self.tr('Meteo-qt Configuration'))

    def wind_unit_change_apply(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.wind_unit_changed = True

    def units(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.units_changed = True
        unit = self.units_combo.currentText()
        setUnit = [
            key for key, value in self.units_dico.items() if value == unit
        ]
        if setUnit[0] == 'metric':
            self.wind_unit_combo.model().item(2).setEnabled(True)
        else:
            self.wind_unit_combo.model().item(2).setEnabled(False)
            wind = self.wind_unit_combo.currentText()
            setWind = [
                key for key, value in self.wind_unit_dico.items() if value == wind
            ]
            if setWind[0] == 'km':
                self.wind_unit_combo.setCurrentIndex(
                    self.wind_unit_combo.findText(self.wind_unit_dico['df'])
                )

    def language(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.lang_changed = True

    def city_default(self):
        allitems = [
            self.city_combo.itemText(i) for i in range(self.city_combo.count())
        ]
        allitems_not_translated = []
        for i in allitems:
            allitems_not_translated.append(self.find_city_key(i))
        city_name = self.city_combo.currentText()
        city_name = self.find_city_key(city_name)
        citytosave = city_name.split('_')
        # This self variable will serve to check if a translation
        # exist for the current city when quitting
        self.citytosave = '_'.join(citytosave)
        if len(citytosave) < 3:
            return
        self.id_before = citytosave[2]
        self.city_before = citytosave[0]
        self.country_before = citytosave[1]
        self.city_list_before = allitems_not_translated[:]
        self.city_list_before.pop(self.city_list_before.index(city_name))
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def interval(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.interval_changed = True

    def edit_cities_list(self):
        apikey = self.owmkey_text.text()
        apiid = '&APPID=' + apikey
        if apikey == '':
            self.statusbar.setText(self.nokey_message)
            return
        dialog = citylistdlg.CityListDlg(
            self.citylist, self.accurate_url, apiid,
            self.trans_cities_dict, self
        )
        dialog.citieslist_signal.connect(self.cities_list)
        dialog.citiesdict_signal.connect(self.cities_dict)
        dialog.exec_()

    def cities_dict(self, cit_dict):
        self.trans_cities_dict = cit_dict

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
            desktop_file = [
                '[Desktop Entry]\n',
                'Exec=meteo-qt\n',
                'Name=meteo-qt\n',
                'Type=Application\n',
                'Version=1.0\n',
                'X-LXQt-Need-Tray=true\n'
            ]
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
        current_color = self.temp_tray_color
        if hasattr(self, 'color_before'):
            current_color = self.color_before
        col = QColorDialog.getColor(QColor(current_color), self)
        if col.isValid():
            self.temp_colorButton.setStyleSheet(
                'QWidget {{ background-color: {0} }}'.format(col.name())
            )
            # focus to next elem to show immediatley the colour
            # in the button (in some DEs)
            self.temp_color_resetButton.setFocus()
            self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
            self.color_before = col.name()
        else:
            logging.debug('Invalid color:' + str(col))
            self.temp_color_resetButton.setFocus()

    def color_reset(self):
        self.temp_colorButton.setStyleSheet('QWidget { background-color:  }')
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

    def temp_decimal(self, state):
        self.temp_decimal_state = state
        self.temp_decimal_changed = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def activate_toggle_check(self):
        current_tray_option = self.tray_icon_combo.currentText()
        for key, value in self.tray_dico.items():
            if value == current_tray_option:
                if key == 'icon&temp' or key == 'icon&feels_like':
                    self.toggle_tray_spinbox.setEnabled(True)
                else:
                    self.toggle_tray_spinbox.setEnabled(False)

    def tray(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.tray_changed = True
        self.activate_toggle_check()

    def tray_apply(self):
        tray = self.tray_icon_combo.currentText()
        self.settings.setValue('Tray', tray)
        logging.debug('Write >' + 'Tray >' + str(tray))
        settray = [
            key for key, value in self.tray_dico.items() if value == tray
        ]
        self.settings.setValue('TrayType', settray[0])

    def tray_icon_init_size_change(self):
        self.tray_icon_init_cmb_changed = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def tray_icon_init_size_apply(self):
        self.settings.setValue('Tray_icon_init_size', self.tray_icon_init_cmb.currentText())

    def tray_icon_temp_pos_change(self, pos):
        self.tray_icon_temp_pos_spinbox_changed = True
        self.tray_icon_temp_pos = pos
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def tray_icon_temp_pos_apply(self):
        self.settings.setValue('Tray_icon_temp_position', str(self.tray_icon_temp_pos))

    def toggle_tray_interval_change(self, interval):
        self.toggle_tray_spinbox_changed = True
        self.toggle_tray_interval = interval
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def toggle_tray_interval_apply(self):
        self.settings.setValue('Toggle_tray_interval', str(self.toggle_tray_interval))

    def getfont(self):
        if self.font_tray_conf_new != "":
            current_font = self.font_tray_conf_new
        else:
            current_font = self.font_tray_conf
        ff = QFont()
        ff.fromString(current_font)
        font, ok = QFontDialog.getFont(ff, self)
        if ok and font.toString() != self.font_tray_conf:
            self.font_tray_changed = True
            self.font_tray_conf_new = font.toString()
            self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
            font_tray_btn_label = (
            f"{self.font_tray_conf_new.split(',')[0]} - "
            f"{self.font_tray_conf_new.split(',')[1]} - "
            f"{self.font_tray_conf_new.split(',')[-1]}"
            )
            self.font_tray_btn.setText(font_tray_btn_label)

    def font_tray_apply(self):
        logging.debug(f'Apply font for tray: {self.font_tray_conf_new}')
        self.settings.setValue('FontTray', self.font_tray_conf_new)

    def system_theme_icons(self):
        self.comboBox_icons_theme_changed = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def system_icontheme_apply(self):
        if self.comboBox_icons_theme.currentText() == self.system_default_theme_translated['System default']:
            self.settings.setValue('IconsTheme', 'System default')
        else:
            self.settings.setValue('IconsTheme', self.comboBox_icons_theme.currentText())

    def start_minimized(self, state):
        self.start_minimized_state = state
        self.start_minimized_changed = True
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def start_minimized_apply(self):
        if self.start_minimized_state == 2:
            start_minimized = 'True'
        else:
            start_minimized = 'False'
        self.settings.setValue('StartMinimized', start_minimized)

    def logging_set(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        self.logging_changed = True

    def logging_level_apply(self):
        level = self.logging_level_combo.currentText()
        self.settings.setValue('Logging/Level', level)

    def proxy(self, state):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)
        if state == 2:
            self.proxy_bool = True
            self.proxy_button.setEnabled(True)
        else:
            self.proxy_bool = False
            self.proxy_button.setEnabled(False)

    def proxy_settings(self):
        dialog = proxydlg.Proxy(self)
        dialog.exec_()

    def apikey_changed(self):
        self.buttonBox.button(QDialogButtonBox.Apply).setEnabled(True)

    def apply_settings(self):
        self.accepted()

    def clear_translations(self):
        ''' Save the list of the current cities list
            and remove the odd or blank translations'''
        self.settings.setValue('CityList', str(self.citylist))
        translations_to_delete = []
        for key, value in self.trans_cities_dict.items():
            if key == value or value == '' or key not in self.citylist:
                translations_to_delete.append(key)
        for i in translations_to_delete:
            del self.trans_cities_dict[i]
        self.settings.setValue(
            'CitiesTranslation', str(self.trans_cities_dict)
        )
        logging.debug(
            'write ' + 'CitiesTranslation ' + str(self.trans_cities_dict)
        )

    def accepted(self):
        self.clear_translations()
        apikey = self.owmkey_text.text()
        city_name = self.city_combo.currentText()
        if apikey == '':
            self.statusbar.setText(self.nokey_message)
            return
        else:
            self.statusbar.setText('')
            self.settings.setValue('APPID', str(self.owmkey_text.text()))
        if city_name == '':
            self.statusbar.setText(self.nocity_message)
            return
        else:
            self.statusbar.setText('')
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
        if hasattr(self, 'color_before'):
            self.settings.setValue('TrayColor', self.color_before)
            if self.color_before == '':
                self.color_before = 'None'
            logging.debug(
                'Write font color for temp in tray: {0}'.format(self.color_before)
            )
        if self.autostart_changed:
            self.autostart_apply()
        if self.interval_changed:
            time = self.interval_combo.currentText()
            self.settings.setValue('Interval', time)
            logging.debug('Write ' + 'Interval ' + str(time))
        if self.lang_changed:
            lang = self.language_combo.currentText()
            setlang = [
                key for key, value in self.language_dico.items() if value == lang
            ]
            self.settings.setValue('Language', setlang[0])
            logging.debug('Write ' + 'Language ' + str(setlang[0]))
        if self.units_changed:
            unit = self.units_combo.currentText()
            setUnit = [
                key for key, value in self.units_dico.items() if value == unit
            ]
            self.settings.setValue('Unit', setUnit[0])
            logging.debug('Write ' + 'Unit ' + str(setUnit[0]))
        if self.wind_unit_changed:
            wind = self.wind_unit_combo.currentText()
            setWind = [
                key for key, value in self.wind_unit_dico.items() if value == wind
            ]
            logging.debug('Write ' + 'Wind_unit ' + str(setWind[0]))
            self.settings.setValue('Wind_unit', str(setWind[0]))
        if self.temp_decimal_changed:
            decimal = self.temp_decimal_combo.currentText()
            decimal_bool_str = 'False'
            if decimal == '0.1°':
                decimal_bool_str = 'True'
            self.settings.setValue('Decimal', decimal_bool_str)
            logging.debug('Write: Decimal in tray icon = ' + decimal_bool_str)
        if self.notifier_changed:
            self.notifier_apply()
        if self.tray_changed:
            self.tray_apply()
        if self.tray_icon_init_cmb_changed:
            self.tray_icon_init_size_apply()
        if self.tray_icon_temp_pos_spinbox_changed:
            self.tray_icon_temp_pos_apply()
        if self.toggle_tray_spinbox_changed:
            self.toggle_tray_interval_apply()
        if self.font_tray_changed:
            self.font_tray_apply()
        if self.comboBox_icons_theme_changed:
            self.system_icontheme_apply()
        if self.start_minimized_changed:
            self.start_minimized_apply()
        if self.logging_changed:
            self.logging_level_apply()
        proxy_url = self.settings.value('Proxy_url') or ''
        if proxy_url == '':
            self.proxy_bool = False
        self.settings.setValue('Proxy', str(self.proxy_bool))
        self.applied_signal.emit()

    def accept(self):
        self.accepted()
        apikey = self.owmkey_text.text()
        city_name = self.city_combo.currentText()
        if apikey == '':
            self.statusbar.setText(self.nokey_message)
            return
        if city_name == '':
            self.statusbar.setText(self.nocity_message)
            return
        QDialog.accept(self)

    def add_cities_incombo(self):
        list_cities = ''
        self.city_combo.clear()
        if self.clear_combo:
            return
        if self.first:
            list_cities = self.settings.value('CityList')
            if list_cities is not None:
                self.city_list_before = list_cities[:]
            self.citylist = [
                self.set_city + '_'
                + self.settings.value('Country') + '_'
                + self.settings.value('ID')
            ]
        else:
            self.citylist = [
                self.city_before + '_' + self.country_before
                + '_' + self.id_before
            ]
            list_cities = self.city_list_before[:]
        if list_cities is None:
            list_cities = []
        if list_cities != '' and list_cities is not None:
            if type(list_cities) is str:
                list_cities = eval(list_cities)
            self.citylist = self.citylist + list_cities
        duplicate = []
        for i in self.citylist:
            if i not in duplicate:
                duplicate.append(i)
        self.citylist = duplicate[:]
        self.translated = []
        for city in self.citylist:
            self.translated.append(self.trans_cities_dict.get(city, city))
        self.city_combo.addItems(self.translated)
        if len(list_cities) > 0:
            maxi = len(max(list_cities, key=len))
            self.city_combo.setMinimumSize(maxi * 8, 23)

    def find_city_key(self, city):
        for key, value in self.trans_cities_dict.items():
            if value == city:
                return key
        return city
