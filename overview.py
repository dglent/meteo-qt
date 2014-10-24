#!/usr/bin/env python3

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import datetime
import urllib.request
from lxml import etree
import time



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
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.tree = forecast
        self.forecast_inerror = forecast_inerror
        self.icon_url = icon_url
        self.forecast_weather_list = []
        self.weatherdata = weatherdata
        self.icon_list = []
        self.unit_temp = self.units_dico[unit]
        self.totalLayout = QVBoxLayout()
        #----First part overview day -----
        self.overLayout = QVBoxLayout()
        #---------------------------------
        self.cityLabel = QLabel('<font size="4"><b>' + self.weatherdata['City'] +
                               ',  ' + self.weatherdata['Country']+'<\b><\font>')
        self.overLayout.addWidget(self.cityLabel)
        self.iconTempLayout = QHBoxLayout()
        self.iconLabel = QLabel()
        self.iconLabel.setPixmap(icon)
        self.iconTempLayout.addWidget(self.iconLabel)
        self.tempLabel = QLabel('<font size="5"><b>' + '{0:.1f}'.format(float(self.weatherdata['Temp'][:-1])) +
                               ' ' + self.unit_temp + '<\b><\font>')
        self.iconTempLayout.addWidget(self.tempLabel)
        self.iconTempLayout.addStretch()
        self.overLayout.addLayout(self.iconTempLayout)
        self.weather = QLabel('<font size="4"><b>' + self.weatherdata['Meteo'] +
                             '<\b><\font>')
        self.overLayout.addWidget(self.weather)
        self.line = QLabel('<font color=grey>__________<\font>')
        self.overLayout.addWidget(self.line)
        #------Second part overview day---------
        self.overGrid = QGridLayout()
        self.windLabel = QLabel('<font size="3" color=grey><b>' +
                                self.tr('Wind') + '<\font><\b>')
        self.wind = QLabel('<font color=grey>' + self.weatherdata['Wind'][0] +
                          ' m/s ' + self.weatherdata['Wind'][1] + ' '+
                          self.weatherdata['Wind'][2] + '° ' +
                          self.weatherdata['Wind'][3] + ' ' +
                          self.weatherdata['Wind'][4] + '<\font>')
        self.cloudsLabel = QLabel('<font size="3" color=grey><b>' +
                                  self.tr('Cloudiness') + '<\b><\font>')
        self.cloudsName = QLabel('<font color=grey>' + self.weatherdata['Clouds'] +
                                 '<\font>')
        self.pressureLabel = QLabel('<font size="3" color=grey><b>' +
                                    self.tr('Pressure') + '<\b><\font>')
        self.pressureValue = QLabel('<font color=grey>' + self.weatherdata['Pressure'][0] + ' ' +
                                    self.weatherdata['Pressure'][1] + '<\font>')
        self.humidityLabel = QLabel('<font size="3" color=grey><b>' +
                                    self.tr('Humidity') + '<\b><\font>')
        self.humidityValue = QLabel('<font color=grey>' + self.weatherdata['Humidity'][0] + ' ' +
                                    self.weatherdata['Humidity'][1] + '<\font>')
        # convert from UTC to local time
        self.sunrise_label = QLabel('<font color=grey><b>' + self.tr('Sunrise') + '</b></font>')
        sunrise = self.weatherdata['Sunrise'].split('T')[1].split(':')
        rise_time = QTime(int(sunrise[0]),int(sunrise[1]),int(sunrise[2]))
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
        self.overGrid.addWidget(self.windLabel, 0,0)
        self.overGrid.addWidget(self.wind, 0,1)
        self.overGrid.addWidget(self.cloudsLabel, 1,0)
        self.overGrid.addWidget(self.cloudsName, 1,1)
        self.overGrid.addWidget(self.pressureLabel, 2,0)
        self.overGrid.addWidget(self.pressureValue, 2,1)
        self.overGrid.addWidget(self.humidityLabel, 3,0)
        self.overGrid.addWidget(self.humidityValue, 3,1,1,3) # keeps alignment left
        self.overGrid.addWidget(self.sunrise_label, 4,0)
        self.overGrid.addWidget(self.sunrise_value, 4,1)
        self.overGrid.addWidget(self.sunset_label, 5,0)
        self.overGrid.addWidget(self.sunset_value, 5,1)

        #--------------Forecast---------------------
        self.forecastDaysLayout = QHBoxLayout()
        self.forecastIconsLayout = QHBoxLayout()
        self.forecastMinMAxLayout = QHBoxLayout()
        #--------------------------------------------

        self.totalLayout.addLayout(self.overLayout)
        self.totalLayout.addLayout(self.overGrid)

        self.totalLayout.addLayout(self.forecastIconsLayout)
        self.totalLayout.addLayout(self.forecastDaysLayout)
        self.totalLayout.addLayout(self.forecastMinMAxLayout)
        if not forecast_inerror:
            self.forecastdata()
            self.iconfetch()
        self.setLayout(self.totalLayout)



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
            self.forecastDaysLayout.addWidget(label)
            mlabel = QLabel('<font color=grey>'+'{0:.0f}'.format(float(self.tree[4][d][4].get('min'))) +
                            '°<br/>' + '{0:.0f}'.format(float(self.tree[4][d][4].get('max'))) + '°</font>')
            mlabel.setAlignment(Qt.AlignHCenter)
            mlabel.setToolTip(self.tr('Min Max Temperature of the day'))
            self.forecastMinMAxLayout.addWidget(mlabel)
            self.icon_list.append(self.tree[4][d][0].get('var')) #icon
            self.forecast_weather_list.append(self.tree[4][d][0].get('name')) #weather

    def iconfetch(self):
        self.download_thread = IconDownload(self.icon_url, self.icon_list)
        self.connect(self.download_thread, SIGNAL('wimage(PyQt_PyObject)'), self.iconwidget)
        self.connect(self.download_thread, SIGNAL('error(QString)'), self.error)
        self.download_thread.start()

    def iconwidget(self, icon):
        image = QImage()
        image.loadFromData(icon)
        iconlabel = QLabel()
        iconpixmap = QPixmap(image)
        iconlabel.setPixmap(iconpixmap)
        iconlabel.setToolTip(self.forecast_weather_list.pop(0))
        self.forecastIconsLayout.addWidget(iconlabel)

    def error(self, error):
        print('error in download of forecast icon:\n', error)


class IconDownload(QThread):
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
                    self.emit(SIGNAL('error(QString)'), self.error)
                    return
                self.emit(SIGNAL('wimage(PyQt_PyObject)'), data)
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            error = 'Error ' + str(error.code) + ' ' + str(error.reason)
            self.emit(SIGNAL('error(QString)'), error)
        print('Download forecast icons thread done')

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