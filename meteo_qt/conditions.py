from PyQt5.QtCore import QCoreApplication, QObject


class WeatherConditions(QObject):

    def __init__(self, parent=None):
        super(WeatherConditions, self).__init__(parent)
        self.trans = {'200': self.tr('thunderstorm with light rain'),
                      '201': self.tr('thunderstorm with rain'),
                      '202': self.tr('thunderstorm with heavy rain'),
                      '210': self.tr('light thunderstorm'),
                      '211': self.tr('thunderstorm'),
                      '212': self.tr('heavy thunderstorm'),
                      '221': self.tr('ragged thunderstorm'),
                      '230': self.tr('thunderstorm with light drizzle'),
                      '231': self.tr('thunderstorm with drizzle'),
                      '232': self.tr('thunderstorm with heavy drizzle'),
                      '300': self.tr('light intensity drizzle'),
                      '301': self.tr('drizzle'),
                      '302': self.tr('heavy intensity drizzle'),
                      '310': self.tr('light intensity drizzle rain'),
                      '311': self.tr('drizzle rain'),
                      '312': self.tr('heavy intensity drizzle rain'),
                      '313': self.tr('shower rain and drizzle'),
                      '314': self.tr('heavy shower rain and drizzle'),
                      '321': self.tr('shower drizzle'),
                      '500': self.tr('light rain'),
                      '501': self.tr('moderate rain'),
                      '502': self.tr('heavy intensity rain'),
                      '503': self.tr('very heavy rain'),
                      '504': self.tr('extreme rain'),
                      '511': self.tr('freezing rain'),
                      '520': self.tr('light intensity shower rain'),
                      '521': self.tr('shower rain'),
                      '522': self.tr('heavy intensity shower rain'),
                      '531': self.tr('ragged shower rain'),
                      '600': self.tr('light snow'),
                      '601': self.tr('snow'),
                      '602': self.tr('heavy snow'),
                      '611': self.tr('sleet'),
                      '612': self.tr('shower sleet'),
                      '615': self.tr('light rain and snow'),
                      '616': self.tr('rain and snow'),
                      '620': self.tr('light shower snow'),
                      '621': self.tr('shower snow'),
                      '622': self.tr('heavy shower snow'),
                      '701': self.tr('mist'),
                      '711': self.tr('smoke'),
                      '721': self.tr('haze'),
                      '731': self.tr('sand, dust whirls'),
                      '741': self.tr('fog'),
                      '751': self.tr('sand'),
                      '761': self.tr('dust'),
                      '762': self.tr('volcanic ash'),
                      '771': self.tr('squalls'),
                      '781': self.tr('tornado'),
                      '800': self.tr('clear sky'),
                      '801': self.tr('few clouds'),
                      '802': self.tr('scattered clouds'),
                      '803': self.tr('broken clouds'),
                      '804': self.tr('overcast clouds'),
                      '900': self.tr('tornado'),
                      '901': self.tr('tropical storm'),
                      '902': self.tr('hurricane'),
                      '903': self.tr('cold'),
                      '904': self.tr('hot'),
                      '905': self.tr('windy'),
                      '906': self.tr('hail'),
                      '951': self.tr('calm'),
                      '952': self.tr('light breeze'),
                      '953': self.tr('gentle breeze'),
                      '954': self.tr('moderate breeze'),
                      '955': self.tr('fresh breeze'),
                      '956': self.tr('strong breeze'),
                      '957': self.tr('high wind, near gale'),
                      '958': self.tr('gale'),
                      '959': self.tr('severe gale'),
                      '960': self.tr('storm'),
                      '961': self.tr('violent storm'),
                      '962': self.tr('hurricane')}

        self.clouds = {'clear sky': '800',
                       'few clouds': '801',
                       'scattered clouds': '802',
                       'broken clouds': '803',
                       'overcast clouds': '804'}

        self.wind = {'calm': '951',
                     'light breeze': '952',
                     'gentle breeze': '953',
                     'moderate breeze': '954',
                     'fresh breeze': '955',
                     'strong breeze': '956',
                     'high wind, near gale': '957',
                     'gale': '958',
                     'severe gale': '959',
                     'storm': '960',
                     'violent storm': '961',
                     'hurricane': '962'}

        self.rain = {'no': QCoreApplication.translate(
                     'Precipitation type', 'no', 'Weather overview dialogue'),
                     'rain': QCoreApplication.translate(
                     'Precipitation type', 'rain',
                     'Weather overview dialogue'),
                     'snow': QCoreApplication.translate(
                     'Precipitation type', 'snow',
                     'Weather overview dialogue')
                     }

        self.wind_direction = {'N': self.tr('North'),
                               'NE': self.tr('NorthEast'),
                               'NNE': self.tr('North-northeast'),
                               'NW': self.tr('NorthWest'),
                               'NNW': self.tr('North-northwest'),
                               'S': self.tr('South'),
                               'SE': self.tr('SouthEast'),
                               'SSE': self.tr('South-southeast'),
                               'SW': self.tr('SouthWest'),
                               'SSW': self.tr('South-southwest'),
                               'E': self.tr('East'),
                               'ESE': self.tr('East-southeast'),
                               'ENE': self.tr('East-northeast'),
                               'W': self.tr('West'),
                               'WSW': self.tr('West-southwest'),
                               'WNW': self.tr('West-northwest')}

        self.wind_codes = {'N': self.tr('N'),
                           'NE': self.tr('NE'),
                           'NNE': self.tr('NNE'),
                           'NW': self.tr('NW'),
                           'NNW': self.tr('NNW'),
                           'S': self.tr('S'),
                           'SE': self.tr('SE'),
                           'SSE': self.tr('SSE'),
                           'SW': self.tr('SW'),
                           'SSW': self.tr('SSW'),
                           'E': self.tr('E'),
                           'ESE': self.tr('ESE'),
                           'ENE': self.tr('ENE'),
                           'W': self.tr('W'),
                           'WSW': self.tr('WSW'),
                           'WNW': self.tr('WNW')}

        self.uv_risk = {'Low':
                        QCoreApplication.translate('UV risk', 'Low', ''),
                        'Moderate':
                        QCoreApplication.translate('UV risk',
                                                   'Moderate', ''),
                        'High':
                        QCoreApplication.translate('UV risk', 'High', ''),
                        'Very high':
                        QCoreApplication.translate('UV risk', 'Very high', ''),
                        'Extreme':
                        QCoreApplication.translate('UV risk', 'Extreme', ''),
                        'None': '-'}

        self.uv_recommend = {
            'Low': QCoreApplication.translate(
                'Low UV recommended protection',
                '''Wear sunglasses on bright days; use sunscreen if there is
                snow on<br/>the ground, which reflects UV radiation,
                or if you have particularly fair skin.''',
                'Low https://en.wikipedia.org/wiki/Ultraviolet_index'),
            'Moderate': QCoreApplication.translate(
                'Moderate UV recommended protection',
                '''Take precautions, such as covering up, if you will be
                outside.<br/>Stay in shade near midday
                when the sun is strongest.''',
                'Moderate https://en.wikipedia.org/wiki/Ultraviolet_index'),
            'High': QCoreApplication.translate(
                'High UV recommended protection',
                '''Cover the body with sun protective clothing, use SPF 30+
                sunscreen,<br/>wear a hat, reduce time in the sun within three
                hours of solar noon, and wear sunglasses.''',
                'High https://en.wikipedia.org/wiki/Ultraviolet_index'),
            'Very high': QCoreApplication.translate(
                'Very high UV recommended protection',
                '''Wear SPF 30+ sunscreen, a shirt, sunglasses, and a
                wide-brimmed hat.<br/>Do not stay in the sun for too long.''',
                'Very high https://en.wikipedia.org/wiki/Ultraviolet_index'),
            'Extreme': QCoreApplication.translate(
                'Extreme UV recommended protection',
                '''Take all precautions: Wear SPF 30+ sunscreen, a long-sleeved
                shirt and trousers,<br/>sunglasses, and a very broad hat.
                Avoid the sun within three hours of solar noon.''',
                'Extreme https://en.wikipedia.org/wiki/Ultraviolet_index'),
            'None': '-'
        }

        self.beaufort = {'0': QCoreApplication.translate('Beaufort scale 0 - Wikipedia', 'Sea: Sea like a mirror\nLand: Calm. Smoke rises vertically', 'Tooltip in Weather overview dialogue'),
                         '1': QCoreApplication.translate('Beaufort scale 1 - Wikipedia', 'Sea: Ripples with the appearance of scales are formed, but without foam crests\nLand: Smoke drift indicates wind direction. Leaves and wind vanes are stationary', 'Tooltip in Weather overview dialogue'),
                         '2': QCoreApplication.translate('Beaufort scale 2 - Wikipedia', 'Sea: Small wavelets, still short but more pronounced; crests have a glassy appearance and do not break\nLand: Wind felt on exposed skin. Leaves rustle. Wind vanes begin to move', 'Tooltip in Weather overview dialogue'),
                         '3': QCoreApplication.translate('Beaufort scale 3 - Wikipedia', 'Sea: Large wavelets. Crests begin to break; scattered whitecaps\nLand: Leaves and small twigs constantly moving, light flags extended', 'Tooltip in Weather overview dialogue'),
                         '4': QCoreApplication.translate('Beaufort scale 4 - Wikipedia', 'Sea: Small waves with breaking crests. Fairly frequent whitecaps\nLand: Dust and loose paper raised. Small branches begin to move', 'Tooltip in Weather overview dialogue'),
                         '5': QCoreApplication.translate('Beaufort scale 5 - Wikipedia', 'Moderate waves of some length. Many whitecaps. Small amounts of spray\nLand: Branches of a moderate size move. Small trees in leaf begin to sway', 'Tooltip in Weather overview dialogue'),
                         '6': QCoreApplication.translate('Beaufort scale 6 - Wikipedia', 'Sea: Long waves begin to form. White foam crests are very frequent. Some airborne spray is present\nLand: Large branches in motion. Whistling heard in overhead wires. Umbrella use becomes difficult. Empty plastic bins tip over', 'Tooltip in Weather overview dialogue'),
                         '7': QCoreApplication.translate('Beaufort scale 7 - Wikipedia', 'Sea: Sea heaps up. Some foam from breaking waves is blown into streaks along wind direction. Moderate amounts of airborne spray\nLand: Whole trees in motion. Effort needed to walk against the wind', 'Tooltip in Weather overview dialogue'),
                         '8': QCoreApplication.translate('Beaufort scale 8 - Wikipedia', 'Sea: Moderately high waves with breaking crests forming spindrift. Well-marked streaks of foam are blown along wind direction. Considerable airborne spray\Land: Some twigs broken from trees. Cars veer on road. Progress on foot is seriously impeded', 'Tooltip in Weather overview dialogue'),
                         '9': QCoreApplication.translate('Beaufort scale 9 - Wikipedia', 'Sea: High waves whose crests sometimes roll over. Dense foam is blown along wind direction. Large amounts of airborne spray may begin to reduce visibility\Land: Some branches break off trees, and some small trees blow over. Construction/temporary signs and barricades blow over', 'Tooltip in Weather overview dialogue'),
                         '10': QCoreApplication.translate('Beaufort scale 10 - Wikipedia', 'Sea: Very high waves with overhanging crests. Large patches of foam from wave crests give the sea a white appearance. Considerable tumbling of waves with heavy impact. Large amounts of airborne spray reduce visibility\nLand: Trees are broken off or uprooted, structural damage likely', 'Tooltip in Weather overview dialogue'),
                         '11': QCoreApplication.translate('Beaufort scale 11 - Wikipedia', 'Sea: Exceptionally high waves. Very large patches of foam, driven before the wind, cover much of the sea surface. Very large amounts of airborne spray severely reduce visibility\nLand: Widespread vegetation and structural damage likely', 'Tooltip in Weather overview dialogue'),
                         '12': QCoreApplication.translate('Beaufort scale 12 - Wikipedia', 'Sea: Huge waves. Sea is completely white with foam and spray. Air is filled with driving spray, greatly reducing visibility\nLand: Severe widespread damage to vegetation and structures. Debris and unsecured objects are hurled about', 'Tooltip in Weather overview dialogue')
                         }
