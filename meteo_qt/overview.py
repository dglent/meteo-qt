#!/usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import datetime
import urllib.request
from lxml import etree
import time
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

    def __init__(self, weatherdata, icon, forecast_inerror, forecast, unit,
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
        self.settings = QSettings()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.tree = forecast
        self.forecast_inerror = forecast_inerror
        self.icon_url = icon_url
        self.forecast_weather_list = []
        self.weatherdata = weatherdata
        self.icon_list = []
        self.unit_temp = self.units_dico[unit]
        self.total_layout = QVBoxLayout()
        #----First part overview day -----
        self.over_layout = QVBoxLayout()
        #---------------------------------
        self.city_label = QLabel('<font size="4"><b>' + self.weatherdata['City'] +
                               ',  ' + self.weatherdata['Country']+'<\b><\font>')
        self.over_layout.addWidget(self.city_label)
        self.icontemp_layout = QHBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon)
        self.icontemp_layout.addWidget(self.icon_label)
        self.temp_label = QLabel('<font size="5"><b>' + '{0:.1f}'.format(float(self.weatherdata['Temp'][:-1])) +
                               ' ' + self.unit_temp + '<\b><\font>')
        self.icontemp_layout.addWidget(self.temp_label)
        self.icontemp_layout.addStretch()
        self.over_layout.addLayout(self.icontemp_layout)
        self.weather = QLabel('<font size="4"><b>' + self.weatherdata['Meteo'] +
                             '<\b><\font>')
        self.over_layout.addWidget(self.weather)
        self.line = QLabel('<font color=grey>__________<\font>')
        self.over_layout.addWidget(self.line)
        #------Second part overview day---------
        self.over_grid = QGridLayout()
        self.wind_label = QLabel('<font size="3" color=grey><b>' +
                                self.tr('Wind') + '<\font><\b>')
        wind_unit = self.settings.value('Unit') or 'metric'
        speed_unit = ' m/s '
        if wind_unit == 'imperial':
            speed_unit = ' mph '
        self.wind = QLabel('<font color=grey>' + self.weatherdata['Wind'][0] +
                          speed_unit + self.weatherdata['Wind'][1] + ' '+
                          self.weatherdata['Wind'][2] + '° ' +
                          self.weatherdata['Wind'][3] + ' ' +
                          self.weatherdata['Wind'][4] + '<\font>')
        self.clouds_label = QLabel('<font size="3" color=grey><b>' +
                                  self.tr('Cloudiness') + '<\b><\font>')
        self.clouds_name = QLabel('<font color=grey>' + self.weatherdata['Clouds'] + '<\font>')
        self.pressure_label = QLabel('<font size="3" color=grey><b>' +
                                    self.tr('Pressure') + '<\b><\font>')
        self.pressure_value = QLabel('<font color=grey>' + self.weatherdata['Pressure'][0] + ' ' +
                                    self.weatherdata['Pressure'][1] + '<\font>')
        self.humidity_label = QLabel('<font size="3" color=grey><b>' +
                                    self.tr('Humidity') + '<\b><\font>')
        self.humidity_value = QLabel('<font color=grey>' + self.weatherdata['Humidity'][0] + ' ' +
                                    self.weatherdata['Humidity'][1] + '<\font>')
        # Convert sun rise/set from UTC to local time
        self.sunrise_label = QLabel('<font color=grey><b>' + self.tr('Sunrise') + '</b></font>')
        # Create a list ['h', 'm', 's'] and pass it to QTime
        sunrise = self.weatherdata['Sunrise'].split('T')[1].split(':')
        rise_time = QTime(int(sunrise[0]),int(sunrise[1]),int(sunrise[2]))
        # add the diff UTC-local in seconds
        rise_ = rise_time.addSecs(time.localtime().tm_gmtoff)
        rise_str = rise_.toString()
        self.sunrise_value = QLabel('<font color=grey>' + rise_str + '</font>')
        self.sunset_label = QLabel('<font color=grey><b>' + self.tr('Sunset') + '</b></font>')
        sunset = self.weatherdata['Sunset'].split('T')[1].split(':')
        set_time = QTime(int(sunset[0]),int(sunset[1]),int(sunset[2]))
        set_ = set_time.addSecs(time.localtime().tm_gmtoff)
        set_str = set_.toString()
        self.sunset_value = QLabel('<font color=grey>' + set_str + '</font>')
        #----------------------------------
        self.over_grid.addWidget(self.wind_label, 0,0)
        self.over_grid.addWidget(self.wind, 0,1)
        self.over_grid.addWidget(self.clouds_label, 1,0)
        self.over_grid.addWidget(self.clouds_name, 1,1)
        self.over_grid.addWidget(self.pressure_label, 2,0)
        self.over_grid.addWidget(self.pressure_value, 2,1)
        self.over_grid.addWidget(self.humidity_label, 3,0)
        self.over_grid.addWidget(self.humidity_value, 3,1,1,3) # keeps alignment left
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
        if not forecast_inerror:
            self.forecastdata()
            self.iconfetch()
        self.setLayout(self.total_layout)
        self.setWindowTitle(self.tr('Weather status'))
        self.restoreGeometry(self.settings.value("OverviewCity/Geometry",
                QByteArray()))

    def forecastdata(self):
        for d in range(1,7):
            day = self.tree[4][d].get('day')
            date_list = self.tree[4][d].get('day').split('-')
            day_of_week = str(datetime.date(
                int(date_list[0]),int(date_list[1]),
                int(date_list[2])).weekday())
            label = QLabel(''+ self.days_dico[day_of_week] +
                           '')
            label.setAlignment(Qt.AlignHCenter)
            self.forecast_days_layout.addWidget(label)
            mlabel = QLabel('<font color=grey>'+'{0:.0f}'.format(float(self.tree[4][d][4].get('min'))) +
                            '°<br/>' + '{0:.0f}'.format(float(self.tree[4][d][4].get('max'))) + '°</font>')
            mlabel.setAlignment(Qt.AlignHCenter)
            mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
            self.forecast_minmax_layout.addWidget(mlabel)
            self.icon_list.append(self.tree[4][d][0].get('var')) #icon
            weather_cond = self.tree[4][d][0].get('name')
            try:
                weather_cond = self.conditions[self.tree[4][d][0].get('number')]
            except:
                print('Cannot find localisation string for :', weather_cond)
                pass
            self.forecast_weather_list.append(weather_cond) #weather

    def iconfetch(self):
        self.download_thread = IconDownload(self.icon_url, self.icon_list)
        self.download_thread.wimage['PyQt_PyObject'].connect(self.iconwidget)
        self.download_thread.error['QString'].connect(self.error)
        self.download_thread.start()

    def iconwidget(self, icon):
        image = QImage()
        image.loadFromData(icon)
        iconlabel = QLabel()
        iconlabel.setAlignment(Qt.AlignHCenter)
        iconpixmap = QPixmap(image)
        iconlabel.setPixmap(iconpixmap)
        iconlabel.setToolTip(self.forecast_weather_list.pop(0))
        self.forecast_icons_layout.addWidget(iconlabel)

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

    def __init__(self, icon_url, icon):
        QThread.__init__(self)
        self.icon_url = icon_url
        self.icon = icon

    def __del__(self):
        self.wait()

    def run(self):
        try:
            for i in range(6):
                url = self.icon_url + self.icon[i] + '.png'
                data = urllib.request.urlopen(url).read()
                if self.html404(data, 'icon'):
                    self.error['QString'].emit(self.error_message)
                    return
                self.wimage['PyQt_PyObject'].emit(data)
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            error = 'Error ' + str(error.code) + ' ' + str(error.reason)
            self.error['QString'].emit(error)
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
