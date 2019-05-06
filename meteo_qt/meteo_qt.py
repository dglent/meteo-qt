#!/usr/bin/python3
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
import gc

from PyQt5.QtCore import (
    PYQT_VERSION_STR, QT_VERSION_STR, QCoreApplication, QByteArray,
    QLibraryInfo, QLocale, QSettings, Qt, QThread, QTimer, QTranslator,
    pyqtSignal, pyqtSlot, QTime
)
from PyQt5.QtGui import (
    QColor, QCursor, QFont, QIcon, QImage, QMovie, QPainter, QPixmap,
    QTransform, QTextDocument
)
from PyQt5.QtWidgets import (
    QDialog, QAction, QApplication, QMainWindow, QMenu, QSystemTrayIcon, qApp,
    QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
)

try:
    import qrc_resources
    import settings
    import searchcity
    import conditions
    import about_dlg
except ImportError:
    from meteo_qt import qrc_resources
    from meteo_qt import settings
    from meteo_qt import searchcity
    from meteo_qt import conditions
    from meteo_qt import about_dlg


__version__ = "1.0.0"


class SystemTrayIcon(QMainWindow):
    units_dico = {'metric': '°C',
                  'imperial': '°F',
                  ' ': '°K'}



    def __init__(self, parent=None):
        super(SystemTrayIcon, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.settings = QSettings()
        self.cityChangeTimer = QTimer()
        self.cityChangeTimer.timeout.connect(self.update_city_gif)

        self.language = self.settings.value('Language') or ''
        self.temp_decimal_bool = self.settings.value('Decimal') or False
        # initialize the tray icon type in case of first run: issue#42
        self.tray_type = self.settings.value('TrayType') or 'icon&temp'
        self.cond = conditions.WeatherConditions()
        self.temporary_city_status = False
        self.conditions = self.cond.trans
        self.clouds = self.cond.clouds
        self.wind = self.cond.wind
        self.wind_dir = self.cond.wind_direction
        self.wind_codes = self.cond.wind_codes
        self.inerror = False
        self.tentatives = 0
        self.baseurl = 'http://api.openweathermap.org/data/2.5/weather?id='
        self.accurate_url = 'http://api.openweathermap.org/data/2.5/find?q='
        self.day_forecast_url = (
            'http://api.openweathermap.org/data/2.5/forecast?id='
        )
        self.forecast6_url = (
            'http://api.openweathermap.org/data/2.5/forecast/daily?id='
        )
        self.wIconUrl = 'http://openweathermap.org/img/w/'
        apikey = self.settings.value('APPID') or ''
        self.appid = '&APPID=' + apikey
        self.forecast_icon_url = self.wIconUrl
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.menu = QMenu()
        self.citiesMenu = QMenu(self.tr('Cities'))
        desktops_no_left_click = ['ubuntu', 'budgie-desktop']
        if os.environ.get('DESKTOP_SESSION') in desktops_no_left_click:
            # Missing left click on Unity environment issue 63
            self.panelAction = QAction(
                QCoreApplication.translate(
                    "Tray context menu", "Toggle Window",
                    "Open/closes the application window"
                ), self
            )
            self.panelAction.setIcon(QIcon(':/panel'))
            self.menu.addAction(self.panelAction)
            self.panelAction.triggered.connect(self.showpanel)
        self.tempCityAction = QAction(self.tr('&Temporary city'), self)
        self.refreshAction = QAction(self.tr('&Update'), self)
        self.settingsAction = QAction(self.tr('&Settings'), self)
        self.aboutAction = QAction(self.tr('&About'), self)
        self.exitAction = QAction(self.tr('Exit'), self)
        self.exitAction.setIcon(QIcon(':/exit'))
        self.aboutAction.setIcon(QIcon(':/info'))
        self.refreshAction.setIcon(QIcon(':/refresh'))
        self.settingsAction.setIcon(QIcon(':/configure'))
        self.tempCityAction.setIcon(QIcon(':/tempcity'))
        self.citiesMenu.setIcon(QIcon(':/bookmarks'))
        self.menu.addAction(self.settingsAction)
        self.menu.addAction(self.refreshAction)
        self.menu.addMenu(self.citiesMenu)
        self.menu.addAction(self.tempCityAction)
        self.menu.addAction(self.aboutAction)
        self.menu.addAction(self.exitAction)
        self.settingsAction.triggered.connect(self.config)
        self.exitAction.triggered.connect(qApp.quit)
        self.refreshAction.triggered.connect(self.manual_refresh)
        self.aboutAction.triggered.connect(self.about)
        self.tempCityAction.triggered.connect(self.tempcity)
        self.systray = QSystemTrayIcon()
        self.systray.setContextMenu(self.menu)
        self.systray.activated.connect(self.activate)
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip(self.tr('Searching weather data...'))

        self.notification = ''
        self.hPaTrend = 0
        self.trendCities_dic = {}
        self.notifier_id = ''
        self.temp_trend = ''
        self.systray.show()
        # The dictionnary has to be intialized here. If there is an error
        # the program couldn't become functionnal if the dictionnary is
        # reinitialized in the weatherdata method
        self.weatherDataDico = {}
        # The traycolor has to be initialized here for the case when we cannot
        # reach the tray method (case: set the color at first time usage)
        self.traycolor = ''
        self.days_dico = {'0': self.tr('Mon'),
                          '1': self.tr('Tue'),
                          '2': self.tr('Wed'),
                          '3': self.tr('Thu'),
                          '4': self.tr('Fri'),
                          '5': self.tr('Sat'),
                          '6': self.tr('Sun')}
        self.precipitation = self.cond.rain
        self.wind_direction = self.cond.wind_codes
        self.wind_name_dic = self.cond.wind
        self.clouds_name_dic = self.cond.clouds
        self.beaufort_sea_land = self.cond.beaufort
        self.hpa_indications = self.cond.pressure
        self.uv_risk = self.cond.uv_risk
        self.uv_recommend = self.cond.uv_recommend

        self.refresh()

    def overviewcity(self):
        temp_trend = ''
        if self.temp_trend == " ↗":
            temp_trend = " "
        elif self.temp_trend == " ↘":
            temp_trend = ""
        self.overviewcitydlg = QDialog()
        self.setCentralWidget(self.overviewcitydlg)


        self.forecast_weather_list = []
        self.dayforecast_weather_list = []
        self.icon_list = []
        self.dayforecast_icon_list = []
        self.unit_temp = self.units_dico[self.unit]
        total_layout = QVBoxLayout()

        # ----First part overview day -----
        over_layout = QVBoxLayout()
        self.dayforecast_layout = QHBoxLayout()
        self.dayforecast_temp_layout = QHBoxLayout()
        # Check for city translation
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        city_notrans = (
            self.weatherDataDico['City'] + '_'
            + self.weatherDataDico['Country'] + '_'
            + self.weatherDataDico['Id']
        )
        if city_notrans in cities_trans_dict:
            city_label = cities_trans_dict[city_notrans]
        else:
            city_label = (
                self.weatherDataDico['City'] + ',  '
                + self.weatherDataDico['Country']
            )
        self.city_label = QLabel(
            '<font size="4"><b>' + city_label + '<\b><\font>'
        )
        over_layout.addWidget(self.city_label)
        icontemp_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self.wIcon)
        icontemp_layout.addWidget(icon_label)
        temp_label = QLabel(
            '<font size="5"><b>' + '{0:.1f}'
            .format(float(self.weatherDataDico['Temp'][:-1])) + ' '
            + self.unit_temp + temp_trend + '<\b><\font>'
        )
        icontemp_layout.addWidget(temp_label)
        over_layout.addLayout(icontemp_layout)
        weather = QLabel(
            '<font size="4"><b>'
            + self.weatherDataDico['Meteo']
            + '<\b><\font>'
        )
        icontemp_layout.addWidget(weather)
        icontemp_layout.addStretch()
        over_layout.addLayout(self.dayforecast_layout)
        over_layout.addLayout(self.dayforecast_temp_layout)
        # ------Second part overview day---------
        self.over_grid = QGridLayout()
        # Wind
        self.wind_label = QLabel(
            '<font size="3" color=><b>' + self.tr('Wind') + '<\font><\b>'
        )
        self.wind_label.setAlignment(Qt.AlignTop)
        wind_unit = self.settings.value('Unit') or 'metric'
        beaufort = self.settings.value('Beaufort') or 'False'
        self.bft_bool = eval(beaufort)
        self.unit_system = ' m/s '
        self.unit_system_wind = ' m/s '
        if wind_unit == 'imperial':
            self.unit_system = ' mph '
            self.unit_system_wind = ' mph '
        windLabelDescr = QLabel('None')
        wind_speed = '{0:.1f}'.format(float(self.weatherDataDico['Wind'][0]))
        windTobeaufort = str(self.convertToBeaufort(wind_speed))
        if self.bft_bool is True:
            wind_speed = windTobeaufort
            unit_system_wind = ' Bft. '
        try:
            windLabelDescr = QLabel(
                '<font color=>' + self.weatherDataDico['Wind'][4]
                + ' ' + self.weatherDataDico['Wind'][2] + '° ' + '<br/>'
                + wind_speed + unit_system_wind
                + self.weatherDataDico['Wind'][1] + '<\font>'
            )
            windLabelDescr.setToolTip(
                self.beaufort_sea_land[windTobeaufort]
            )
        except:
            logging.error(
                'Cannot find wind informations:\n'
                + str(self.weatherDataDico['Wind'])
            )
        self.wind_icon_label = QLabel()
        self.wind_icon_label.setAlignment(Qt.AlignLeft)
        self.wind_icon = QPixmap(':/arrow')
        self.wind_icon_direction()
        # Clouds
        self.clouds_label = QLabel(
            '<font size="3" color=><b>' + self.tr('Cloudiness') + '<\b><\font>'
        )
        clouds_name = QLabel(
            '<font color=>' + self.weatherDataDico['Clouds'] + '<\font>'
        )
        # Pressure
        self.pressure_label = QLabel(
            '<font size="3" color=><b>' + self.tr('Pressure') + '<\b><\font>'
        )
        if self.hPaTrend == 0:
            hpa = ""
        elif self.hPaTrend < 0:
            hpa = ""
        elif self.hPaTrend > 0:
            hpa = ""
        pressure_value = QLabel(
            '<font color=>' + str(float(self.weatherDataDico['Pressure'][0]))
            + ' ' + self.weatherDataDico['Pressure'][1] + " " + hpa + '<\font>'
        )
        pressure_value.setToolTip(self.hpa_indications['hpa'])
        # Humidity
        self.humidity_label = QLabel(
            '<font size="3" color=><b>' + self.tr('Humidity') + '<\b><\font>'
        )
        humidity_value = QLabel(
            '<font color=>' + self.weatherDataDico['Humidity'][0] + ' '
            + self.weatherDataDico['Humidity'][1] + '<\font>'
        )
        # Precipitation
        precipitation_label = QLabel(
            '<font size="3" color=><b>'
            + QCoreApplication.translate(
                'Precipitation type (no/rain/snow)',
                'Precipitation', 'Weather overview dialogue'
            )
            + '<\b><\font>'
        )
        rain_mode = (
            self.precipitation[self.weatherDataDico['Precipitation'][0]]
        )
        rain_value = self.weatherDataDico['Precipitation'][1]
        rain_unit = ' mm '
        if rain_value == '':
            rain_unit = ''
        else:
            if wind_unit == 'imperial':
                rain_unit = 'inch'
                rain_value = str(float(rain_value) / 25.4)
                rain_value = "{0:.4f}".format(float(rain_value))
            else:
                rain_value = "{0:.2f}".format(float(rain_value))
        precipitation_value = QLabel(
            '<font color=>' + rain_mode + ' ' + rain_value
            + ' ' + rain_unit + '</font>'
        )
        # Sunrise Sunset Daylight
        sunrise_label = QLabel(
            '<font color=><b>' + self.tr('Sunrise') + '</b></font>'
        )
        sunset_label = QLabel(
            '<font color=><b>' + self.tr('Sunset') + '</b></font>'
        )
        rise_str = self.utc('Sunrise', 'weatherdata')
        set_str = self.utc('Sunset', 'weatherdata')
        sunrise_value = QLabel(
            '<font color=>' + rise_str[:-3] + '</font>'
        )
        sunset_value = QLabel('<font color=>' + set_str[:-3] + '</font>')
        daylight_label = QLabel(
            '<font color=><b>'
            + QCoreApplication.translate(
                'Daylight duration', 'Daylight',
                'Weather overview dialogue'
            )
            + '</b></font>'
        )
        daylight_value = self.daylight_delta(rise_str[:-3], set_str[:-3])
        daylight_value_label = QLabel(
            '<font color=>' + daylight_value + '</font>'
        )
        # --UV---
        self.uv_label = QLabel(
            '<font size="3" color=><b>'
            + QCoreApplication.translate(
                'Ultraviolet index', 'UV',
                'Label in weather info dialogue'
            )
            + '<\b><\font>'
        )
        self.uv_label.setAlignment(Qt.AlignTop)
        fetching_text = (
            '<font color=>'
            + QCoreApplication.translate(
                'Ultraviolet index',
                'Fetching...',
                ''
            )
            + '<\font>'
        )
        self.uv_value_label = QLabel()
        self.uv_value_label.setText(fetching_text)
        # Ozone
        self.ozone_label = QLabel(
            '<font size="3" color=><b>'
            + QCoreApplication.translate(
                'Ozone data title',
                'Ozone',
                'Label in weather info dialogue'
            )
            + '<\b><\font>'
        )
        self.ozone_value_label = QLabel()
        self.ozone_value_label.setText(fetching_text)
        self.over_grid.addWidget(self.wind_label, 0, 0)
        self.over_grid.addWidget(windLabelDescr, 0, 1)
        self.over_grid.addWidget(self.wind_icon_label, 0, 2)
        self.over_grid.addWidget(self.clouds_label, 1, 0)
        self.over_grid.addWidget(clouds_name, 1, 1)
        self.over_grid.addWidget(self.pressure_label, 2, 0)
        self.over_grid.addWidget(pressure_value, 2, 1)
        self.over_grid.addWidget(self.humidity_label, 3, 0)
        self.over_grid.addWidget(humidity_value, 3, 1, 1, 3)  # align left
        self.over_grid.addWidget(precipitation_label, 4, 0)
        self.over_grid.addWidget(precipitation_value, 4, 1)
        self.over_grid.addWidget(sunrise_label, 5, 0)
        self.over_grid.addWidget(sunrise_value, 5, 1)
        self.over_grid.addWidget(sunset_label, 6, 0)
        self.over_grid.addWidget(sunset_value, 6, 1)
        self.over_grid.addWidget(daylight_label, 7, 0)
        self.over_grid.addWidget(daylight_value_label, 7, 1)
        # -------------Forecast-------------
        self.forecast_days_layout = QHBoxLayout()
        self.forecast_icons_layout = QHBoxLayout()
        self.forecast_minmax_layout = QHBoxLayout()
        # ----------------------------------
        total_layout.addLayout(over_layout)
        total_layout.addLayout(self.over_grid)
        total_layout.addLayout(self.forecast_icons_layout)
        total_layout.addLayout(self.forecast_days_layout)
        total_layout.addLayout(self.forecast_minmax_layout)

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
        self.ozone_fetch()
        logging.debug('Fetched ozone data')

        self.overviewcitydlg.setLayout(total_layout)
        self.setWindowTitle(self.tr('Weather status'))
        self.restoreGeometry(self.settings.value("MainWindow/Geometry",
                                                 QByteArray()))
        ##  Option to start with the panel closed, true by defaut
        #   starting with the panel open can be useful for users who don't have plasma
        #   installed (to set keyboard shortcuts or other default window behaviours)
        start_minimized = self.settings.value('StartMinimized') or 'True'
        if start_minimized == 'False':
            self.showpanel()

    def daylight_delta(self, s1, s2):
        FMT = '%H:%M'
        tdelta = (
            datetime.datetime.strptime(s2, FMT)
            - datetime.datetime.strptime(s1, FMT)
        )
        m, s = divmod(tdelta.seconds, 60)
        h, m = divmod(m, 60)
        if len(str(m)) == 1:
            m = '0' + str(m)
        daylight_in_hours = str(h) + ":" + str(m)
        return daylight_in_hours

    def utc(self, rise_set, what):
        ''' Convert sun rise/set from UTC to local time
            'rise_set' is 'Sunrise' or 'Sunset' when it is for weatherdata
            or the index of hour in day forecast when dayforecast'''
        listtotime = ''
        # Create a list ['h', 'm', 's'] and pass it to QTime
        if what == 'weatherdata':
            listtotime = (
                self.weatherDataDico[rise_set].split('T')[1].split(':')
            )
        elif what == 'dayforecast':
            if not self.json_data_bool:
                listtotime = (
                    self.dayforecast_data[4][rise_set].get('from')
                    .split('T')[1].split(':')
                )
            else:
                listtotime = (
                    self.dayforecast_data['list'][rise_set]['dt_txt'][10:]
                    .split(':')
                )
        suntime = QTime(int(listtotime[0]), int(listtotime[1]), int(
            listtotime[2]))
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
        transf = QTransform()
        angle = self.weatherDataDico['Wind'][2]
        logging.debug('Wind degrees direction: ' + angle)
        transf.rotate(int(float(angle)))
        rotated = self.wind_icon.transformed(
            transf, mode=Qt.SmoothTransformation
        )
        self.wind_icon_label.setPixmap(rotated)

    def ozone_du(self, du):
        if du <= 125:
            return '#060106'  # black
        elif du <= 150:
            return '#340634'  # magenta
        elif du <= 175:
            return '#590b59'  # fuccia
        elif du <= 200:
            return '#421e85'  # violet
        elif du <= 225:
            return '#121e99'  # blue
        elif du <= 250:
            return '#125696'  # blue sea
        elif du <= 275:
            return '#198586'  # raf
        elif du <= 300:
            return '#21b1b1'  # cyan
        elif du <= 325:
            return '#64b341'  # light green
        elif du <= 350:
            return '#1cac1c'  # green
        elif du <= 375:
            return '#93a92c'  # green oil
        elif du <= 400:
            return '#baba2b'  # yellow
        elif du <= 425:
            return '#af771f'  # orange
        elif du <= 450:
            return '#842910'  # brown
        elif du <= 475:
            return '#501516'  # brown dark
        elif du > 475:
            return '#210909'  # darker brown

    def uv_color(self, uv):
        try:
            uv = float(uv)
        except:
            return ('grey', 'None')
        if uv <= 2.99:
            return ('green', 'Low')
        elif uv <= 5.99:
            return ('yellow', 'Moderate')
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

    def find_min_max(self, fetched_file_periods):
        ''' Find the minimum and maximum temperature of
            the day in the 4 days forecast '''
        self.date_temp_forecast = {}
        for d in range(1, fetched_file_periods):
            date_list = self.dayforecast_data[4][d].get('from').split('-')
            date_list_time = date_list[2].split('T')
            date_list[2] = date_list_time[0]
            if not date_list[2] in self.date_temp_forecast:
                self.date_temp_forecast[date_list[2]] = []
            self.date_temp_forecast[date_list[2]].append(
                float(self.dayforecast_data[4][d][4].get('max')))

    def forecast6data(self):
        '''Forecast for the next 6 days'''
        # Some times server sends less data
        doc = QTextDocument()
        periods = 7
        fetched_file_periods = (len(self.forecast6_data.xpath('//time')))
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            logging.warning('Reduce forecast for the next 6 days to {0}'.format(
                periods - 1))
        for d in range(1, periods):
            date_list = self.forecast6_data[4][d].get('day').split('-')
            day_of_week = str(datetime.date(
                int(date_list[0]), int(date_list[1]),
                int(date_list[2])).weekday())
            label = QLabel('' + self.days_dico[day_of_week] + '')
            label.setToolTip(self.forecast6_data[4][d].get('day'))
            label.setAlignment(Qt.AlignHCenter)
            self.forecast_days_layout.addWidget(label)
            mlabel = QLabel(
                '<font color=>' + '{0:.0f}'
                .format(float(self.forecast6_data[4][d][4].get('min')))
                + '°<br/>' + '{0:.0f}'
                .format(float(self.forecast6_data[4][d][4].get('max')))
                + '°</font>'
            )
            mlabel.setAlignment(Qt.AlignHCenter)
            mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
            self.forecast_minmax_layout.addWidget(mlabel)
            # icon
            self.icon_list.append(self.forecast6_data[4][d][0].get('var'))
            weather_cond = self.forecast6_data[4][d][0].get('name')
            try:
                weather_cond = (
                    self.conditions[self.forecast6_data[4][d][0].get('number')]
                )
            except:
                logging.warn(
                    'Cannot find localisation string for :'
                    + weather_cond
                )
                pass
            try:
                # Take the label translated text and remove the html tags
                doc.setHtml(self.precipitation_label.text())
                precipitation_label = doc.toPlainText() + ': '
                precipitation_type = self.forecast6_data[4][d][1].get('type')
                precipitation_type = (
                    self.precipitation[precipitation_type] + ' '
                )
                precipitation_value = self.forecast6_data[4][d][1].get('value')
                rain_unit = ' mm'
                if self.unit_system == ' mph ':
                    rain_unit = ' inch'
                    precipitation_value = (
                        str(float(precipitation_value) / 25.4) + ' '
                    )
                    precipitation_value = (
                        "{0:.2f}".format(float(precipitation_value))
                    )
                else:
                    precipitation_value = (
                        "{0:.1f}".format(float(precipitation_value))
                    )
                weather_cond += (
                    '\n' + precipitation_label + precipitation_type
                    + precipitation_value + rain_unit
                )
            except:
                pass
            doc.setHtml(self.wind_label.text())
            wind = doc.toPlainText() + ': '
            try:
                wind_direction = (
                    self.wind_direction[
                        self.forecast6_data[4][d][2].get('code')
                    ]
                )
            except:
                wind_direction = ''
            wind_speed = (
                '{0:.1f}'.format(
                    float(self.forecast6_data[4][d][3].get('mps'))
                )
            )
            if self.bft_bool:
                wind_speed = str(self.convertToBeaufort(wind_speed))
            weather_cond += (
                '\n' + wind + wind_speed + self.unit_system_wind
                + wind_direction
            )
            doc.setHtml(self.pressure_label.text())
            pressure_label = doc.toPlainText() + ': '
            pressure = (
                '{0:.1f}'.format(
                    float(self.forecast6_data[4][d][5].get('value'))
                )
            )
            weather_cond += '\n' + pressure_label + pressure + ' hPa'
            humidity = self.forecast6_data[4][d][6].get('value')
            doc.setHtml(self.humidity_label.text())
            humidity_label = doc.toPlainText() + ': '
            weather_cond += '\n' + humidity_label + humidity + ' %'
            clouds = self.forecast6_data[4][d][7].get('all')
            doc.setHtml(self.clouds_label.text())
            clouds_label = doc.toPlainText() + ': '
            weather_cond += '\n' + clouds_label + clouds + ' %'
            self.forecast_weather_list.append(weather_cond)

    def forecastdata(self):
        '''Forecast for the next 4 days'''
        # Some times server sends less data
        doc = QTextDocument()
        fetched_file_periods = (len(self.dayforecast_data.xpath('//time')))
        self.find_min_max(fetched_file_periods)
        for d in range(1, fetched_file_periods):
            # Find the day for the forecast (today+1) at 12:00:00
            date_list = self.dayforecast_data[4][d].get('from').split('-')
            date_list_time = date_list[2].split('T')
            date_list[2] = date_list_time[0]
            date_list.append(date_list_time[1])
            if (
                datetime.datetime.now().day == int(date_list[2])
                or date_list[3] != '12:00:00'
            ):
                continue
            day_of_week = str(datetime.date(
                int(date_list[0]), int(date_list[1]),
                int(date_list[2])).weekday())
            label = QLabel('' + self.days_dico[day_of_week] + '')
            label.setToolTip('-'.join(i for i in date_list[:3]))
            label.setAlignment(Qt.AlignHCenter)
            self.forecast_days_layout.addWidget(label)
            temp_min = min(self.date_temp_forecast[date_list[2]])
            temp_max = max(self.date_temp_forecast[date_list[2]])
            mlabel = QLabel(
                '<font color=>' + '{0:.0f}'.format(temp_min) + '°<br/>'
                + '{0:.0f}'.format(temp_max) + '°</font>'
            )
            mlabel.setAlignment(Qt.AlignHCenter)
            mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
            self.forecast_minmax_layout.addWidget(mlabel)
            # icon
            self.icon_list.append(self.dayforecast_data[4][d][0].get('var'))
            weather_cond = self.dayforecast_data[4][d][0].get('name')
            try:
                weather_cond = (
                    self.conditions[
                        self.dayforecast_data[4][d][0].get('number')
                    ]
                )
            except:
                logging.warn(
                    'Cannot find localisation string for :'
                    + weather_cond
                )
                pass
            try:
                # Take the label translated text and remove the html tags
                doc.setHtml(self.precipitation_label.text())
                precipitation_label = doc.toPlainText() + ': '
                precipitation_type = self.dayforecast_data[4][d][1].get('type')
                precipitation_type = (
                    self.precipitation[precipitation_type] + ' '
                )
                precipitation_value = (
                    self.dayforecast_data[4][d][1].get('value')
                )
                rain_unit = ' mm'
                if self.unit_system == ' mph ':
                    rain_unit = ' inch'
                    precipitation_value = (
                        str(float(precipitation_value) / 25.4) + ' '
                    )
                    precipitation_value = (
                        "{0:.2f}".format(float(precipitation_value))
                    )
                else:
                    precipitation_value = (
                        "{0:.1f}".format(float(precipitation_value))
                    )
                weather_cond += (
                    '\n' + precipitation_label + precipitation_type
                    + precipitation_value + rain_unit
                )
            except:
                pass
            doc.setHtml(self.wind_label.text())
            wind = doc.toPlainText() + ': '
            try:
                wind_direction = (
                    self.wind_direction[
                        self.dayforecast_data[4][d][2].get('code')
                    ]
                )
            except:
                wind_direction = ''
            wind_speed = (
                '{0:.1f}'.format(
                    float(self.dayforecast_data[4][d][3].get('mps'))
                )
            )
            if self.bft_bool:
                wind_speed = str(self.convertToBeaufort(wind_speed))
            weather_cond += (
                '\n' + wind + wind_speed + self.unit_system_wind
                + wind_direction
            )
            doc.setHtml(self.pressure_label.text())
            pressure_label = doc.toPlainText() + ': '
            pressure = (
                '{0:.1f}'.format(
                    float(self.dayforecast_data[4][d][5].get('value'))
                )
            )
            weather_cond += '\n' + pressure_label + pressure + ' hPa'
            humidity = self.dayforecast_data[4][d][6].get('value')
            doc.setHtml(self.humidity_label.text())
            humidity_label = doc.toPlainText() + ': '
            weather_cond += '\n' + humidity_label + humidity + ' %'
            clouds = self.dayforecast_data[4][d][7].get('all')
            doc.setHtml(self.clouds_label.text())
            clouds_label = doc.toPlainText() + ': '
            weather_cond += '\n' + clouds_label + clouds + ' %'
            self.forecast_weather_list.append(weather_cond)

    def iconfetch(self):
        logging.debug('Download forecast icons...')
        self.download_thread = (
            IconDownload(self.forecast_icon_url, self.icon_list)
        )
        self.download_thread.wimage['PyQt_PyObject'].connect(self.iconwidget)
        self.download_thread.url_error_signal['QString'].connect(self.errorIconFetch)
        self.download_thread.start()

    def iconwidget(self, icon):
        '''Next days forecast icons'''
        image = QImage()
        image.loadFromData(icon)
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignHCenter)
        iconpixmap = QPixmap(image)
        iconlabel.setPixmap(iconpixmap)
        try:
            iconlabel.setToolTip(self.forecast_weather_list.pop(0))
            self.forecast_icons_layout.addWidget(iconlabel)
        except IndexError as error:
            logging.error(str(error) + ' forecast_weather_list')
            return

    def dayforecastdata(self):
        '''Fetch forecast for the day'''
        periods = 6
        start = 0
        if not self.json_data_bool:
            start = 1
            periods = 7
            fetched_file_periods = (len(self.dayforecast_data.xpath('//time')))
            if fetched_file_periods < periods:
                # Some times server sends less data
                periods = fetched_file_periods
                logging.warn(
                    'Reduce forecast of the day to {0}'.format(periods - 1)
                )
        for d in range(start, periods):
            clouds_translated = ''
            wind = ''
            timeofday = self.utc(d, 'dayforecast')
            if not self.json_data_bool:
                weather_cond = self.conditions[
                    self.dayforecast_data[4][d][0].get('number')
                ]
                self.dayforecast_icon_list.append(
                    self.dayforecast_data[4][d][0].get('var')
                )
                temperature_at_hour = float(
                    self.dayforecast_data[4][d][4].get('value')
                )
                precipitation = str(
                    self.dayforecast_data[4][d][1].get('value')
                )
                precipitation_type = str(
                    self.dayforecast_data[4][d][1].get('type')
                )
                windspeed = self.dayforecast_data[4][d][3].get('mps')
                winddircode = self.dayforecast_data[4][d][2].get('code')
                wind_name = self.dayforecast_data[4][d][3].get('name')
                try:
                    wind_name_translated = (
                        self.conditions[self.wind_name_dic[wind_name.lower()]]
                        + '<br/>'
                    )
                    wind += wind_name_translated
                except KeyError:
                    logging.warn('Cannot find wind name :' + str(wind_name))
                    logging.info('Set wind name to None')
                    wind = ''
                finally:
                    if wind == '':
                        wind += '<br/>'
                clouds = self.dayforecast_data[4][d][7].get('value')
                cloudspercent = self.dayforecast_data[4][d][7].get('all')
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
                precipitation_orig = self.dayforecast_data['list'][d]
                precipitation_rain = precipitation_orig.get('rain')
                precipitation_snow = precipitation_orig.get('snow')
                if (
                    precipitation_rain is not None
                    and len(precipitation_rain) > 0
                ):
                    precipitation_type = 'rain'
                    precipitation = precipitation_rain['3h']
                elif (
                    precipitation_snow is not None
                    and len(precipitation_snow) > 0
                ):
                    precipitation_type = 'snow'
                    precipitation_snow['3h']
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

            self.dayforecast_weather_list.append(weather_cond)
            daytime = QLabel(
                '<font color=>' + timeofday[:-3] + '<br/>'
                + '{0:.0f}'.format(temperature_at_hour)
                + '°' + '</font>'
            )
            daytime.setAlignment(Qt.AlignHCenter)
            unit = self.settings.value('Unit') or 'metric'
            if unit == 'metric':
                mu = 'mm'
                if precipitation.count('None') == 0:
                    precipitation = "{0:.1f}".format(float(precipitation))
            elif unit == 'imperial':
                mu = 'inch'
                if precipitation.count('None') == 0:
                    precipitation = str(float(precipitation) / 25.0)
                    precipitation = "{0:.2f}".format(float(precipitation))
            elif unit == ' ':
                mu = 'kelvin'
            ttip = (
                str(precipitation) + ' ' + mu + ' ' + precipitation_type
                + '<br/>'
            )
            if ttip.count('None') >= 1:
                ttip = ''
            else:
                ttip = ttip.replace('snow', self.tr('snow'))
                ttip = ttip.replace('rain', self.tr('rain'))
            if self.bft_bool is True:
                windspeed = self.convertToBeaufort(windspeed)
            ttip = ttip + (str(windspeed) + ' ' + self.unit_system_wind)
            if winddircode != '':
                wind = self.wind_direction[winddircode] + ' '
            else:
                logging.warn(
                    'Wind direction code is missing: '
                    + str(winddircode)
                )
            if clouds != '':
                try:
                    # In JSON there is no clouds description
                    clouds_translated = (
                        self.conditions[self.clouds_name_dic[clouds.lower()]]
                    )
                except KeyError:
                    logging.warn(
                        'The clouding description in json is not relevant'
                    )
                    clouds_translated = ''
            else:
                logging.warn('Clouding name is missing: ' + str(clouds))
            clouds_cond = clouds_translated + ' ' + str(cloudspercent) + '%'
            ttip = ttip + wind + clouds_cond
            daytime.setToolTip(ttip)
            self.dayforecast_temp_layout.addWidget(daytime)

    def ozone_fetch(self):
        logging.debug('Download ozone info...')
        self.ozone_thread = Ozone(self.uv_coord)
        self.ozone_thread.o3_signal['PyQt_PyObject'].connect(self.ozone_index)
        self.ozone_thread.start()

    def ozone_index(self, index):
        try:
            du = int(index)
            o3_color = self.ozone_du(du)
            factor = str(du)[:1] + '.' + str(du)[1:2]
            gauge = '◼' * round(float(factor))
            logging.debug('Ozone gauge: ' + gauge)

        except:
            du = '-'
            o3_color = None
        du_unit = QCoreApplication.translate(
            'Dobson Units',
            'DU',
            'Ozone value label'
        )
        if o3_color is not None:
            self.ozone_value_label.setText(
                '<font color=>' + str(du) + ' ' + du_unit
                + '</font>' + '<font color=' + o3_color
                + '> ' + gauge + '</font>'
            )
            self.ozone_value_label.setToolTip(
                QCoreApplication.translate(
                    'Ozone value tooltip',
                    '''The average amount of ozone in the <br/> atmosphere is
                    roughly 300 Dobson Units. What scientists call the
                    Antarctic Ozone “Hole” is an area where the ozone
                    concentration drops to an average of about 100 Dobson
                    Units.''',
                    'http://ozonewatch.gsfc.nasa.gov/facts/dobson_SH.html'
                )
            )
        else:
            self.ozone_value_label.setText(
                '<font color=>' + str(du) + '</font>'
            )
        if du != '-':
            self.over_grid.addWidget(self.ozone_label, 9, 0)
            self.over_grid.addWidget(self.ozone_value_label, 9, 1)

    def uv_fetch(self):
        logging.debug('Download uv info...')
        self.uv_thread = Uv(self.uv_coord)
        self.uv_thread.uv_signal['PyQt_PyObject'].connect(self.uv_index)
        self.uv_thread.start()

    def uv_index(self, index):
        uv_gauge = '-'
        uv_color = self.uv_color(index)
        if uv_color[1] != 'None':
            uv_gauge = '◼' * int(round(float(index)))
            if uv_gauge == '':
                uv_gauge = '◼'
            self.uv_value_label.setText(
                '<font color=>' + '{0:.1f}'.format(float(index))
                + '  ' + self.uv_risk[uv_color[1]] + '</font>'
                + '<br/>' + '<font color=' + uv_color[0] + '><b>'
                + uv_gauge + '</b></font>'
            )
        else:
            self.uv_value_label.setText('<font color=>' + uv_gauge + '</font>')
        logging.debug('UV gauge ◼: ' + uv_gauge)
        self.uv_value_label.setToolTip(self.uv_recommend[uv_color[1]])
        if uv_gauge != '-':
            self.over_grid.addWidget(self.uv_label, 8, 0)
            self.over_grid.addWidget(self.uv_value_label, 8, 1)

    def dayiconfetch(self):
        '''Icons for the forecast of the day'''
        logging.debug('Download forecast icons for the day...')
        self.day_download_thread = IconDownload(
            self.forecast_icon_url, self.dayforecast_icon_list
        )
        self.day_download_thread.wimage['PyQt_PyObject'].connect(self.dayiconwidget)
        self.day_download_thread.url_error_signal['QString'].connect(self.errorIconFetch)
        self.day_download_thread.start()

    def dayiconwidget(self, icon):
        '''Forecast icons of the day'''
        image = QImage()
        image.loadFromData(icon)
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignHCenter)
        iconpixmap = QPixmap(image)
        iconlabel.setPixmap(iconpixmap)
        try:
            iconlabel.setToolTip(self.dayforecast_weather_list.pop(0))
            self.dayforecast_layout.addWidget(iconlabel)
        except IndexError as error:
            logging.error(str(error) + 'dayforecast_weather_list')

    def moveEvent(self, event):
        self.settings.setValue("MainWindow/Geometry", self.saveGeometry())

    def resizeEvent(self, event):
        self.settings.setValue("MainWindow/Geometry", self.saveGeometry())

    def hideEvent(self, event):
        self.settings.setValue("MainWindow/Geometry", self.saveGeometry())

    def errorIconFetch(self, error):
        logging.error('error in download of forecast icon:\n' + error)

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
        if (
            self.day_download_thread.isRunning()
            or self.download_thread.isRunning()
        ):
            logging.debug(
                'WheelEvent : Downloading icons - remaining thread...'
            )
            return
        self.icon_city_loading()
        current_city = self.city
        current_id = self.id_
        current_country = self.country

        cities = eval(self.settings.value('CityList') or [])
        if len(cities) == 0:
            return
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        direction = event.pixelDelta().y()
        actual_city = current_city + '_' + current_country + '_' + current_id
        for key, value in cities_trans_dict.items():
            if current_city + '_' + current_country + '_' + current_id == key:
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
        citytosetlist = cities[current_city_index].split('_')
        self.settings.setValue('City', citytosetlist[0])
        self.settings.setValue('Country', citytosetlist[1])
        self.settings.setValue('ID', citytosetlist[2])
        self.timer.singleShot(500, self.refresh)

    def cities_menu(self):
        # Don't add the temporary city in the list
        if self.temporary_city_status:
            return
        self.citiesMenu.clear()
        cities = self.settings.value('CityList') or []
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        if type(cities) is str:
            cities = eval(cities)
        try:
            current_city = (
                self.settings.value('City') + '_'
                + self.settings.value('Country') + '_'
                + self.settings.value('ID')
            )
        except:
            logging.debug(
                'Cities menu : firsttime run,'
                'if clic cancel in settings without any city configured'
            )
            pass
        # Prevent duplicate entries
        try:
            city_toadd = cities.pop(cities.index(current_city))
        except:
            city_toadd = current_city
        finally:
            cities.insert(0, city_toadd)
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
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        self.cities_trans_dict = eval(cities_trans)
        logging.debug('Cities' + str(cities_list))
        if cities_list is None:
            self.empty_cities_list()
        if type(cities_list) is not list:
            # FIXME some times is read as string (?)
            cities_list = eval(cities_list)
        prev_city = (
            self.settings.value('City') + '_'
            + self.settings.value('Country') + '_'
            + self.settings.value('ID')
        )
        citytoset = ''
        # Set the chosen city as the default
        for town in cities_list:
            if town == self.find_city_key(city):
                ind = cities_list.index(town)
                citytoset = cities_list[ind]
                citytosetlist = citytoset.split('_')
                self.settings.setValue('City', citytosetlist[0])
                self.settings.setValue('Country', citytosetlist[1])
                self.settings.setValue('ID', citytosetlist[2])
                if prev_city not in cities_list:
                    cities_list.append(prev_city)
                self.settings.setValue('CityList', str(cities_list))
                logging.debug(cities_list)
        self.refresh()

    def find_city_key(self, city):
        for key, value in self.cities_trans_dict.items():
            if value == city:
                return key
        return city

    def empty_cities_list(self):
        self.citiesMenu.addAction(self.tr('Empty list'))

    def refresh(self):
        if (
            hasattr(self, 'overviewcitydlg')
            and not self.cityChangeTimer.isActive()
        ):
            self.icon_city_loading()
        self.inerror = False
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip(self.tr('Fetching weather data ...'))
        self.city = self.settings.value('City') or ''
        self.id_ = self.settings.value('ID') or None
        if self.id_ is None:
            # Clear the menu, no cities configured
            self.citiesMenu.clear()
            self.empty_cities_list()
            self.timer.singleShot(2000, self.firsttime)
            self.id_ = ''
            self.systray.setToolTip(self.tr('No city configured'))
            return
        # A city has been found, create the cities menu now
        self.cities_menu()
        self.country = self.settings.value('Country') or ''
        self.unit = self.settings.value('Unit') or 'metric'
        self.beaufort = self.settings.value('Beaufort') or 'False'
        self.suffix = ('&mode=xml&units=' + self.unit + self.appid)
        self.interval = int(self.settings.value('Interval') or 30) * 60 * 1000
        self.timer.start(self.interval)
        self.update()

    def firsttime(self):
        self.temp = ''
        self.wIcon = QPixmap(':/noicon')
        self.systray.showMessage(
            'meteo-qt:\n',
            self.tr('No city has been configured yet.')
            + '\n' + self.tr('Right click on the icon and click on Settings.')
        )

    def update(self):
        if hasattr(self, 'downloadThread'):
            if self.downloadThread.isRunning():
                logging.debug('remaining thread...')
                return
        logging.debug('Update...')
        self.icon_loading()
        self.wIcon = QPixmap(':/noicon')
        self.downloadThread = Download(
            self.wIconUrl, self.baseurl, self.day_forecast_url,
            self.forecast6_url, self.id_, self.suffix
        )
        self.downloadThread.wimage['PyQt_PyObject'].connect(self.makeicon)
        self.downloadThread.finished.connect(self.tray)
        self.downloadThread.xmlpage['PyQt_PyObject'].connect(self.weatherdata)
        self.downloadThread.day_forecast_rawpage.connect(self.dayforecast)
        self.forcast6daysBool = False
        self.downloadThread.forecast6_rawpage.connect(self.forecast6)
        self.downloadThread.uv_signal.connect(self.uv)
        self.downloadThread.error.connect(self.error)
        self.downloadThread.done.connect(self.done, Qt.QueuedConnection)
        self.downloadThread.start()

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
            logging.debug('Trying to retrieve data ...')
            self.timer.singleShot(10000, self.try_again)
            return
        if hasattr(self, 'updateicon'):
            # Keep a reference of the image to update the icon in overview
            self.wIcon = self.updateicon
        if hasattr(self, 'dayforecast_data'):
            self.overviewcity()
            return
        else:
            self.try_again()

    def try_again(self):
        self.nodata_message()
        logging.debug('Attempts: ' + str(self.tentatives))
        self.tentatives += 1
        self.timer.singleShot(5000, self.refresh)

    def nodata_message(self):
        nodata = QCoreApplication.translate(
            "Tray icon", "Searching for weather data...",
            "Tooltip (when mouse over the icon")
        self.systray.setToolTip(nodata)
        self.notification = nodata

    def error(self, error):
        logging.error('Error:\n' + str(error))
        self.nodata_message()
        self.timer.start(self.interval)
        self.inerror = True

    def makeicon(self, data):
        image = QImage()
        image.loadFromData(data)
        self.wIcon = QPixmap(image)
        # Keep a reference of the image to update the icon in overview
        self.updateicon = self.wIcon

    def weatherdata(self, tree):
        if self.inerror:
            return
        self.tempFloat = tree[1].get('value')
        self.temp = ' ' + str(round(float(self.tempFloat))) + '°'
        self.temp_decimal = '{0:.1f}'.format(float(self.tempFloat)) + '°'
        self.meteo = tree[8].get('value')
        meteo_condition = tree[8].get('number')
        try:
            self.meteo = self.conditions[meteo_condition]
        except:
            logging.debug('Cannot find localisation string for'
                          'meteo_condition:' + str(meteo_condition))
            pass
        clouds = tree[5].get('name')
        clouds_percent = tree[5].get('value') + '%'
        try:
            clouds = self.clouds[clouds]
            clouds = self.conditions[clouds]
        except:
            logging.debug(
                'Cannot find localisation string for clouds:'
                + str(clouds)
            )
            pass
        wind = tree[4][0].get('name').lower()
        try:
            wind = self.wind[wind]
            wind = self.conditions[wind]
        except:
            logging.debug(
                'Cannot find localisation string for wind:'
                + str(wind)
            )
            pass
        try:
            wind_codes = tree[4][2].get('code')
            wind_dir_value = tree[4][2].get('value')
            wind_dir = tree[4][2].get('name')
        except:
            wind_codes = tree[4][1].get('code')
            wind_dir_value = tree[4][1].get('value')
            wind_dir = tree[4][1].get('name')
        try:
            wind_codes = self.wind_codes[wind_codes]
        except:
            logging.debug(
                'Cannot find localisation string for wind_codes:'
                + str(wind_codes)
            )
            pass
        try:
            wind_dir = self.wind_dir[tree[4][2].get('code')]
        except:
            logging.debug(
                'Cannot find localisation string for wind_dir:'
                + str(wind_dir)
            )
            pass
        self.city_weather_info = (
            self.city + ' ' + self.country + ' '
            + self.temp_decimal + ' ' + self.meteo
        )
        self.tooltip_weather()
        self.notification = self.city_weather_info
        self.weatherDataDico['Id'] = self.id_
        self.weatherDataDico['City'] = self.city
        self.weatherDataDico['Country'] = self.country
        self.weatherDataDico['Temp'] = self.tempFloat + '°'
        self.weatherDataDico['Meteo'] = self.meteo
        self.weatherDataDico['Humidity'] = (tree[2].get('value'),
                                            tree[2].get('unit'))
        self.weatherDataDico['Wind'] = (
            tree[4][0].get('value'), wind, str(int(float(wind_dir_value))),
            wind_codes, wind_dir)
        self.weatherDataDico['Clouds'] = (clouds_percent + ' ' + clouds)
        self.weatherDataDico['Pressure'] = (tree[3].get('value'),
                                            tree[3].get('unit'))
        self.weatherDataDico['Humidity'] = (tree[2].get('value'),
                                            tree[2].get('unit'))
        self.weatherDataDico['Sunrise'] = tree[0][2].get('rise')
        self.weatherDataDico['Sunset'] = tree[0][2].get('set')
        rain_value = tree[7].get('value')
        if rain_value is None:
            rain_value = ''
        self.weatherDataDico['Precipitation'] = (
            tree[7].get('mode'), rain_value
        )
        if self.id_ not in self.trendCities_dic:
            # dict {'id': 'hPa', , '',  'T°', 'temp_trend', 'weather changedBool'}
            self.trendCities_dic[self.id_] = [''] * 5
        # hPa trend
        pressure = float(self.weatherDataDico['Pressure'][0])
        if (
            self.id_ in self.trendCities_dic
            and self.trendCities_dic[self.id_][0] is not ''
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
            and self.trendCities_dic[self.id_][2] is not ''
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
        self.systray.setToolTip(self.city_weather_info + self.temp_trend)

    def tooltip_weather(self):
        # Creation of the tray tootltip
        trans_cities = self.settings.value('CitiesTranslation') or '{}'
        trans_cities_dict = eval(trans_cities)
        city = self.city + '_' + self.country + '_' + self.id_
        if city in trans_cities_dict:
            self.city_weather_info = (
                trans_cities_dict[city] + ' '
                + self.temp_decimal + ' ' + self.meteo
            )
        else:
            self.city_weather_info = (
                self.city + ' ' + self.country + ' '
                + self.temp_decimal + ' ' + self.meteo
            )

    def tray(self):
        temp_decimal = eval(self.settings.value('Decimal') or 'False')
        try:
            if temp_decimal:
                temp_tray = self.temp_decimal
            else:
                temp_tray = self.temp
        except:
            # First time launch
            return
        if self.inerror or not hasattr(self, 'temp'):
            logging.critical('Cannot paint icon!')
            return
        try:
            self.gif_loading.stop()
        except:
            # In first time run the gif is not animated
            pass
        logging.debug('Paint tray icon...')
        # Place empty.png here to initialize the icon
        # don't paint the T° over the old value
        icon = QPixmap(':/empty')
        self.traycolor = self.settings.value('TrayColor') or ''
        self.fontsize = self.settings.value('FontSize') or '18'
        self.tray_type = self.settings.value('TrayType') or 'icon&temp'
        pt = QPainter()
        pt.begin(icon)
        if self.tray_type != 'temp':
            pt.drawPixmap(0, -12, 64, 64, self.wIcon)
        self.bold_set = self.settings.value('Bold') or 'False'
        if self.bold_set == 'True':
            br = QFont.Bold
        else:
            br = QFont.Normal
        pt.setFont(QFont('sans-sertif', int(self.fontsize), weight=br))
        pt.setPen(QColor(self.traycolor))
        if self.tray_type == 'icon&temp':
            pt.drawText(icon.rect(), Qt.AlignBottom | Qt.AlignCenter,
                        str(temp_tray))
        if self.tray_type == 'temp':
            pt.drawText(icon.rect(), Qt.AlignCenter, str(temp_tray))
        pt.end()
        if self.tray_type == 'icon':
            self.systray.setIcon(QIcon(self.wIcon))
        else:
            self.systray.setIcon(QIcon(icon))
        if self.notifier_settings():
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
                            self.trendCities_dic[self.id_][4] is
                                True or self.trendCities_dic[self.id_][4] == ''
                        ):
                            self.systray.showMessage(
                                'meteo-qt', self.notification + self.temp_trend
                            )
                            return
            except KeyError:
                return
        self.notifier_id = self.id_  # To always notify when city changes
        self.restore_city()
        self.tentatives = 0
        self.tooltip_weather()
        logging.info('Actual weather status for: ' + self.notification)

    def notifier_settings(self):
        notifier = self.settings.value('Notifications') or 'True'
        notifier = eval(notifier)
        if notifier:
            return True
        else:
            return False

    def restore_city(self):
        if self.temporary_city_status:
            logging.debug(
                'Restore the default settings (city) '
                + 'Forget the temporary city...'
            )
            for e in (
                ('ID', self.id_2),
                ('City', self.city2),
                ('Country', self.country2)
            ):
                self.citydata(e)
            self.temporary_city_status = False

    def showpanel(self):
        self.activate(3)

    def activate(self, reason):
        ##  Option to start with the panel closed, true by defaut
        #   starting with the panel open can be useful for users who don't have plasma
        #   installed (to set keyboard shortcuts or other default window behaviours)
        start_minimized = self.settings.value('StartMinimized') or 'True'
        if reason == 3:
            if self.inerror or self.id_ is None or self.id_ == '':
                return
            if self.isVisible() and start_minimized == 'True':
                self.hide()
            else:
                self.show()
        elif reason == 1:
            self.menu.popup(QCursor.pos())

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.settings.setValue("MainWindow/State", self.saveState())

    def overview(self):
        if self.inerror or len(self.weatherDataDico) == 0:
            return
        self.show()

    def config_save(self):
        logging.debug('Config saving...')
        city = self.settings.value('City'),
        id_ = self.settings.value('ID')
        country = self.settings.value('Country')
        unit = self.settings.value('Unit')
        beaufort = self.settings.value('Beaufort')
        traycolor = self.settings.value('TrayColor')
        tray_type = self.settings.value('TrayType')
        fontsize = self.settings.value('FontSize')
        bold_set = self.settings.value('Bold')
        language = self.settings.value('Language')
        decimal = self.settings.value('Decimal')
        self.appid = '&APPID=' + self.settings.value('APPID') or ''
        if language != self.language and language is not None:
            self.systray.showMessage(
                'meteo-qt:',
                QCoreApplication.translate(
                    "System tray notification",
                    "The application has to be restarted to apply the language setting",
                    ''
                )
            )
            self.language = language
        # Check if update is needed
        if traycolor is None:
            traycolor = ''
        if (
            self.traycolor != traycolor
            or self.tray_type != tray_type
            or self.fontsize != fontsize or self.bold_set != bold_set
            or decimal != self.temp_decimal
        ):
            self.tray()
        if (
            city[0] == self.city
            and id_ == self.id_
            and country == self.country
            and unit == self.unit
            and beaufort == self.beaufort
        ):
            return
        else:
            logging.debug('Apply changes from settings...')
            self.refresh()

    def config(self):
        dialog = settings.MeteoSettings(self.accurate_url, self.appid, self)
        dialog.applied_signal.connect(self.config_save)
        if dialog.exec_() == 1:
            self.config_save()
            logging.debug('Update Cities menu...')
            self.cities_menu()

    def tempcity(self):
        # Prevent to register a temporary city
        # This happen when a temporary city is still loading
        self.restore_city()
        dialog = searchcity.SearchCity(self.accurate_url, self.appid, self)
        self.id_2, self.city2, self.country2 = (self.settings.value('ID'),
                                                self.settings.value('City'),
                                                self.settings.value('Country'))
        dialog.id_signal[tuple].connect(self.citydata)
        dialog.city_signal[tuple].connect(self.citydata)
        dialog.country_signal[tuple].connect(self.citydata)
        if dialog.exec_():
            self.temporary_city_status = True
            self.systray.setToolTip(self.tr('Fetching weather data...'))
            self.refresh()

    def citydata(self, what):
        self.settings.setValue(what[0], what[1])
        logging.debug('write ' + str(what[0]) + ' ' + str(what[1]))

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
            <a href="https://www.transifex.com/projects/p/meteo-qt/">
            Transifex</a> platform.
            <p>If you want to report a dysfunction or a suggestion,
            feel free to open an issue in
            <a href="https://github.com/dglent/meteo-qt/issues">
            github</a>."""
        )

        dialog = about_dlg.AboutDialog(title, text, image, self)
        dialog.exec_()


class Download(QThread):
    wimage = pyqtSignal(['PyQt_PyObject'])
    xmlpage = pyqtSignal(['PyQt_PyObject'])
    forecast6_rawpage = pyqtSignal(['PyQt_PyObject'])
    day_forecast_rawpage = pyqtSignal(['PyQt_PyObject'])
    uv_signal = pyqtSignal(['PyQt_PyObject'])
    error = pyqtSignal(['QString'])
    done = pyqtSignal([int])

    def __init__(self, iconurl, baseurl, day_forecast_url, forecast6_url, id_,
                 suffix, parent=None):
        QThread.__init__(self, parent)
        self.wIconUrl = iconurl
        self.baseurl = baseurl
        self.day_forecast_url = day_forecast_url
        self.forecast6_url = forecast6_url
        self.id_ = id_
        self.suffix = suffix
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
            proxy_tot = 'http://' + ':' + proxy_port
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    'http://' + proxy_user + ':' + proxy_password
                    + '@' + proxy_url + ':' + proxy_port
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
            'Fetching url for 6 days :' + self.forecast6_url
            + self.id_ + self.suffix + '&cnt=7'
        )
        reqforecast6 = (
            self.forecast6_url + self.id_
            + self.suffix + '&cnt=7'
        )
        try:
            reqforecast6 = urllib.request.urlopen(
                self.forecast6_url + self.id_
                + self.suffix + '&cnt=7', timeout=5
            )
            pageforecast6 = reqforecast6.read()
            if str(pageforecast6).count('ClientError') > 0:
                raise TypeError
            treeforecast6 = etree.fromstring(pageforecast6)
            forcast6days = True
        except (
            urllib.error.HTTPError, urllib.error.URLError, etree.XMLSyntaxError, TypeError
        ) as e:
            forcast6days = False
            logging.error(' Url of 6 days forcast not available : ' + str(reqforecast6))
            logging.error('6 days forcast not available : ' + str(e))

        try:
            logging.debug(
                'Fetching url for actual weather: ' + self.baseurl
                + self.id_ + self.suffix
            )
            req = urllib.request.urlopen(
                self.baseurl + self.id_ + self.suffix, timeout=5)
            logging.debug(
                'Fetching url for forecast of the day + 4:'
                + self.day_forecast_url + self.id_ + self.suffix
            )
            reqdayforecast = urllib.request.urlopen(
                self.day_forecast_url + self.id_ + self.suffix, timeout=5)
            page = req.read()
            pagedayforecast = reqdayforecast.read()
            if self.html404(page, 'city'):
                raise urllib.error.HTTPError
            elif self.html404(pagedayforecast, 'day_forecast'):
                # Try with json
                logging.debug(
                    'Fetching json url for forecast of the day :'
                    + self.day_forecast_url + self.id_
                    + self.suffix.replace('xml', 'json')
                )
                reqdayforecast = urllib.request.urlopen(
                    self.day_forecast_url + self.id_
                    + self.suffix.replace('xml', 'json'), timeout=5
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
            tree = etree.fromstring(page)
            lat = tree[0][0].get('lat')
            lon = tree[0][0].get('lon')
            uv_ind = (lat, lon)
            self.uv_signal['PyQt_PyObject'].emit(uv_ind)
            if not use_json_day_forecast:
                treedayforecast = etree.fromstring(pagedayforecast)
            weather_icon = tree[8].get('icon')
            url = self.wIconUrl + weather_icon + '.png'
            logging.debug('Icon url: ' + url)
            data = urllib.request.urlopen(url).read()
            if self.html404(data, 'icon'):
                raise urllib.error.HTTPError
            self.xmlpage['PyQt_PyObject'].emit(tree)
            self.wimage['PyQt_PyObject'].emit(data)
            if forcast6days:
                self.forecast6_rawpage['PyQt_PyObject'].emit(treeforecast6)
            self.day_forecast_rawpage['PyQt_PyObject'].emit(treedayforecast)
            self.done.emit(int(done))
        except (
            urllib.error.HTTPError, urllib.error.URLError, TypeError
        ) as error:
            if self.tentatives >= 10:
                done = 1
                try:
                    m_error = (
                        self.tr('Error :\n') + str(error.code)
                        + ' ' + str(error.reason)
                    )
                except:
                    m_error = str(error)
                logging.error(m_error)
                self.error['QString'].emit(m_error)
                self.done.emit(int(done))
                return
            else:
                self.tentatives += 1
                logging.warn('Error: ' + str(error))
                logging.info('Try again...' + str(self.tentatives))
                self.run()
        except timeout:
            if self.tentatives >= 10:
                done = 1
                logging.error('Timeout error, abandon...')
                self.done.emit(int(done))
                return
            else:
                self.tentatives += 1
                logging.warn(
                    '5 secondes timeout, new tentative: '
                    + str(self.tentatives)
                )
                self.run()
        except (etree.XMLSyntaxError) as error:
            logging.critical('Error: ' + str(error))
            done = 1
            self.done.emit(int(done))

        logging.debug('Download thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error_message = code + ' ' + message + '@' + what
            logging.debug(str(self.error_message))
            return True
        except:
            return False


class Ozone(QThread):
    o3_signal = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, coord, parent=None):
        QThread.__init__(self, parent)
        self.coord = coord
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
            proxy_tot = 'http://' + ':' + proxy_port
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    'http://' + proxy_user + ':' + proxy_password
                    + '@' + proxy_url + ':' + proxy_port
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
            lat = self.coord[0]
            lon = self.coord[1]
            url = (
                'http://api.openweathermap.org/pollution/v1/o3/'
                + lat + ',' + lon
                + '/current.json?appid=' + self.appid
            )
            logging.debug('Fetching url for ozone index: ' + str(url))
            req = urllib.request.urlopen(url, timeout=5)
            page = req.read()
            dico_value = eval(page)
            o3_ind = dico_value['data']
            logging.debug('Ozone index: ' + str(o3_ind))
        except:
            o3_ind = '-'
            logging.error('Cannot find Ozone index')
        self.o3_signal['PyQt_PyObject'].emit(o3_ind)


class Uv(QThread):
    uv_signal = pyqtSignal(['PyQt_PyObject'])

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
            proxy_tot = 'http://' + ':' + proxy_port
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    'http://' + proxy_user + ':' + proxy_password
                    + '@' + proxy_url + ':' + proxy_port
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
            lat = self.uv_coord[0]
            lon = self.uv_coord[1]
            url = (
                'http://api.openweathermap.org/data/2.5/uvi?lat='
                + lat + '&lon=' + lon + '&appid=' + self.appid
            )
            logging.debug('Fetching url for uv index: ' + str(url))
            req = urllib.request.urlopen(url, timeout=5)
            page = req.read().decode('utf-8')
            dicUV = json.loads(page)
            uv_ind = dicUV['value']
            logging.debug('UV index: ' + str(uv_ind))
        except:
            uv_ind = '-'
            logging.error('Cannot find UV index')
        self.uv_signal['PyQt_PyObject'].emit(uv_ind)


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
                    'http://' + proxy_user + ':' + proxy_password
                    + '@' + proxy_url + ':' + proxy_port
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
                url = self.icon_url + self.icon[i] + '.png'
                logging.debug('Icon downloading: ' + url)
                data = urllib.request.urlopen(url, timeout=5).read()
                if self.html404(data, 'icon'):
                    self.url_error_signal['QString'].emit(self.error_message)
                    return
                self.wimage['PyQt_PyObject'].emit(data)
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            try:
                url_error = (
                    'Error: ' + str(error.code) + ': ' + str(error.reason)
                )
            except:
                url_error = error
            logging.error(str(url_error))
            self.url_error_signal['QString'].emit(url_error)
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
            self.error_message = code + ' ' + message + '@' + what
            logging.error(self.error_message)
            return True
        except:
            return False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName('meteo-qt')
    app.setOrganizationDomain('meteo-qt')
    app.setApplicationName('meteo-qt')
    app.setWindowIcon(QIcon(':/logo'))
    filePath = os.path.dirname(os.path.realpath(__file__))
    settings = QSettings()
    locale = settings.value('Language')
    if locale is None or locale == '':
        locale = QLocale.system().name()
    appTranslator = QTranslator()
    if os.path.exists(filePath + '/translations/'):
        appTranslator.load(
            filePath + "/translations/meteo-qt_" + locale
        )
    else:
        appTranslator.load(
            "/usr/share/meteo_qt/translations/meteo-qt_" + locale
        )
    app.installTranslator(appTranslator)
    qtTranslator = QTranslator()
    qtTranslator.load(
        "qt_" + locale, QLibraryInfo.location(
            QLibraryInfo.TranslationsPath
        )
    )
    app.installTranslator(qtTranslator)

    logLevel = settings.value('Logging/Level')
    if logLevel == '' or logLevel is None:
        logLevel = 'INFO'
        settings.setValue('Logging/Level', 'INFO')

    logPath = os.path.dirname(settings.fileName())
    logFile = logPath + '/meteo-qt.log'
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

    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s'
        '- %(lineno)s: %(module)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        filename=logFile, level=logLevel
    )
    logger = logging.getLogger('meteo-qt')
    logger.setLevel(logLevel)
    loggerStream = logging.getLogger()
    handlerStream = logging.StreamHandler()
    loggerStreamFormatter = logging.Formatter(
        '%(levelname)s: %(message)s - %(lineno)s :%(module)s'
    )
    handlerStream.setFormatter(loggerStreamFormatter)
    loggerStream.addHandler(handlerStream)

    m = SystemTrayIcon()
    app.exec_()


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

    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ' CRASH:'

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
    logFile = logPath + '/meteo-qt.log'
    with open(logFile, 'a') as logfile:
        logfile.write(msg)


sys.excepthook = excepthook

if __name__ == '__main__':
    main()
