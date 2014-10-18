#!/usr/bin/python3
# Purpose: System tray weather application
# Weather data: http://openweathermap.org
# Author: Dimitrios Glentadakis dglent@free.fr
# License: GPLv3

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import urllib.request
from lxml import etree
import platform
import qrc_resources
import settings
import overview
import searchcity


__version__ = "0.1.0"


class SystemTrayIcon(QMainWindow):

    def __init__(self, parent=None):
        super(SystemTrayIcon, self).__init__(parent)
        self.weatherDataDico = {}
        self.inerror = False
        self.forecast_inerror = False
        self.tentatives = 0
        self.baseurl = 'http://api.openweathermap.org/data/2.5/weather?id='
        self.accurate_url = 'http://api.openweathermap.org/data/2.5/find?q='
        self.forecast_url = 'http://api.openweathermap.org/data/2.5/forecast?id='
        self.wIconUrl = 'http://openweathermap.org/img/w/'
        self.timer = QTimer(self)
        QObject.connect(self.timer, SIGNAL("timeout()"), self.refresh)
        self.menu = QMenu()
        tempCityAction = QAction('&Temporary city', self)
        refreshAction = QAction('&Update', self)
        settingsAction = QAction('&Settings', self)
        aboutAction = QAction('&About', self)
        exitAction = QAction('Exit', self)
        exitAction.setIcon(QIcon(':/exit'))
        aboutAction.setIcon(QIcon(':/info'))
        refreshAction.setIcon(QIcon(':/refresh'))
        settingsAction.setIcon(QIcon(':/configure'))
        tempCityAction.setIcon(QIcon(':/tempcity'))
        self.menu.addAction(settingsAction)
        self.menu.addAction(refreshAction)
        self.menu.addAction(tempCityAction)
        self.menu.addAction(aboutAction)
        self.menu.addAction(exitAction)
        self.connect(settingsAction, SIGNAL('triggered()'), self.config)
        self.connect(exitAction, SIGNAL('triggered()'), qApp.quit)
        self.connect(refreshAction, SIGNAL('triggered()'), self.refresh)
        self.connect(aboutAction, SIGNAL('triggered()'), self.about)
        self.connect(tempCityAction, SIGNAL('triggered()'), self.tempcity)
        self.systray = QSystemTrayIcon()
        self.systray.activated.connect(self.activate)
        self.systray.setIcon(QIcon(':/noicon'))
        self.systray.setToolTip('Searching weather data...')
        self.systray.show()
        self.refresh()

    def refresh(self):
        self.systray.setToolTip('Fetching weather data ...')
        self.settings = QSettings()
        self.city = self.settings.value('City') or 'Kalamata'
        self.id_ = self.settings.value('ID')
        if self.id_ == None:
            self.timer.singleShot(10000, self.firsttime)
            self.id_ = '261604'
        self.country = self.settings.value('Country') or 'GR'
        self.lang = self.settings.value('Language') or 'en'
        lang_suffix = ('&lang=' + self.lang)
        self.unit = self.settings.value('Unit') or 'metric'
        self.suffix = ('&mode=xml&units=' + self.unit + lang_suffix)
        self.update()
        self.timer.start(1800000)

    def firsttime(self):
        self.systray.showMessage('meteo-qt:\n',
                                 'There is no any city configured\n' +
                                 'Right click on the icon and click on Settings')

    def update(self):
        print('update')
        self.wIcon = QPixmap(':/noicon')
        self.downloadThread = Download(
            self.wIconUrl, self.baseurl, self.forecast_url, self.id_, self.suffix)
        self.connect(self.downloadThread,
                     SIGNAL('wimage(PyQt_PyObject)'), self.makeicon)
        self.connect(self.downloadThread,
                     SIGNAL('finished()'), self.tray)
        self.connect(self.downloadThread,
                     SIGNAL('xmlpage(PyQt_PyObject)'), self.weatherdata)
        self.connect(self.downloadThread,
                     SIGNAL('forecast_rawpage(PyQt_PyObject)'), self.forecast)
        self.connect(self.downloadThread,
                     SIGNAL('error(QString)'), self.error)
        self.connect(self.downloadThread,
                     SIGNAL('done(int)'), self.done)
        self.downloadThread.start()

    def forecast(self, data):
        self.forecast_data = data

    def done(self, done):
        if done == 0:
            self.inerror = False
            self.tentatives = 0
        elif done == 1:
            self.systray.setIcon(QIcon(':/noicon'))
        try:
            if self.overviewcity.isVisible():
                self.overviewcity.hide()
                self.wIcon = self.updateicon
                self.overview()
        except:
            pass

    def error(self, error):
        print('error')
        what = error[error.find('@')+1:]
        if what == 'city':
                    self.inerror = True
        elif what == 'forecast':
            self.forecast_inerror = True
        elif what == 'icon':
            return
        self.systray.setToolTip('meteo-qt: Cannot find data!')
        if self.tentatives >= 10:
            mdialog = QMessageBox.critical(
                self, 'meteo-qt', error, QMessageBox.Ok)
            self.timer.start(1800000)
            self.tentatives = 0
        else:
            self.tentatives += 1
            self.timer.singleShot(2000, self.update)

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
        self.systray.setToolTip(self.city + ' '  + self.country + ' ' +
                                self.temp + ' ' + self.meteo)
        self.weatherDataDico['City'] = self.city
        self.weatherDataDico['Country'] = self.country
        self.weatherDataDico['Temp'] = self.tempFloat + '°'
        self.weatherDataDico['Meteo'] = self.meteo
        self.weatherDataDico['Humidity'] = tree[2].get('value'), tree[2].get('unit')
        self.weatherDataDico['Wind'] = (tree[4][0].get('value'), tree[4][0].get('name'),
                                        tree[4][1].get('value'), tree[4][1].get('code'),
                                        tree[4][1].get('name'))
        self.weatherDataDico['Clouds'] = tree[5].get('name')
        self.weatherDataDico['Pressure'] = tree[3].get('value'), tree[3].get('unit')
        self.weatherDataDico['Humidity'] = tree[2].get('value'), tree[2].get('unit')

    def tray(self):
        print('Paint tray icon')
        if self.inerror:
            return
        # Place empty.png here to initialize the icon
        # don't paint the T° over the old value
        self.icon = QPixmap(':/empty')
        pt = QPainter(self.icon)
        pt.drawPixmap(QPointF(1.0,0.0), self.wIcon)
        pt.setFont(QFont('sans-sertif', self.wIcon.width()*0.36,52))
        pt.drawText(self.icon.rect(), Qt.AlignBottom, str(self.temp))
        pt.end()
        self.systray.setIcon(QIcon(self.icon))

    def activate(self, reason):
        if reason == 3:
            try:
                if self.overviewcity.isVisible():
                    self.overviewcity.hide()
                else:
                    self.overview()
            except:
                self.overview()
        elif reason == 1:
            self.menu.popup(QCursor.pos())

    def overview(self):
        if self.inerror or len(self.weatherDataDico) == 0:
            return
        self.overviewcity = overview.OverviewCity(self.weatherDataDico, self.wIcon,
                                       self.forecast_inerror, self.forecast_data,
                                    self.unit, self)
        self.overviewcity.show()

    def config(self):
        dialog = settings.MeteoSettings(self.accurate_url, self)
        if dialog.exec_() == 0:
            (city, id_, country, lang, unit) = (self.settings.value('City'),
                                          self.settings.value('ID'),
                                          self.settings.value('Country'),
                                          self.settings.value('Language'),
                                          self.settings.value('Unit'))
            if (city == self.city and id_ == self.id_ and
                country == self.country and lang == self.lang and unit == self.unit):
                return
            else:
                self.refresh()

    def tempcity(self):
        dialog = searchcity.SearchCity(self.accurate_url, self)
        self.id_2, self.city2, self.country2 = (self.settings.value('ID'),
                                                self.settings.value('City'),
                                                self.settings.value('Country'))
        for e in 'id','city','country':
            self.connect(dialog, SIGNAL(e + '(PyQt_PyObject)'), self.citydata)
        if dialog.exec_():
            self.systray.setToolTip('Fetching weather data ...')
            self.refresh()
            # Restore the initial settings
            for e in ('ID', self.id_2), ('City', self.city2), ('Country', self.country2):
                self.citydata(e)

    def citydata(self, what):
        self.settings.setValue(what[0], what[1])
        print('write ', what[0], what[1])

    def about(self):
        QMessageBox.about(self, "Application for weather status information",
                        """<b>meteo-qt</b> v{0}
                        <p>Author: Dimitrios Glentadakis <a href="mailto:dglent@free.fr">dglent@free.fr</a>
                        <p>A simple application showing the weather status
                        <br/>information on the system tray.
                        <br/>Website: <a href="https://github.com/dglent/meteo-qt">
                        https://github.com/dglent/meteo-qt</a>
                        <br/>Data source: <a href="http://openweathermap.org/">
                        http://openweathermap.org/</a>.
                        <p>License: GPLv3 <br/>Python {1} - Qt {2} - PyQt {3} on {4}""".format(
                        __version__, platform.python_version(),
                        QT_VERSION_STR, PYQT_VERSION_STR, platform.system()))


class Download(QThread):
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
            reqforecast = urllib.request.urlopen(self.forecast_url + self.id_ + self.suffix)
            page = req.read()
            pageforecast = reqforecast.read()
            if self.html404(page, 'city'):
                self.emit(SIGNAL('error(QString)'), self.error)
                return
            elif self.html404(pageforecast, 'forecast'):
                self.emit(SIGNAL('error(QString)'), self.error)
                return
            tree = etree.fromstring(page)
            treeforecast = etree.fromstring(pageforecast)
            weather_icon = tree[8].get('icon')
            url = self.wIconUrl + weather_icon + '.png'
            data = urllib.request.urlopen(url).read()
            if self.html404(data, 'icon'):
                self.emit(SIGNAL('error(QString)'), self.error)
                done = 1
            self.emit(SIGNAL('xmlpage(PyQt_PyObject)'), tree)
            self.emit(SIGNAL('wimage(PyQt_PyObject)'), data)
            self.emit(SIGNAL('forecast_rawpage(PyQt_PyObject)'), treeforecast)
            self.emit(SIGNAL('done(int)'), int(done))
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            error = 'Error ' + str(error.code) + ' ' + str(error.reason)
            self.emit(SIGNAL('error(QString)'), error)
        print('Download thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error = code + ' ' + message + '@' + what
            print(self.error)
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
    m = SystemTrayIcon()
    app.exec_()

if __name__ == '__main__':
    main()

