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


__version__ = "0.4.0"


class SystemTrayIcon(QMainWindow):
    def __init__(self, parent=None):
        super(SystemTrayIcon, self).__init__(parent)
        cond = conditions.WeatherConditions()
        self.conditions = cond.trans
        self.clouds = cond.clouds
        self.wind = cond.wind
        self.wind_dir = cond.wind_direction
        self.wind_codes = cond.wind_codes
        self.weatherDataDico = {}
        self.inerror = False
        self.forecast_inerror = False
        self.tentatives = 0
        self.baseurl = 'http://api.openweathermap.org/data/2.5/weather?id='
        self.accurate_url = 'http://api.openweathermap.org/data/2.5/find?q='
        self.forecast_url = 'http://api.openweathermap.org/data/2.5/forecast/daily?id='
        self.wIconUrl = 'http://openweathermap.org/img/w/'
        self.forecats_icon_url = self.wIconUrl
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
        self.systray.activated.connect(self.activate)
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip(self.tr('Searching weather data...'))
        self.systray.show()
        self.refresh()

    def cities_menu(self):
        self.citiesMenu.clear()
        cities = self.settings.value('CityList')
        if cities != None and cities != '' and cities != '[]':
            if type(cities) is not list:
                cities = eval(cities)
            for city in cities:
                action = QAction(city, self)
                action.triggered.connect(partial(self.changecity, city))
                self.citiesMenu.addAction(action)
        else:
            self.citiesMenu.addAction(self.tr('Empty list'))
            return

    @pyqtSlot(str)
    def changecity(self, city):
        cities_list = self.settings.value('CityList')
        if cities_list == None:
            self.citiesMenu.addAction('Empty list')
        if type(cities_list) is not list:
            cities_list = eval(cities_list)
        prev_city = (self.settings.value('City') + '_' +
                     self.settings.value('Country') + '_' +
                     self.settings.value('ID'))
        citytoset = ''
        for town in cities_list:
            if town == city:
                ind = cities_list.index(town)
                citytoset = cities_list.pop(ind)
                citytosetlist = citytoset.split('_')
                self.settings.setValue('City', citytosetlist[0])
                self.settings.setValue('Country', citytosetlist[1])
                self.settings.setValue('ID', citytosetlist[2])
                cities_list.append(prev_city)
                self.settings.setValue('CityList', cities_list)
        self.refresh()


    def refresh(self):
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
        self.settings = QSettings()
        self.cities_menu()
        self.city = self.settings.value('City') or ''
        self.id_ = self.settings.value('ID')
        if self.id_ == None:
            self.timer.singleShot(2000, self.firsttime)
            self.id_ = ''
            self.systray.setToolTip(self.tr('No city configured'))
            return
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
        print('update')
        self.wIcon = QPixmap(':/noicon')
        self.downloadThread = Download(
            self.wIconUrl, self.baseurl, self.forecast_url, self.id_, self.suffix)
        self.downloadThread.wimage['PyQt_PyObject'].connect(self.makeicon)
        self.downloadThread.finished.connect(self.tray)
        self.downloadThread.xmlpage['PyQt_PyObject'].connect(self.weatherdata)
        self.downloadThread.forecast_rawpage.connect(self.forecast)
        self.downloadThread.error.connect(self.error)
        self.downloadThread.done.connect(self.done)
        self.downloadThread.start()

    def forecast(self, data):
        self.forecast_data = data

    def done(self, done):
        if done == 0:
            self.inerror = False
            self.tentatives = 0
        elif done == 1:
            self.systray.setIcon(QIcon(':/noicon'))
        if hasattr(self, 'updateicon'):
            # Keep a reference of the image to update the icon in overview
            self.wIcon = self.updateicon
        # Update also the overview dialog if open
        try:
            if self.overviewcity.isVisible():
                self.overviewcity.hide()
                if hasattr(self, 'forecast_data'):
                    self.overviewcity = overview.OverviewCity(
                        self.weatherDataDico, self.wIcon,
                        self.forecast_inerror, self.forecast_data,
                        self.unit, self.forecats_icon_url, self)
                    self.overview()
                else:
                    return
        except:
            if hasattr(self, 'forecast_data'):
                self.overviewcity = overview.OverviewCity(
                    self.weatherDataDico, self.wIcon, self.forecast_inerror,
                    self.forecast_data, self.unit, self.forecats_icon_url,
                    self)
            else:
                return

    def error(self, error):
        print(self.tentatives)
        print('Error:\n', error)
        what = error[error.find('@')+1:]
        if what == 'city':
                    self.inerror = True
        elif what == 'forecast':
            self.forecast_inerror = True
        elif what == 'icon':
            return
        self.systray.setToolTip(self.tr('meteo-qt: Cannot find data!'))
        if self.tentatives >= 10:
            mdialog = QMessageBox.critical(
                self, 'meteo-qt', error, QMessageBox.Ok)
            self.timer.start(self.interval)
            self.inerror = True
            self.tentatives = 0
        else:
            self.tentatives += 1
            self.timer.singleShot(5000, self.update)
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
        self.systray.setToolTip(self.city + ' '  + self.country + ' ' +
                                self.temp + ' ' + self.meteo)
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
        if self.inerror:
            return
        print('Paint tray icon')
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

    def activate(self, reason):
        if reason == 3:
            if self.inerror:
                return
            try:
                if self.overviewcity.isVisible():
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

    def tempcity(self):
        dialog = searchcity.SearchCity(self.accurate_url, self)
        self.id_2, self.city2, self.country2 = (self.settings.value('ID'),
                                                self.settings.value('City'),
                                                self.settings.value('Country'))
        dialog.id_signal[tuple].connect(self.citydata)
        dialog.city_signal[tuple].connect(self.citydata)
        dialog.country_signal[tuple].connect(self.citydata)
        if dialog.exec_():
            self.systray.setToolTip(self.tr('Fetching weather data...'))
            self.refresh()
            # Restore the initial settings
            for e in ('ID', self.id_2), ('City', self.city2), ('Country', self.country2):
                self.citydata(e)

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
                        <br/>Website: <a href="https://github.com/dglent/meteo-qt">
                        https://github.com/dglent/meteo-qt</a>
                        <br/>Data source: <a href="http://openweathermap.org/">
                        http://openweathermap.org/</a>.
                        <p>To translate meteo-qt in your language or contribute to
                        current translations, you can either do it directly in
                        github by sending a pull request, or choose the file
                        of the language you want to translate from here:
                        <a href="https://github.com/dglent/meteo-qt/tree/master/meteo_qt/translations">
                        https://github.com/dglent/meteo-qt/tree/master/meteo_qt/translations</a>
                        and send me the file by email.
                        <p>If you want to report a dysfunction or a suggestion,
                        feel free to open an <a href="https://github.com/dglent/meteo-qt/issues">
                        issue</a> in github.""")

        contributors = self.tr("""Jürgen <a href="mailto:linux@psyca.de">linux@psyca.de</a><br/>
            [de] German translation
            <p>Dimitrios Glentadakis <a href="mailto:dglent@free.fr">dglent@free.fr</a><br/>
            [el] Greek translation
            <p>Rémi Verschelde <a href="mailto:remi@verschelde.fr">remi@verschelde.fr</a><br/>
            [fr] French translation, Project
            <p>Yuri Chornoivan <a href="mailto:yurchor@ukr.net">yurchor@ukr.net</a><br/>
            [uk] Ukranian translation
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
    error = pyqtSignal(['QString'])
    done = pyqtSignal([int])

    def __init__(self, iconurl, baseurl, forecast_url, id_, suffix):
        QThread.__init__(self)
        self.wIconUrl = iconurl
        self.baseurl = baseurl
        self.forecast_url = forecast_url
        self.id_ = id_
        self.suffix = suffix

    def __del__(self):
        self.wait()

    def run(self):
        done = False
        done = 0
        try:
            req = urllib.request.urlopen(self.baseurl + self.id_ + self.suffix)
            reqforecast = urllib.request.urlopen(self.forecast_url + self.id_ + self.suffix + '&cnt=7')
            page = req.read()
            pageforecast = reqforecast.read()
            if self.html404(page, 'city'):
                self.error['QString'].emit(self.error_message)
                return
            elif self.html404(pageforecast, 'forecast'):
                self.errror['QString'].emit(self.error_message)
                return
            tree = etree.fromstring(page)
            treeforecast = etree.fromstring(pageforecast)
            weather_icon = tree[8].get('icon')
            url = self.wIconUrl + weather_icon + '.png'
            data = urllib.request.urlopen(url).read()
            if self.html404(data, 'icon'):
                self.error['QString'].emit(self.error_message)
                done = 1
            self.xmlpage['PyQt_PyObject'].emit(tree)
            self.wimage['PyQt_PyObject'].emit(data)
            self.forecast_rawpage['PyQt_PyObject'].emit(treeforecast)
            self.done.emit(int(done))
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            code = ''
            if hasattr(error, 'code'):
                code = str(error.code)
            print(code, error.reason)
            m_error = self.tr('Error :\n') + code + ' ' + str(error.reason)
            self.error['QString'].emit(m_error)
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

