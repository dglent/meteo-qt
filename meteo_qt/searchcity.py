import logging
import urllib.request
from socket import timeout
import json
import re

from lxml import etree
from PyQt5.QtCore import (
    QByteArray, QCoreApplication, QSettings, QThread,
    QTimer, pyqtSignal, Qt
)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QVBoxLayout, QCompleter
)

try:
    import owm_cities
except ImportError:
    from meteo_qt import owp_cities


class SearchCity(QDialog):
    id_signal = pyqtSignal([tuple])
    city_signal = pyqtSignal([tuple])
    country_signal = pyqtSignal([tuple])

    def __init__(self, accurate_url, appid, parent=None):
        super(SearchCity, self).__init__(parent)
        self.settings = QSettings()
        self.delay = 1000
        self.search_string = self.tr('Searching...')
        self.timer = QTimer()
        self.accurate_url = accurate_url
        self.suffix = '&type=like&mode=xml' + appid
        self.layout = QVBoxLayout()
        self.lineLayout = QHBoxLayout()
        self.buttonSearch = QPushButton()
        self.buttonSearch.setIcon(QIcon(':/find'))
        self.buttonSearch.setToolTip(
            QCoreApplication.translate(
                'Search city button Tooltip',
                'Search city',
                'Search for the given place'
            )
        )
        self.buttonSearch.clicked.connect(self.search)
        self.buttonMyLocation = QPushButton()
        self.buttonMyLocation.setIcon(QIcon(':/mylocation'))
        self.buttonMyLocation.setToolTip(
            QCoreApplication.translate(
                'Search by geolocalisation button tooltip',
                'Find my location',
                'Automatic search of my place'
            )
        )
        self.buttonMyLocation.clicked.connect(self.myLocation)
        self.line_search = QLineEdit(
            QCoreApplication.translate(
                'Search city dialogue',
                'Start typing the city or the ID or the geographic '
                'coordinates "latitude, longitude"',
                'Default message in the search field'
            )
        )
        self.line_search.selectAll()

        completer = QCompleter(owm_cities.cities_list, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.line_search.setCompleter(completer)

        self.listWidget = QListWidget()
        self.status = QLabel()
        self.lineLayout.addWidget(self.line_search)
        self.lineLayout.addWidget(self.buttonSearch)
        self.lineLayout.addWidget(self.buttonMyLocation)
        self.layout.addLayout(self.lineLayout)
        self.layout.addWidget(self.listWidget)
        self.layout.addWidget(self.status)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch()
        self.buttonOk = QPushButton(self.tr('&Ok'))
        self.buttonOk.setEnabled(False)
        self.buttonCancel = QPushButton(self.tr('&Cancel'))
        self.buttonLayout.addWidget(self.buttonOk)
        self.buttonLayout.addWidget(self.buttonCancel)
        self.layout.addLayout(self.buttonLayout)
        self.setMinimumWidth(800)
        self.setLayout(self.layout)
        self.line_search.returnPressed.connect(self.search)
        self.line_search.textChanged.connect(self.timer_run)
        self.buttonOk.clicked.connect(self.accept)
        self.buttonCancel.clicked.connect(self.reject)
        self.listWidget.itemSelectionChanged.connect(self.buttonCheck)
        self.listWidget.itemDoubleClicked['QListWidgetItem *'].connect(self.accept)
        self.restoreGeometry(
            self.settings.value("SearchCity/Geometry", QByteArray())
        )
        self.timer_search = QTimer(self)
        self.timer_search.timeout.connect(self.search)
        self.setWindowTitle(
            QCoreApplication.translate(
                'Window title',
                'Find a city',
                'City search dialogue'
            )
        )
        self.status.setText(
            'ℹ ' + QCoreApplication.translate(
                'Status message',
                'Click on "Find my Location" button for automatic geolocation',
                'City search dialogue'
            )
        )

    def timer_run(self):
        self.timer_search.start(1000)
        self.status.setText(
            "ℹ "
            + QCoreApplication.translate(
                "Status message",
                "Put the city's name, comma, 2-letter country code (ex: London, GB)",
                "City search dialogue"
            )
        )

    def closeEvent(self, event):
        self.settings.setValue(
            "SearchCity/Geometry", self.saveGeometry()
        )

    def moveEvent(self, event):
        self.settings.setValue(
            "SearchCity/Geometry", self.saveGeometry()
        )

    def resizeEvent(self, event):
        self.settings.setValue(
            "SearchCity/Geometry", self.saveGeometry()
        )

    def buttonCheck(self):
        '''Enable OK button if an item is selected.'''
        row = self.listWidget.currentRow()
        item = self.listWidget.item(row)
        if item is not None:
            self.buttonOk.setEnabled(True)

    def accept(self):
        row = self.listWidget.currentRow()
        item = self.listWidget.item(row)
        if item is not None:
            selected_city = item.text()
            city_list = selected_city.split(' - ')
            for c in range(len(city_list)):
                city_list[c] = city_list[c].strip()
            id_ = 'ID', city_list[0]
            city = 'City', city_list[1]
            country = 'Country', city_list[2]
            self.id_signal[tuple].emit(id_)
            self.city_signal[tuple].emit(city)
            self.country_signal[tuple].emit(country)
        QDialog.accept(self)

    def thread_terminate(self):
        if hasattr(self, 'workThread'):
            if self.workThread.isRunning():
                self.workThread.terminate()

    def myLocation(self):
        locFound = False
        loc = QCoreApplication.translate(
            'Search city',
            'N/A',
            'Inserted in search field when the automatic'
            'geolocalisation is not available'
        )
        try:
            page = urllib.request.urlopen('http://ipinfo.io/json', timeout=5)
            rep = page.read().decode('utf-8')
            locdic = json.loads(rep)
            loc = locdic['loc']
            locFound = True
        except (KeyError, urllib.error.HTTPError, timeout) as e:
            locFound = False
            logging.critical(
                'Error fetching geolocation from http://ipinfo.io/json: '
                + str(e)
            )
        if locFound is False:

            try:
                data = str(urllib.request.urlopen('http://checkip.dyndns.com/', timeout=5).read())
                myip = re.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(data).group(1)
                url = (
                    'http://api.ipstack.com/{}?access_key=1f5f4144cd87a4eda32832dad469b586'
                    .format(myip)
                )
                page = urllib.request.urlopen(url, timeout=5)
                rep = page.read().decode('utf-8')
                locdic = json.loads(rep)
                loc = str(locdic['latitude']) + ',' + str(locdic['longitude'])
            except (KeyError, urllib.error.HTTPError, timeout) as e:
                logging.critical(
                    'Error fetching geolocation from {}: '.format(url)
                    + str(e)
                )
        self.line_search.setText(loc)

    def search(self):
        self.timer_search.stop()
        self.city = (self.line_search.text())
        self.thread_terminate()
        if len(self.city) < 3:
            self.status.setText(
                QCoreApplication.translate(
                    'SearchCity window',
                    'Please type more than three characters',
                    'Message in the statusbar'
                )
            )
            return

        self.lista = []
        self.errorStatus = False
        self.buttonOk.setEnabled(False)
        self.listWidget.clear()
        self.status.setText(self.search_string)
        self.workThread = WorkThread(self.accurate_url, self.city, self.suffix)
        self.workThread.setTerminationEnabled(True)
        self.workThread.city_signal['QString'].connect(self.addlist)
        self.workThread.finished.connect(self.result)
        self.workThread.error['QString'].connect(self.error)
        self.workThread.searching['QString'].connect(self.searching)
        self.workThread.started.connect(self.thread_started)
        self.timer.singleShot(self.delay, self.threadstart)

    def searching(self, message):
        '''Display a status message when searching takes a while'''
        self.status.setText(message)

    def thread_started(self):
        '''Force the "searching" status message'''
        self.status.setText(self.search_string)

    def threadstart(self):
        self.workThread.start()

    def addlist(self, city):
        logging.debug('Found: ' + str(city))
        if city not in self.lista:
            self.lista.append(city)
            self.errorStatus = False

    def error(self, e):
        self.delay = 2000
        logging.error(e)
        self.status.setText(e)
        self.adjustSize()
        self.errorStatus = True

    def result(self):
        if self.errorStatus:
            return
        if len(self.line_search.text()) < 3:
            self.thread_terminate()
            self.status.clear()
            return
        self.delay = 1000
        # Clear the listWidget elements from an interrupted thread
        self.listWidget.clear()
        self.listWidget.addItems(self.lista)
        number_cities = len(self.lista)
        cities_text = ''
        if number_cities == 0:
            cities_text = self.tr('No results')
        elif number_cities == 1:
            cities_text = self.tr('Found {0} city').format(number_cities)
        elif number_cities > 1:
            cities_text = self.tr('Found {0} cities').format(number_cities)
        self.status.setText(cities_text)


class WorkThread(QThread):
    error = pyqtSignal(['QString'])
    city_signal = pyqtSignal(['QString'])
    searching = pyqtSignal(['QString'])

    def __init__(self, accurate_url, city, suffix, parent=None):
        QThread.__init__(self, parent)
        self.accurate_url = accurate_url
        if city.count(',') == 1:
            ccity = city.split(',')[0]
            ccode = city.split(',')[1]
            self.city = ccity + ',' + ccode.upper()
        else:
            self.city = city
        self.suffix = suffix
        self.tentatives = 1
        self.settings = QSettings()
        coordinates = city.split(',')
        try:
            coordinates[0], coordinates[1] = float(coordinates[0]), float(coordinates[1])
            self.city = 'lat=' + str(coordinates[0]) + '&lon=' + str(coordinates[1])
            self.accurate_url = self.accurate_url.replace('q=', '')
            logging.debug('Search by geographic coordinates' + str(self.city))
        except (ValueError, IndexError) as e:
            logging.debug('Cannot find geographic coordinates' + str(e))
            logging.debug('Search by city name' + str(self.city))
        self.search_by_id = False
        if self.city.isdecimal():
            self.accurate_url = self.accurate_url.replace('find?q=', 'weather?id=')
            self.search_by_id = True
            logging.debug('Search city by ID')

    def run(self):
        use_proxy = self.settings.value('Proxy') or 'False'
        use_proxy = eval(use_proxy)
        proxy_auth = self.settings.value(
            'Use_proxy_authentification'
        ) or 'False'
        proxy_auth = eval(proxy_auth)
        if use_proxy:
            proxy_url = self.settings.value('Proxy_url')
            proxy_port = self.settings.value('Proxy_port')
            proxy_tot = 'http://' + ':' + proxy_port
            if proxy_auth:
                proxy_user = self.settings.value('Proxy_user')
                proxy_password = self.settings.value('Proxy_pass')
                proxy_tot = (
                    'http://' + proxy_user + ':' + proxy_password + '@'
                    + proxy_url + ':' + proxy_port
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
        error_message = self.tr(
            'Data error, please try again later\n'
            'or modify the name of the city'
        )
        self.lista = []
        if self.city == '':
            return
        try:
            logging.debug(
                self.accurate_url + repr(self.city.encode('utf-8'))
                .replace("b'", "")
                .replace("\\x", "%")
                .replace("'", "")
                .replace(' ', '%20')
                + self.suffix
            )
            logging.debug(
                'City before utf8 encode: ' + self.accurate_url
                + self.city + self.suffix
            )
            req = urllib.request.urlopen(
                self.accurate_url + repr(self.city.encode('utf-8'))
                .replace("b'", "")
                .replace("\\x", "%")
                .replace("'", "")
                .replace(' ', '%20')
                + self.suffix, timeout=5
            )
            page = req.read()
            tree = etree.fromstring(page)
        except timeout:
            if self.tentatives == 10:
                logging.error(error_message)
                return
            else:
                self.tentatives += 1
                searching_message = self.tr('Please wait, searching...')
                logging.debug(searching_message)
                self.searching['QString'].emit(searching_message)
                self.run()
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            code = ''
            if hasattr(error, 'code'):
                code = str(error.code)
            m_error = (
                self.tr('Error: ') + code + ' ' + str(error.reason)
                + self.tr('\nTry again later')
            )
            if self.tentatives == 10:
                self.error['QString'].emit(m_error)
                return
            else:
                self.tentatives += 1
                logging.debug('Tries: ' + str(self.tentatives))
                self.run()
        # No result
        if self.search_by_id is False:
            try:
                if int(tree[1].text) == 0:
                    logging.debug('Number of cities: 0')
                    if self.tentatives == 10:
                        return
                    else:
                        self.tentatives += 1
                        logging.debug('Tries: ' + str(self.tentatives))
                        logging.debug('Try to retreive city information...')
                        self.run()
            except:
                return

            for i in range(int(tree[1].text)):
                city = tree[3][i][0].get('name')
                country = tree[3][i][0][1].text
                if country is None:
                    country = ''
                id_ = tree[3][i][0].get('id')
                lon = tree[3][i][0][0].get('lon')
                lat = tree[3][i][0][0].get('lat')
                if int(id_) == 0:
                    logging.error('Error ID: ' + str(id_))
                    if self.tentatives == 10:
                        self.error['QString'].emit(error_message)
                        return
                    else:
                        self.tentatives += 1
                        logging.debug('Tries: ' + str(self.tentatives))
                        logging.debug('Try to retrieve city information...')
                        # Try with a fuzzy city name
                        if city != '':
                            logging.info('Change search to:' + city)
                            self.city = (
                                repr(city.encode('utf-8'))
                                .replace("b'", "")
                                .replace("\\x", "%")
                                .replace("'", "")
                                .replace(' ', '%20')
                            )
                        self.run()
                if city == '':
                    if self.tentatives == 10:
                        self.error['QString'].emit(error_message)
                        return
                    else:
                        self.tentatives += 1
                        logging.debug('Tries: ' + str(self.tentatives))
                        logging.debug('Try to retrieve city information...')
                        self.run()
                try:
                    if id_ == '0':
                        continue

                    place = (
                        id_
                        + ' - '
                        + city
                        + ' - '
                        + country
                        + ' - '
                        + ' {0}° '
                        + ','
                        + ' {1}°'
                    ).format(lat, lon)

                    if place in self.lista:
                        continue
                    self.lista.append(place)
                except:
                    logging.critical('An error has occured:')
                    logging.critical('ID' + str(id_))
                    logging.critical('City' + str(city))
                    logging.critical('Country' + str(country))
                    return
        else:
            try:
                city = tree[0].get('name')
            except UnboundLocalError:
                logging.debug(f"Could'nt find any city with the ID {self.city}")
                return
            if city == '':
                if self.tentatives == 10:
                    self.error['QString'].emit(error_message)
                    return
                else:
                    self.tentatives += 1
                    logging.debug('Tries: ' + str(self.tentatives))
                    logging.debug('Try to retrieve city information...')
                    self.run()
            country = tree[0][1].text
            if country is None:
                country = ''
            id_ = tree[0].get('id')
            lon = tree[0][0].get('lon')
            lat = tree[0][0].get('lat')
            place = (
                id_
                + ' - '
                + city
                + ' - '
                + country
                + ' - '
                + ' {0}° '
                + '-'
                + ' {1}°'
            ).format(lat, lon)
            self.lista.append(place)


        for i in self.lista:
            self.city_signal['QString'].emit(i)
        logging.debug('City thread done')
