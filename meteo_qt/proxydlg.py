from PyQt6.QtCore import QCoreApplication, QSettings, Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QVBoxLayout)


class Proxy(QDialog):
    id_signal = pyqtSignal([tuple])
    city_signal = pyqtSignal([tuple])
    country_signal = pyqtSignal([tuple])

    def __init__(self, parent=None):
        super(Proxy, self).__init__(parent)
        self.settings = QSettings()

        self.layout = QVBoxLayout()

        self.buttonLayout = QHBoxLayout()
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonLayout.addWidget(self.buttonBox)

        self.proxy_url_label = QLabel(
            QCoreApplication.translate(
                'Entry label for the proxy url',
                'Proxy URL:',
                'Proxy settings dialogue'
            )
        )
        self.proxy_url_line = QLineEdit()
        url = self.settings.value('Proxy_url') or ''
        self.proxy_url_line = QLineEdit(url)
        self.proxy_url_line.setMinimumWidth(300)

        self.proxy_port_label = QLabel(
            QCoreApplication.translate(
                'Entry label for the proxy port',
                'Port:',
                'Proxy settings dialogue'
            )
        )
        port = self.settings.value('Proxy_port') or ''
        self.proxy_port_line = QLineEdit(port)

        self.proxy_auth_label = QLabel(
            QCoreApplication.translate(
                'Checkbox',
                'Use proxy authentification',
                'Proxy settings dialogue'
            )
        )
        self.proxy_auth_checkbox = QCheckBox()
        self.proxy_auth_bool = eval(
            self.settings.value('Use_proxy_authentification')
            or 'False'
        )
        self.proxy_auth_checkbox.setChecked(self.proxy_auth_bool)
        self.proxy_auth_checkbox.stateChanged.connect(self.proxy_auth)

        self.proxy_user_label = QLabel(QCoreApplication.translate(
            'Proxy username authentification',
            'User ID:', 'Proxy configuration dialogue'))
        self.proxy_user_label.setEnabled(self.proxy_auth_bool)
        self.proxy_pass_label = QLabel(QCoreApplication.translate(
            'Proxy password authentification',
            'Password:', 'Proxy configuration dialogue'))
        self.proxy_pass_label.setEnabled(self.proxy_auth_bool)

        user = self.settings.value('Proxy_user') or ''
        self.proxy_user_line = QLineEdit(user)
        self.proxy_user_line.setEnabled(self.proxy_auth_bool)
        password = self.settings.value('Proxy_password') or ''
        self.proxy_pass_line = QLineEdit(password)
        self.proxy_pass_line.setEnabled(self.proxy_auth_bool)
        self.proxy_pass_line.setEchoMode(QLineEdit.EchoMode.Password)

        self.status_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_layout.addWidget(self.status_label)

        self.panel = QGridLayout()
        self.panel.addWidget(self.proxy_url_label, 0, 0)
        self.panel.addWidget(self.proxy_url_line, 0, 1)
        self.panel.addWidget(self.proxy_port_label, 0, 2)
        self.panel.addWidget(self.proxy_port_line, 0, 3)
        self.panel.addWidget(self.proxy_auth_label, 1, 0)
        self.panel.addWidget(self.proxy_auth_checkbox, 1, 1)
        self.panel.addWidget(self.proxy_user_label, 2, 0)
        self.panel.addWidget(self.proxy_user_line, 2, 1)
        self.panel.addWidget(self.proxy_pass_label, 3, 0)
        self.panel.addWidget(self.proxy_pass_line, 3, 1)

        self.layout.addLayout(self.panel)
        self.layout.addLayout(self.status_layout)
        self.layout.addLayout(self.buttonLayout)

        self.setLayout(self.layout)

    def proxy_auth(self, state):
        if state == 2:
            self.proxy_auth_bool = True
            self.proxy_user_label.setEnabled(True)
            self.proxy_pass_label.setEnabled(True)
            self.proxy_user_line.setEnabled(True)
            self.proxy_pass_line.setEnabled(True)
        else:
            self.proxy_auth_bool = False
            self.proxy_user_label.setEnabled(False)
            self.proxy_pass_label.setEnabled(False)
            self.proxy_user_line.setEnabled(False)
            self.proxy_pass_line.setEnabled(False)

    def accept(self):
        port = self.proxy_port_line.text()
        if port.isdigit() or port == '':
            self.settings.setValue('Proxy_url', self.proxy_url_line.text())
            self.settings.setValue('Proxy_port', port)
            self.settings.setValue('Use_proxy_authentification',
                                   str(self.proxy_auth_bool))
            if self.proxy_auth_bool:
                self.settings.setValue('Proxy_user',
                                       self.proxy_user_line.text())
                self.settings.setValue('Proxy_password',
                                       self.proxy_pass_line.text())
        else:
            self.status_label.setText('Port number must contain only digits')
            return
        QDialog.accept(self)
