from PyQt5.QtCore import QSize, QCoreApplication
from PyQt5.QtGui import QPixmap, QTextCursor, QIcon
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QTabWidget, QTextBrowser, QVBoxLayout
)


class AboutDialog(QDialog):
    def __init__(self, title, text, image, parent=None):
        super(AboutDialog, self).__init__(parent)
        layout = QVBoxLayout()
        titleLayout = QHBoxLayout()
        name_versionLabel = QLabel(title)
        contentsLayout = QHBoxLayout()
        aboutBrowser = QTextBrowser()
        aboutBrowser.append(text)
        aboutBrowser.setOpenExternalLinks(True)
        creditsBrowser = QTextBrowser()
        creditsBrowser.append(self.contributors())
        creditsBrowser.setOpenExternalLinks(True)
        TabWidget = QTabWidget()
        TabWidget.addTab(aboutBrowser, self.tr('About'))
        TabWidget.addTab(creditsBrowser, self.tr('Contributors'))
        aboutBrowser.moveCursor(QTextCursor.Start)
        creditsBrowser.moveCursor(QTextCursor.Start)
        imageLabel = QLabel()
        icon = QIcon.fromTheme('weather-few-clouds')
        if icon.isNull():
            imageLabel.setPixmap(QPixmap(image))
        else:
            imageLabel.setPixmap(icon.pixmap(48, 48))
        titleLayout.addWidget(imageLabel)
        titleLayout.addWidget(name_versionLabel)
        titleLayout.addStretch()
        contentsLayout.addWidget(TabWidget)
        buttonLayout = QHBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        buttonLayout.addWidget(buttonBox)
        layout.addLayout(titleLayout)
        layout.addLayout(contentsLayout)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)
        buttonBox.clicked.connect(self.accept)
        self.setMinimumSize(QSize(380, 400))
        self.setWindowTitle(self.tr('About Meteo-qt'))

    def contributors(self):

        contributors = (
            QCoreApplication.translate(
                '',
                'Jiri Podhorecky<br/>'
                'Pavel Fric<br/>'
                '[cs] Czech translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Jürgen Thurau <a href="mailto:linux@psyca.de">linux@psyca.de</a>'
                '<br/>[de] German translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Peter Mattern '
                '<a href="mailto:pmattern@arcor.de">pmattern@arcor.de</a>'
                '<br/> [de] German translation, Project',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Dimitrios Glentadakis '
                '<a href="mailto:dglent@free.fr">dglent@free.fr</a>'
                '<br/> [el] Greek translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p> juancarlospaco '
                '<a href="mailto:JuanCarlosPaco@gmail.com">'
                'JuanCarlosPaco@gmail.com</a>'
                '<br/> [es] Spanish translation, Project',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Ozkar L. Garcell '
                '<a href="mailto:ozkar.garcell@gmail.com">'
                'ozkar.garcell@gmail.com</a>'
                '<br/> Teo Laírla (teolairlasg) '
                '<a href="mailto:teo.lairla@iessierradeguara.com">'
                'teo.lairla@iessierradeguara.com</a>'
                '<br/> [es] Spanish translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Laurene Albrand '
                '<a href="mailto:laurenealbrand@outlook.com">'
                'laurenealbrand@outlook.com</a>'
                '<br/> [fr] French translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Rémi Verschelde '
                '<a href="mailto:remi@verschelde.fr">remi@verschelde.fr</a>'
                '<br/> [fr] French translation, Project',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>werthad <a href="mailto:werthad@gmail.com">'
                'werthad@gmail.com</a>'
                '<br/> [hu] Hungarian translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Archita Zabaleta <a href="mailto:architazabaleta@gmail.com">'
                'architazabaleta@gmail.com</a>'
                '<br/> [it] Italian translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>standreas <a href="mailto:standreas@riseup.net">'
                'standreas@riseup.net</a>'
                '<br/> [it] Italian translation, Weblate',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Masamichi Ito <a href="https://github.com/ito32bit">'
                'https://github.com/ito32bit</a>'
                '<br/> [ja] Japanese translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Heimen Stoffels '
                '<a href="mailto:vistausss@outlook.com">'
                'vistausss@outlook.com</a>'
                '<br/> [nl] Dutch translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Daniel Napora '
                '<a href="mailto:napcok@gmail.com">napcok@gmail.com</a>'
                '<br/> Tomasz Przybył '
                '<a href="mailto:fademind@gmail.com">fademind@gmail.com</a>'
                '<br/> [pl] Polish translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Adrian Moise'
                '<a href="mailto:sah.mat.ro@gmail.com">sah.mat.ro@gmail.com</a>'
                '<br/> [ro] Romanian translation',
                ''
            )

            + QCoreApplication.translate(
                '',
                '<p>Artem Vorotnikov '
                '<a href="mailto:artem@vorotnikov.me">artem@vorotnikov.me</a>'
                '<br/> Sergey Shitikov '
                '<a href="mailto:rw4lll@yandex.ru">rw4lll@yandex.ru</a>'
                '<br/>Alexey Zakaldaev '
                '<a href="mailto:nelex111@gmail.com">nelex111@gmail.com</a>'
                '<br/>Liliya Panova<br/> [ru] Russian translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>jose1711 '
                '<a href="mailto:jose1711@gmail.com">'
                'jose1711@gmail.com</a>'
                '<br> [sk] Slovak translation, Project',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Luna bittin Jernberg '
                '<br> [sv] Swedish translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Atilla Öntaş '
                '<a href="mailto:tarakbumba@gmail.com">'
                'tarakbumba@gmail.com</a>'
                '<br/> [tr] Turkish translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>Yuri Chornoivan '
                '<a href="mailto:yurchor@ukr.net">yurchor@ukr.net</a>'
                '<br/> [uk] Ukrainian translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>You-Cheng Hsieh '
                '<a href="mailto:yochenhsieh@gmail.com">'
                'yochenhsieh@gmail.com</a>'
                '<br/> [zh_TW] Chinese (Taiwan) translation',
                ''
            )
            + QCoreApplication.translate(
                '',
                '<p>pmav99<br/> Project',
                ''
            )
        )
        return contributors
