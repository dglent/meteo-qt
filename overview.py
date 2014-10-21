#!/usr/bin/env python3

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class OverviewCity(QDialog):

    def __init__(self, weatherdata, icon, forecast_inerror, forecast, unit, parent=None):
        super(OverviewCity, self).__init__(parent)
        self.forecast = forecast
        self.forecast_inerror = forecast_inerror
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.weatherdata = weatherdata
        self.unitTemp = self.tempunit(unit)
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
        self.tempLabel = QLabel('<font size="5"><b>' + self.weatherdata['Temp'][:-1] +
                               ' ' + self.unitTemp + '<\b><\font>')
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
        self.overGrid.addWidget(self.windLabel, 0,0)
        self.overGrid.addWidget(self.wind, 0,1)
        self.overGrid.addWidget(self.cloudsLabel, 1,0)
        self.overGrid.addWidget(self.cloudsName, 1,1)
        self.overGrid.addWidget(self.pressureLabel, 2,0)
        self.overGrid.addWidget(self.pressureValue, 2,1)
        self.overGrid.addWidget(self.humidityLabel, 3,0)
        self.overGrid.addWidget(self.humidityValue, 3,1)
        #-----------------------------------
        self.totalLayout.addLayout(self.overLayout)
        self.totalLayout.addLayout(self.overGrid)
        self.setLayout(self.totalLayout)

    def tempunit(self, unit):
        unitsDico = {'metric': '°C', 'imperial': '°F', ' ': '°K'}
        return unitsDico[unit]
