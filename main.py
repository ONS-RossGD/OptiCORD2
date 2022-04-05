"""OptiCORD - An Optimisation tool for CORD users.
"""

__version__ = '2.0.0'

import sys
import ctypes
import warnings
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from actions import attempt_recovery
from ui import mainwindow, welcome
from ui.resources import resource_init  # looks redundant but isn't
from util import TempFile
from tables import NaturalNameWarning


def main():
    """Main loop"""
    app = QApplication(sys.argv)
    # set up the path for QSettings so it can be accessed anywhere
    app.setApplicationName("OptiCORD")
    app.setOrganizationName("ONS")
    app.setOrganizationDomain("ons.gov.uk")
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
        print("Exiting")


if __name__ == "__main__":
    main()
