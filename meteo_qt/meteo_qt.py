#!/usr/bin/python3
# Purpose: System tray weather application
# Weather data: http://openweathermap.org
# Author: Dimitrios Glentadakis dglent@free.fr
# License: GPLv3

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import urllib.request
from lxml import etree
import platform
import os
from functools import partial
import re
from socket import timeout

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


__version__ = "0.6.0"


class SystemTrayIcon(QMainWindow):
    def __init__(self, parent=None):
        super(SystemTrayIcon, self).__init__(parent)
        self.settings = QSettings()
        cond = conditions.WeatherConditions()
        self.temporary_city_status = False
        self.conditions = cond.trans
        self.clouds = cond.clouds
        self.wind = cond.wind
        self.wind_dir = cond.wind_direction
        self.wind_codes = cond.wind_codes
        self.weatherDataDico = {}
        self.inerror = False
        self.forecast_inerror = False
        self.dayforecast_inerror = False
        self.tentatives = 0
        self.done_tentatives = 0
        self.baseurl = 'http://api.openweathermap.org/data/2.5/weather?id='
        self.accurate_url = 'http://api.openweathermap.org/data/2.5/find?q='
        self.forecast_url = 'http://api.openweathermap.org/data/2.5/forecast/daily?id='
        self.day_forecast_url = 'http://api.openweathermap.org/data/2.5/forecast?id='
        self.wIconUrl = 'http://openweathermap.org/img/w/'
        self.forecast_icon_url = self.wIconUrl
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.menu = QMenu()
        self.citiesMenu = QMenu(self.tr('Cities'))
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
        self.refreshAction.triggered.connect(self.refresh)
        self.aboutAction.triggered.connect(self.about)
        self.tempCityAction.triggered.connect(self.tempcity)
        self.systray = QSystemTrayIcon()
        self.systray.setContextMenu(self.menu)
        self.systray.activated.connect(self.activate)
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip(self.tr('Searching weather data...'))
        self.systray.show()
        self.refresh()
        self.notification = ''
        self.notification_temp = 0
        self.notifications_id = ''

    def cities_menu(self):
        # Don't add the temporary city in the list
        if self.temporary_city_status:
            return
        self.citiesMenu.clear()
        cities = self.settings.value('CityList') or []
        if type(cities) is str:
            cities = eval(cities)
        current_city = (self.settings.value('City') + '_' +
                     self.settings.value('Country') + '_' +
                     self.settings.value('ID'))
        # Prevent duplicate entries
        try:
            city_toadd = cities.pop(cities.index(current_city))
        except:
            city_toadd = current_city
        finally:
            cities.insert(0, city_toadd)
        if cities != None and cities != '' and cities != '[]':
            if type(cities) is not list:
                #FIXME sometimes the list of cities is read as a string (?)
                # eval to a list
                cities = eval(cities)
            # Create the cities list menu
            for city in cities:
                action = QAction(city, self)
                action.triggered.connect(partial(self.changecity, city))
                self.citiesMenu.addAction(action)

    @pyqtSlot(str)
    def changecity(self, city):
        cities_list = self.settings.value('CityList')
        if cities_list == None:
            self.citiesMenu.addAction('Empty list')
        if type(cities_list) is not list:
            #FIXME some times is read as string (?)
            cities_list = eval(cities_list)
        prev_city = (self.settings.value('City') + '_' +
                     self.settings.value('Country') + '_' +
                     self.settings.value('ID'))
        citytoset = ''
        # Set the chosen city as the default
        for town in cities_list:
            if town == city:
                ind = cities_list.index(town)
                citytoset = cities_list[ind]
                citytosetlist = citytoset.split('_')
                self.settings.setValue('City', citytosetlist[0])
                self.settings.setValue('Country', citytosetlist[1])
                self.settings.setValue('ID', citytosetlist[2])
                if prev_city not in cities_list:
                    cities_list.append(prev_city)
                self.settings.setValue('CityList', cities_list)
                print(cities_list)
        self.refresh()

    def refresh(self):
        self.dayforecast_inerror = False
        self.systray.setIcon(QIcon(':/noicon'))
        if hasattr(self, 'overviewcity'):
            # if visible, it has to ...remain visible
            # (try reason) Prevent C++ wrapper error
            try:
                if not self.overviewcity.isVisible():
                    # kills the reference to overviewcity
                    # in order to be refreshed
                    self.overviewcity.close()
            except:
                pass
        self.systray.setToolTip(self.tr('Fetching weather data ...'))
        self.city = self.settings.value('City') or ''
        self.id_ = self.settings.value('ID') or None
        if self.id_ == None:
            # Clear the menu, no cities configured
            self.citiesMenu.clear()
            self.citiesMenu.addAction(self.tr('Empty list'))
            try:
                self.overviewcity.close()
            except:
                e = sys.exc_info()[0]
                print('Error: ', e )
                pass
            self.timer.singleShot(2000, self.firsttime)
            self.id_ = ''
            self.systray.setToolTip(self.tr('No city configured'))
            return
        # A city has been found, create the cities menu now
        self.cities_menu()
        self.country = self.settings.value('Country') or ''
        self.unit = self.settings.value('Unit') or 'metric'
        self.suffix = ('&mode=xml&units=' + self.unit)
        self.traycolor = self.settings.value('TrayColor') or ''
        self.interval = int(self.settings.value('Interval') or 30)*60*1000
        self.timer.start(self.interval)
        self.update()

    def firsttime(self):
        self.systray.showMessage('meteo-qt:\n',
                                 self.tr('No city has been configured yet.') + '\n' +
                                 self.tr('Right click on the icon and click on Settings.'))

    def update(self):
        print('Update...')
        self.wIcon = QPixmap(':/noicon')
        self.downloadThread = Download(self.wIconUrl, self.baseurl,
                                       self.forecast_url, self.day_forecast_url,
                                       self.id_, self.suffix)
        self.downloadThread.setTerminationEnabled(True)
        self.downloadThread.wimage['PyQt_PyObject'].connect(self.makeicon)
        self.downloadThread.finished.connect(self.tray)
        self.downloadThread.xmlpage['PyQt_PyObject'].connect(self.weatherdata)
        self.downloadThread.forecast_rawpage.connect(self.forecast)
        self.downloadThread.day_forecast_rawpage.connect(self.dayforecast)
        self.downloadThread.error.connect(self.error)
        self.downloadThread.done.connect(self.done, Qt.QueuedConnection)
        self.downloadThread.start()

    def forecast(self, data):
        self.forecast_data = data

    def dayforecast(self, data):
        self.dayforecast_data = data

    def instance_overviewcity(self):
        try:
            self.overviewcity = overview.OverviewCity(
                self.weatherDataDico, self.wIcon,
                self.forecast_inerror, self.forecast_data,
                self.dayforecast_inerror, self.dayforecast_data,
                self.unit, self.forecast_icon_url, self)
            self.done_tentatives = 0
        except:
            e = sys.exc_info()[0]
            print('Error: ', e )
            self.done_tentatives += 1
            print('Try to create the city overview...\nTentatives: ',
                  self.done_tentatives)
            return 'error'

    def done(self, done):
        if done == 0:
            self.inerror = False
            self.tentatives = 0
        elif done == 1:
            self.systray.setIcon(QIcon(':/noicon'))
            return
        if hasattr(self, 'updateicon'):
            # Keep a reference of the image to update the icon in overview
            self.wIcon = self.updateicon
        if hasattr(self, 'forecast_data'):
            if hasattr(self, 'overviewcity'):
                # Sometimes the overviewcity is in namespace but deleted:
                # RuntimeError: wrapped C/C++ object of type OverviewCity has been deleted
                try:
                    # Update also the overview dialog if open
                    if self.overviewcity.isVisible():
                        self.overviewcity.hide()
                        self.instance_overviewcity()
                        self.overview()
                except:
                    e = sys.exc_info()[0]
                    print('Error: ', e )
                    print('Overview instance has been deleted, try again...')
                    self.instance_overviewcity()
            else:
                instance = self.instance_overviewcity()
                if instance == 'error':
                    if self.done_tentatives < 10:
                        self.try_again()
                    else:
                        return
        else:
            if self.tentatives < 10:
                self.try_again()
            else:
                return

    def try_again(self):
        self.tentatives += 1
        print('Tentatives: ', self.tentatives)
        self.refresh()

    def error(self, error):
        print('Error:\n', error)
        nodata = self.tr('meteo-qt: Cannot find data!')
        self.systray.setToolTip(nodata)
        self.notification = nodata
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
        self.meteo = tree[8].get('value')
        meteo_condition = tree[8].get('number')
        try:
            self.meteo = self.conditions[meteo_condition]
        except:
            print('Cannot find localisation string for meteo_condition:',meteo_condition)
            pass
        clouds = tree[5].get('name')
        clouds_percent = tree[5].get('value') + '%'
        try:
            clouds = self.clouds[clouds]
            clouds = self.conditions[clouds]
        except:
            print('Cannot find localisation string for clouds:', clouds)
            pass
        wind = tree[4][0].get('name').lower()
        try:
            wind = self.wind[wind]
            wind = self.conditions[wind]
        except:
            print('Cannot find localisation string for wind:', wind)
            pass
        wind_codes = tree[4][1].get('code')
        try:
            wind_codes = self.wind_codes[wind_codes]
        except:
            print('Cannot find localisation string for wind_codes:', wind_codes)
            pass
        wind_dir = tree[4][1].get('name')
        try:
            wind_dir = self.wind_dir[tree[4][1].get('code')]
        except:
            print('Cannot find localisation string for wind_dir:', wind_dir)
            pass
        city_weather_info = (self.city + ' '  + self.country + ' ' + self.temp +
                             ' ' + self.meteo)
        self.systray.setToolTip(city_weather_info)
        self.notification = city_weather_info
        self.weatherDataDico['City'] = self.city
        self.weatherDataDico['Country'] = self.country
        self.weatherDataDico['Temp'] = self.tempFloat + '°'
        self.weatherDataDico['Meteo'] = self.meteo
        self.weatherDataDico['Humidity'] = tree[2].get('value'), tree[2].get('unit')
        self.weatherDataDico['Wind'] = (tree[4][0].get('value'), wind + '<br/>',
                                        tree[4][1].get('value'), wind_codes,
                                        wind_dir)
        self.weatherDataDico['Clouds'] = (clouds + '<br/>' + clouds_percent)
        self.weatherDataDico['Pressure'] = tree[3].get('value'), tree[3].get('unit')
        self.weatherDataDico['Humidity'] = tree[2].get('value'), tree[2].get('unit')
        self.weatherDataDico['Sunrise'] = tree[0][2].get('rise')
        self.weatherDataDico['Sunset'] = tree[0][2].get('set')

    def tray(self):
        if self.inerror or not hasattr(self, 'temp'):
            print('Cannot paint icon!')
            if hasattr(self, 'overviewcity'):
                try:
                    self.overviewcity.hide()
                except:
                    pass
            return
        print('Paint tray icon...')
        # Place empty.png here to initialize the icon
        # don't paint the T° over the old value
        self.icon = QPixmap(':/empty')
        pt = QPainter(self.icon)
        pt.drawPixmap(QPointF(1.0,0.0), self.wIcon)
        pt.setFont(QFont('sans-sertif', self.wIcon.width()*0.36,52))
        pt.setPen(QColor(self.traycolor))
        pt.drawText(self.icon.rect(), Qt.AlignBottom, str(self.temp))
        pt.end()
        self.systray.setIcon(QIcon(self.icon))
        try:
            if not self.overviewcity.isVisible():
                notifier = self.settings.value('Notifications') or 'True'
                notifier = eval(notifier)
                if notifier:
                    temp = int(re.search('\d+', self.temp).group())
                    if temp != self.notification_temp or self.id_ != self.notifications_id:
                        self.notifications_id = self.id_
                        self.notification_temp = temp
                        self.systray.showMessage('meteo-qt', self.notification)
        except:
            print('OverviewCity has been deleted',
                  'Download weather information again...')
            self.refresh()
            return
        self.restore_city()

    def restore_city(self):
        if self.temporary_city_status:
            print('Restore the default settings (city)',
                  'Forget the temporary city...')
            for e in ('ID', self.id_2), ('City', self.city2), ('Country', self.country2):
                self.citydata(e)
            self.temporary_city_status = False

    def activate(self, reason):
        if reason == 3:
            if self.inerror or self.id_ == None or self.id_ == '':
                return
            try:
                if hasattr(self, 'overviewcity') and self.overviewcity.isVisible():
                    self.overviewcity.hide()
                else:
                    self.overviewcity.hide()
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
        print('Config saving...')
        city = self.settings.value('City'),
        id_ = self.settings.value('ID')
        country = self.settings.value('Country')
        unit = self.settings.value('Unit')
        interval = self.settings.value('Interval')
        traycolor = self.settings.value('TrayColor')
        # Check if update is needed
        if traycolor == None:
            traycolor = ''
        if (city[0] == self.city and
           id_ == self.id_ and
           country == self.country and
           unit == self.unit and
           str(int(int(self.interval)/1000/60)) == interval and
           self.traycolor == traycolor):
            return
        else:
            self.refresh()

    def config(self):
        dialog = settings.MeteoSettings(self.accurate_url, self)
        dialog.applied_signal.connect(self.config_save)
        if dialog.exec_() == 1:
            self.config_save()
            print('Update Cities menu...')
            self.cities_menu()

    def tempcity(self):
        # Prevent to register a temporary city
        # This happen when a temporary city is still loading
        self.restore_city()
        dialog = searchcity.SearchCity(self.accurate_url, self)
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
        print('write ', what[0], what[1])

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

        contributors = self.tr("""Jürgen <a href="mailto:linux@psyca.de">linux@psyca.de</a><br/>
            [de] German translation
            <p>Dimitrios Glentadakis <a href="mailto:dglent@free.fr">dglent@free.fr</a><br/>
            [el] Greek translation
            <p>Ozkar L. Garcell <a href="mailto:ozkar.garcell@gmail.com">ozkar.garcell@gmail.com</a><br/>
            [es] Spanish translation
            <p>Laurene Albrand <a href="mailto:laurenealbrand@outlook.com">laurenealbrand@outlook.com</a><br/>
            [fr] French translation
            <p>Rémi Verschelde <a href="mailto:remi@verschelde.fr">remi@verschelde.fr</a><br/>
            [fr] French translation, Project
            <p>Daniel Napora <a href="mailto:napcok@gmail.com">napcok@gmail.com</a><br/>
            [pl] Polish translation
            <p>Artem Vorotnikov <a href="mailto:artem@vorotnikov.me">artem@vorotnikov.me</a><br/>
            [ru] Russian translation
            <p>Yuri Chornoivan <a href="mailto:yurchor@ukr.net">yurchor@ukr.net</a><br/>
            [uk] Ukranian translation
            <p>Atilla Öntaş <a href="mailto:tarakbumba@gmail.com">tarakbumba@gmail.com</a><br/>
            [tr] Turkish translation
            <p>You-Cheng Hsieh <a href="mailto:yochenhsieh@gmail.com">yochenhsieh@gmail.com</a><br/>
            [zh_TW] Chinese (Taiwan) translation
            <p>pmav99<br/>
            Project""")

        dialog = about_dlg.AboutDialog(title, text, image, contributors, self)
        dialog.exec_()


class Download(QThread):
    wimage = pyqtSignal(['PyQt_PyObject'])
    xmlpage = pyqtSignal(['PyQt_PyObject'])
    forecast_rawpage= pyqtSignal(['PyQt_PyObject'])
    day_forecast_rawpage = pyqtSignal(['PyQt_PyObject'])
    error = pyqtSignal(['QString'])
    done = pyqtSignal([int])

    def __init__(self, iconurl, baseurl, forecast_url, day_forecast_url, id_, suffix):
        QThread.__init__(self)
        self.wIconUrl = iconurl
        self.baseurl = baseurl
        self.forecast_url = forecast_url
        self.day_forecast_url = day_forecast_url
        self.id_ = id_
        self.suffix = suffix
        self.tentatives = 0

    #def __del__(self):
        #self.wait()

    def run(self):
        done = 0
        try:
            req = urllib.request.urlopen(self.baseurl + self.id_ + self.suffix, timeout=5)
            reqforecast = urllib.request.urlopen(self.forecast_url + self.id_ + self.suffix + '&cnt=7', timeout=5)
            reqdayforecast = urllib.request.urlopen(self.day_forecast_url + self.id_ + self.suffix, timeout=5)
            page = req.read()
            pageforecast = reqforecast.read()
            pagedayforecast = reqdayforecast.read()
            if self.html404(page, 'city'):
                raise urllib.error.HTTPError
            elif self.html404(pageforecast, 'forecast'):
                raise urllib.error.HTTPError
            elif self.html404(pagedayforecast, 'day_forecast'):
                raise urllib.error.HTTPError
            tree = etree.fromstring(page)
            treeforecast = etree.fromstring(pageforecast)
            treedayforecast = etree.fromstring(pagedayforecast)
            weather_icon = tree[8].get('icon')
            url = self.wIconUrl + weather_icon + '.png'
            data = urllib.request.urlopen(url).read()
            if self.html404(data, 'icon'):
                raise urllib.error.HTTPError
            self.xmlpage['PyQt_PyObject'].emit(tree)
            self.wimage['PyQt_PyObject'].emit(data)
            self.forecast_rawpage['PyQt_PyObject'].emit(treeforecast)
            self.day_forecast_rawpage['PyQt_PyObject'].emit(treedayforecast)
            self.done.emit(int(done))
        except (urllib.error.HTTPError, urllib.error.URLError, TypeError) as error:
            if self.tentatives >= 10:
                done = 1
                code = ''
                m_error = error
                if hasattr(error, 'code'):
                    code = str(error.code)
                    print(code, error.reason)
                    m_error = self.tr('Error :\n') + code + ' ' + str(error.reason)
                else:
                    print(m_error)
                self.error['QString'].emit(m_error)
                self.done.emit(int(done))
                return
            else:
                self.tentatives += 1
                print('Error: ', error)
                print('Try again...', self.tentatives)
                self.run()
        except timeout:
            if self.tentatives >= 10:
                done = 1
                print('Timeout error, abandon...')
                self.done.emit(int(done))
                return
            else:
                self.tentatives += 1
                print('5 secondes timeout, new tentative: ', self.tentatives)
                self.run()
        print('Download thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error_message = code + ' ' + message + '@' + what
            print(self.error_message)
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
    if locale == None or locale == '':
        locale = QLocale.system().name()
    appTranslator = QTranslator()
    if os.path.exists(filePath + '/translations/'):
        appTranslator.load(filePath + "/translations/meteo-qt_" + locale)
    else:
        appTranslator.load("/usr/share/meteo_qt/translations/meteo-qt_" + locale)
    app.installTranslator(appTranslator)
    qtTranslator = QTranslator()
    qtTranslator.load("qt_" + locale,
                      QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtTranslator)
    m = SystemTrayIcon()
    app.exec_()

if __name__ == '__main__':
    main()

