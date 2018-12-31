from PyQt5.QtCore import QCoreApplication, QSettings, Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QVBoxLayout)


class CityTranslate(QDialog):
    city_signal = pyqtSignal([dict])

    def __init__(self, city, cities_list, parent=None):
        super(CityTranslate, self).__init__(parent)
        self.city = city
        self.settings = QSettings()
        self.trans_cities_dict = cities_list
        self.layout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout()
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonLayout.addWidget(self.buttonBox)
        self.untranslate_city_label = QLabel(self.find_city_key(self.city))
        self.translate_line = QLineEdit(self.city)
        self.translate_line.selectAll()
        self.translate_line.setMinimumWidth(300)
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_layout.addWidget(self.status_label)
        self.panel = QGridLayout()
        self.panel.addWidget(self.untranslate_city_label, 0, 0)
        self.panel.addWidget(self.translate_line, 1, 0)
        self.layout.addLayout(self.panel)
        self.layout.addLayout(self.status_layout)
        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)
        self.setWindowTitle(QCoreApplication.translate('Window title',
                            'City translation', 'City translation dialogue'))

    def find_city_key(self, city):
        for key, value in self.trans_cities_dict.items():
            if value == city:
                return key
        return city

    def accept(self):
        city_dict = {}
        current_city = self.translate_line.text()
        for city, trans in self.trans_cities_dict.items():
            if (
                current_city == trans
                and city != self.untranslate_city_label.text()
            ):
                self.status_label.setText(
                    QCoreApplication.translate(
                        'Warning message in dialog status bar',
                        'The city allready exist',
                        'City translation'
                    )
                )
                return

        city_dict[self.untranslate_city_label.text()] = (
            self.translate_line.text()
        )

        self.city_signal[dict].emit(city_dict)
        QDialog.accept(self)
