import datetime
import logging
import time
import urllib.request
from socket import timeout

from PyQt5.QtCore import (QByteArray, QCoreApplication, QSettings, Qt, QThread,
                          QTime, pyqtSignal)
from PyQt5.QtGui import QImage, QPixmap, QTextDocument, QTransform
from PyQt5.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QVBoxLayout)

try:
    import conditions
    import qrc_resources
except:
    from meteo_qt import conditions
    from meteo_qt import qrc_resources


class OverviewCity(QDialog):
    closed_status_dialogue = pyqtSignal([bool])
    units_dico = {'metric': '°C',
                  'imperial': '°F',
                  ' ': '°K'}

    def __init__(self, weatherdata, icon, forecast, dayforecast,
                 json_data_bool, unit, icon_url, uv_coord, parent=None):
        super(OverviewCity, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.json_data_bool = json_data_bool
        self.days_dico = {'0': self.tr('Mon'),
                          '1': self.tr('Tue'),
                          '2': self.tr('Wed'),
                          '3': self.tr('Thu'),
                          '4': self.tr('Fri'),
                          '5': self.tr('Sat'),
                          '6': self.tr('Sun')}
        cond = conditions.WeatherConditions()
        self.conditions = cond.trans
        self.precipitation = cond.rain
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
        # Check for city translation
        cities_trans = self.settings.value('CitiesTranslation') or '{}'
        cities_trans_dict = eval(cities_trans)
        city_notrans = (self.weatherdata['City'] + '_' +
                        self.weatherdata['Country'] + '_' +
                        self.weatherdata['Id'])
        if city_notrans in cities_trans_dict:
            city_label = cities_trans_dict[city_notrans]
        else:
            city_label = (self.weatherdata['City'] + ',  ' +
                          self.weatherdata['Country'])
        self.city_label = QLabel('<font size="4"><b>' +
                                 city_label + '<\b><\font>')
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
        self.over_layout.addLayout(self.icontemp_layout)
        self.weather = QLabel('<font size="4"><b>' +
                              self.weatherdata['Meteo'] + '<\b><\font>')
        self.icontemp_layout.addWidget(self.weather)
        self.icontemp_layout.addStretch()
        self.over_layout.addLayout(self.dayforecast_layout)
        self.over_layout.addLayout(self.dayforecast_temp_layout)
        # ------Second part overview day---------
        self.over_grid = QGridLayout()
        # Wind
        self.wind_label = QLabel('<font size="3" color=grey><b>' +
                                 self.tr('Wind') + '<\font><\b>')
        self.wind_label.setAlignment(Qt.AlignTop)
        wind_unit = self.settings.value('Unit') or 'metric'
        self.speed_unit = ' m/s '
        if wind_unit == 'imperial':
            self.speed_unit = ' mph '
        self.wind = QLabel('None')
        try:
            self.wind = QLabel('<font color=grey>' +
                               self.weatherdata['Wind'][4] +
                               ' ' + self.weatherdata['Wind'][2] + '° ' +
                               '<br/>' + '{0:.1f}'.format(float(self.weatherdata['Wind'][0])) +
                               self.speed_unit + self.weatherdata['Wind'][1] +
                               '<\font>')
        except:
            logging.error('Cannot find wind informations:\n' +
                          str(self.weatherdata['Wind']))
        self.wind_icon_label = QLabel()
        self.wind_icon_label.setAlignment(Qt.AlignLeft)
        self.wind_icon = QPixmap(':/arrow')
        self.wind_icon_direction()
        # ----------------
        self.clouds_label = QLabel('<font size="3" color=grey><b>' +
                                   self.tr('Cloudiness') + '<\b><\font>')
        self.clouds_name = QLabel('<font color=grey>' +
                                  self.weatherdata['Clouds'] + '<\font>')
        self.pressure_label = QLabel('<font size="3" color=grey><b>' +
                                     self.tr('Pressure') + '<\b><\font>')
        self.pressure_value = QLabel('<font color=grey>' +
                                     str(round(float(self.weatherdata['Pressure'][0]))) + ' ' +
                                     self.weatherdata['Pressure'][1] +
                                     '<\font>')
        self.humidity_label = QLabel('<font size="3" color=grey><b>' +
                                     self.tr('Humidity') + '<\b><\font>')
        self.humidity_value = QLabel('<font color=grey>' +
                                     self.weatherdata['Humidity'][0] + ' ' +
                                     self.weatherdata['Humidity'][1] +
                                     '<\font>')
        self.precipitation_label = QLabel('<font size="3" color=grey><b>' +
                                          QCoreApplication.translate('Precipitation type (no/rain/snow)',
                                            'Precipitation', 'Weather overview dialogue') +
                                          '<\b><\font>')
        rain_mode = self.precipitation[self.weatherdata['Precipitation'][0]]
        rain_value = self.weatherdata['Precipitation'][1]
        rain_unit = ' mm '
        if rain_value == '':
            rain_unit = ''
        else:
            if wind_unit == 'imperial':
                rain_unit = 'inch'
                rain_value = str(float(rain_value) / 25.4)
                rain_value = "{0:.4f}".format(float(rain_value))
            else:
                rain_value = "{0:.2f}".format(float(rain_value))
        self.precipitation_value = QLabel('<font color=grey>' +
                                          rain_mode + ' ' + rain_value + ' ' + rain_unit +
                                          '</font>')
        # Sunrise Sunset Daylight
        self.sunrise_label = QLabel('<font color=grey><b>' +
                                    self.tr('Sunrise') + '</b></font>')
        self.sunset_label = QLabel('<font color=grey><b>' +
                                   self.tr('Sunset') + '</b></font>')
        rise_str = self.utc('Sunrise', 'weatherdata')
        set_str = self.utc('Sunset', 'weatherdata')
        self.sunrise_value = QLabel('<font color=grey>' + rise_str[:-3] + '</font>')
        self.sunset_value = QLabel('<font color=grey>' + set_str[:-3] + '</font>')
        self.daylight_label = QLabel('<font color=grey><b>' +
                                  QCoreApplication.translate(
                                    'Daylight duration', 'Daylight',
                                    'Weather overview dialogue') + '</b></font>')

        daylight_value = self.daylight_delta(rise_str[:-3], set_str[:-3])
        self.daylight_value_label = QLabel('<font color=grey>' + daylight_value + '</font>')
        # --UV---
        self.uv_label = QLabel(
            '<font size="3" color=grey><b>' + QCoreApplication.translate(
                'Ultraviolet index', 'UV', 'Label in weather info dialogue' +
                '<\b><\font>'))
        self.uv_label.setAlignment(Qt.AlignTop)
        fetching_text = ('<font color=grey>' + QCoreApplication.translate(
                            'Ultraviolet index', 'Fetching...', '' + '<\font>'))
        self.uv_value_label = QLabel()
        self.uv_value_label.setText(fetching_text)
        # Ozone
        self.ozone_label = QLabel(
            '<font size="3" color=grey><b>' + QCoreApplication.translate(
                'Ozone data title', 'Ozone', 'Label in weather info dialogue' +
                '<\b><\font>'))
        self.ozone_value_label = QLabel()
        self.ozone_value_label.setText(fetching_text)
        self.over_grid.addWidget(self.wind_label, 0, 0)
        self.over_grid.addWidget(self.wind, 0, 1)
        self.over_grid.addWidget(self.wind_icon_label, 0, 2)
        self.over_grid.addWidget(self.clouds_label, 1, 0)
        self.over_grid.addWidget(self.clouds_name, 1, 1)
        self.over_grid.addWidget(self.pressure_label, 2, 0)
        self.over_grid.addWidget(self.pressure_value, 2, 1)
        self.over_grid.addWidget(self.humidity_label, 3, 0)
        self.over_grid.addWidget(self.humidity_value, 3, 1, 1, 3)  # align left
        self.over_grid.addWidget(self.precipitation_label, 4, 0)
        self.over_grid.addWidget(self.precipitation_value, 4, 1)
        self.over_grid.addWidget(self.sunrise_label, 5, 0)
        self.over_grid.addWidget(self.sunrise_value, 5, 1)
        self.over_grid.addWidget(self.sunset_label, 6, 0)
        self.over_grid.addWidget(self.sunset_value, 6, 1)
        self.over_grid.addWidget(self.daylight_label, 7, 0)
        self.over_grid.addWidget(self.daylight_value_label, 7, 1)
        self.over_grid.addWidget(self.uv_label, 8, 0)
        self.over_grid.addWidget(self.uv_value_label, 8, 1)
        self.over_grid.addWidget(self.ozone_label, 9, 0)
        self.over_grid.addWidget(self.ozone_value_label, 9, 1)
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
        self.ozone_fetch()
        logging.debug('Fetched ozone data')
        self.setLayout(self.total_layout)
        self.setWindowTitle(self.tr('Weather status'))
        self.restoreGeometry(self.settings.value("OverviewCity/Geometry",
                                                 QByteArray()))

    def daylight_delta(self, s1, s2):
        FMT = '%H:%M'
        tdelta = (datetime.datetime.strptime(s2, FMT) -
                  datetime.datetime.strptime(s1, FMT))
        m, s = divmod(tdelta.seconds, 60)
        h, m = divmod(m, 60)
        daylight_in_hours = str(h) + ":" + str(m)
        return daylight_in_hours

    def wind_icon_direction(self):
        transf = QTransform()
        angle = self.weatherdata['Wind'][2]
        logging.debug('Wind degrees direction: ' + angle)
        transf.rotate(int(float(angle)))
        rotated = self.wind_icon.transformed(transf, mode=Qt.SmoothTransformation)
        self.wind_icon_label.setPixmap(rotated)

    def ozone_du(self, du):
        if du <= 125:
            return '#060106' # black
        if du <= 150:
            return '#340634' # magenta
        if du <= 175:
            return '#590b59' # fuccia
        if du <= 200:
            return '#421e85' # violet
        if du <= 225:
            return '#121e99' # blue
        if du <= 250:
            return '#125696' # blue sea
        if du <= 275:
            return '#198586' # raf
        if du <= 300:
            return '#21b1b1' # cyan
        if du <= 325:
            return '#64b341' # light green
        if du <= 350:
            return '#1cac1c' # green
        if du <= 375:
            return '#93a92c' # green oil
        if du <= 400:
            return '#baba2b' # yellow
        if du <= 425:
            return '#af771f' # orange
        if du <= 450:
            return '#842910' # brown
        if du <= 475:
            return '#501516' # brown dark
        if du > 475:
            return '#210909' # darker brown

    def uv_color(self, uv):
        try:
            uv = float(uv)
        except:
            return ('grey', 'None')
        if uv <= 2.9:
            return ('green', 'Low')
        elif uv <= 5.9:
            return ('yellow', 'Moderate')
        elif uv <= 7.9:
            return ('orange', 'High')
        elif uv <= 10.9:
            return ('red', 'Very high')
        elif uv >= 11:
            return ('purple', 'Extreme')

    def winddir_json_code(self, deg):
        deg = float(deg)
        if deg < 22.5 or deg > 337.5:
            return 'N'
        elif deg < 45:
            return 'NNE'
        elif deg < 67.5:
            return 'NE'
        elif deg < 90:
            return 'ENE'
        elif deg < 112.5:
            return 'E'
        elif deg < 135:
            return 'ESE'
        elif deg < 157.5:
            return 'SE'
        elif deg < 180:
            return 'SSE'
        elif deg < 202.5:
            return 'S'
        elif deg < 225:
            return 'SSW'
        elif deg < 247.5:
            return 'SW'
        elif deg < 270:
            return 'WSW'
        elif deg < 292.5:
            return 'W'
        elif deg < 315:
            return 'WNW'
        elif deg <= 337.5:
            return 'NNW'

    def utc(self, rise_set, what):
        ''' Convert sun rise/set from UTC to local time
            'rise_set' is 'Sunrise' or 'Sunset when it is for weatherdata
            or the index of hour in day forecast when dayforecast'''
        listtotime = ''
        # Create a list ['h', 'm', 's'] and pass it to QTime
        if what == 'weatherdata':
            listtotime = self.weatherdata[rise_set].split('T')[1].split(':')
        elif what == 'dayforecast':
            if not self.json_data_bool:
                listtotime = self.tree_day[4][rise_set].get('from').split('T')[1].split(':')
            else:
                listtotime = self.tree_day['list'][rise_set]['dt_txt'][10:].split(':')
        suntime = QTime(int(listtotime[0]), int(listtotime[1]), int(
            listtotime[2]))
        # add the diff UTC-local in seconds
        utc_time = suntime.addSecs(time.localtime().tm_gmtoff)
        utc_time_str = utc_time.toString()
        return utc_time_str

    def forecastdata(self):
        '''Forecast for the next 6 days'''
        # Some times server sends less data
        doc = QTextDocument()
        periods = 7
        fetched_file_periods = (len(self.tree.xpath('//time')))
        if fetched_file_periods < periods:
            periods = fetched_file_periods
            logging.warn('Reduce forecast for the next 6 days to {0}'.format(
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
            try:
                doc.setHtml(self.precipitation_label.text())
                precipitation_label = doc.toPlainText() + ': '
                precipitation_type = self.tree[4][d][1].get('type')
                precipitation_type = self.precipitation[precipitation_type] + ' '
                precipitation_value = self.tree[4][d][1].get('value')
                rain_unit = ' mm'
                if self.speed_unit == ' mph ':
                    rain_unit = ' inch'
                    precipitation_value = str(float(precipitation_value) / 25.4) + ' '
                    precipitation_value = "{0:.2f}".format(float(precipitation_value))
                else:
                    precipitation_value = "{0:.1f}".format(float(precipitation_value))
                weather_cond += ('\n' + precipitation_label + precipitation_type +
                                 precipitation_value + rain_unit)
            except:
                pass
            doc.setHtml(self.wind_label.text())
            wind = doc.toPlainText() + ': '
            try:
                wind_direction = self.wind_direction[self.tree[4][d][2].get('code')]
            except:
                wind_direction = ''
            wind_speed = '{0:.1f}'.format(float(self.tree[4][d][3].get('mps')))
            weather_cond += '\n' + wind + wind_speed + self.speed_unit + wind_direction
            doc.setHtml(self.pressure_label.text())
            pressure_label = doc.toPlainText() + ': '
            pressure = '{0:.1f}'.format(float(self.tree[4][d][5].get('value')))
            weather_cond += '\n' + pressure_label + pressure + ' hPa'
            humidity = self.tree[4][d][6].get('value')
            doc.setHtml(self.humidity_label.text())
            humidity_label = doc.toPlainText() + ': '
            weather_cond += '\n' + humidity_label + humidity + ' %'
            clouds = self.tree[4][d][7].get('all')
            doc.setHtml(self.clouds_label.text())
            clouds_label = doc.toPlainText() + ': '
            weather_cond += '\n' + clouds_label + clouds + ' %'

            self.forecast_weather_list.append(weather_cond)

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
        periods = 6
        start = 0
        if not self.json_data_bool:
            start = 1
            periods = 7
            fetched_file_periods = (len(self.tree_day.xpath('//time')))
            if fetched_file_periods < periods:
                # Some times server sends less data
                periods = fetched_file_periods
                logging.warn('Reduce forecast of the day to {0}'.format(periods-1))
        for d in range(start, periods):
            clouds_translated = ''
            wind = ''
            timeofday = self.utc(d, 'dayforecast')
            if not self.json_data_bool:
                weather_cond = self.conditions[self.tree_day[4][d][0].get('number')]
                self.dayforecast_icon_list.append(self.tree_day[4][d][0].get('var'))
                temperature_at_hour = float(self.tree_day[4][d][4].get('value'))
                precipitation = str(self.tree_day[4][d][1].get('value'))
                precipitation_type = str(self.tree_day[4][d][1].get('type'))
                windspeed = self.tree_day[4][d][3].get('mps')
                winddircode = self.tree_day[4][d][2].get('code')
                wind_name = self.tree_day[4][d][3].get('name')
                try:
                    wind_name_translated = (self.conditions[self.wind_name_dic[wind_name.lower()]] +
                                            '<br/>')
                    wind += wind_name_translated
                except KeyError:
                    logging.warn('Cannot find wind name :' + str(wind_name))
                    logging.info('Set wind name to None')
                    wind = ''
                finally:
                    if wind == '':
                        wind += '<br/>'
                clouds = self.tree_day[4][d][7].get('value')
                cloudspercent = self.tree_day[4][d][7].get('all')
            else:
                weather_cond = self.conditions[str(self.tree_day['list'][d]['weather'][0]['id'])]
                self.dayforecast_icon_list.append(self.tree_day['list'][d]['weather'][0]['icon'])
                temperature_at_hour = float(self.tree_day['list'][d]['main']['temp'])
                precipitation_orig = self.tree_day['list'][d]
                precipitation_rain = precipitation_orig.get('rain')
                precipitation_snow = precipitation_orig.get('snow')
                if precipitation_rain != None and len(precipitation_rain) > 0:
                    precipitation_type = 'rain'
                    precipitation = precipitation_rain['3h']
                elif precipitation_snow != None and len(precipitation_snow) > 0:
                    precipitation_type = 'snow'
                    precipitation_snow['3h']
                else:
                    precipitation = 'None'
                windspeed = self.tree_day['list'][d]['wind']['speed']
                winddircode = self.winddir_json_code(self.tree_day['list'][d]['wind'].get('deg'))
                clouds = self.tree_day['list'][d]['weather'][0]['description']
                cloudspercent = self.tree_day['list'][0]['clouds']['all']

            self.dayforecast_weather_list.append(weather_cond)
            daytime = QLabel(
                '<font color=grey>' + timeofday[:-3] + '<br/>' +
                '{0:.0f}'.format(temperature_at_hour) +
                '°' + '</font>')
            daytime.setAlignment(Qt.AlignHCenter)
            unit = self.settings.value('Unit') or 'metric'
            if unit == 'metric':
                mu = 'mm'
            elif unit == 'imperial':
                mu = 'inch'
                if precipitation.count('None') == 0:
                    precipitation = str(float(precipitation) / 25.0)
            ttip = str(precipitation) + ' ' + mu + ' ' + precipitation_type + '<br/>'
            if ttip.count('None') >= 1:
                ttip = ''
            else:
                ttip = ttip.replace('snow', self.tr('snow'))
                ttip = ttip.replace('rain', self.tr('rain'))
            ttip = ttip + (str(windspeed) + ' ' + self.speed_unit)
            if winddircode != '':
                wind = self.wind_direction[winddircode] + ' '
            else:
                logging.warn('Wind direction code is missing: ' +
                             str(winddircode))
            if clouds != '':
                try:
                    # In JSON there is no clouds description
                    clouds_translated = self.conditions[self.clouds_name_dic[clouds.lower()]]
                except KeyError:
                    logging.warn('The clouding description in json is not relevant')
                    clouds_translated = ''
            else:
                logging.warn('Clouding name is missing: ' + str(clouds))
            clouds_cond = clouds_translated + ' ' + str(cloudspercent) + '%'
            ttip = ttip + wind + clouds_cond
            daytime.setToolTip(ttip)
            self.dayforecast_temp_layout.addWidget(daytime)

    def ozone_fetch(self):
        logging.debug('Download ozone info...')
        self.ozone_thread = Ozone(self.uv_coord)
        self.ozone_thread.o3_signal['PyQt_PyObject'].connect(self.ozone_index)
        self.ozone_thread.start()

    def ozone_index(self, index):
        try:
            du = int(index)
            o3_color = self.ozone_du(du)
            factor = str(du)[:1] + '.' + str(du)[1:2]
            gauge = '◼' * round(float(factor))
            logging.debug('Ozone gauge: ' + gauge)

        except:
            du = '-'
            o3_color = None
        du_unit = QCoreApplication.translate('Dobson Units', 'DU', 'Ozone value label')
        if o3_color is not None:
            self.ozone_value_label.setText('<font color=grey>' + str(du) + ' ' + du_unit +
                    '</font>' + '<font color=' + o3_color + '> ' + gauge + '</font>')
            self.ozone_value_label.setToolTip(QCoreApplication.translate(
                'Ozone value tooltip', '''The average amount of ozone in the <br/> atmosphere is
                roughly 300 Dobson Units. What scientists call the Antarctic Ozone “Hole”
                is an area where the ozone concentration drops to an average of about
                100 Dobson Units.''', 'http://ozonewatch.gsfc.nasa.gov/facts/dobson_SH.html'))
        else:
            self.ozone_value_label.setText('<font color=grey>' + str(du) + '</font>')

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
            self.uv_value_label.setText('<font color=grey>' + '{0:.1f}'.format(float(index)) +
                    '  ' + self.uv_risk[uv_color[1]] + '</font>' +
                    '<br/>' + '<font color=' + uv_color[0] + '><b>' +
                    uv_gauge + '</b></font>')
        else:
            self.uv_value_label.setText('<font color=grey>' + uv_gauge + '</font>')
        logging.debug('UV gauge ◼: ' + uv_gauge)
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

class Ozone(QThread):
    o3_signal = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, coord, parent=None):
        QThread.__init__(self, parent)
        self.coord = coord
        self.settings = QSettings()
        self.appid = self.settings.value('APPID') or ''

    def run(self):
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
        try:
            lat = self.coord[0]
            lon = self.coord[1]
            url = ('http://api.openweathermap.org/pollution/v1/o3/' +
                   lat + ',' + lon +
                   '/current.json?appid=' + self.appid)
            logging.debug('Fetching url for ozone index: ' + str(url))
            req = urllib.request.urlopen(url, timeout=5)
            page = req.read()
            dico_value = eval(page)
            o3_ind = dico_value['data']
            logging.debug('Ozone index: ' + str(o3_ind))
        except:
            o3_ind = '-'
            logging.error('Cannot find Ozone index')
        self.o3_signal['PyQt_PyObject'].emit(o3_ind)


class Uv(QThread):
    uv_signal = pyqtSignal(['PyQt_PyObject'])

    def __init__(self, uv_coord, parent=None):
        QThread.__init__(self, parent)
        self.uv_coord = uv_coord
        self.settings = QSettings()
        self.appid = self.settings.value('APPID') or ''

    def run(self):
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
        try:
            lat = self.uv_coord[0]
            lon = self.uv_coord[1]
            url = ('http://api.owm.io/air/1.0/uvi/current?lat=' +
                   lat + '&lon=' + lon +
                   '&appid=' + self.appid)
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
        self.settings = QSettings()

    def run(self):
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
