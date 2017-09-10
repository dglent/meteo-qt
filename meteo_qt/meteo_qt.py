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

from PyQt5.QtCore import (PYQT_VERSION_STR, QT_VERSION_STR, QCoreApplication,
                          QLibraryInfo, QLocale, QSettings, Qt, QThread,
                          QTimer, QTranslator, pyqtSignal, pyqtSlot)
from PyQt5.QtGui import (QColor, QCursor, QFont, QIcon, QImage, QMovie,
                         QPainter, QPixmap)
from PyQt5.QtWidgets import (QAction, QApplication, QMainWindow, QMenu,
                             QSystemTrayIcon, qApp)

try:
    import qrc_resources
    import settings
    import overview
    import searchcity
    import conditions
    import about_dlg
except:
    from meteo_qt import qrc_resources
    from meteo_qt import settings
    from meteo_qt import overview
    from meteo_qt import searchcity
    from meteo_qt import conditions
    from meteo_qt import about_dlg


__version__ = "0.9.7"


class SystemTrayIcon(QMainWindow):
    def __init__(self, parent=None):
        super(SystemTrayIcon, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.settings = QSettings()
        self.language = self.settings.value('Language') or ''
        self.temp_decimal_bool = self.settings.value('Decimal') or False
        # initialize the tray icon type in case of first run: issue#42
        self.tray_type = self.settings.value('TrayType') or 'icon&temp'
        cond = conditions.WeatherConditions()
        self.temporary_city_status = False
        self.conditions = cond.trans
        self.clouds = cond.clouds
        self.wind = cond.wind
        self.wind_dir = cond.wind_direction
        self.wind_codes = cond.wind_codes
        self.inerror = False
        self.tentatives = 0
        self.baseurl = 'http://api.openweathermap.org/data/2.5/weather?id='
        self.accurate_url = 'http://api.openweathermap.org/data/2.5/find?q='
        self.day_forecast_url = ('http://api.openweathermap.org/data/2.5/forecast?id=')
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
            self.panelAction = QAction(QCoreApplication.translate(
                                "Tray context menu", "Toggle Window",
                                "Open/closes the application window"), self)
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
        self.refresh()

    def icon_loading(self):
        self.gif_loading = QMovie(":/loading")
        self.gif_loading.frameChanged.connect(self.update_gif)
        self.gif_loading.start()

    def update_gif(self):
        gif_frame = self.gif_loading.currentPixmap()
        self.systray.setIcon(QIcon(gif_frame))

    def manual_refresh(self):
        self.tentatives = 0
        self.refresh()

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
            current_city = (self.settings.value('City') + '_' +
                        self.settings.value('Country') + '_' +
                        self.settings.value('ID'))
        except:
            # firsttime run,if clic cancel in settings without any city configured
            pass
        # Prevent duplicate entries
        try:
            city_toadd = cities.pop(cities.index(current_city))
        except:
            city_toadd = current_city
        finally:
            cities.insert(0, city_toadd)
        # If we delete all cities it results to a '__'
        if (cities is not None and cities != '' and cities != '[]' and
                cities != ['__']):
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
        cities_list = self.settings.value('CityList')
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        self.cities_trans_dict = eval(cities_trans)
        logging.debug('Cities' + str(cities_list))
        if cities_list is None:
            self.empty_cities_list()
        if type(cities_list) is not list:
            # FIXME some times is read as string (?)
            cities_list = eval(cities_list)
        prev_city = (self.settings.value('City') + '_' +
                     self.settings.value('Country') + '_' +
                     self.settings.value('ID'))
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
        for key,value in self.cities_trans_dict.items():
            if value == city:
                return key
        return city

    def empty_cities_list(self):
        self.citiesMenu.addAction(self.tr('Empty list'))

    def refresh(self):
        self.inerror = False
        self.window_visible = False
        self.systray.setIcon(QIcon(':/noicon'))
        if hasattr(self, 'overviewcity'):
            # if visible, it has to ...remain visible
            # (try reason) Prevent C++ wrapper error
            try:
                if not self.overviewcity.isVisible():
                    # kills the reference to overviewcity
                    # in order to be refreshed
                    self.overviewcity.close()
                    del self.overviewcity
                else:
                    self.overviewcity.close()
                    self.window_visible = True
            except:
                pass
        self.systray.setToolTip(self.tr('Fetching weather data ...'))
        self.city = self.settings.value('City') or ''
        self.id_ = self.settings.value('ID') or None
        if self.id_ is None:
            # Clear the menu, no cities configured
            self.citiesMenu.clear()
            self.empty_cities_list()
            # Sometimes self.overviewcity is in namespace but deleted
            try:
                self.overviewcity.close()
            except:
                e = sys.exc_info()[0]
                logging.error('Error closing overviewcity: ' + str(e))
                pass
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
        self.interval = int(self.settings.value('Interval') or 30)*60*1000
        self.timer.start(self.interval)
        self.update()

    def firsttime(self):
        self.temp = ''
        self.wIcon = QPixmap(':/noicon')
        self.systray.showMessage(
            'meteo-qt:\n', self.tr('No city has been configured yet.') +
            '\n' + self.tr('Right click on the icon and click on Settings.'))

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
            self.id_, self.suffix)
        self.downloadThread.wimage['PyQt_PyObject'].connect(self.makeicon)
        self.downloadThread.finished.connect(self.tray)
        self.downloadThread.xmlpage['PyQt_PyObject'].connect(self.weatherdata)
        self.downloadThread.day_forecast_rawpage.connect(self.dayforecast)
        self.downloadThread.uv_signal.connect(self.uv)
        self.downloadThread.error.connect(self.error)
        self.downloadThread.done.connect(self.done, Qt.QueuedConnection)
        self.downloadThread.start()

    def uv(self, value):
        self.uv_coord = value

    def dayforecast(self, data):
        if type(data) == dict:
            self.json_data_bool = True
        else:
            self.json_data_bool = False
        self.dayforecast_data = data

    def instance_overviewcity(self):
        try:
            self.inerror = False
            if hasattr(self, 'overviewcity'):
                logging.debug('Deleting overviewcity instance...')
                del self.overviewcity
            self.overviewcity = overview.OverviewCity(
                self.weatherDataDico, self.wIcon,
                self.dayforecast_data, self.json_data_bool, self.unit, self.forecast_icon_url,
                self.uv_coord, self.hPaTrend, self.temp_trend, self)
            self.overviewcity.closed_status_dialogue.connect(self.remove_object)
        except:
            self.inerror = True
            e = sys.exc_info()[0]
            logging.error('Error: ' + str(e))
            logging.debug('Try to create the city overview...\nAttempts: ' +
                          str(self.tentatives))
            return 'error'

    def remove_object(self):
        del self.overviewcity

    def done(self, done):
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
            if hasattr(self, 'overviewcity'):
                try:
                    # Update also the overview dialog if open
                    if self.overviewcity.isVisible():
                        # delete dialog to prevent memory leak
                        self.overviewcity.close()
                        self.instance_overviewcity()
                        self.overview()
                except:
                    # if the dialogue has been closed by the 'X' button
                    # remove the delelted window object from memory
                    # RuntimeError: wrapped C/C++ object of type OverviewCity has been deleted
                    self.remove_object()
                    self.instance_overviewcity()
            elif self.window_visible is True:
                self.instance_overviewcity()
                self.overview()
            else:
                self.inerror = True
                self.try_create_overview()
        else:
            self.try_again()

    def try_create_overview(self):
        logging.debug('Tries to create overview :' + str(self.tentatives))
        instance = self.instance_overviewcity()
        if instance == 'error':
            self.inerror = True
            self.refresh()
        else:
            self.tentatives = 0
            self.inerror = False
            self.tooltip_weather()

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
            logging.debug('Cannot find localisation string for clouds:' +
                          str(clouds))
            pass
        wind = tree[4][0].get('name').lower()
        try:
            wind = self.wind[wind]
            wind = self.conditions[wind]
        except:
            logging.debug('Cannot find localisation string for wind:' +
                          str(wind))
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
            logging.debug('Cannot find localisation string for wind_codes:' +
                          str(wind_codes))
            pass
        try:
            wind_dir = self.wind_dir[tree[4][2].get('code')]
        except:
            logging.debug('Cannot find localisation string for wind_dir:' +
                          str(wind_dir))
            pass
        self.city_weather_info = (self.city + ' ' + self.country + ' ' +
                                  self.temp_decimal + ' ' + self.meteo)
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
        if rain_value == None:
            rain_value = ''
        self.weatherDataDico['Precipitation'] = (tree[7].get('mode'), rain_value)
        if self.id_ not in self.trendCities_dic:
            # dict {'id': 'hPa', 'T°'}
            self.trendCities_dic[self.id_] = [''] * 2
        # hPa self.temp_trend
        pressure = int(self.weatherDataDico['Pressure'][0])
        if self.id_ in self.trendCities_dic and self.trendCities_dic[self.id_][0] is not '':
            self.hPaTrend = pressure - int(self.trendCities_dic[self.id_][0])
        else:
            self.hPaTrend = 0
        self.trendCities_dic[self.id_][0] = pressure
        # Temperature trend
        self.notifier()

    def tooltip_weather(self):
        # Creation of the tray tootltip
        trans_cities = self.settings.value('CitiesTranslation') or '{}'
        trans_cities_dict = eval(trans_cities)
        city = self.city + '_' + self.country + '_' + self.id_
        if city in trans_cities_dict:
            self.city_weather_info = (trans_cities_dict[city] +
                                      ' ' + self.temp_decimal +
                                      ' ' + self.meteo)
        else:
            self.city_weather_info = (self.city + ' ' + self.country + ' ' +
                                  self.temp_decimal + ' ' + self.meteo)

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
            if hasattr(self, 'overviewcity'):
                try:
                    # delete dialog to prevent memory leak
                    self.overviewcity.close()
                except:
                    pass
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
            if (self.temp_trend != '' or self.trendCities_dic[self.id_][1] ==
                    '' or self.id_ != self.notifier_id):
                try:
                    if not self.overviewcity.isVisible():
                        self.systray.showMessage('meteo-qt', self.notification +
                                                 self.temp_trend)
                except AttributeError:
                    logging.debug('!!! OverviewCity in garbages, try again...')
                    self.systray.showMessage('meteo-qt', self.notification +
                                             self.temp_trend)
                    self.try_again()
                    return
        self.notifier_id = self.id_
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

    def notifier(self):
        ''' The notification is being shown:
        On a city change or first launch or if the temperature changes
        The notification is not shown if is turned off from the settings.
        The tray tooltip is set here '''
        self.temp_trend = ''
        temp = float(self.tempFloat)
        # if self.notifier_settings():
        if (self.id_ in self.trendCities_dic and
                self.trendCities_dic[self.id_][1] is not ''):
            if temp > float(self.trendCities_dic[self.id_][1]):
                self.temp_trend = " "
            elif temp < float(self.trendCities_dic[self.id_][1]):
                self.temp_trend = " "
        self.trendCities_dic[self.id_][1] = temp
        self.systray.setToolTip(self.city_weather_info + self.temp_trend)

    def restore_city(self):
        if self.temporary_city_status:
            logging.debug('Restore the default settings (city)' +
                          'Forget the temporary city...')
            for e in ('ID', self.id_2), ('City', self.city2), ('Country', self.country2):
                self.citydata(e)
            self.temporary_city_status = False

    def showpanel(self):
        self.activate(3)

    def activate(self, reason):
        if reason == 3:
            if self.inerror or self.id_ is None or self.id_ == '':
                return
            try:
                if hasattr(self, 'overviewcity') and self.overviewcity.isVisible():
                    self.overviewcity.hide()
                else:
                    self.overviewcity.hide()
                    # If dialog closed by the "X"
                    self.done(0)
                    self.overview()
            except:
                self.done(0)
                self.overview()
        elif reason == 1:
            self.menu.popup(QCursor.pos())

    def overview(self):
        if self.inerror or len(self.weatherDataDico) == 0:
            return
        self.overviewcity.show()

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
            self.systray.showMessage('meteo-qt:',QCoreApplication.translate(
                    "System tray notification",
                    "The application has to be restarted to apply the language setting", ''))
            self.language = language
        # Check if update is needed
        if traycolor is None:
            traycolor = ''
        if (self.traycolor != traycolor or self.tray_type != tray_type or
                self.fontsize != fontsize or self.bold_set != bold_set or
                decimal != self.temp_decimal):
            self.tray()
        if (city[0] == self.city and
           id_ == self.id_ and
           country == self.country and
           unit == self.unit and
           beaufort == self.beaufort):
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
        title = self.tr("""<b>meteo-qt</b> v{0}
            <br/>License: GPLv3
            <br/>Python {1} - Qt {2} - PyQt {3} on {4}""").format(
                __version__, platform.python_version(),
                QT_VERSION_STR, PYQT_VERSION_STR, platform.system())
        image = ':/logo'
        text = self.tr("""<p>Author: Dimitrios Glentadakis <a href="mailto:dglent@free.fr">dglent@free.fr</a>
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
                        feel free to open an issue in <a href="https://github.com/dglent/meteo-qt/issues">
                        github</a>.""")

        contributors = QCoreApplication.translate("About dialog", """
            Pavel Fric<br/>
            [cs] Czech translation
            <p>Jürgen <a href="mailto:linux@psyca.de">linux@psyca.de</a><br/>
            [de] German translation
            <p>Peter Mattern <a href="mailto:pmattern@arcor.de">pmattern@arcor.de</a><br/>
            [de] German translation, Project
            <p>Dimitrios Glentadakis <a href="mailto:dglent@free.fr">dglent@free.fr</a><br/>
            [el] Greek translation
            <p> juancarlospaco <a href="mailto:JuanCarlosPaco@gmail.com">JuanCarlosPaco@gmail.com</a><br/>
            [es] Spanish translation, Project
            <p>Ozkar L. Garcell <a href="mailto:ozkar.garcell@gmail.com">ozkar.garcell@gmail.com</a><br/>
            [es] Spanish translation
            <p>Laurene Albrand <a href="mailto:laurenealbrand@outlook.com">laurenealbrand@outlook.com</a><br/>
            [fr] French translation
            <p>Rémi Verschelde <a href="mailto:remi@verschelde.fr">remi@verschelde.fr</a><br/>
            [fr] French translation, Project
            <p>Daniel Napora <a href="mailto:napcok@gmail.com">napcok@gmail.com</a><br/>
            Tomasz Przybył <a href="mailto:fademind@gmail.com">fademind@gmail.com</a><br/>
            [pl] Polish translation
            <p>Artem Vorotnikov <a href="mailto:artem@vorotnikov.me">artem@vorotnikov.me</a><br/>
            [ru] Russian translation
            <p>Atilla Öntaş <a href="mailto:tarakbumba@gmail.com">tarakbumba@gmail.com</a><br/>
            [tr] Turkish translation
            <p>Yuri Chornoivan <a href="mailto:yurchor@ukr.net">yurchor@ukr.net</a><br/>
            [uk] Ukrainian translation
            <p>You-Cheng Hsieh <a href="mailto:yochenhsieh@gmail.com">yochenhsieh@gmail.com</a><br/>
            [zh_TW] Chinese (Taiwan) translation
            <p>pmav99<br/>
            Project""", "List of contributors")

        dialog = about_dlg.AboutDialog(title, text, image, contributors, self)
        dialog.exec_()


class Download(QThread):
    wimage = pyqtSignal(['PyQt_PyObject'])
    xmlpage = pyqtSignal(['PyQt_PyObject'])
    forecast_rawpage = pyqtSignal(['PyQt_PyObject'])
    day_forecast_rawpage = pyqtSignal(['PyQt_PyObject'])
    uv_signal = pyqtSignal(['PyQt_PyObject'])
    error = pyqtSignal(['QString'])
    done = pyqtSignal([int])

    def __init__(self, iconurl, baseurl, day_forecast_url, id_,
                 suffix, parent=None):
        QThread.__init__(self, parent)
        self.wIconUrl = iconurl
        self.baseurl = baseurl
        self.day_forecast_url = day_forecast_url
        self.id_ = id_
        self.suffix = suffix
        self.tentatives = 0
        self.settings = QSettings()

    def run(self):
        use_json_day_forecast = False
        use_proxy = self.settings.value('Proxy') or 'False'
        use_proxy = eval(use_proxy)
        proxy_auth = self.settings.value('Use_proxy_authentification') or 'False'
        proxy_auth = eval(proxy_auth)
        if use_proxy:
            proxy_url = self.settings.value('Proxy_url')
            proxy_port = self.settings.value('Proxy_port')
            proxy_tot = 'http://' + ':' + proxy_port
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = 'http://' + proxy_user + ':' + proxy_password + '@' + proxy_url + ':' + proxy_port
            proxy = urllib.request.ProxyHandler({"http":proxy_tot})
            auth = urllib.request.HTTPBasicAuthHandler()
            opener = urllib.request.build_opener(proxy, auth, urllib.request.HTTPHandler)
            urllib.request.install_opener(opener)
        else:
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
        done = 0
        try:
            logging.debug('Fetching url for actual weather: ' + self.baseurl +
                          self.id_ + self.suffix)
            req = urllib.request.urlopen(
                self.baseurl + self.id_ + self.suffix, timeout=5)
            logging.debug('Fetching url for forecast of the day + 4:' +
                          self.day_forecast_url + self.id_ + self.suffix)
            reqdayforecast = urllib.request.urlopen(
                self.day_forecast_url + self.id_ + self.suffix, timeout=5)
            page = req.read()
            pagedayforecast = reqdayforecast.read()
            if self.html404(page, 'city'):
                raise urllib.error.HTTPError
            elif self.html404(pagedayforecast, 'day_forecast'):
                # Try with json
                logging.debug('Fetching json url for forecast of the day :' +
                          self.day_forecast_url + self.id_ + self.suffix.replace('xml', 'json'))
                reqdayforecast = urllib.request.urlopen(
                        self.day_forecast_url + self.id_ +
                        self.suffix.replace('xml', 'json'), timeout=5)
                pagedayforecast = reqdayforecast.read().decode('utf-8')
                if self.html404(pagedayforecast, 'day_forecast'):
                    raise urllib.error.HTTPError
                else:
                    treedayforecast = json.loads(pagedayforecast)
                    use_json_day_forecast = True
                    logging.debug('Found json page for the forecast of the day')
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
            self.day_forecast_rawpage['PyQt_PyObject'].emit(treedayforecast)
            self.done.emit(int(done))
        except (urllib.error.HTTPError, urllib.error.URLError, TypeError) as error:
            if self.tentatives >= 10:
                done = 1
                try:
                    m_error = self.tr('Error :\n') + str(error.code) + ' ' + str(error.reason)
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
                logging.warn('5 secondes timeout, new tentative: ' +
                             str(self.tentatives))
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
        appTranslator.load(filePath + "/translations/meteo-qt_" + locale)
    else:
        appTranslator.load("/usr/share/meteo_qt/translations/meteo-qt_" +
                           locale)
    app.installTranslator(appTranslator)
    qtTranslator = QTranslator()
    qtTranslator.load("qt_" + locale,
                      QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtTranslator)

    log_level = settings.value('Logging/Level')
    if log_level == '' or log_level is None:
        log_level = 'INFO'
        settings.setValue('Logging/Level', 'INFO')

    log_filename = os.path.dirname(settings.fileName())
    if not os.path.exists(log_filename):
        os.makedirs(log_filename)
    log_filename = log_filename + '/meteo-qt.log'

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s - %(module)s - %(name)s',
                        datefmt='%m/%d/%Y %H:%M:%S',
                        filename=log_filename, level=log_level)
    logger = logging.getLogger('meteo-qt')
    logger.setLevel(log_level)
    handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=20, backupCount=5)
    logger1 = logging.getLogger()
    handler1 = logging.StreamHandler()
    logger1Formatter = logging.Formatter('%(levelname)s: %(message)s - %(module)s')
    handler1.setFormatter(logger1Formatter)
    logger.addHandler(handler)
    logger1.addHandler(handler1)

    m = SystemTrayIcon()
    app.exec_()

if __name__ == '__main__':
    main()
