from PyQt5.QtCore import QThread, pyqtSignal, QSettings, Qt, QTime, QByteArray
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
    )
import datetime
import urllib.request
from lxml import etree
import time
from socket import timeout

try:
    import conditions
except:
    from meteo_qt import conditions


class OverviewCity(QDialog):

    units_dico = {
        'metric': '°C',
        'imperial': '°F',
        ' ': '°K'
     }

    def __init__(self, weatherdata, icon, forecast, dayforecast, unit,
                 icon_url, parent=None):
        super(OverviewCity, self).__init__(parent)
        self.days_dico = {
        '0': self.tr('Mon'),
        '1': self.tr('Tue'),
        '2': self.tr('Wed'),
        '3': self.tr('Thu'),
        '4': self.tr('Fri'),
        '5': self.tr('Sat'),
        '6': self.tr('Sun')
        }
        cond = conditions.WeatherConditions()
        self.conditions = cond.trans
        self.wind_direction = cond.wind_codes
        self.wind_name_dic = cond.wind
        self.clouds_name_dic = cond.clouds
        self.settings = QSettings()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.tree = forecast
        self.tree_day = dayforecast
        self.icon_url = icon_url
        self.forecast_weather_list = []
        self.dayforecast_weather_list = []
        self.weatherdata = weatherdata
        self.icon_list = []
        self.dayforecast_icon_list = []
        self.unit_temp = self.units_dico[unit]
        self.total_layout = QVBoxLayout()
        #----First part overview day -----
        self.over_layout = QVBoxLayout()
        self.dayforecast_layout = QHBoxLayout()
        self.dayforecast_temp_layout = QHBoxLayout()
        #---------------------------------
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
        #------Second part overview day---------
        self.over_grid = QGridLayout()
        self.wind_label = QLabel('<font size="3" color=grey><b>' +
                                self.tr('Wind') + '<\font><\b>')
        wind_unit = self.settings.value('Unit') or 'metric'
        self.speed_unit = ' m/s '
        if wind_unit == 'imperial':
            self.speed_unit = ' mph '
        self.wind = QLabel('<font color=grey>' + self.weatherdata['Wind'][0] +
                          self.speed_unit + self.weatherdata['Wind'][1] + ' '+
                          self.weatherdata['Wind'][2] + '° ' +
                          self.weatherdata['Wind'][3] + ' ' +
                          self.weatherdata['Wind'][4] + '<\font>')
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
        #----------------------------------
        self.over_grid.addWidget(self.wind_label, 0,0)
        self.over_grid.addWidget(self.wind, 0,1)
        self.over_grid.addWidget(self.clouds_label, 1,0)
        self.over_grid.addWidget(self.clouds_name, 1,1)
        self.over_grid.addWidget(self.pressure_label, 2,0)
        self.over_grid.addWidget(self.pressure_value, 2,1)
        self.over_grid.addWidget(self.humidity_label, 3,0)
        # keeps alignment left
        self.over_grid.addWidget(self.humidity_value, 3,1,1,3)
        self.over_grid.addWidget(self.sunrise_label, 4,0)
        self.over_grid.addWidget(self.sunrise_value, 4,1)
        self.over_grid.addWidget(self.sunset_label, 5,0)
        self.over_grid.addWidget(self.sunset_value, 5,1)
        #--------------Forecast---------------------
        self.forecast_days_layout = QHBoxLayout()
        self.forecast_icons_layout = QHBoxLayout()
        self.forecast_minmax_layout = QHBoxLayout()
        #--------------------------------------------
        self.total_layout.addLayout(self.over_layout)
        self.total_layout.addLayout(self.over_grid)
        self.total_layout.addLayout(self.forecast_icons_layout)
        self.total_layout.addLayout(self.forecast_days_layout)
        self.total_layout.addLayout(self.forecast_minmax_layout)
        self.forecastdata()
        print('Fetched forecast data')
        self.iconfetch()
        print('Fetched 6 days forecast icons')
        self.dayforecastdata()
        print('Fetched day forecast data')
        self.dayiconfetch()
        print('Fetched day forcast icons')
        self.setLayout(self.total_layout)
        self.setWindowTitle(self.tr('Weather status'))
        self.restoreGeometry(self.settings.value("OverviewCity/Geometry",
                QByteArray()))

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
        suntime = QTime(int(listtotime[0]),int(listtotime[1]),int(
            listtotime[2]))
        # add the diff UTC-local in seconds
        utc_time = suntime.addSecs(time.localtime().tm_gmtoff)
        utc_time_str = utc_time.toString()
        return utc_time_str

    def forecastdata(self):
        '''Forecast for the next 6 days'''
        #Some times server sends less data
        periods = 7
        fetched_file_periods = (len(self.tree.xpath('//time')))
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            print('Reduce forcast for the next 6 days to {0}'.format(
                periods-1))
        for d in range(1, periods):
            date_list = self.tree[4][d].get('day').split('-')
            day_of_week = str(datetime.date(
                int(date_list[0]),int(date_list[1]),
                int(date_list[2])).weekday())
            label = QLabel(''+ self.days_dico[day_of_week] + '')
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
            self.icon_list.append(self.tree[4][d][0].get('var')) #icon
            weather_cond = self.tree[4][d][0].get('name')
            try:
                weather_cond = self.conditions[self.tree[4][d][0].get(
                    'number')]
            except:
                print('Cannot find localisation string for :', weather_cond)
                pass
            self.forecast_weather_list.append(weather_cond) #weather

    def iconfetch(self):
        print('Download 6 days forecast icons...')
        self.download_thread = IconDownload(self.icon_url, self.icon_list)
        self.download_thread.wimage['PyQt_PyObject'].connect(self.iconwidget)
        self.download_thread.error['QString'].connect(self.error)
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
        #Some times server sends less data
        periods = 7
        fetched_file_periods = (len(self.tree_day.xpath('//time')))
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            print('Reduce forcast of the day to {0}'.format(periods-1))
        for d in range(1, periods):
            timeofday = self.utc(d, 'dayforecast')
            weather_cond = self.conditions[self.tree_day[4][d][0].get('number')]
            self.dayforecast_weather_list.append(weather_cond)
            #icon
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
                print('Wind direction code is missing: ', winddircode)
            wind_name = self.tree_day[4][d][3].get('name')
            try:
                wind_name_translated = (
                    self.conditions[self.wind_name_dic[wind_name.lower()]] +
                    '<br/>')
                wind += wind_name_translated
            except KeyError:
                print('Cannot find wind name :', wind_name)
                print('Set wind name to None')
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
                print('Clouding name is missing: ', clouds)
            clouds_cond = clouds_translated + ' ' + cloudspercent + '%'
            ttip = ttip + wind + clouds_cond
            daytime.setToolTip(ttip)
            self.dayforecast_temp_layout.addWidget(daytime)

    def dayiconfetch(self):
        '''Icons for the forecast of the day'''
        print('Download forecast icons for the day...')
        self.day_download_thread = IconDownload(self.icon_url, self.dayforecast_icon_list)
        self.day_download_thread.wimage['PyQt_PyObject'].connect(self.dayiconwidget)
        self.day_download_thread.error['QString'].connect(self.error)
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
        print('error in download of forecast icon:\n', error)

    def moveEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

    def resizeEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

    def hideEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

    def closeEvent(self, event):
        self.settings.setValue("OverviewCity/Geometry", self.saveGeometry())

class IconDownload(QThread):
    error = pyqtSignal(['QString'])
    wimage = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, icon_url, icon, parent=None):
        QThread.__init__(self, parent)
        self.icon_url = icon_url
        self.icon = icon
        self.tentatives = 0
        #Some times server sends less data
        self.periods = 6
        periods = len(self.icon)
        if periods < 6:
            self.periods = periods

    def run(self):
        try:
            for i in range(self.periods):
                url = self.icon_url + self.icon[i] + '.png'
                data = urllib.request.urlopen(url, timeout=5).read()
                if self.html404(data, 'icon'):
                    self.error['QString'].emit(self.error_message)
                    return
                self.wimage['PyQt_PyObject'].emit(data)
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            error = 'Error ' + str(error.code) + ' ' + str(error.reason)
            self.error['QString'].emit(error)
        except timeout:
            if self.tentatives >= 10:
                done = 1
                print('Timeout error, abandon...')
                return
            else:
                self.tentatives += 1
                print('5 secondes timeout, new tentative: ', self.tentatives)
                self.run()
        print('Download forecast icons thread done')

    def html404(self, page, what):
        try:
            dico = eval(page.decode('utf-8'))
            code = dico['cod']
            message = dico['message']
            self.error_message = code + ' ' + message + '@' + what
            print(self.error)
            return True
        except:
            return False
