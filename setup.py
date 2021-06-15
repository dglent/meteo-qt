#!/usr/bin/env python3

import glob
import os
from distutils.command.build import build
from distutils.core import setup


class BuildQm(build):
    # os.system('pyrcc5 -o meteo_qt/qrc_resources.py meteo_qt/resources.qrc')
    os.system('pylupdate5 meteo_qt/meteo_qt.pro')
    for ts in glob.glob('meteo_qt/translations/*.ts'):
        os.system('lrelease {0} -qm {1}'.format(ts, (ts[:-2] + 'qm')))


setup(
    name='meteo_qt',
    version='2.4',
    description='A system tray application for the weather status',
    author='Dimitrios Glentadakis',
    author_email='dglent@free.fr',
    url='https://github.com/dglent/meteo-qt',
    license='GPLv3',
    packages=['meteo_qt'],
    keywords=['weather', 'qt', 'trayicon', 'openweathermap', 'forecast'],
    data_files=[('/usr/share/applications', ['share/meteo-qt.desktop']),
                ('/usr/share/icons', ['meteo_qt/images/weather-few-clouds.png']),
                ('/usr/share/meteo_qt/translations',
                    ['meteo_qt/translations/meteo-qt_bg.qm',
                     'meteo_qt/translations/meteo-qt_ca.qm',
                     'meteo_qt/translations/meteo-qt_cs.qm',
                     'meteo_qt/translations/meteo-qt_da.qm',
                     'meteo_qt/translations/meteo-qt_de.qm',
                     'meteo_qt/translations/meteo-qt_el.qm',
                     'meteo_qt/translations/meteo-qt_en.qm',
                     'meteo_qt/translations/meteo-qt_es.qm',
                     'meteo_qt/translations/meteo-qt_fi.qm',
                     'meteo_qt/translations/meteo-qt_fr.qm',
                     'meteo_qt/translations/meteo-qt_he.qm',
                     'meteo_qt/translations/meteo-qt_hu.qm',
                     'meteo_qt/translations/meteo-qt_it.qm',
                     'meteo_qt/translations/meteo-qt_ja.qm',
                     'meteo_qt/translations/meteo-qt_lt.qm',
                     'meteo_qt/translations/meteo-qt_nb.qm',
                     'meteo_qt/translations/meteo-qt_nl.qm',
                     'meteo_qt/translations/meteo-qt_pl.qm',
                     'meteo_qt/translations/meteo-qt_pt_BR.qm',
                     'meteo_qt/translations/meteo-qt_pt.qm',
                     'meteo_qt/translations/meteo-qt_ro.qm',
                     'meteo_qt/translations/meteo-qt_ru.qm',
                     'meteo_qt/translations/meteo-qt_sk.qm',
                     'meteo_qt/translations/meteo-qt_sv.qm',
                     'meteo_qt/translations/meteo-qt_tr.qm',
                     'meteo_qt/translations/meteo-qt_uk.qm',
                     'meteo_qt/translations/meteo-qt_vi.qm',
                     'meteo_qt/translations/meteo-qt_zh_CN.qm',
                     'meteo_qt/translations/meteo-qt_zh_TW.qm']),
                ('/usr/share/doc/meteo-qt',
                    ['README.md', 'LICENSE', 'CHANGELOG', 'TODO'])],
        scripts=["bin/meteo-qt"],
        cmdclass={'build_qm': BuildQm},
        include_package_data=True,
        zip_safe=True,
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Other Audience',
            'Natural Language :: English',
            'License :: OSI Approved :: GNU General Public License (GPL)',
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: Implementation :: CPython',
    ],
)
