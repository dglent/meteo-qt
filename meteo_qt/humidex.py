# https://gist.github.com/sourceperl/45587ea99ff123745428

import math
from PyQt5.QtCore import (
    QCoreApplication, QObject
)


class Humidex(QObject):

    def __init__(self, t_air=0.0, rel_humidity=0, unit='°C', parent=None):
        super(Humidex, self).__init__(parent)
        ''' Output:
            self.dew_point : T° 0.0 [string]
            self.comfort_text : Comfort level [string]
        '''
        if unit == '°F':
            t_air_c = float('{0:.1f}'.format((t_air - 32) / 1.8))
        elif unit == '°K':
            t_air_c = float('{0:.1f}'.format(t_air - 273.15))
        else:
            t_air_c = t_air
        dew_point_c = self.get_dew_point_c(t_air_c, rel_humidity)
        self.comfort_text = self.comfort_level(dew_point_c)
        if unit == '°F':
            self.dew_point = '{0:.1f}'.format(dew_point_c * 1.8 + 32)
        elif unit == '°K':
            self.dew_point = '{0:.1f}'.format(dew_point_c + 273.15)
        else:
            self.dew_point = '{0:.1f}'.format(dew_point_c)

    def comfort_level(self, dew_point):
        if dew_point < 10.0:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Dry',
                'Weather info dialogue'
            )
        elif dew_point < 13.0:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Very comfortable',
                'Weather info dialogue'
            )
        elif dew_point < 16.0:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Comfortable',
                'Weather info dialogue'
            )
        elif dew_point < 19.0:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Alright',
                'Weather info dialogue'
            )
        elif dew_point < 22.0:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Uncomfortable',
                'Weather info dialogue'
            )
        elif dew_point < 25.0:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Very uncomfortable',
                'Weather info dialogue'
            )
        else:
            return QCoreApplication.translate(
                'Comfort level depending the dew point',
                'Severely uncomfortable',
                'Weather info dialogue'
            )

    def get_frost_point_c(self, t_air_c, dew_point_c):
        """Compute the frost point in degrees Celsius

        :param t_air_c: current ambient temperature in degrees Celsius
        :type t_air_c: float
        :param dew_point_c: current dew point in degrees Celsius
        :type dew_point_c: float
        :return: the frost point in degrees Celsius
        :rtype: float
        """
        # code from: https://gist.github.com/sourceperl/45587ea99ff123745428
        dew_point_k = 273.15 + dew_point_c
        t_air_k = 273.15 + t_air_c
        frost_point_k = dew_point_k - t_air_k + 2671.02 / ((2954.61 / t_air_k) + 2.193665 * math.log(t_air_k) - 13.3448)
        return frost_point_k - 273.15

    def get_dew_point_c(self, t_air_c, rel_humidity):
        """Compute the dew point in degrees Celsius

        :param t_air_c: current ambient temperature in degrees Celsius
        :type t_air_c: float
        :param rel_humidity: relative humidity in %
        :type rel_humidity: float
        :return: the dew point in degrees Celsius
        :rtype: float
        """
        # code from: https://gist.github.com/sourceperl/45587ea99ff123745428
        A = 17.27
        B = 237.7
        alpha = ((A * t_air_c) / (B + t_air_c)) + math.log(rel_humidity / 100.0)
        return (B * alpha) / (A - alpha)
