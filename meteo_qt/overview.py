from PyQt5.QtCore import (
    QThread, pyqtSignal, QSettings, Qt, QTime, QByteArray,
    QCoreApplication
    )
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
    )
import datetime
import urllib.request
import time
from socket import timeout
import logging

try:
    import conditions
except:
    from meteo_qt import conditions


class OverviewCity(QDialog):
    closed_status_dialogue = pyqtSignal([bool])
    units_dico = {'metric': '°C',
                  'imperial': '°F',
                  ' ': '°K'}

    def __init__(self, weatherdata, icon, forecast, dayforecast, unit,
                 icon_url, uv_coord, parent=None):
        super(OverviewCity, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.days_dico = {'0': self.tr('Mon'),
                          '1': self.tr('Tue'),
                          '2': self.tr('Wed'),
                          '3': self.tr('Thu'),
                          '4': self.tr('Fri'),
                          '5': self.tr('Sat'),
                          '6': self.tr('Sun')}
        cond = conditions.WeatherConditions()
        self.conditions = cond.trans
        self.wind_direction = cond.wind_codes
        self.wind_name_dic = cond.wind
        self.clouds_name_dic = cond.clouds
        self.uv_risk = cond.uv_risk
        self.uv_recommend = cond.uv_recommend
        self.settings = QSettings()
        self.tree = forecast
        self.tree_day = dayforecast
        self.icon_url = icon_url
        self.uv_coord = uv_coord
        self.forecast_weather_list = []
        self.dayforecast_weather_list = []
        self.weatherdata = weatherdata
        self.icon_list = []
        self.dayforecast_icon_list = []
        self.unit_temp = self.units_dico[unit]
        self.total_layout = QVBoxLayout()
        # ----First part overview day -----
        self.over_layout = QVBoxLayout()
        self.dayforecast_layout = QHBoxLayout()
        self.dayforecast_temp_layout = QHBoxLayout()
        # ---------------------------------
        self.city_label = QLabel(
            '<font size="4"><b>' + self.weatherdata['City'] + ',  ' +
            self.weatherdata['Country']+'<\b><\font>')
        self.over_layout.addWidget(self.city_label)
        self.icontemp_layout = QHBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon)
        self.icontemp_layout.addWidget(self.icon_label)
        self.temp_label = QLabel(
            '<font size="5"><b>' + '{0:.1f}'.format(
                float(self.weatherdata['Temp'][:-1])) + ' ' + self.unit_temp +
            '<\b><\font>')
        self.icontemp_layout.addWidget(self.temp_label)
        self.icontemp_layout.addStretch()
        self.over_layout.addLayout(self.icontemp_layout)
        self.weather = QLabel('<font size="4"><b>' +
                              self.weatherdata['Meteo'] + '<\b><\font>')
        self.over_layout.addWidget(self.weather)
        self.over_layout.addLayout(self.dayforecast_layout)
        self.over_layout.addLayout(self.dayforecast_temp_layout)
        # ------Second part overview day---------
        self.over_grid = QGridLayout()
        self.wind_label = QLabel('<font size="3" color=grey><b>' +
                                 self.tr('Wind') + '<\font><\b>')
        wind_unit = self.settings.value('Unit') or 'metric'
        self.speed_unit = ' m/s '
        if wind_unit == 'imperial':
            self.speed_unit = ' mph '
        self.wind = QLabel('None')
        try:
            self.wind = QLabel('<font color=grey>' +
                               self.weatherdata['Wind'][0] +
                               self.speed_unit + self.weatherdata['Wind'][1] +
                               ' ' + self.weatherdata['Wind'][2] + '° ' +
                               self.weatherdata['Wind'][3] + ' ' +
                               self.weatherdata['Wind'][4] + '<\font>')
        except:
            logging.error('Cannot find wind informations:\n' +
                          str(self.weatherdata['Wind']))
        self.clouds_label = QLabel('<font size="3" color=grey><b>' +
                                   self.tr('Cloudiness') + '<\b><\font>')
        self.clouds_name = QLabel('<font color=grey>' +
                                  self.weatherdata['Clouds'] + '<\font>')
        self.pressure_label = QLabel('<font size="3" color=grey><b>' +
                                     self.tr('Pressure') + '<\b><\font>')
        self.pressure_value = QLabel('<font color=grey>' +
                                     self.weatherdata['Pressure'][0] + ' ' +
                                     self.weatherdata['Pressure'][1] +
                                     '<\font>')
        self.humidity_label = QLabel('<font size="3" color=grey><b>' +
                                     self.tr('Humidity') + '<\b><\font>')
        self.humidity_value = QLabel('<font color=grey>' +
                                     self.weatherdata['Humidity'][0] + ' ' +
                                     self.weatherdata['Humidity'][1] +
                                     '<\font>')
        self.sunrise_label = QLabel('<font color=grey><b>' +
                                    self.tr('Sunrise') + '</b></font>')
        self.sunset_label = QLabel('<font color=grey><b>' +
                                   self.tr('Sunset') + '</b></font>')
        rise_str = self.utc('Sunrise', 'weatherdata')
        set_str = self.utc('Sunset', 'weatherdata')
        self.sunrise_value = QLabel('<font color=grey>' + rise_str + '</font>')
        self.sunset_value = QLabel('<font color=grey>' + set_str + '</font>')
        # --UV---
        self.uv_label = QLabel(
            '<font size="3" color=grey><b>' + QCoreApplication.translate(
                'Ultraviolet index', 'UV', 'Label in weather info dialogue' +
                '<\b><\font>'))
        self.uv_value_label = QLabel('<font color=grey>' +
                                     QCoreApplication.translate('Ultraviolet '
                                                                'index',
                                                                'Fetching...',
                                                                '' + '<\font>')
                                     )
        # -------------------------
        self.over_grid.addWidget(self.wind_label, 0, 0)
        self.over_grid.addWidget(self.wind, 0, 1)
        self.over_grid.addWidget(self.clouds_label, 1, 0)
        self.over_grid.addWidget(self.clouds_name, 1, 1)
        self.over_grid.addWidget(self.pressure_label, 2, 0)
        self.over_grid.addWidget(self.pressure_value, 2, 1)
        self.over_grid.addWidget(self.humidity_label, 3, 0)
        self.over_grid.addWidget(self.humidity_value, 3, 1, 1, 3)  # align left
        self.over_grid.addWidget(self.sunrise_label, 4, 0)
        self.over_grid.addWidget(self.sunrise_value, 4, 1)
        self.over_grid.addWidget(self.sunset_label, 5, 0)
        self.over_grid.addWidget(self.sunset_value, 5, 1)
        self.over_grid.addWidget(self.uv_label, 6, 0)
        self.over_grid.addWidget(self.uv_value_label, 6, 1)
        # -------------Forecast-------------
        self.forecast_days_layout = QHBoxLayout()
        self.forecast_icons_layout = QHBoxLayout()
        self.forecast_minmax_layout = QHBoxLayout()
        # ----------------------------------
        self.total_layout.addLayout(self.over_layout)
        self.total_layout.addLayout(self.over_grid)
        self.total_layout.addLayout(self.forecast_icons_layout)
        self.total_layout.addLayout(self.forecast_days_layout)
        self.total_layout.addLayout(self.forecast_minmax_layout)
        self.forecastdata()
        logging.debug('Fetched forecast data')
        self.iconfetch()
        logging.debug('Fetched 6 days forecast icons')
        self.dayforecastdata()
        logging.debug('Fetched day forecast data')
        self.dayiconfetch()
        logging.debug('Fetched day forcast icons')
        self.uv_fetch()
        logging.debug('Fetched uv index')
        self.setLayout(self.total_layout)
        self.setWindowTitle(self.tr('Weather status'))
        self.restoreGeometry(self.settings.value("OverviewCity/Geometry",
                                                 QByteArray()))

    def uv_color(self, uv):
        try:
            uv = float(uv)
        except:
            return ('grey', 'None')
        if uv <= 2.9:
            return ('green', 'Low')
        if uv <= 5.9:
            return ('yellow', 'Moderate')
        if uv <= 7.9:
            return ('orange', 'High')
        if uv <= 10.9:
            return ('red', 'Very high')
        if uv >= 11:
            return ('purple', 'Extreme')

    def utc(self, rise_set, what):
        ''' Convert sun rise/set from UTC to local time
            'rise_set' is 'Sunrise' or 'Sunset when it is for weatherdata
            or the index of hour in day forecast when dayforecast'''
        listtotime = ''
        # Create a list ['h', 'm', 's'] and pass it to QTime
        if what == 'weatherdata':
            listtotime = self.weatherdata[rise_set].split('T')[1].split(':')
        elif what == 'dayforecast':
            listtotime = self.tree_day[4][rise_set].get('from').split(
                'T')[1].split(':')
        suntime = QTime(int(listtotime[0]), int(listtotime[1]), int(
            listtotime[2]))
        # add the diff UTC-local in seconds
        utc_time = suntime.addSecs(time.localtime().tm_gmtoff)
        utc_time_str = utc_time.toString()
        return utc_time_str

    def forecastdata(self):
        '''Forecast for the next 6 days'''
        # Some times server sends less data
        periods = 7
        fetched_file_periods = (len(self.tree.xpath('//time')))
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            logging.warn('Reduce forcast for the next 6 days to {0}'.format(
                periods-1))
        for d in range(1, periods):
            date_list = self.tree[4][d].get('day').split('-')
            day_of_week = str(datetime.date(
                int(date_list[0]), int(date_list[1]),
                int(date_list[2])).weekday())
            label = QLabel('' + self.days_dico[day_of_week] + '')
            label.setToolTip(self.tree[4][d].get('day'))
            label.setAlignment(Qt.AlignHCenter)
            self.forecast_days_layout.addWidget(label)
            mlabel = QLabel(
                '<font color=grey>' + '{0:.0f}'.format(float(
                    self.tree[4][d][4].get('min'))) + '°<br/>' +
                '{0:.0f}'.format(float(self.tree[4][d][4].get('max'))) +
                '°</font>')
            mlabel.setAlignment(Qt.AlignHCenter)
            mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
            self.forecast_minmax_layout.addWidget(mlabel)
            self.icon_list.append(self.tree[4][d][0].get('var'))  # icon
            weather_cond = self.tree[4][d][0].get('name')
            try:
                weather_cond = self.conditions[self.tree[4][d][0].get(
                    'number')]
            except:
                logging.warn('Cannot find localisation string for :' +
                             weather_cond)
                pass
            self.forecast_weather_list.append(weather_cond)  # weather

    def iconfetch(self):
        logging.debug('Download 6 days forecast icons...')
        self.download_thread = IconDownload(self.icon_url, self.icon_list)
        self.download_thread.wimage['PyQt_PyObject'].connect(self.iconwidget)
        self.download_thread.url_error_signal['QString'].connect(self.error)
        self.download_thread.start()

    def iconwidget(self, icon):
        '''6 days forecast icons'''
        image = QImage()
        image.loadFromData(icon)
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignHCenter)
        iconpixmap = QPixmap(image)
        iconlabel.setPixmap(iconpixmap)
        iconlabel.setToolTip(self.forecast_weather_list.pop(0))
        self.forecast_icons_layout.addWidget(iconlabel)

    def dayforecastdata(self):
        '''Fetch forecast for the day'''
        # Some times server sends less data
        periods = 7
        fetched_file_periods = (len(self.tree_day.xpath('//time')))
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            logging.warn('Reduce forcast of the day to {0}'.format(periods-1))
        for d in range(1, periods):
            timeofday = self.utc(d, 'dayforecast')
            weather_cond = self.conditions[self.tree_day[4][d][0].get('number')]
            self.dayforecast_weather_list.append(weather_cond)
            # icon
            self.dayforecast_icon_list.append(self.tree_day[4][d][0].get('var'))
            daytime = QLabel(
                '<font color=grey>' + timeofday[:-3] + '<br/>' +
                '{0:.0f}'.format(float(self.tree_day[4][d][4].get('value'))) +
                '°' + '</font>')
            daytime.setAlignment(Qt.AlignHCenter)
            unit = self.settings.value('Unit') or 'metric'
            precipitation = str(self.tree_day[4][d][1].get('value'))
            if unit == 'metric':
                mu = 'mm'
            elif unit == 'imperial':
                mu = 'inch'
                if precipitation.count('None') == 0:
                    precipitation = str(float(precipitation) / 25.0)
            ttip = (precipitation + ' ' + mu + ' ' +
                    str(self.tree_day[4][d][1].get('type')) + '<br/>')
            if ttip.count('None') >= 1:
                ttip = ''
            else:
                ttip = ttip.replace('snow', self.tr('snow'))
                ttip = ttip.replace('rain', self.tr('rain'))
            # Winddirection/speed
            windspeed = self.tree_day[4][d][3].get('mps')
            ttip = ttip + (windspeed + ' ' + self.speed_unit)
            winddircode = self.tree_day[4][d][2].get('code')
            wind = ''
            if winddircode != '':
                wind = self.wind_direction[winddircode] + ' '
            else:
                logging.warn('Wind direction code is missing: ' +
                             str(winddircode))
            wind_name = self.tree_day[4][d][3].get('name')
            try:
                wind_name_translated = (
                    self.conditions[self.wind_name_dic[wind_name.lower()]] +
                    '<br/>')
                wind += wind_name_translated
            except KeyError:
                logging.warn('Cannot find wind name :' + str(wind_name))
                logging.info('Set wind name to None')
                wind = ''
            finally:
                if wind == '':
                    wind += '<br/>'
            # Clouds
            clouds_translated = ''
            clouds = self.tree_day[4][d][7].get('value')
            cloudspercent = self.tree_day[4][d][7].get('all')
            if clouds != '':
                clouds_translated = self.conditions[self.clouds_name_dic[clouds.lower()]]
            else:
                logging.warn('Clouding name is missing: ' + str(clouds))
            clouds_cond = clouds_translated + ' ' + cloudspercent + '%'
            ttip = ttip + wind + clouds_cond
            daytime.setToolTip(ttip)
            self.dayforecast_temp_layout.addWidget(daytime)

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
        self.uv_value_label.setText('<font color=grey>' + str(index) +
                                    '  ' + self.uv_risk[uv_color[1]] +
                                    '</font>' + ' < font color=' +
                                    uv_color[0] + '><b>' +
                                    uv_gauge + '</b></font>')
        self.uv_value_label.setToolTip(self.uv_recommend[uv_color[1]])

    def dayiconfetch(self):
        '''Icons for the forecast of the day'''
        logging.debug('Download forecast icons for the day...')
        self.day_download_thread = IconDownload(self.icon_url,
                                                self.dayforecast_icon_list)
        self.day_download_thread.wimage['PyQt_PyObject'].connect(self.dayiconwidget)
        self.day_download_thread.url_error_signal['QString'].connect(self.error)
        self.day_download_thread.start()

    def dayiconwidget(self, icon):
        '''Forecast icons of the day'''
        image = QImage()
        image.loadFromData(icon)
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignHCenter)
        iconpixmap = QPixmap(image)
        iconlabel.setPixmap(iconpixmap)
        iconlabel.setToolTip(self.dayforecast_weather_list.pop(0))
        self.dayforecast_layout.addWidget(iconlabel)

    def error(self, error):
        logging.error('error in download of forecast icon:\n' + error)

    def moveEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

    def resizeEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

    def hideEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

    def closeEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())
        exit = True
        self.closed_status_dialogue.emit(exit)


class Uv(QThread):
    uv_signal = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, uv_coord, parent=None):
        QThread.__init__(self, parent)
        self.uv_coord = uv_coord

    def run(self):
        try:
            lat = self.uv_coord[0]
            lon = self.uv_coord[1]
            url = ('http://api.owm.io/air/1.0/uvi/current?lat=' +
                   lat + '&lon=' + lon +
                   '&appid=18dc60bd132b7fb4534911d2aa67f0e7')
            logging.debug('Fetching url for uv index: ' + str(url))
            req = urllib.request.urlopen(url, timeout=5)
            page = req.read()
            dico_value = eval(page)
            uv_ind = dico_value['value']
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

    def run(self):
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
                url_error = 'Error: ' + str(error.code) + ': ' + str(error.reason)
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
                logging.info('5 secondes timeout, new tentative: ' +
                             str(self.tentatives))
                self.run()
        logging.debug('Download forecast icons thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error_message = code + ' ' + message + '@' + what
            logging.error(self.error)
            return True
        except:
            return False
