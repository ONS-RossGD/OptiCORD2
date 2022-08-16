"""OptiCORD - An Optimisation tool for CORD users.
"""

__version__ = '2.0.0'

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import ctypes
import warnings
from shutil import copyfile
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from actions import attempt_recovery
from ui import mainwindow, welcome
from PyQt5.QtCore import QSettings
from ui.resources import resource_init  # looks redundant but isn't
from util import TempFile
from tables import NaturalNameWarning

log = logging.getLogger('OptiCORD')
root = os.getcwd()


def copy_settings():
    try:
        copyfile(
            f'C:/Users/{os.getlogin()}/AppData/Roaming/ONS/OptiCORD.ini',
            f'{root}/logs/{os.getlogin()}.ini'
        )
    except:
        pass


def setup_logging():
    """Sets up logging module for use later on"""


log.setLevel(logging.DEBUG)
rf = RotatingFileHandler(f'{root}/logs/{os.getlogin()}.log',
                         maxBytes=100000, backupCount=1)
rf.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(asctime)s %(threadName)-12s'
                        ' %(levelname)-8s: %(message)s',
                        datefmt='%m-%d %H:%M')
rf.setFormatter(fmt)
log.addHandler(rf)
log.debug('----------------------NEW SESSION----------------------')


def main():
    """Main loop"""
    app = QApplication(sys.argv)
    # set up the path for QSettings so it can be accessed anywhere
    app.setApplicationName("OptiCORD")
    app.setOrganizationName("ONS")
    app.setOrganizationDomain("ons.gov.uk")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    setup_logging()
    # TODO python hack to set task bar icon, may not be needed in exe
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        f'ONS.OptiCORD.{__version__}')
    # ignore NaturalNameWarnings as this functionality is not used
    warnings.filterwarnings('ignore', category=NaturalNameWarning)
    mw = mainwindow.MainWindow()  # creates the main window instance
    # set the icon
    mw.setWindowIcon(QIcon('./ui/resources/OptiCORD_icon.png'))
    # set the window title
    mw.setWindowTitle(f'OptiCORD v{__version__}')
    # initially show the welcome page
    mw.setCentralWidget(welcome.WelcomePage(mw))
    mw.show()  # begin showing to user
    TempFile.check_existing()  # check if OptiCORD closed unexpectedly
    if TempFile.recovery_path:
        # offer recovery attempt
        attempt_recovery(mw)
    try:
        sys.exit(app.exec_())
    except:  # TODO catch correct Exception.
        log.exception('System excited with exception:\n')
    finally:
        copy_settings()


if __name__ == "__main__":
    main()
