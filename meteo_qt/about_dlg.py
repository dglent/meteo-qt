#!/usr/bin/env python3


from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class AboutDialog(QDialog):
    def __init__(self, title, text, image, contributors, parent=None):
        super(AboutDialog, self).__init__(parent)
        layout = QVBoxLayout()
        titleLayout = QHBoxLayout()
        name_versionLabel = QLabel(title)
        contentsLayout = QHBoxLayout()
        aboutBrowser = QTextBrowser()
        aboutBrowser.append(text)
        aboutBrowser.setOpenExternalLinks(True)
        creditsBrowser = QTextBrowser()
        creditsBrowser.append(contributors)
        creditsBrowser.setOpenExternalLinks(True)
        TabWidget = QTabWidget()
        TabWidget.addTab(aboutBrowser, self.tr('About'))
        TabWidget.addTab(creditsBrowser, self.tr('Contributors'))
        aboutBrowser.moveCursor(QTextCursor.Start)
        creditsBrowser.moveCursor(QTextCursor.Start)
        imageLabel = QLabel()
        imageLabel.setPixmap(QPixmap(image))
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

