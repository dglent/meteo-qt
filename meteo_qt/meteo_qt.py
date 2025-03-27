# Purpose: System tray weather application
# Weather data: http://openweathermap.org
# Author: Dimitrios Glentadakis dglent@free.fr
# License: GPLv3

import logging
import logging.handlers
import os
import platform
import sys
import urllib.request
from functools import partial
from socket import timeout
from lxml import etree
import json
import time
import datetime
import traceback
from io import StringIO

from PyQt6.QtCore import (
    PYQT_VERSION_STR, QT_VERSION_STR, QCoreApplication, QByteArray,
    QLibraryInfo, QLocale, QSettings, Qt, QThread, QTimer, QTranslator,
    pyqtSignal, pyqtSlot, QTime, QSize
)
from PyQt6.QtGui import (
    QAction, QColor, QCursor, QFont, QIcon, QImage, QMovie, QPainter, QPixmap,
    QTransform, QTextDocument, QTextCursor, QColorConstants
)
from PyQt6.QtWidgets import (
    QDialog, QApplication, QMainWindow, QMenu, QSystemTrayIcon,
    QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QGraphicsDropShadowEffect,
    QTextBrowser, QPushButton
)

try:
    import qrc_resources
    import settings
    import searchcity
    import conditions
    import about_dlg
    import humidex
except ImportError:
    from meteo_qt import qrc_resources
    from meteo_qt import settings
    from meteo_qt import searchcity
    from meteo_qt import conditions
    from meteo_qt import about_dlg
    from meteo_qt import humidex


__version__ = "4.1"


class SystemTrayIcon(QMainWindow):
    units_dico = {
        'metric': '°C',
        'imperial': '°F',
        ' ': '°K'
    }

    def __init__(self, parent=None):
        super(SystemTrayIcon, self).__init__(parent)
        self.settings = QSettings()
        self.cityChangeTimer = QTimer()
        self.cityChangeTimer.timeout.connect(self.update_city_gif)

        self.tomorrow_translation = QCoreApplication.translate(
            "Tray notification popup",
            "<b>Tomorrow:</b>",
            "Title for the weather conditions"
        )
        self.tomorrow_notification_text = ""
        self.tomorrow_notification_timer = QTimer()
        self.tomorrow_notification_timer.timeout.connect(self.tomorrow_tray_notification)

        self.alerts_dlg = AlertsDLG(parent=self)
        self.alerts_timer = QTimer()
        self.alerts_timer.timeout.connect(self.next_alert_event)
        self.language = self.settings.value('Language') or ''
        self.temp_decimal_bool = self.settings.value('Decimal') or False
        # initialize the tray icon type in case of first run: issue#42
        self.tray_type = self.settings.value('TrayType') or 'icon&temp'
        self.system_icons = self.settings.value('IconsTheme') or 'System default'
        self.cond = conditions.WeatherConditions()
        self.temporary_city_status = False
        self.conditions = self.cond.trans
        self.clouds = self.cond.clouds
        self.wind = self.cond.wind
        self.wind_dir = self.cond.wind_direction
        self.wind_codes = self.cond.wind_codes
        self.inerror = False
        self.tentatives = 0
        self.system_icons_dico = {
            '01d': ('weather-clear', 'weather-clear-symbolic'),
            '01n': ('weather-clear-night', 'weather-clear-night-symbolic'),
            '02d': ('weather-few-clouds', 'weather-few-clouds-symbolic'),
            '02n': ('weather-few-clouds-night', 'weather-few-clouds-night-symbolic'),
            '03d': ('weather-clouds', 'weather-overcast', 'weather-overcast-symbolic'),
            '03n': ('weather-clouds-night', 'weather-overcast', 'weather-overcast-symbolic'),
            '04d': ('weather-many-clouds', 'weather-overcast', 'weather-overcast-symbolic'),
            '04n': ('weather-many-clouds', 'weather-overcast', 'weather-overcast-symbolic'),
            '09d': ('weather-showers', 'weather-showers-symbolic'),
            '09n': ('weather-showers', 'weather-showers-symbolic'),
            '10d': ('weather-showers-day', 'weather-showers', 'weather-showers-symbolic'),
            '10n': ('weather-showers-night', 'weather-showers', 'weather-showers-symbolic'),
            '11d': ('weather-storm-day', 'weather-storm', 'weather-storm-symbolic'),
            '11n': ('weather-storm-night', 'weather-storm', 'weather-storm-symbolic'),
            '13d': ('weather-snow', 'weather-snow-symbolic'),
            '13n': ('weather-snow', 'weather-snow-symbolic'),
            '50d': ('weather-fog', 'weather-fog-symbolic'),
            '50n': ('weather-fog', 'weather-fog-symbolic'),
        }
        url_prefix = 'http://api.openweathermap.org/data/2.5'
        self.baseurl = f'{url_prefix}/weather?id='
        self.accurate_url = f'{url_prefix}/find?q='
        self.day_forecast_url = f'{url_prefix}/forecast?id='
        self.forecast6_url = f'{url_prefix}/forecast/daily?id='
        self.wIconUrl = 'http://openweathermap.org/img/w/'
        apikey = self.settings.value('APPID') or ''
        self.appid = '&APPID=' + apikey
        self.forecast_icon_url = self.wIconUrl
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.menu = QMenu()

        self.citiesMenu = QMenu(self.tr('Cities'))
        if os.environ.get('DESKTOP_SESSION') in ['unity', 'ubuntu', 'budgie-desktop']:
            # Missing left click on Unity environment issue #63
            self.panelAction = QAction(
                QCoreApplication.translate(
                    "Tray context menu",
                    "Toggle Window",
                    "Open/closes the application window"
                ),
                self
            )
            self.menu.addAction(self.panelAction)
            self.panelAction.triggered.connect(self.showpanel)
        self.tempCityAction = QAction(self.tr('&Temporary city'), self)
        self.refreshAction = QAction(
            QCoreApplication.translate(
                'Action to refresh the weather infos from the server',
                '&Refresh',
                'Systray icon context menu'
            ),
            self
        )
        self.alertsAction = QAction(
            QCoreApplication.translate(
                'Action to open the dialog with the weather alerts',
                '&Alerts',
                'Systray icon context menu'
            ),
            self
        )
        self.alert_json = None
        self.alert_event = ''
        self.alertsAction.setEnabled(False)
        self.settingsAction = QAction(self.tr('&Settings'), self)
        self.aboutAction = QAction(self.tr('&About'), self)
        self.exitAction = QAction(self.tr('Exit'), self)
        self.menu.addAction(self.alertsAction)
        self.menu.addAction(self.settingsAction)
        self.menu.addAction(self.refreshAction)
        self.menu.addMenu(self.citiesMenu)
        self.menu.addAction(self.tempCityAction)
        self.menu.addAction(self.aboutAction)
        self.menu.addAction(self.exitAction)
        self.alertsAction.triggered.connect(self.show_alert)
        self.settingsAction.triggered.connect(self.config)
        self.exitAction.triggered.connect(QApplication.instance().quit)
        self.refreshAction.triggered.connect(self.manual_refresh)
        self.aboutAction.triggered.connect(self.about)
        self.tempCityAction.triggered.connect(self.tempcity)
        self.systray = QSystemTrayIcon()
        self.systray.setContextMenu(self.menu)
        self.systray.activated.connect(self.activate)
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip(self.tr('Searching weather data...'))
        self.feels_like_translated = QCoreApplication.translate(
            "The Feels Like Temperature",
            "Feels like",
            "Weather info window"
        )
        self.notification = ""
        self.uv_index_exp = ""
        self.hPaTrend = 0
        self.trendCities_dic = {}
        self.notifier_id = ""
        self.temp_trend = ""
        self.systray.show()
        # The dictionnary has to be intialized here. If there is an error
        # the program couldn't become functionnal if the dictionnary is
        # reinitialized in the weatherdata method
        self.weatherDataDico = {}
        # The traycolor has to be initialized here for the case when we cannot
        # reach the tray method (case: set the color at first time usage)
        self.traycolor = ''
        self.days_dico = {
            '0': self.tr('Mon'),
            '1': self.tr('Tue'),
            '2': self.tr('Wed'),
            '3': self.tr('Thu'),
            '4': self.tr('Fri'),
            '5': self.tr('Sat'),
            '6': self.tr('Sun')
        }
        self.precipitation_probability_str = QCoreApplication.translate(
            'Tooltip forcast of the day',
            'Probability of precipitation',
            'Weather info window'
        )
        self.precipitation = self.cond.rain
        self.wind_direction = self.cond.wind_codes
        self.wind_name_dic = self.cond.wind
        self.clouds_name_dic = self.cond.clouds
        self.beaufort_sea_land = self.cond.beaufort
        self.hpa_indications = self.cond.pressure
        self.uv_risk = self.cond.uv_risk
        self.uv_recommend = self.cond.uv_recommend
        self.doc = QTextDocument()
        self.create_overview()
        self.toggle_tray_timer = QTimer()
        self.toggle_tray_bool = False
        self.toggle_tray_action = False
        self.toggle_tray_timer.timeout.connect(self.toggle_tray)
        self.set_toggle_tray_interval()
        self.city = self.settings.value('City') or ''
        self.country = self.settings.value('Country') or ''
        self.id_ = self.settings.value('ID') or ''
        self.current_city_display = f'{self.city}_{self.country}_{self.id_}'
        self.tray_menu_icons()
        self.cities_menu()
        self.refresh()

    def tray_menu_icons(self):
        if hasattr(self, 'panelAction'):
            icon = QIcon.fromTheme('preferences-system-windows')
            if icon.isNull():
                icon = QIcon(':/panel')
            self.panelAction.setIcon(icon)
        icon = QIcon.fromTheme('application-exit')
        if icon.isNull():
            icon = QIcon(':/exit')
        self.exitAction.setIcon(icon)
        icon = QIcon.fromTheme('help-about')
        if icon.isNull():
            icon = QIcon(':/info')
        self.aboutAction.setIcon(icon)
        icon = QIcon.fromTheme('view-refresh')
        if icon.isNull():
            icon = QIcon(':/refresh')
        self.refreshAction.setIcon(icon)
        icon = QIcon.fromTheme('applications-system')
        if icon.isNull():
            icon = QIcon(':/configure')
        self.settingsAction.setIcon(icon)
        icon = QIcon.fromTheme('go-jump')
        if icon.isNull():
            icon = QIcon(':/tempcity')
        self.tempCityAction.setIcon(icon)
        icon = QIcon.fromTheme('user-bookmarks')
        if icon.isNull():
            icon = QIcon(':/bookmarks')
        self.citiesMenu.setIcon(icon)
        icon = QIcon.fromTheme('dialog-warning')
        if icon.isNull():
            icon = QIcon(':/dialog-warning')
        self.alertsAction.setIcon(icon)

    def set_toggle_tray_interval(self):
        interval = self.settings.value('Toggle_tray_interval') or '0'
        interval = int(interval)
        tray_type = self.settings.value('TrayType') or 'icon&temp'
        self.tray_type_config = tray_type
        self.toggle_tray_timer.stop()
        if interval > 0 and tray_type in ['icon&temp', 'icon&feels_like']:
            self.toggle_tray_bool = True
            self.tray_type = 'icon'
            self.toggle_tray_timer.start(interval * 1000)
        else:
            # Restore the value from the settings file
            self.tray_type = tray_type
            self.toggle_tray_bool = False

    def toggle_tray_state(self):
        tray_type = self.settings.value('TrayType') or 'icon&temp'
        if tray_type == 'icon&temp':
            if self.tray_type == 'icon':
                self.tray_type = 'temp'
            else:
                self.tray_type = 'icon'
        elif tray_type == 'icon&feels_like':
            if self.tray_type == 'icon':
                self.tray_type = 'feels_like_temp'
            else:
                self.tray_type = 'icon'

    def toggle_tray(self):
        self.toggle_tray_action = True
        self.toggle_tray_state()
        self.tray()
        self.toggle_tray_action = False

    def shadow_effect(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(50, 50, 50, 100))
        shadow.setXOffset(5)
        shadow.setYOffset(5)
        shadow.setBlurRadius(20)
        return shadow

    def create_overview(self):
        self.overviewcitydlg = QDialog()
        self.setCentralWidget(self.overviewcitydlg)
        self.total_layout = QVBoxLayout()

        # ----First part overview day -----
        self.over_layout = QVBoxLayout()
        self.dayforecast_layout = QHBoxLayout()
        self.dayforecast_temp_layout = QHBoxLayout()

        self.city_label = QLabel()
        self.over_layout.addWidget(self.city_label)
        self.icontemp_layout = QHBoxLayout()
        self.icon_label = QLabel()
        self.icontemp_layout.addWidget(self.icon_label)
        self.temp_label = QLabel()
        self.temp_label.setWordWrap(True)
        self.icontemp_layout.addWidget(self.temp_label)
        self.over_layout.addLayout(self.icontemp_layout)
        self.weather_label = QLabel()
        self.weather_label.setWordWrap(True)
        self.icontemp_layout.addWidget(self.weather_label)
        self.icontemp_layout.addStretch()
        self.over_layout.addLayout(self.dayforecast_layout)
        self.over_layout.addLayout(self.dayforecast_temp_layout)
        # ------Second part overview day---------
        self.over_grid = QGridLayout()
        # Feels Like
        self.feels_like_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                self.feels_like_translated
            )
        )
        self.feels_like_value = QLabel()
        # Wind
        self.wind_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label before the wind description',
                    'Wind',
                    'Weather info panel'
                )
            )
        )
        self.wind_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.windLabelDescr = QLabel('None')
        self.wind_icon_label = QLabel()
        self.wind_icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.wind_icon = QPixmap(':/arrow')
        # Clouds
        self.clouds_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label for the cloudiness (%)',
                    'Cloudiness',
                    'Weather info panel'
                )
            )
        )
        self.clouds_name = QLabel()
        # Pressure
        self.pressure_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label for the pressure (hPa)',
                    'Pressure',
                    'Weather info panel'
                )
            )
        )
        self.pressure_value = QLabel()
        # Humidity
        self.humidity_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label for the humidity (%)',
                    'Humidity',
                    'Weather info panel'
                )
            )
        )
        self.humidity_value = QLabel()
        # Visibility
        self.visibility_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Visibility (distance) label',
                    'Visibility',
                    'Weather overview dialogue'
                )
            )
        )
        self.visibility_value = QLabel()
        # Dew point
        self.dew_point_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Dew point label',
                    'Dew point',
                    'Weather overview dialogue'
                )
            )
        )
        self.dew_point_value = QLabel()
        # Comfort level
        self.comfort_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Comfort level',
                    'Comfort',
                    'Weather overview dialogue'
                )
            )
        )
        self.comfort_value = QLabel()
        # Precipitation
        self.precipitation_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Precipitation type (no/rain/snow)',
                    'Precipitation',
                    'Weather overview dialogue'
                )
            )
        )
        self.precipitation_value = QLabel()
        # Sunrise Sunset Daylight
        self.sunrise_label = QLabel(
            '<font color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label for the sunrise time (hh:mm)',
                    'Sunrise',
                    'Weather info panel'
                )
            )
        )
        self.sunset_label = QLabel(
            '<font color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label for the sunset (hh:mm)',
                    'Sunset',
                    'Weather info panel'
                )
            )
        )
        self.sunrise_value = QLabel()
        self.sunset_value = QLabel()
        self.daylight_label = QLabel(
            '<font color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Daylight duration',
                    'Daylight',
                    'Weather overview dialogue'
                )
            )
        )
        self.daylight_value_label = QLabel()

        # --- Air pollution ---
        self.air_pollution_label = QLabel(
            '<font><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Label for air quality index (air pollution)',
                    'Air quality',
                    'Label in weather info dialogue'
                )
            )
        )
        self.aqi = {
            0: QCoreApplication.translate(
                'The air quality index is not available',
                'Unavailable',
                'The value in the weather info dialogue'
            ),
            1: QCoreApplication.translate(
                'Air Quality Index 1',
                'Good',
                'The value in the weather info dialogue'
            ),
            2: QCoreApplication.translate(
                'Air Quality Index 2',
                'Fair',
                'The value in the weather info dialogue'
            ),
            3: QCoreApplication.translate(
                'Air Quality Index 3',
                'Moderate',
                'The value in the weather info dialogue'
            ),
            4: QCoreApplication.translate(
                'Air Quality Index 4',
                'Poor',
                'The value in the weather info dialogue'
            ),
            5: QCoreApplication.translate(
                'Air Quality Index 5',
                'Very Poor',
                'The value in the weather info dialogue'
            )
        }

        # --UV---
        self.uv_label = QLabel(
            '<font size="3" color=><b>{}</b></font>'.format(
                QCoreApplication.translate(
                    'Ultraviolet index',
                    'UV',
                    'Label in weather info dialogue'
                )
            )
        )
        self.uv_label.setToolTip(
            QCoreApplication.translate(
                'Tooltip of UV label',
                'The ultraviolet index at 12 PM',
                'Label in weather info dialogue'
            )
        )
        self.air_pollution_value_label = QLabel()
        self.uv_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.uv_value_label = QLabel()

        self.over_grid.addWidget(self.feels_like_label, 0, 0)
        self.over_grid.addWidget(self.feels_like_value, 0, 1)
        self.over_grid.addWidget(self.wind_label, 1, 0)
        self.over_grid.addWidget(self.windLabelDescr, 1, 1)
        self.over_grid.addWidget(self.wind_icon_label, 1, 2)
        self.over_grid.addWidget(self.clouds_label, 2, 0)
        self.over_grid.addWidget(self.clouds_name, 2, 1)
        self.over_grid.addWidget(self.pressure_label, 3, 0)
        self.over_grid.addWidget(self.pressure_value, 3, 1)
        self.over_grid.addWidget(self.humidity_label, 4, 0)
        self.over_grid.addWidget(self.humidity_value, 4, 1, 1, 3)  # align left
        self.over_grid.addWidget(self.visibility_label, 5, 0)
        self.over_grid.addWidget(self.visibility_value, 5, 1)
        self.over_grid.addWidget(self.dew_point_label, 6, 0)
        self.over_grid.addWidget(self.dew_point_value, 6, 1)
        self.over_grid.addWidget(self.comfort_label, 7, 0)
        self.over_grid.addWidget(self.comfort_value, 7, 1)
        self.over_grid.addWidget(self.precipitation_label, 8, 0)
        self.over_grid.addWidget(self.precipitation_value, 8, 1)
        self.over_grid.addWidget(self.sunrise_label, 9, 0)
        self.over_grid.addWidget(self.sunrise_value, 9, 1)
        self.over_grid.addWidget(self.sunset_label, 10, 0)
        self.over_grid.addWidget(self.sunset_value, 10, 1)
        self.over_grid.addWidget(self.daylight_label, 11, 0)
        self.over_grid.addWidget(self.daylight_value_label, 11, 1)
        self.over_grid.addWidget(self.air_pollution_label, 12, 0)
        self.over_grid.addWidget(self.air_pollution_value_label, 12, 1)
        self.over_grid.addWidget(self.uv_label, 13, 0)
        self.over_grid.addWidget(self.uv_value_label, 13, 1)
        # # -------------Forecast-------------
        self.forecast_days_layout = QHBoxLayout()
        self.forecast_icons_layout = QHBoxLayout()
        self.forecast_minmax_layout = QHBoxLayout()
        # ----------------------------------
        self.total_layout.addLayout(self.over_layout)
        self.total_layout.addLayout(self.over_grid)
        self.total_layout.addLayout(self.forecast_icons_layout)
        self.total_layout.addLayout(self.forecast_days_layout)
        self.total_layout.addLayout(self.forecast_minmax_layout)

        self.overviewcitydlg.setLayout(self.total_layout)
        self.setWindowTitle(self.tr('Weather status'))

    def overviewcity_weather_label(self):
        weather_des = f'<font size="3"><b>{self.weatherDataDico["Meteo"]}</b>'
        if self.alert_event != '':
            weather_des += f'<br/>{self.alert_event.replace("warning", "")}</font>'
        else:
            weather_des += '</font>'
        self.weather_label.setText(weather_des)

    def overviewcity(self):
        self.forecast_weather_list = []
        self.dayforecast_weather_list = []
        self.icon_list = []
        self.dayforecast_icon_list = []
        self.unit_temp = self.units_dico[self.unit]
        # ----First part overview day -----

        # Check for city translation
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        city_notrans = (
            '{0}_{1}_{2}'.format(
                self.weatherDataDico['City'],
                self.weatherDataDico['Country'],
                self.weatherDataDico['Id']
            )
        )
        if city_notrans in cities_trans_dict:
            city_label = cities_trans_dict[city_notrans]
        else:
            city_label = (
                '{0}, {1}'.format(
                    self.weatherDataDico['City'],
                    self.weatherDataDico['Country']
                )
            )
        self.city_label.setText(
            f'<font size="4"><b>{city_label}</b></font>'
        )

        self.icon_label.setPixmap(self.wIcon)
        shadow = self.shadow_effect()
        self.icon_label.setGraphicsEffect(shadow)

        self.temp_label.setText(
            '<font size="5"><b>{0} {1}{2}</b></font>'.format(
                '{0:.1f}'.format(float(self.weatherDataDico['Temp'][:-1])),
                self.unit_temp,
                self.temp_trend
            )
        )
        # Set the current weather label + alert message
        self.overviewcity_weather_label()

        self.feels_like_value.setText(
            '{0} {1}'.format(
                self.weatherDataDico['Feels_like'][0],
                self.weatherDataDico['Feels_like'][1]
            )
        )

        # Wind
        wind_unit_speed_config = self.settings.value('Wind_unit') or 'df'
        if wind_unit_speed_config == 'bf':
            self.bft_bool = True
        else:
            self.bft_bool = False
        self.unit_system = ' m/s '
        self.unit_system_wind = ' m/s '
        if self.unit == 'imperial':
            self.unit_system = ' mph '
            self.unit_system_wind = ' mph '

        wind_speed = '{0:.1f}'.format(float(self.weatherDataDico['Wind'][0]))
        windTobeaufort = str(self.convertToBeaufort(wind_speed))

        if self.bft_bool is True:
            wind_speed = windTobeaufort
            self.unit_system_wind = ' Bft. '

        if self.unit == 'metric' and wind_unit_speed_config == 'km':
            self.wind_km_bool = True
            wind_speed = '{0:.1f}'.format(float(wind_speed) * 3.6)
            self.unit_system_wind = QCoreApplication.translate(
                '''Unit displayed after the wind speed value and before
                the wind description (keep the spaces before and after)''',
                ' km/h ',
                'Weather Infos panel'
            )
        else:
            self.wind_km_bool = False

        try:
            self.windLabelDescr.setText(
                '<font color=>{0} {1}° <br/>{2}{3}{4}</font>'.format(
                    self.weatherDataDico['Wind'][4],
                    self.weatherDataDico['Wind'][2],
                    wind_speed,
                    self.unit_system_wind,
                    self.weatherDataDico['Wind'][1]
                )
            )
            self.windLabelDescr.setToolTip(
                self.beaufort_sea_land[windTobeaufort]
            )
        except Exception:
            logging.error(
                'Cannot find wind informations:\n{}'.format(
                    self.weatherDataDico['Wind']
                )
            )

        self.wind_icon_direction()

        # Clouds
        self.clouds_name.setText(
            f'<font color=>{self.weatherDataDico["Clouds"]}</font>'
        )

        # Pressure
        if self.hPaTrend == 0:
            hpa = "→"
        elif self.hPaTrend < 0:
            hpa = "↘"
        elif self.hPaTrend > 0:
            hpa = "↗"
        self.pressure_value.setText(
            '<font color=>{0} {1} {2}</font>'.format(
                str(float(self.weatherDataDico['Pressure'][0])),
                self.weatherDataDico['Pressure'][1],
                hpa
            )
        )
        self.pressure_value.setToolTip(self.hpa_indications['hpa'])
        # Humidity
        self.humidity_value.setText(
            '<font color=>{0} {1}</font>'.format(
                self.weatherDataDico['Humidity'][0],
                self.weatherDataDico['Humidity'][1]
            )
        )
        visibility_unit = 'km'
        visibility_distance = '{0:.1f}'.format(int(self.weatherDataDico["Visibility"]) / 1000)
        if self.unit == 'imperial':
            visibility_unit = 'mi'
            visibility_distance = '{0:.1f}'.format(float(visibility_distance) / 1.609344)
        self.visibility_value.setText(
            f'{visibility_distance} {visibility_unit}'
        )
        # Dew point
        t_air = float('{0:.1f}'.format(float(self.weatherDataDico['Temp'][:-1])))
        hum = humidex.Humidex(
            t_air=t_air,
            rel_humidity=int(self.weatherDataDico['Humidity'][0]),
            unit=self.unit_temp
        )
        self.dew_point_value.setText(
            f'<font color=>{hum.dew_point} {self.unit_temp}</font>'
        )
        # Comfort
        self.comfort_value.setText(
            f'<font color=>{hum.comfort_text}</font>'
        )
        self.comfort_value.setToolTip(hum.comfort_ttip)
        # Precipitation
        rain_mode = (
            self.precipitation[self.weatherDataDico['Precipitation'][0]]
        )
        rain_value = self.weatherDataDico['Precipitation'][1]
        rain_unit = ' mm '
        if rain_value == '':
            rain_unit = ''
        else:
            if self.unit == 'imperial':
                rain_unit = 'inch'
                rain_value = str(float(rain_value) / 25.4)
                rain_value = "{0:.4f}".format(float(rain_value))
            else:
                rain_value = "{0:.2f}".format(float(rain_value))
        self.precipitation_value.setText(
            '<font color=>{0} {1} {2}</font>'.format(
                rain_mode,
                rain_value,
                rain_unit
            )
        )
        # Sunrise Sunset Daylight
        try:
            rise_str = self.utc('Sunrise', 'weatherdata')
            set_str = self.utc('Sunset', 'weatherdata')
        except (AttributeError, ValueError):
            logging.error('Cannot find sunrise, sunset time info')
            # if value is None
            rise_str = '00:00:00'
            set_str = '00:00:00'

        self.sunrise_value.setText(
            f'<font color=>{rise_str[:-3]}</font>'
        )
        self.sunset_value.setText(
            f'<font color=>{set_str[:-3]}</font>'
        )

        daylight_value = self.daylight_delta(rise_str[:-3], set_str[:-3])
        self.daylight_value_label.setText(
            f'<font color=>{daylight_value}</font>'
        )
        # --UV---
        fetching_text = (
            '<font color=>{}</font>'.format(
                QCoreApplication.translate(
                    'Ultraviolet index waiting text label',
                    'Fetching...',
                    'Weather info dialogue'
                )
            )
        )
        self.uv_value_label.setText(fetching_text)

        if self.forcast6daysBool:
            self.forecast6data()
        else:
            self.forecastdata()
        self.iconfetch()
        logging.debug('Fetched 6 days forecast icons')
        self.dayforecastdata()
        logging.debug('Fetched day forecast data')
        self.dayiconfetch()
        logging.debug('Fetched day forcast icons')
        self.uv_fetch()
        logging.debug('Fetched uv index')

        self.restoreGeometry(
            self.settings.value(
                "MainWindow/Geometry",
                QByteArray()
            )
        )
        # Option to start with the panel closed, true by defaut
        # starting with the panel open can be useful for users who don't have plasma
        # installed (to set keyboard shortcuts or other default window behaviours)
        start_minimized = self.settings.value('StartMinimized') or 'True'
        if start_minimized == 'False':
            self.showpanel()
        logging.info(
            f"\nEXPORT_START\n"
            f"City,{city_label}\n"
            f"Temperature,{float(self.weatherDataDico['Temp'][:-1])} {self.unit_temp}\n"
            f"Feels like,{self.feels_like_value.text()}\n"
            f"Wind,{self.weatherDataDico['Wind'][4]} {wind_speed} {self.unit_system_wind} {self.weatherDataDico['Wind'][1]}\n"
            f"Cloudiness,{self.weatherDataDico['Clouds']}\n"
            f"Humidity,{self.weatherDataDico['Humidity'][0]} {self.weatherDataDico['Humidity'][1]}\n"
            f"Visibility,{visibility_distance} {visibility_unit}\n"
            f"Comfort,{hum.comfort_text}\n"
            f"Precipitation,{rain_mode} {rain_value} {rain_unit}\n"
            f"Sunrise,{rise_str[:-3]}\n"
            f"Sunset,{set_str[:-3]}\n"
            f"Daylight,{daylight_value}\n"
            f"Air quality,{self.air_pollution_value_label.text()}\n"
            f"UV,{self.uv_index_exp}\n"
            f"EXPORT_END\n"
        )

    def daylight_delta(self, s1, s2):
        FMT = '%H:%M'
        tdelta = (
            datetime.datetime.strptime(s2, FMT)
            - datetime.datetime.strptime(s1, FMT)
        )
        m, s = divmod(tdelta.seconds, 60)
        h, m = divmod(m, 60)
        if len(str(m)) == 1:
            m = f'0{str(m)}'
        daylight_in_hours = f'{str(h)}:{str(m)}'
        return daylight_in_hours

    def utc(self, rise_set, what):
        ''' Convert sun rise/set from UTC to local time
            'rise_set' is 'Sunrise' or 'Sunset' when it is for weatherdata
            or the index of hour in day forecast when dayforecast'''
        strtime = ''
        if what == 'weatherdata':
            strtime = (
                self.weatherDataDico[rise_set].split('T')[1]
            )
        elif what == 'dayforecast':
            if not self.json_data_bool:
                strtime = (
                    self.dayforecast_data[4][rise_set].get('from')
                    .split('T')[1]
                )
            else:
                strtime = (
                    self.dayforecast_data['list'][rise_set]['dt_txt'][10:]
                )

        suntime = QTime.fromString(strtime.strip())

        # add the diff UTC-local in seconds
        utc_time = suntime.addSecs(time.localtime().tm_gmtoff)
        utc_time_str = utc_time.toString()
        return utc_time_str

    def convertToBeaufort(self, speed):
        speed = float(speed)
        if self.unit_system.strip() == 'm/s':
            if speed <= 0.2:
                return 0
            elif speed <= 1.5:
                return 1
            elif speed <= 3.3:
                return 2
            elif speed <= 5.4:
                return 3
            elif speed <= 7.9:
                return 4
            elif speed <= 10.7:
                return 5
            elif speed <= 13.8:
                return 6
            elif speed <= 17.1:
                return 7
            elif speed <= 20.7:
                return 8
            elif speed <= 24.4:
                return 9
            elif speed <= 28.4:
                return 10
            elif speed <= 32.4:
                return 11
            elif speed <= 36.9:
                return 12
        elif self.unit_system.strip() == 'mph':
            if speed < 1:
                return 0
            elif speed < 4:
                return 1
            elif speed < 8:
                return 2
            elif speed < 13:
                return 3
            elif speed < 18:
                return 4
            elif speed < 25:
                return 5
            elif speed < 32:
                return 6
            elif speed < 39:
                return 7
            elif speed < 47:
                return 8
            elif speed < 55:
                return 9
            elif speed < 64:
                return 10
            elif speed < 73:
                return 11
            elif speed <= 82:
                return 12

    def wind_icon_direction(self):
        angle = self.weatherDataDico['Wind'][2]
        if angle == '':
            if self.wind_icon_label.isVisible is True:
                self.wind_icon_label.hide()
            return
        else:
            if self.wind_icon_label.isVisible is False:
                self.wind_icon_label.show()
        transf = QTransform()
        logging.debug(f'Wind degrees direction: {angle}')
        transf.rotate(int(float(angle)))
        rotated = self.wind_icon.transformed(
            transf, mode=Qt.TransformationMode.SmoothTransformation
        )
        self.wind_icon_label.setPixmap(rotated)

    def uv_color(self, uv):
        try:
            uv = float(uv)
        except Exception:
            return ('grey', 'None')
        if uv <= 2.99:
            return ('green', 'Low')
        elif uv <= 5.99:
            return ('gold', 'Moderate')
        elif uv <= 7.99:
            return ('orange', 'High')
        elif uv <= 10.99:
            return ('red', 'Very high')
        elif uv >= 11:
            return ('purple', 'Extreme')

    def winddir_json_code(self, deg):
        deg = float(deg)
        if deg < 22.5 or deg > 337.5:
            return 'N'
        elif deg < 45:
            return 'NNE'
        elif deg < 67.5:
            return 'NE'
        elif deg < 90:
            return 'ENE'
        elif deg < 112.5:
            return 'E'
        elif deg < 135:
            return 'ESE'
        elif deg < 157.5:
            return 'SE'
        elif deg < 180:
            return 'SSE'
        elif deg < 202.5:
            return 'S'
        elif deg < 225:
            return 'SSW'
        elif deg < 247.5:
            return 'SW'
        elif deg < 270:
            return 'WSW'
        elif deg < 292.5:
            return 'W'
        elif deg < 315:
            return 'WNW'
        elif deg <= 337.5:
            return 'NNW'

    def find_min_max(self):
        ''' Collate the temperature of each forecast time
            to find the min max T° of the forecast
            of the day in the 4 days forecast '''
        self.date_temp_forecast = {}
        if not self.json_data_bool:
            for element in self.dayforecast_data.iter():
                if element.tag == 'time':
                    date_list = element.get('from').split('-')
                    date_list_time = date_list[2].split('T')
                    date_list[2] = date_list_time[0]
                if element.tag == 'temperature':
                    if not date_list[2] in self.date_temp_forecast:
                        self.date_temp_forecast[date_list[2]] = []
                    self.date_temp_forecast[date_list[2]].append(
                        float(element.get('max')))
        else:
            for tag in self.dayforecast_data['list']:
                day = int(tag.get('dt'))
                day = time.localtime(day)
                day = str(day.tm_mday)
                if day not in self.date_temp_forecast:
                    self.date_temp_forecast[day] = []
                self.date_temp_forecast[day].append(
                    float(tag['main'].get('temp_max'))
                )

    def forecast6data(self):
        '''Forecast for the next 6 days'''
        self.clearLayout(self.forecast_minmax_layout)
        self.clearLayout(self.forecast_days_layout)
        periods = 7
        fetched_file_periods = (len(self.forecast6_data.xpath('//time')))
        # Some times server sends less data
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            logging.warning(
                'Reduce forecast for the next 6 days to {0}'.format(
                    periods - 1
                )
            )
        counter_day = 0
        forecast_data = False
        tomorrow_collected = False
        self.tomorrow_notification_text = ""
        self.tomorrow_notification_text += self.tomorrow_translation + '\n'
        trans_cities = self.settings.value('CitiesTranslation') or '{}'
        trans_cities_dict = eval(trans_cities)
        city = f'{self.city}_{self.country}_{self.id_}'
        city_name = self.city
        if city in trans_cities_dict:
            city_name = trans_cities_dict[city]
        self.tomorrow_notification_text += city_name + '\n'
        t_unit = {'celsius': '°C', 'fahrenheit': '°F', 'kelvin': '°K'}
        for element in self.forecast6_data.iter():

            if element.tag == 'time':
                forecast_data = True
            if forecast_data is False:
                continue

            if element.tag == 'time':
                counter_day += 1
                if counter_day == periods:
                    break

                weather_end = False
                date_list = element.get('day').split('-')
                day_of_week = str(datetime.date(
                    int(date_list[0]), int(date_list[1]),
                    int(date_list[2])).weekday()
                )
                label = QLabel(f'{self.days_dico[day_of_week]}')
                label.setToolTip(element.get('day'))
                label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                self.forecast_days_layout.addWidget(label)

            if element.tag == 'temperature':
                t_air = element.get('max')
                if not tomorrow_collected:
                    self.tomorrow_notification_text += f'{t_air} {t_unit[element.get("unit")]}\n'
                mlabel = QLabel(
                    '<font color=>{0}°<br/>{1}°</font>'.format(
                        '{0:.0f}'.format(float(element.get('min'))),
                        '{0:.0f}'.format(float(element.get('max')))
                    )
                )
                mlabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
                self.forecast_minmax_layout.addWidget(mlabel)

            if element.tag == 'symbol':
                # icon
                self.icon_list.append(element.get('var'))
                weather_cond = element.get('name')
                try:
                    weather_cond = (
                        self.conditions[element.get('number')]
                    )
                except KeyError:
                    logging.warning(
                        f'Cannot find localisation string for: {weather_cond}'
                    )
                    pass
                if not tomorrow_collected:
                    self.tomorrow_notification_text += weather_cond + ' '

            if element.tag == 'feels_like':
                feels_like_day = element.get('day')
                feels_like_morning = element.get('morn')
                feels_like_night = element.get('night')
                feels_like_eve = element.get('eve')
                feels_like_unit = element.get('unit')
                if feels_like_unit == 'celsius':
                    feels_like_unit = '°C'
                else:
                    feels_like_unit = '°F'
                feels_like_day_label = QCoreApplication.translate(
                    'Tooltip on weather icon on 6 days forecast',
                    'Day',
                    'Weather information window'
                )
                feels_like_morning_label = QCoreApplication.translate(
                    'Tooltip on weather icon on 6 days forecast',
                    'Morning',
                    'Weather information window'
                )
                feels_like_eve_label = QCoreApplication.translate(
                    'Tooltip on weather icon on 6 days forecast',
                    'Evening',
                    'Weather information window'
                )
                feels_like_night_label = QCoreApplication.translate(
                    'Tooltip on weather icon on 6 days forecast',
                    'Night',
                    'Weather information window'
                )
                weather_cond += (
                    f'\n―――――\n{self.feels_like_translated} \n'
                    f'{feels_like_morning_label} {feels_like_morning} {feels_like_unit}\n'
                    f'{feels_like_day_label} {feels_like_day} {feels_like_unit}\n'
                    f'{feels_like_eve_label} {feels_like_eve} {feels_like_unit}\n'
                    f'{feels_like_night_label} {feels_like_night} {feels_like_unit}\n'
                    '―――――'
                )
                if not tomorrow_collected:
                    self.tomorrow_notification_text += f'{self.feels_like_translated}: {feels_like_day} {feels_like_unit}'
                    tomorrow_collected = True

            if element.tag == 'precipitation':

                try:
                    # Take the label translated text and remove the html tags
                    self.doc.setHtml(self.precipitation_label.text())
                    precipitation_label = f'{self.doc.toPlainText()}: '
                    precipitation_type = element.get('type')
                    precipitation_type = (
                        f'{self.precipitation[precipitation_type]} '
                    )
                    precipitation_value = element.get('value')
                    rain_unit = ' mm'
                    if self.unit_system == ' mph ':
                        rain_unit = ' inch'
                        precipitation_value = (
                            f'{str(float(precipitation_value) / 25.4)} '
                        )
                        precipitation_value = (
                            "{0:.2f}".format(float(precipitation_value))
                        )
                    else:
                        precipitation_value = (
                            "{0:.1f}".format(float(precipitation_value))
                        )
                    weather_cond += (
                        '\n{0}{1}{2}{3}'.format(
                            precipitation_label,
                            precipitation_type,
                            precipitation_value,
                            rain_unit
                        )
                    )
                except Exception:
                    pass

            if element.tag == 'windDirection':
                self.doc.setHtml(self.wind_label.text())
                wind = f'{self.doc.toPlainText()}: '
                try:
                    wind_direction = (
                        self.wind_direction[element.get('code')]
                    )
                except KeyError:
                    wind_direction = ''

            if element.tag == 'windSpeed':
                wind_speed = (
                    '{0:.1f}'.format(float(element.get('mps')))
                )
                if self.bft_bool:
                    wind_speed = str(self.convertToBeaufort(wind_speed))
                if self.wind_km_bool:
                    wind_speed = '{0:.1f}'.format(float(wind_speed) * 3.6)

                weather_cond += (
                    '\n{0}{1}{2}{3}'.format(
                        wind,
                        wind_speed,
                        self.unit_system_wind,
                        wind_direction
                    )
                )

            if element.tag == 'pressure':

                self.doc.setHtml(self.pressure_label.text())
                pressure_label = f'{self.doc.toPlainText()}: '
                pressure = (
                    '{0:.1f}'.format(
                        float(element.get('value'))
                    )
                )
                weather_cond += f'\n{pressure_label}{pressure} hPa'

            if element.tag == 'humidity':
                humidity = element.get('value')
                self.doc.setHtml(self.humidity_label.text())
                humidity_label = f'{self.doc.toPlainText()}: '
                weather_cond += f'\n{humidity_label}{humidity} %'

            if element.tag == 'clouds':
                clouds = element.get('all')
                self.doc.setHtml(self.clouds_label.text())
                clouds_label = f'{self.doc.toPlainText()}: '
                weather_cond += f'\n{clouds_label}{clouds} %'
                weather_end = True

            if weather_end is True:
                self.forecast_weather_list.append(weather_cond)
                weather_end = False

    def forecastdata(self):
        '''Forecast for the next 4 days'''
        self.clearLayout(self.forecast_minmax_layout)
        self.clearLayout(self.forecast_days_layout)
        self.find_min_max()
        weather_end = False
        collate_info = False
        t_unit = {'celsius': '°C', 'fahrenheit': '°F', 'kelvin': '°K'}
        t_air = ''

        tomorrow_collected = False
        self.tomorrow_notification_text = ""
        self.tomorrow_notification_text += self.tomorrow_translation + '\n'
        trans_cities = self.settings.value('CitiesTranslation') or '{}'
        trans_cities_dict = eval(trans_cities)
        city = f'{self.city}_{self.country}_{self.id_}'
        city_name = self.city
        if city in trans_cities_dict:
            city_name = trans_cities_dict[city]
        self.tomorrow_notification_text += city_name + '\n'

        if not self.json_data_bool:
            for element in self.dayforecast_data.iter():
                # Find the day for the forecast (today+1) at 12:00:00
                if element.tag == 'time':
                    date_list = element.get('from').split('-')
                    date_list_time = date_list[2].split('T')
                    date_list[2] = date_list_time[0]
                    date_list.append(date_list_time[1])
                    if (
                        datetime.datetime.now().day == int(date_list[2])
                        or date_list[3] != '12:00:00'
                    ):
                        collate_info = False
                        continue
                    else:
                        collate_info = True
                    day_of_week = str(
                        datetime.date(
                            int(date_list[0]),
                            int(date_list[1]),
                            int(date_list[2])
                        ).weekday()
                    )

                    label = QLabel(f'{self.days_dico[day_of_week]}')
                    label.setToolTip('-'.join(i for i in date_list[:3]))
                    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                    self.forecast_days_layout.addWidget(label)
                    temp_min = min(self.date_temp_forecast[date_list[2]])
                    temp_max = max(self.date_temp_forecast[date_list[2]])
                    mlabel = QLabel(
                        '<font color=>{0}°<br/>{1}°</font>'.format(
                            '{0:.0f}'.format(temp_min),
                            '{0:.0f}'.format(temp_max)
                        )
                    )
                    mlabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                    mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
                    self.forecast_minmax_layout.addWidget(mlabel)

                if element.tag == 'symbol' and collate_info:
                    # icon
                    self.icon_list.append(element.get('var'))
                    weather_cond = element.get('name')
                    try:
                        weather_cond = (
                            self.conditions[
                                element.get('number')
                            ]
                        )
                    except Exception:
                        logging.warning(
                            f'Cannot find localisation string for: {weather_cond}'
                        )
                        pass

                    if not tomorrow_collected:
                        self.tomorrow_notification_text += weather_cond + ' '

                if element.tag == 'precipitation' and collate_info:
                    precipitation = int(float(element.get('probability')) * 100)
                    weather_cond += (
                        '\n{0} {1}%'.format(
                            self.precipitation_probability_str,
                            precipitation
                        )
                    )

                    self.doc.setHtml(self.wind_label.text())
                    wind = f'{self.doc.toPlainText()}: '

                if element.tag == 'windDirection' and collate_info:
                    try:
                        wind_direction = (
                            self.wind_direction[
                                element.get('code')
                            ]
                        )
                    except Exception:
                        wind_direction = ''

                if element.tag == 'windSpeed' and collate_info:
                    wind_speed = (
                        '{0:.1f}'.format(
                            float(element.get('mps'))
                        )
                    )
                    if self.bft_bool:
                        wind_speed = str(self.convertToBeaufort(wind_speed))
                    if self.wind_km_bool:
                        wind_speed = '{0:.1f}'.format(float(wind_speed) * 3.6)
                    weather_cond += (
                        '\n{0}{1}{2}{3}'.format(
                            wind,
                            wind_speed,
                            self.unit_system_wind,
                            wind_direction
                        )
                    )

                if element.tag == 'temperature' and collate_info:
                    t_air = element.get('value')
                    if not tomorrow_collected:
                        self.tomorrow_notification_text += f'{t_air} {t_unit[element.get("unit")]}\n'

                if element.tag == 'feels_like' and collate_info:
                    feels_like_value = element.get('value')
                    feels_like_unit = t_unit[element.get('unit')]
                    weather_cond += f'\n{self.feels_like_translated}: {feels_like_value} {feels_like_unit}'
                    if not tomorrow_collected:
                        self.tomorrow_notification_text += f'{self.feels_like_translated}: {feels_like_value} {feels_like_unit}'
                        tomorrow_collected = True

                if element.tag == 'pressure' and collate_info:
                    self.doc.setHtml(self.pressure_label.text())
                    pressure_label = f'{self.doc.toPlainText()}: '
                    pressure = (
                        '{0:.1f}'.format(
                            float(
                                element.get('value')
                            )
                        )
                    )
                    weather_cond += f'\n{pressure_label}{pressure} hPa'

                if element.tag == 'humidity' and collate_info:
                    humidity = element.get('value')
                    self.doc.setHtml(self.humidity_label.text())
                    humidity_label = f'{self.doc.toPlainText()}: '
                    weather_cond += f'\n{humidity_label}{humidity} %'
                    if t_air != '':
                        t_air = float('{0:.1f}'.format(float(t_air)))
                        hum = humidex.Humidex(
                            t_air=t_air,
                            rel_humidity=int(humidity),
                            unit=self.unit_temp
                        )
                        self.doc.setHtml(self.dew_point_label.text())
                        weather_cond += f'\n{self.doc.toPlainText()}: {hum.dew_point} {self.unit_temp}'
                        self.doc.setHtml(self.comfort_label.text())
                        weather_cond += f'\n{self.doc.toPlainText()}: {hum.comfort_text}'

                if element.tag == 'clouds' and collate_info:
                    clouds = element.get('all')
                    self.doc.setHtml(self.clouds_label.text())
                    weather_cond += f'\n{self.doc.toPlainText()}: {clouds} %'
                    weather_end = True

                if weather_end is True:
                    self.forecast_weather_list.append(weather_cond)
                    weather_end = False
        else:
            for tag in self.dayforecast_data['list']:
                day = tag.get('dt_txt')
                day = int(day.split(' ')[0].split('-')[-1])
                if (
                    tag.get('dt_txt').count('12:00:00') == 0
                    or day == datetime.datetime.now().day
                ):
                    continue
                else:
                    date_list = tag.get('dt_txt').split(' ')[0].split('-')
                    day_of_week = str(datetime.date(
                        int(date_list[0]),
                        int(date_list[1]),
                        int(date_list[2])
                    ).weekday())
                    label = QLabel(f'{self.days_dico[day_of_week]}')
                    label.setToolTip('-'.join(i for i in date_list[:3]))
                    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                    self.forecast_days_layout.addWidget(label)
                    temp_min = min(self.date_temp_forecast[date_list[2]])
                    temp_max = max(self.date_temp_forecast[date_list[2]])
                    mlabel = QLabel(
                        '<font color=>{0}°<br/>{1}°</font>'.format(
                            '{0:.0f}'.format(temp_min),
                            '{0:.0f}'.format(temp_max)
                        )
                    )
                    mlabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                    mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
                    self.forecast_minmax_layout.addWidget(mlabel)

                    # icon
                    self.icon_list.append(tag['weather'][0]['icon'])
                    weather_cond = tag['weather'][0]['description']
                    try:
                        weather_cond = (
                            self.conditions[
                                str(tag['weather'][0]['id'])
                            ]
                        )
                    except Exception:
                        logging.warning(
                            f'Cannot find localisation string for: {weather_cond}'
                        )
                        pass

                    self.doc.setHtml(self.wind_label.text())
                    wind = f'{self.doc.toPlainText()}: '

                    try:
                        wind_direction = (
                            self.wind_direction[
                                element.get('code')
                            ]
                        )
                    except Exception:
                        wind_direction = ''

                    wind_speed = (
                        '{0:.1f}'.format(
                            float(tag['wind']['speed'])
                        )
                    )
                    if self.bft_bool:
                        wind_speed = str(self.convertToBeaufort(wind_speed))
                    if self.wind_km_bool:
                        wind_speed = '{0:.1f}'.format(float(wind_speed) * 3.6)
                    weather_cond += (
                        '\n{0}{1}{2}{3}'.format(
                            wind,
                            wind_speed,
                            self.unit_system_wind,
                            wind_direction
                        )
                    )
                    t_air = tag['main']['temp']
                    feels_like_value = tag['main']['feels_like']
                    weather_cond += f'\n{self.feels_like_translated}: {feels_like_value} {self.unit_temp}'

                    self.doc.setHtml(self.pressure_label.text())
                    pressure_label = f'{self.doc.toPlainText()}: '
                    pressure = tag['main']['pressure']
                    weather_cond += f'\n{pressure_label}{pressure} hPa'

                    humidity = tag['main']['humidity']
                    self.doc.setHtml(self.humidity_label.text())
                    humidity_label = f'{self.doc.toPlainText()}: '
                    weather_cond += f'\n{humidity_label}{humidity} %'
                    if t_air != '':
                        t_air = float('{0:.1f}'.format(float(t_air)))
                        hum = humidex.Humidex(
                            t_air=t_air,
                            rel_humidity=int(humidity),
                            unit=self.unit_temp
                        )
                        self.doc.setHtml(self.dew_point_label.text())
                        weather_cond += f'\n{self.doc.toPlainText()}: {hum.dew_point} {self.unit_temp}'
                        self.doc.setHtml(self.comfort_label.text())
                        weather_cond += f'\n{self.doc.toPlainText()}: {hum.comfort_text}'

                    clouds = tag['clouds']['all']
                    self.doc.setHtml(self.clouds_label.text())
                    weather_cond += f'\n{self.doc.toPlainText()}: {clouds} %'
                    weather_end = True
                    self.forecast_weather_list.append(weather_cond)

    def iconfetch(self):
        '''Get icons for the next days forecast'''
        self.clearLayout(self.forecast_icons_layout)
        logging.debug('Download forecast icons...')
        self.download_thread = (
            IconDownload(self.forecast_icon_url, self.icon_list)
        )
        self.download_thread.wimage.connect(self.iconwidget)
        self.download_thread.url_error_signal.connect(self.errorIconFetch)
        self.download_thread.start()

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def iconwidget(self, icon):
        '''Next days forecast icons'''
        def make_icon(data):
            image = QImage()
            image.loadFromData(data)
            return QPixmap(image)

        icon_data = icon[0]
        icon_name = icon[1]
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.system_icons = self.settings.value('IconsTheme') or 'System default'
        if self.system_icons != 'OpenWeatherMap':
            if self.system_icons != 'System default':
                QIcon.setThemeName(self.system_icons)
            for icon in self.system_icons_dico[icon_name]:
                image = QIcon.fromTheme(icon)
                if image.name() == '':
                    logging.warning(
                        f"The icon {icon} for the openweathermap icon {icon_name} "
                        f"doesn't exist in the system icons theme '{QIcon.themeName()}'"
                    )
                    iconpixmap = make_icon(icon_data)
                else:
                    iconpixmap = image.pixmap(QSize(50, 50))
                    break
        else:
            iconpixmap = make_icon(icon_data)

        shadow = self.shadow_effect()
        iconlabel.setGraphicsEffect(shadow)
        iconlabel.setPixmap(iconpixmap)

        try:
            iconlabel.setToolTip(self.forecast_weather_list.pop(0))
            self.forecast_icons_layout.addWidget(iconlabel)
        except IndexError as error:
            logging.error(f'{str(error)} forecast_weather_list')
            return

    def dayforecastdata(self):
        '''Fetch forecast for the day'''
        self.clearLayout(self.dayforecast_temp_layout)
        periods = 6
        start = 0
        if not self.json_data_bool:
            start = 1
            periods = 7
            fetched_file_periods = (len(self.dayforecast_data.xpath('//time')))
            # Some times server sends less data
            if fetched_file_periods < periods:
                periods = fetched_file_periods
                logging.warning(
                    'Reduce forecast of the day to {0}'.format(periods - 1)
                )
        feels_like_unit_dic = {'celsius': '°C', 'fahrenheit': '°F', 'kelvin': '°K'}
        for d in range(start, periods):
            clouds_translated = ''
            wind = ''
            timeofday = self.utc(d, 'dayforecast')
            if not self.json_data_bool:
                for element in self.dayforecast_data[4][d].iter():
                    if element.tag == 'symbol':
                        weather_cond = self.conditions[
                            element.get('number')
                        ]
                        self.dayforecast_icon_list.append(
                            element.get('var')
                        )
                    if element.tag == 'temperature':
                        temperature_at_hour = float(
                            element.get('value')
                        )
                    if element.tag == 'feels_like':
                        feels_like_value = element.get('value')
                        feels_like_unit = feels_like_unit_dic[element.get('unit')]
                    if element.tag == 'precipitation':
                        precipitation = int(float(element.get('probability')) * 100)
                    if element.tag == 'windDirection':
                        winddircode = element.get('code')
                    if element.tag == 'windSpeed':
                        windspeed = element.get('mps')
                        wind_name = element.get('name')
                        try:
                            wind_name_translated = (
                                f'{self.conditions[self.wind_name_dic[wind_name.lower()]]}<br/>'
                            )
                            wind += wind_name_translated
                        except KeyError:
                            logging.warning(f'Cannot find wind name: {str(wind_name)}')
                            logging.info('Set wind name to None')
                            wind = ''
                        finally:
                            if wind == '':
                                wind += '<br/>'
                    if element.tag == 'pressure':
                        pressure = element.get('value')
                    if element.tag == 'humidity':
                        humidity = element.get('value')
                    if element.tag == 'clouds':
                        clouds = element.get('value')
                        cloudspercent = element.get('all')
            else:
                weather_cond = self.conditions[
                    str(self.dayforecast_data['list'][d]['weather'][0]['id'])
                ]
                self.dayforecast_icon_list.append(
                    self.dayforecast_data['list'][d]['weather'][0]['icon']
                )
                temperature_at_hour = float(
                    self.dayforecast_data['list'][d]['main']['temp']
                )
                feels_like_value = self.dayforecast_data['list'][d]['main']['feels_like']
                feels_like_unit = self.unit_temp
                precipitation_orig = self.dayforecast_data['list'][d]
                precipitation_rain = precipitation_orig.get('rain', None)
                precipitation_snow = precipitation_orig.get('snow', None)
                if (
                    precipitation_rain is not None
                    and len(precipitation_rain) > 0
                ):
                    precipitation = str(precipitation_rain['3h'])
                elif (
                    precipitation_snow is not None
                    and len(precipitation_snow) > 0
                ):
                    precipitation = str(precipitation_snow['3h'])
                else:
                    precipitation = 'None'
                windspeed = self.dayforecast_data['list'][d]['wind']['speed']
                winddircode = (
                    self.winddir_json_code(
                        self.dayforecast_data['list'][d]['wind'].get('deg')
                    )
                )
                clouds = (
                    self.dayforecast_data['list']
                    [d]['weather'][0]['description']
                )
                cloudspercent = (
                    self.dayforecast_data['list'][0]['clouds']['all']
                )
                pressure = self.dayforecast_data['list'][d]['main']['pressure']
                humidity = self.dayforecast_data['list'][d]['main']['humidity']

            self.dayforecast_weather_list.append(weather_cond)
            daytime = QLabel(
                '<font color=>{0}<br/>{1}°</font>'.format(
                    timeofday[:-3],
                    '{0:.0f}'.format(temperature_at_hour)
                )
            )
            daytime.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            ttip = (
                f'{self.feels_like_translated} '
                f'{feels_like_value} {feels_like_unit}'
                '<br/>'
            )
            ttip_prec = (
                f'{self.precipitation_probability_str} {precipitation}%<br/>'
            )
            ttip += ttip_prec
            if self.bft_bool is True:
                windspeed = self.convertToBeaufort(windspeed)
            if self.wind_km_bool:
                windspeed = '{0:.1f}'.format(float(windspeed) * 3.6)
            ttip += f'{str(windspeed)} {self.unit_system_wind}'
            if winddircode != '':
                wind = f'{self.wind_direction[winddircode]} '
            else:
                logging.warning(
                    'Wind direction code is missing: {}'.format(
                        str(winddircode)
                    )
                )
            if clouds != '':
                try:
                    # In JSON there is no clouds description
                    clouds_translated = (
                        self.conditions[self.clouds_name_dic[clouds.lower()]]
                    )
                except KeyError:
                    self.doc.setHtml(self.clouds_label.text())
                    clouds_translated = self.doc.toPlainText()
            else:
                logging.warning(f'Clouding name is missing: {str(clouds)}')
            clouds_cond = f'{clouds_translated} {str(cloudspercent)}%'
            ttip += f'{wind}<br/>{clouds_cond}<br/>'
            pressure_local = QCoreApplication.translate(
                'Tootltip forcast of the day',
                'Pressure',
                'Weather info window'
            )
            humidity_local = QCoreApplication.translate(
                'Tootltip forcast of the day',
                'Humidity',
                'Weather info window'
            )
            ttip += f'{pressure_local} {pressure}  hPa<br/>'
            ttip += f'{humidity_local} {humidity} %'
            daytime.setToolTip(ttip)
            self.dayforecast_temp_layout.addWidget(daytime)

    def uv_fetch(self):
        logging.debug('Download uv info...')
        self.uv_thread = Uv(self.uv_coord)
        self.uv_thread.uv_signal.connect(self.uv_index)
        self.uv_thread.air_pollution_signal.connect(self.air_pollution)
        self.uv_thread.start()

    def air_pollution(self, data):
        aqi = data[0]['main']['aqi']
        values = data[0]['components']
        self.air_pollution_value_label.setText(self.aqi[aqi])
        self.air_pollution_value_label.setToolTip(
            '\n'.join(f'{key}: {value}' for key, value in values.items())
        )

    def uv_index(self, index):
        uv_gauge = '-'
        uv_color = self.uv_color(index)
        self.uv_index_exp = f"{index} {uv_color[1]}"
        if uv_color[1] != 'None':
            uv_gauge = '◼' * int(round(float(index)))
            if uv_gauge == '':
                uv_gauge = '◼'
            self.uv_value_label.setText(
                '<font color=>{0} {1}</font><br/><font color={2}><b>{3}</b></font>'.format(
                    '{0:.1f}'.format(float(index)),
                    self.uv_risk[uv_color[1]],
                    uv_color[0],
                    uv_gauge
                )
            )
        else:
            self.uv_value_label.setText(f'<font color=>{uv_gauge}</font>')
        logging.debug(f'UV gauge ◼: {uv_gauge}')
        self.uv_value_label.setToolTip(self.uv_recommend[uv_color[1]])
        if uv_gauge == '-':
            self.uv_label.hide()
            self.uv_value_label.hide()
        else:
            self.uv_label.show()
            self.uv_value_label.show()

    def dayiconfetch(self):
        '''Icons for the forecast of the day'''
        self.clearLayout(self.dayforecast_layout)
        logging.debug('Download forecast icons for the day...')
        self.day_download_thread = IconDownload(
            self.forecast_icon_url, self.dayforecast_icon_list
        )
        self.day_download_thread.wimage['PyQt_PyObject'].connect(self.dayiconwidget)
        self.day_download_thread.url_error_signal['QString'].connect(self.errorIconFetch)
        self.day_download_thread.start()

    def dayiconwidget(self, icon):
        '''Forecast icons of the day'''
        def make_icon(data):
            image = QImage()
            image.loadFromData(data)
            return QPixmap(image)

        icon_data = icon[0]
        icon_name = icon[1]
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.system_icons = self.settings.value('IconsTheme') or 'System default'
        if self.system_icons != 'OpenWeatherMap':
            if self.system_icons != 'System default':
                QIcon.setThemeName(self.system_icons)
            for icon in self.system_icons_dico[icon_name]:
                image = QIcon.fromTheme(icon)
                if image.name() == '':
                    logging.warning(
                        f"The icon {icon} for the openweathermap icon {icon_name} "
                        f"doesn't exist in the system icons theme '{QIcon.themeName()}'"
                    )
                    iconpixmap = make_icon(icon_data)
                else:
                    iconpixmap = image.pixmap(QSize(50, 50))
                    break
        else:
            iconpixmap = make_icon(icon_data)

        shadow = self.shadow_effect()
        iconlabel.setGraphicsEffect(shadow)
        iconlabel.setPixmap(iconpixmap)

        try:
            iconlabel.setToolTip(self.dayforecast_weather_list.pop(0))
            self.dayforecast_layout.addWidget(iconlabel)
        except IndexError as error:
            logging.error(f'{str(error)} dayforecast_weather_list')

    def moveEvent(self, event):
        self.settings.setValue("MainWindow/Geometry", self.saveGeometry())

    def resizeEvent(self, event):
        self.settings.setValue("MainWindow/Geometry", self.saveGeometry())

    def hideEvent(self, event):
        self.settings.setValue("MainWindow/Geometry", self.saveGeometry())

    def errorIconFetch(self, error):
        logging.error(f'error in download of forecast icon:\n{error}')

    def icon_loading(self):
        self.gif_loading = QMovie(":/loading")
        self.gif_loading.frameChanged.connect(self.update_gif)
        self.gif_loading.start()

    def update_gif(self):
        gif_frame = self.gif_loading.currentPixmap()
        self.systray.setIcon(QIcon(gif_frame))

    def icon_city_loading(self):
        self.city_label.setText('▉')
        self.cityChangeTimer.start(20)

    def update_city_gif(self):
        current = self.city_label.text()
        current += '▌'
        if len(current) > 35:
            current = '▉'
        self.city_label.setText(current)

    def manual_refresh(self):
        self.tentatives = 0
        self.refresh()

    def wheelEvent(self, event):
        if hasattr(self, 'day_download_thread'):
            if self.day_download_thread.isRunning():
                logging.debug(
                    'WheelEvent: Downloading icons - remaining thread "day_download_thread"...'
                )
                return
        if hasattr(self, 'download_thread'):
            if self.download_thread.isRunning():
                logging.debug(
                    'WheelEvent: Downloading icons - remaining thread "download_thread"...'
                )
                return

        self.icon_city_loading()
        cities = eval(self.settings.value('CityList') or [])
        if len(cities) == 0:
            return
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        direction = event.angleDelta().y()
        actual_city = self.current_city_display
        for key, value in cities_trans_dict.items():
            if self.current_city_display == key:
                actual_city = key
        if actual_city not in cities:
            cities.append(actual_city)
        current_city_index = cities.index(actual_city)

        if direction > 0:
            current_city_index += 1
            if current_city_index >= len(cities):
                current_city_index = 0
        else:
            current_city_index -= 1
            if current_city_index < 0:
                current_city_index = len(cities) - 1
        self.current_city_display = cities[current_city_index]
        self.city, self.country, self.id_ = self.current_city_display.split('_')
        self.timer.singleShot(500, self.refresh)

    def cities_menu(self):
        self.citiesMenu.clear()
        cities = self.settings.value('CityList') or []
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        if type(cities) is str:
            cities = eval(cities)

        # If we delete all cities it results to a '__'
        if (
            cities is not None
            and cities != ''
            and cities != '[]'
            and cities != ['__']
        ):
            if type(cities) is not list:
                # FIXME sometimes the list of cities is read as a string (?)
                # eval to a list
                cities = eval(cities)
            # Create the cities list menu
            for city in cities:
                if city in cities_trans_dict:
                    city = cities_trans_dict[city]
                action = QAction(city, self)
                action.triggered.connect(partial(self.changecity, city))
                self.citiesMenu.addAction(action)
        else:
            self.empty_cities_list()

    @pyqtSlot(str)
    def changecity(self, city):
        if hasattr(self, 'city_label'):
            self.icon_city_loading()
        cities_list = self.settings.value('CityList')
        cities_list = eval(cities_list)
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        self.cities_trans_dict = eval(cities_trans)
        logging.debug(f'Cities {str(cities_list)}')
        if cities_list is None:
            self.empty_cities_list()
        for town in cities_list:
            if town == self.find_city_key(city):
                ind = cities_list.index(town)
                self.current_city_display = cities_list[ind]
        self.refresh()

    def find_city_key(self, city):
        for key, value in self.cities_trans_dict.items():
            if value == city:
                return key
        return city

    def empty_cities_list(self):
        self.citiesMenu.addAction(self.tr('Empty list'))

    def refresh(self):
        logging.debug('-------- START ---------')

        if (
            hasattr(self, 'overviewcitydlg')
            and not self.cityChangeTimer.isActive()
        ):
            self.icon_city_loading()
        self.inerror = False
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip(self.tr('Fetching weather data...'))
        if self.id_ == '':
            # Clear the menu, no cities configured
            self.citiesMenu.clear()
            self.empty_cities_list()
            self.timer.singleShot(2000, self.firsttime)
            self.id_ = ''
            self.systray.setToolTip(self.tr('No city configured'))
            return
        self.city, self.country, self.id_ = self.current_city_display.split('_')
        logging.debug(self.current_city_display)
        self.unit = self.settings.value('Unit') or 'metric'
        self.wind_unit_speed = self.settings.value('Wind_unit') or 'df'
        self.suffix = f'&mode=xml&units={self.unit}{self.appid}'
        self.interval = int(self.settings.value('Interval') or 30) * 60 * 1000
        self.timer.start(self.interval)
        self.update()

    def firsttime(self):
        self.temp = ''
        self.wIcon = QPixmap(':/noicon')
        self.systray.showMessage(
            'meteo-qt:\n',
            '{0}\n{1}'.format(
                self.tr('No city has been configured yet.'),
                self.tr('Right click on the icon and click on Settings.')
            )
        )

    def update(self):
        if hasattr(self, 'downloadThread'):
            if self.downloadThread.isRunning():
                logging.debug('Update: remaining thread, canceling...')
                return
        logging.debug('Updating...')
        self.icon_loading()
        self.wIcon = QPixmap(':/noicon')
        self.downloadThread = Download(
            self.wIconUrl,
            self.baseurl,
            self.day_forecast_url,
            self.forecast6_url,
            self.id_,
            self.suffix,
        )
        self.alertsAction.setEnabled(False)
        self.alert_event = ''
        self.alerts_cycle = 0
        self.alert_json = ''
        self.alerts_timer.stop()
        self.alerts_dlg.textBrowser.clear()
        self.downloadThread.wimage['PyQt_PyObject'].connect(self.makeicon)
        self.downloadThread.weather_icon_signal.connect(self.weather_icon_name_set)
        self.downloadThread.finished.connect(self.tray)
        self.downloadThread.xmlpage['PyQt_PyObject'].connect(self.weatherdata)
        self.downloadThread.day_forecast_rawpage.connect(self.dayforecast)
        self.forcast6daysBool = False
        self.downloadThread.forecast6_rawpage.connect(self.forecast6)
        self.downloadThread.uv_signal.connect(self.uv)
        self.downloadThread.error.connect(self.error)
        self.downloadThread.done.connect(self.done)
        self.downloadThread.alerts_signal.connect(self.alert_received)
        self.downloadThread.start()

    def alert_received(self, alert_json):
        self.alert_json = alert_json
        if len(alert_json) > 0:
            self.alerts_timer.start(3000)
        self.alertsAction.setEnabled(True)
        for i in range(len(alert_json)):
            alert_json[i]['start'] = datetime.datetime.utcfromtimestamp(
                alert_json[i]['start']
            ).strftime('%Y-%m-%d %H:%M:%S')
            alert_json[i]['end'] = datetime.datetime.utcfromtimestamp(
                alert_json[i]['end']
            ).strftime('%Y-%m-%d %H:%M:%S')
        self.alerts_dlg.show_alert(self.alert_json)
        self.alert_message()

    def alert_message(self):
        total = ''
        if len(self.alert_json) > 1:
            total = f' {self.alerts_cycle + 1}/{len(self.alert_json)}'
        event_message = self.alert_json[self.alerts_cycle]['event'].lower().replace('warning', '')
        self.alert_event = f"⚠ {event_message}{total}"

    def next_alert_event(self):
        self.alerts_cycle += 1
        if self.alerts_cycle == len(self.alert_json):
            self.alerts_cycle = 0
        self.alert_message()
        self.overviewcity_weather_label()

    def uv(self, value):
        self.uv_coord = value

    def forecast6(self, data):
        self.forcast6daysBool = True
        self.forecast6_data = data

    def dayforecast(self, data):
        if type(data) == dict:
            self.json_data_bool = True
        else:
            self.json_data_bool = False
        self.dayforecast_data = data

    def done(self, done):
        self.cityChangeTimer.stop()
        if done == 0:
            self.inerror = False
        elif done == 1:
            self.inerror = True
            logging.debug('Trying to retrieve data...')
            self.timer.singleShot(10000, self.try_again)
            return
        if hasattr(self, 'dayforecast_data'):
            self.overviewcity()
            return
        else:
            self.try_again()

    def try_again(self):
        self.nodata_message()
        logging.debug(f'Attempts: {str(self.tentatives)}')
        self.tentatives += 1
        self.timer.singleShot(5000, self.refresh)

    def nodata_message(self):
        nodata = QCoreApplication.translate(
            "Tray icon",
            "Searching for weather data...",
            "Tooltip (when mouse over the icon"
        )
        self.systray.setToolTip(nodata)
        self.notification = nodata

    def error(self, error):
        logging.error(f'Error:\n{str(error)}')
        self.nodata_message()
        self.timer.start(self.interval)
        self.inerror = True

    def weather_icon_name_set(self, iconname):
        self.weather_icon_name = iconname

    def makeicon(self, data):
        def make_icon(data):
            image = QImage()
            image.loadFromData(data)
            self.wIcon = QPixmap(image)
        self.system_icons = self.settings.value('IconsTheme') or 'System default'
        if self.system_icons != 'OpenWeatherMap':
            if self.system_icons != 'System default':
                QIcon.setThemeName(self.system_icons)
            for icon in self.system_icons_dico[self.weather_icon_name]:
                image = QIcon.fromTheme(icon)
                if image.name() == '':
                    logging.warning(
                        f"The icon {icon} for the openweathermap icon {self.weather_icon_name} "
                        f"doesn't exist in the system icons theme '{QIcon.themeName()}'"
                    )
                    make_icon(data)
                else:
                    self.wIcon = image.pixmap(QSize(50, 50))
                    break
        else:
            make_icon(data)

    def weatherdata(self, tree):
        if self.inerror:
            return
        t_unit = {'celsius': '°C', 'fahrenheit': '°F', 'kelvin': '°K'}
        for element in tree.iter():

            if element.tag == 'sun':
                self.weatherDataDico['Sunrise'] = element.get('rise')
                self.weatherDataDico['Sunset'] = element.get('set')

            if element.tag == 'temperature':
                self.tempFloat = element.get('value')
                self.temp = f' {str(round(float(self.tempFloat)))}°'
                self.temp_decimal = (
                    '{}°'.format(
                        '{0:.1f}'.format(float(self.tempFloat))
                    )
                )

            if element.tag == 'weather':
                self.meteo = element.get('value')
                meteo_condition = element.get('number')
                try:
                    self.meteo = self.conditions[meteo_condition]
                except KeyError:
                    logging.debug(
                        'Cannot find localisation string for'
                        ' meteo_condition:'
                        f'{str(meteo_condition)}'
                    )
                    pass

            if element.tag == 'clouds':
                clouds = element.get('name')
                clouds_percent = element.get('value') + '%'
                try:
                    clouds = self.clouds[clouds]
                    clouds = self.conditions[clouds]
                except KeyError:
                    logging.debug(
                        f'Cannot find localisation string for clouds: {str(clouds)}'
                    )
                    pass

            if element.tag == 'speed':
                wind_value = element.get('value')
                wind = element.get('name').lower()
                try:
                    wind = self.wind[wind]
                    wind = self.conditions[wind]
                except KeyError:
                    logging.debug(
                        f'Cannot find localisation string for wind:{str(wind)}'
                    )
                    pass

            if element.tag == 'direction':
                wind_codes_english = element.get('code')
                wind_dir_value = element.get('value')
                wind_dir = element.get('name')

                try:
                    wind_dir_value = str(int(float(wind_dir_value)))
                except TypeError:
                    wind_dir_value = ''

                try:
                    wind_codes = self.wind_codes[wind_codes_english]
                except (KeyError, UnboundLocalError):
                    logging.debug(
                        f'Cannot find localisation string for wind_codes: {str(wind_codes_english)}'
                    )
                    wind_codes = wind_codes_english

                if wind_codes is None:
                    wind_codes = ''

                try:
                    wind_dir = self.wind_dir[wind_codes_english]
                except KeyError:
                    logging.debug(
                        f'Cannot find localisation string for wind_dir: {str(wind_dir)}'
                    )
                    if wind_dir is None:
                        wind_dir = ''

            if element.tag == 'humidity':
                self.weatherDataDico['Humidity'] = (
                    element.get('value'), element.get('unit')
                )

            if element.tag == 'pressure':
                self.weatherDataDico['Pressure'] = (
                    element.get('value'), element.get('unit')
                )

            if element.tag == 'visibility':
                self.weatherDataDico['Visibility'] = element.get('value')

            if element.tag == 'precipitation':
                rain_mode = element.get('mode')
                rain_value = element.get('value')
                if rain_value is None:
                    rain_value = ''
                self.weatherDataDico['Precipitation'] = (
                    rain_mode, rain_value
                )

            if element.tag == 'feels_like':
                self.weatherDataDico['Feels_like'] = [element.get('value'), t_unit[element.get('unit')]]

        self.city_weather_info = (
            '{0} {1} {2} {3}'.format(
                self.city,
                self.country,
                self.temp_decimal,
                self.meteo
            )
        )
        self.tooltip_weather()
        self.notification = self.city_weather_info
        self.weatherDataDico['Id'] = self.id_
        self.weatherDataDico['City'] = self.city
        self.weatherDataDico['Country'] = self.country
        self.weatherDataDico['Temp'] = f'{self.tempFloat}°'
        self.weatherDataDico['Meteo'] = self.meteo

        self.weatherDataDico['Wind'] = (
            wind_value,
            wind,
            wind_dir_value,
            wind_codes,
            wind_dir
        )
        self.weatherDataDico['Clouds'] = (f'{clouds_percent} {clouds}')

        if self.id_ not in self.trendCities_dic:
            # dict {'id': ['hPa', , '',  'T°', 'temp_trend', 'weather changedBool']}
            self.trendCities_dic[self.id_] = [''] * 5
        # hPa trend
        pressure = float(self.weatherDataDico['Pressure'][0])
        if (
            self.id_ in self.trendCities_dic
            and self.trendCities_dic[self.id_][0] != ''
        ):
            self.hPaTrend = pressure - float(self.trendCities_dic[self.id_][0])
        else:
            self.hPaTrend = 0
        self.trendCities_dic[self.id_][0] = pressure
        # Temperature trend
        self.notifier()

    def notifier(self):
        ''' The notification is being shown:
        On a city change or first launch or if the temperature changes
        The notification is not shown if is turned off from the settings.
        The tray tooltip is set here '''
        temp = float(self.tempFloat)
        if (
            self.id_ in self.trendCities_dic
            and self.trendCities_dic[self.id_][2] != ''
        ):
            if temp > float(self.trendCities_dic[self.id_][2]):
                self.temp_trend = " ↗"
                self.trendCities_dic[self.id_][3] = self.temp_trend
            elif temp < float(self.trendCities_dic[self.id_][2]):
                self.temp_trend = " ↘"
                self.trendCities_dic[self.id_][3] = self.temp_trend
            else:
                self.temp_trend = self.trendCities_dic[self.id_][3]
            if temp == self.trendCities_dic[self.id_][2]:
                self.trendCities_dic[self.id_][4] = False
            else:
                self.trendCities_dic[self.id_][4] = True

        self.trendCities_dic[self.id_][2] = temp
        self.systray.setToolTip(
            self.city_weather_info.replace('<b>', '').replace('</b>', '')
            + self.temp_trend
        )

    def tooltip_weather(self):
        # Creation of the tray tootltip
        trans_cities = self.settings.value('CitiesTranslation') or '{}'
        trans_cities_dict = eval(trans_cities)
        city = f'{self.city}_{self.country}_{self.id_}'
        feels_like = (
            '{0} {1}'.format(
                self.feels_like_translated,
                ' '.join(fl for fl in self.weatherDataDico['Feels_like'])
            )
        )

        city_name = self.city
        if city in trans_cities_dict:
            city_name = trans_cities_dict[city]

        alert_event = ''
        if self.alert_event != '':
            alert_event = f'\n<b>{self.alert_event}</b>'

        self.city_weather_info = (
            '{0} {1} {2}{5}\n{3}\n{4}'.format(
                city_name,
                self.country,
                self.temp_decimal,
                feels_like,
                self.meteo,
                alert_event
            )
        )

    def tray(self):
        temp_decimal = eval(self.settings.value('Decimal') or 'False')
        try:
            if temp_decimal:
                temp_tray = self.temp_decimal
            else:
                temp_tray = self.temp
        except Exception:
            # First time launch
            return
        if self.inerror or not hasattr(self, 'temp'):
            logging.critical('Cannot paint icon!')
            return
        try:
            self.gif_loading.stop()
        except Exception:
            # In first time run the gif is not animated
            pass

        # Initialize the tray icon
        self.tray_icon_init_size = self.settings.value('Tray_icon_init_size') or '64x64'
        w_pix, h_pix = self.tray_icon_init_size.split('x')
        icon = QPixmap(int(w_pix), int(h_pix))
        icon.fill(QColorConstants.Transparent)
        self.traycolor = self.settings.value('TrayColor') or ''
        self.font_tray = self.settings.value('FontTray') or 'sans-serif'
        if not self.toggle_tray_bool:
            self.tray_type = self.settings.value('TrayType') or 'icon&temp'

        if self.tray_type == 'feels_like_temp' or self.tray_type == 'icon&feels_like':
            temp_tray = '{0:.0f}'.format(float(self.weatherDataDico['Feels_like'][0]))
            if temp_decimal:
                temp_tray = '{0:.1f}'.format(float(self.weatherDataDico['Feels_like'][0]))
            temp_tray += '°'
        # --- Paint icon ----------
        pt = QPainter()
        pt.begin(icon)
        if self.tray_type != 'temp' and self.tray_type != 'feels_like_temp':
            self.tray_icon_temp_pos = self.settings.value('Tray_icon_temp_position') or '-12'
            pt.drawPixmap(0, int(self.tray_icon_temp_pos), 64, 64, self.wIcon)
        ff = QFont()
        ff.fromString(self.font_tray)
        pt.setFont(ff)
        pt.setPen(QColor(self.traycolor))
        if self.tray_type == 'icon&temp' or self.tray_type == 'icon&feels_like':
            pt.drawText(
                icon.rect(),
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                str(temp_tray)
            )
        if self.tray_type == 'temp' or self.tray_type == 'feels_like_temp':
            pt.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, str(temp_tray))
        pt.end()
        # -------------------------------
        if self.tray_type == 'icon':
            self.systray.setIcon(QIcon(self.wIcon))
        else:
            self.systray.setIcon(QIcon(icon))
        # Don't show notifications when toggling the tray icon
        if self.notifier_settings() and not self.toggle_tray_action:
            try:
                if (
                    self.temp_trend != ''
                    or self.trendCities_dic[self.id_][1] == ''
                    or self.id_ != self.notifier_id
                ):
                    if not self.isVisible():
                        # Don't show the notification when window is open
                        # Show only if the temperature has changed
                        if (
                            self.trendCities_dic[self.id_][4] is True
                            or self.trendCities_dic[self.id_][4] == ''
                        ):
                            self.systray.showMessage(
                                'meteo-qt', f'{self.notification}{self.temp_trend}'
                            )
                            self.tomorrow_notification_timer.stop()
                            self.tomorrow_notification_timer.start(20000)
                            return
            except KeyError:
                return
        self.notifier_id = self.id_  # To always notify when city changes
        if self.temporary_city_status:
            self.restore_city()
        self.tentatives = 0
        self.tooltip_weather()
        if not self.toggle_tray_action:
            logging.info(f'Actual weather status for: {self.notification}')

    def tomorrow_tray_notification(self):
        self.systray.showMessage(
            'meteo-qt', f'{self.tomorrow_notification_text}'
        )
        self.tomorrow_notification_timer.stop()

    def notifier_settings(self):
        notifier = self.settings.value('Notifications') or 'True'
        notifier = eval(notifier)
        if notifier:
            return True
        else:
            return False

    def restore_city(self):
        self.city = self.settings.value('City') or ''
        self.country = self.settings.value('Country') or ''
        self.id_ = self.settings.value('ID') or ''
        self.current_city_display = f'{self.city}_{self.country}_{self.id_}'
        self.temporary_city_status = False

    def showpanel(self):
        self.activate(3)

    def activate(self, reason):
        # Option to start with the panel closed, true by defaut
        # starting with the panel open can be useful for users who don't have plasma
        # installed (to set keyboard shortcuts or other default window behaviours)
        start_minimized = self.settings.value('StartMinimized') or 'True'
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.inerror or self.id_ is None or self.id_ == '':
                return
            if self.isVisible() and start_minimized == 'True':
                self.hide()
            else:
                self.show()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.menu.popup(QCursor.pos())

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.settings.setValue("MainWindow/State", self.saveState())

    def config_save(self):
        logging.debug('Config saving...')
        city = self.settings.value('City')
        id_ = self.settings.value('ID')
        country = self.settings.value('Country')
        unit = self.settings.value('Unit')
        wind_unit_speed = self.settings.value('Wind_unit')
        traycolor = self.settings.value('TrayColor')
        tray_type = self.settings.value('TrayType')
        system_icons = self.settings.value('IconsTheme')
        font_tray = self.settings.value('FontTray')
        tray_icon_init_size = self.settings.value('Tray_icon_init_size')
        tray_icon_temp_pos = self.settings.value('Tray_icon_temp_position')
        language = self.settings.value('Language')
        decimal = self.settings.value('Decimal')
        toggle_tray_interval = self.settings.value('Toggle_tray_interval') or '0'
        toggle_tray_interval = int(toggle_tray_interval)
        self.appid = f'&APPID={self.settings.value("APPID")}' or ''
        if language != self.language and language is not None:
            self.systray.showMessage(
                'meteo-qt:',
                QCoreApplication.translate(
                    "System tray notification",
                    "The application has to be restarted to apply the language setting",
                    ''
                ),
                QSystemTrayIcon.MessageIcon.Warning
            )
            self.language = language

        # Check if update is needed
        toggle_tray = False
        if (
            self.toggle_tray_timer.interval() != toggle_tray_interval
            or self.tray_type_config != tray_type
        ):
            self.set_toggle_tray_interval()
            toggle_tray = True

        if traycolor is None:
            traycolor = ''
        if (
            self.traycolor != traycolor
            or self.tray_type != tray_type
            or self.font_tray != font_tray
            or decimal != self.temp_decimal_bool
            or toggle_tray
            or self.tray_icon_init_size != tray_icon_init_size
            or self.tray_icon_temp_pos != tray_icon_temp_pos
        ):
            self.tray()
        if (
            city == self.city
            and id_ == self.id_
            and country == self.country
            and unit == self.unit
            and wind_unit_speed == self.wind_unit_speed
            and system_icons == self.system_icons
        ):
            return
        else:
            logging.debug('Apply changes from settings...')
            self.city, self.country, self.id_ = city, country, id_
            self.current_city_display = f'{city}_{country}_{id_}'
            if system_icons != self.system_icons:
                if system_icons == 'System default':
                    # Apply the system default icons theme
                    self.system_icons = self.settings.value('SystemIcons')
                    QIcon.setThemeName(self.system_icons)
            self.refresh()

    def config(self):
        dialog = settings.MeteoSettings(self.accurate_url, self.appid, self)
        dialog.applied_signal.connect(self.config_save)
        if dialog.exec() == 1:
            self.config_save()
            logging.debug('Update Cities menu...')
            self.cities_menu()

    def tempcity(self):
        dialog = searchcity.SearchCity(self.accurate_url, self.appid, self)
        dialog.id_signal[tuple].connect(self.citydata)
        dialog.city_signal[tuple].connect(self.citydata)
        dialog.country_signal[tuple].connect(self.citydata)
        if dialog.exec():
            self.temporary_city_status = True
            self.current_city_display = f'{self.city}_{self.country}_{self.id_}'
            self.systray.setToolTip(self.tr('Fetching weather data...'))
            self.refresh()

    def citydata(self, what):
        if what[0] == 'City':
            self.city = what[1]
        elif what[0] == 'Country':
            self.country = what[1]
        elif what[0] == 'ID':
            self.id_ = what[1]

    def show_alert(self):
        self.alerts_dlg.show_alert(self.alert_json)
        self.alerts_dlg.show()

    def about(self):
        title = self.tr(
            """<b>meteo-qt</b> v{0}
            <br/>License: GPLv3
            <br/>Python {1} - Qt {2} - PyQt {3} on {4}"""
        ).format(
            __version__, platform.python_version(),
            QT_VERSION_STR, PYQT_VERSION_STR, platform.system()
        )
        image = ':/logo'
        text = self.tr(
            """<p>Author: Dimitrios Glentadakis
            <a href="mailto:dglent@free.fr">dglent@free.fr</a>
            <p>A simple application showing the weather status
            information on the system tray.
            <p>Website: <a href="https://github.com/dglent/meteo-qt">
            https://github.com/dglent/meteo-qt</a>
            <br/>Data source: <a href="http://openweathermap.org/">
            OpenWeatherMap</a>.
            <br/>This software uses icons from the
            <a href="http://www.kde.org/">Oxygen Project</a>.
            <p>To translate meteo-qt in your language or contribute to
            current translations, you can use the
            <a href="https://translate.lxqt-project.org/projects/dglent/meteo-qt/">
            Weblate</a> platform.
            <p>If you want to report a dysfunction or a suggestion,
            feel free to open an issue in
            <a href="https://github.com/dglent/meteo-qt/issues">
            github</a>."""
        )

        dialog = about_dlg.AboutDialog(title, text, image, self)
        dialog.exec()


class Download(QThread):
    wimage = pyqtSignal(['PyQt_PyObject'])
    weather_icon_signal = pyqtSignal(['QString'])
    xmlpage = pyqtSignal(['PyQt_PyObject'])
    forecast6_rawpage = pyqtSignal(['PyQt_PyObject'])
    day_forecast_rawpage = pyqtSignal(['PyQt_PyObject'])
    uv_signal = pyqtSignal(['PyQt_PyObject'])
    error = pyqtSignal(['QString'])
    done = pyqtSignal([int])
    alerts_signal = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, iconurl, baseurl, day_forecast_url, forecast6_url, id_,
                 suffix, parent=None):
        QThread.__init__(self, parent)
        self.wIconUrl = iconurl
        self.baseurl = baseurl
        self.day_forecast_url = day_forecast_url
        self.forecast6_url = forecast6_url
        self.id_ = id_
        self.suffix = suffix.replace(' ', '%20%')
        self.tentatives = 0
        self.settings = QSettings()

    def run(self):
        use_json_day_forecast = False
        use_proxy = self.settings.value('Proxy') or 'False'
        use_proxy = eval(use_proxy)
        proxy_auth = (
            self.settings.value('Use_proxy_authentification')
            or 'False'
        )
        proxy_auth = eval(proxy_auth)
        if use_proxy:
            proxy_url = self.settings.value('Proxy_url')
            proxy_port = self.settings.value('Proxy_port')
            proxy_tot = f'http://:{proxy_port}'
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    f'http://{proxy_user}:{proxy_password}@{proxy_url}:{proxy_port}'
                )
            proxy = urllib.request.ProxyHandler(
                {"http": proxy_tot}
            )
            auth = urllib.request.HTTPBasicAuthHandler()
            opener = urllib.request.build_opener(
                proxy, auth, urllib.request.HTTPHandler
            )
            urllib.request.install_opener(opener)
        else:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
        done = 0

        logging.debug(
            f'Fetching url for 6 days: {self.forecast6_url}{self.id_}{self.suffix}&cnt=7'
        )
        reqforecast6 = (
            f'{self.forecast6_url}{self.id_}{self.suffix}&cnt=7'
        )
        try:
            reqforecast6 = urllib.request.urlopen(
                f'{self.forecast6_url}{self.id_}{self.suffix}&cnt=7',
                timeout=10
            )
            pageforecast6 = reqforecast6.read()
            if str(pageforecast6).count('ClientError') > 0:
                raise TypeError
            treeforecast6 = etree.fromstring(pageforecast6)
            forcast6days = True
        except (
                timeout,
                urllib.error.HTTPError,
                urllib.error.URLError,
                etree.XMLSyntaxError,
                TypeError
        ) as e:
            forcast6days = False
            logging.debug(f'Url of 6 days forcast not available: {str(reqforecast6)}')
            logging.debug(f'6 days forcast not available: {str(e)}')

        try:
            logging.debug(
                f'Fetching url for actual weather: {self.baseurl}{self.id_}{self.suffix}'
            )
            req = urllib.request.urlopen(
                f'{self.baseurl}{self.id_}{self.suffix}',
                timeout=10
            )
            logging.debug(
                'Fetching url for forecast of the day + 4: {0}{1}{2}'.format(
                    self.day_forecast_url,
                    self.id_,
                    self.suffix
                )
            )
            reqdayforecast = urllib.request.urlopen(
                f'{self.day_forecast_url}{self.id_}{self.suffix}',
                timeout=10
            )
            page = req.read()
            pagedayforecast = reqdayforecast.read()
            if self.html404(page, 'city'):
                raise urllib.error.HTTPError
            elif self.html404(pagedayforecast, 'day_forecast'):
                # Try with json
                logging.debug(
                    'Fetching json url for forecast of the day: '
                    f'{self.day_forecast_url}{self.id_}'
                    f'{self.suffix.replace("xml", "json")}'
                )
                reqdayforecast = urllib.request.urlopen(
                    f'{self.day_forecast_url}{self.id_}{self.suffix.replace("xml", "json")}',
                    timeout=10
                )
                pagedayforecast = reqdayforecast.read().decode('utf-8')
                if self.html404(pagedayforecast, 'day_forecast'):
                    raise urllib.error.HTTPError
                else:
                    treedayforecast = json.loads(pagedayforecast)
                    use_json_day_forecast = True
                    logging.debug(
                        'Found json page for the forecast of the day'
                    )
            try:
                tree = etree.fromstring(page)
                lat = tree[0][0].get('lat')
                lon = tree[0][0].get('lon')
                weather_icon = tree[9].get('icon')
                for var_ in [lat, lon, weather_icon]:
                    if isinstance(var_, type(None)):
                        raise TypeError
            except TypeError:
                logging.debug(
                    f'Error, use JSON page for the actual weather info {str(traceback.print_exc())}'
                )
                req = urllib.request.urlopen(
                    f'{self.baseurl}{self.id_}{self.suffix.replace("xml", "json")}',
                    timeout=10
                )
                page = req.read().decode('utf-8').replace("'", '"')
                actual_weather_dic = json.loads(page)
                lat = str(actual_weather_dic["coord"]["lat"])
                lon = str(actual_weather_dic["coord"]["lon"])
                weather_icon = actual_weather_dic["weather"][0]["icon"]

            # ALERTS
            appid_ind = self.suffix.find('&APPID=')
            appid = self.suffix[appid_ind + 7:]
            exclude = 'current,minutely,hourly,daily'
            one_call_url = (
                f'http://api.openweathermap.org/data/2.5/onecall?'
                f'lat={lat}&lon={lon}&exclude={exclude}&appid={appid}'
            )
            logging.debug(f'OneCall URL: {one_call_url}')
            try:
                one_call_req = urllib.request.urlopen(one_call_url, timeout=10)
                one_call_rep = one_call_req.read().decode('utf-8')
                onecall_json = json.loads(one_call_rep)
                one_call_alert = onecall_json.get('alerts', False)
                if one_call_alert:
                    self.alerts_signal.emit(one_call_alert)
            except timeout:
                logging.error('Timeout error. Cannot fetch onecall data')
            except urllib.error.HTTPError:
                logging.error('Your openweathermap key has no access to onecall api')

            uv_ind = (lat, lon)
            url = f'{self.wIconUrl}{weather_icon}.png'
            self.weather_icon_signal.emit(weather_icon)
            self.uv_signal.emit(uv_ind)
            if not use_json_day_forecast:
                treedayforecast = etree.fromstring(pagedayforecast)

            logging.debug(f'Icon url: {url}')
            data = urllib.request.urlopen(url).read()
            if self.html404(data, 'icon'):
                raise urllib.error.HTTPError
            self.xmlpage.emit(tree)
            self.wimage.emit(data)
            if forcast6days:
                self.forecast6_rawpage.emit(treeforecast6)
            self.day_forecast_rawpage.emit(treedayforecast)
            self.done.emit(int(done))
        except (
                ConnectionResetError,
                urllib.error.HTTPError,
                urllib.error.URLError
        ) as error:
            if self.tentatives >= 10:
                done = 1
                try:
                    m_error = (
                        f'{self.tr("Error:")}\n{str(error.code)} {str(error.reason)}'
                    )
                except Exception:
                    m_error = str(error)
                logging.error(m_error)
                self.error.emit(m_error)
                self.done.emit(int(done))
                return
            else:
                self.tentatives += 1
                logging.warning(f'Error: {str(error)}')
                logging.info(f'Try again...{str(self.tentatives)}')
                self.run()
        except timeout:
            if self.tentatives >= 10:
                done = 1
                logging.error('Timeout error, abandon...')
                self.done.emit(int(done))
                return
            else:
                self.tentatives += 1
                logging.warning(
                    f'5 secondes timeout, new tentative: {str(self.tentatives)}'
                )
                self.run()
        except (etree.XMLSyntaxError) as error:
            logging.critical(f'Error: {str(error)}')
            done = 1
            self.done.emit(int(done))

        logging.debug('Download thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error_message = f'{code} {message}@{what}'
            logging.debug(str(self.error_message))
            return True
        except Exception:
            return False


class Uv(QThread):
    uv_signal = pyqtSignal(['PyQt_PyObject'])
    air_pollution_signal = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, uv_coord, parent=None):
        QThread.__init__(self, parent)
        self.uv_coord = uv_coord
        self.settings = QSettings()
        self.appid = self.settings.value('APPID') or ''

    def run(self):
        use_proxy = self.settings.value('Proxy') or 'False'
        use_proxy = eval(use_proxy)
        proxy_auth = (
            self.settings.value('Use_proxy_authentification') or 'False'
        )
        proxy_auth = eval(proxy_auth)
        if use_proxy:
            proxy_url = self.settings.value('Proxy_url')
            proxy_port = self.settings.value('Proxy_port')
            proxy_tot = f'http://:{proxy_port}'
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    f'http://{proxy_user}:{proxy_password}@{proxy_url}:{proxy_port}'
                )
            proxy = urllib.request.ProxyHandler({"http": proxy_tot})
            auth = urllib.request.HTTPBasicAuthHandler()
            opener = urllib.request.build_opener(
                proxy, auth, urllib.request.HTTPHandler
            )
            urllib.request.install_opener(opener)
        else:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
        lat = self.uv_coord[0]
        lon = self.uv_coord[1]
        try:
            url = (
                f'http://api.openweathermap.org/data/2.5/uvi?lat={lat}&lon={lon}&appid={self.appid}'
            )
            logging.debug(f'Fetching url for uv index: {str(url)}')
            req = urllib.request.urlopen(url, timeout=10)
            page = req.read().decode('utf-8')
            dicUV = json.loads(page)
            uv_ind = dicUV['value']
            logging.debug(f'UV index: {str(uv_ind)}')
        except Exception:
            uv_ind = '-'
            logging.error('Cannot find UV index')
        try:
            url = (
                f'http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={self.appid}'
            )
            logging.debug(f'Fetching url for air pollution: {str(url)}')
            req = urllib.request.urlopen(url, timeout=10)
            page = req.read().decode('utf-8')
            dic_air = json.loads(page)
            logging.debug(f'Air pollution data: {dic_air}')
            air_pollution_data = dic_air['list']
        except Exception:
            air_pollution_data = {'main': {'aqi': 0}, 'components': {}}
            logging.error('Cannot find Air Quality Index')

        self.uv_signal.emit(uv_ind)
        self.air_pollution_signal.emit(air_pollution_data)


class IconDownload(QThread):
    url_error_signal = pyqtSignal(['QString'])
    wimage = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, icon_url, icon, parent=None):
        QThread.__init__(self, parent)
        self.icon_url = icon_url
        self.icon = icon
        self.tentatives = 0
        # Some times server sends less data
        self.periods = 6
        periods = len(self.icon)
        if periods < 6:
            self.periods = periods
        self.settings = QSettings()

    def run(self):
        use_proxy = self.settings.value('Proxy') or 'False'
        use_proxy = eval(use_proxy)
        proxy_auth = (
            self.settings.value('Use_proxy_authentification') or 'False'
        )
        proxy_auth = eval(proxy_auth)
        if use_proxy:
            proxy_url = self.settings.value('Proxy_url')
            proxy_port = self.settings.value('Proxy_port')
            proxy_tot = 'http://' + ':' + proxy_port
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    f'http://{proxy_user}:{proxy_password}@{proxy_url}:{proxy_port}'
                )
            proxy = urllib.request.ProxyHandler({"http": proxy_tot})
            auth = urllib.request.HTTPBasicAuthHandler()
            opener = urllib.request.build_opener(
                proxy, auth, urllib.request.HTTPHandler
            )
            urllib.request.install_opener(opener)
        else:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
        try:
            for i in range(self.periods):
                url = f'{self.icon_url}{self.icon[i]}.png'
                logging.debug(f'Icon downloading: {url}')
                data = urllib.request.urlopen(url, timeout=10).read()
                if self.html404(data, 'icon'):
                    self.url_error_signal['QString'].emit(self.error_message)
                    return
                self.wimage.emit([data, self.icon[i]])
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            try:
                url_error = (
                    f'Error: {str(error.code)}: {str(error.reason)}'
                )
            except Exception:
                url_error = error
            logging.error(str(url_error))
            self.url_error_signal.emit(url_error)
        except timeout:
            if self.tentatives >= 10:
                logging.error('Timeout error, abandon...')
                return
            else:
                self.tentatives += 1
                logging.info(
                    '5 secondes timeout, new tentative: '
                    + str(self.tentatives)
                )
                self.run()
        logging.debug('Download forecast icons thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error_message = f'{code} {message}@{what}'
            logging.error(self.error_message)
            return True
        except Exception:
            return False


class AlertsDLG(QDialog):

    def __init__(self, parent=None):
        super(AlertsDLG, self).__init__(parent)
        self.textBrowser = QTextBrowser()
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.textBrowser)
        btn_ok = QPushButton('OK')
        btn_ok.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)
        self.setMinimumWidth(400)
        icon = QIcon.fromTheme('dialog-warning')
        if icon.isNull():
            icon = QIcon(':/dialog-warning')
        self.setWindowIcon(icon)

    def show_alert(self, alert_json):
        self.textBrowser.clear()
        for i in range(len(alert_json)):
            for key, value in alert_json[i].items():
                if key == 'event':
                    color = "red"
                    logging.info(f'ALERT {value.lower().replace("warning", "")}')
                else:
                    color = ""
                self.textBrowser.append(f'<font color="{color}"><b>{key}</b>: {value}</font>')
            if i < len(alert_json):
                self.textBrowser.append('<br/>')
        self.textBrowser.moveCursor(QTextCursor.MoveOperation.Start)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName('meteo-qt')
    app.setOrganizationDomain('meteo-qt')
    app.setApplicationName('meteo-qt')
    icon = QIcon.fromTheme('weather-few-clouds')
    if icon.isNull():
        icon = QIcon(':/logo')
    app.setWindowIcon(icon)
    filePath = os.path.dirname(os.path.realpath(__file__))
    settings = QSettings()
    settings.setValue('SystemIcons', QIcon.themeName())
    locale = settings.value('Language')
    if locale is None or locale == '':
        locale = QLocale.system().name()
    appTranslator = QTranslator()
    if os.path.exists(f'{filePath}/translations/'):
        appTranslator.load(
            filePath + f'/translations/meteo-qt_{locale}'
        )
    else:
        appTranslator.load(
            f'/usr/share/meteo_qt/translations/meteo-qt_{locale}'
        )
    app.installTranslator(appTranslator)
    qtTranslator = QTranslator()
    qtTranslator.load(
        f'qt_{locale}',
        QLibraryInfo.path(
            QLibraryInfo.LibraryPath.TranslationsPath
        )
    )
    app.installTranslator(qtTranslator)

    logLevel = settings.value('Logging/Level')
    if logLevel == '' or logLevel is None:
        logLevel = 'INFO'
        settings.setValue('Logging/Level', 'INFO')

    logPath = os.path.dirname(settings.fileName())
    logFile = f'{logPath}/meteo-qt.log'
    if not os.path.exists(logPath):
        os.makedirs(logPath)
    if os.path.isfile(logFile):
        fsize = os.stat(logFile).st_size
        if fsize > 10240000:
            with open(logFile, 'rb') as rFile:
                rFile.seek(102400)
                logData = rFile.read()
            with open(logFile, 'wb') as wFile:
                wFile.write(logData)
            del logData

    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s'
        ' - %(lineno)s: %(module)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        filename=logFile, level=logLevel
    )
    logger = logging.getLogger('meteo-qt')
    logger.setLevel(logLevel)
    loggerStream = logging.getLogger()
    handlerStream = logging.StreamHandler()
    loggerStreamFormatter = logging.Formatter(
        '%(levelname)s: %(message)s - %(lineno)s: %(module)s'
    )
    handlerStream.setFormatter(loggerStreamFormatter)
    loggerStream.addHandler(handlerStream)

    m = SystemTrayIcon()
    app.exec()


def excepthook(exc_type, exc_value, tracebackobj):
    """
    Global function to catch unhandled exceptions.

    Parameters
    ----------
    exc_type : str
        exception type
    exc_value : int
        exception value
    tracebackobj : traceback
        traceback object
    """
    separator = '-' * 80

    now = f'{datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")} CRASH:'

    info = StringIO()
    traceback.print_tb(tracebackobj, None, info)
    info.seek(0)
    info = info.read()

    errmsg = '{}\t \n{}'.format(exc_type, exc_value)
    sections = [now, separator, errmsg, separator, info]
    msg = '\n'.join(sections)

    print(msg)

    settings = QSettings()
    logPath = os.path.dirname(settings.fileName())
    logFile = f'{logPath}/meteo-qt.log'
    with open(logFile, 'a') as logfile:
        logfile.write(msg)


sys.excepthook = excepthook

if __name__ == '__main__':
    main()
