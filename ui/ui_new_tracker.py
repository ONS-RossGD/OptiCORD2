# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'd:\GIT\OptiCORD v2 (Development)\ui\new_tracker.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_TrackerDialog(object):
    def setupUi(self, TrackerDialog):
        TrackerDialog.setObjectName("TrackerDialog")
        TrackerDialog.resize(400, 300)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(TrackerDialog.sizePolicy().hasHeightForWidth())
        TrackerDialog.setSizePolicy(sizePolicy)
        self.layout = QtWidgets.QGridLayout(TrackerDialog)
        self.layout.setObjectName("layout")
        self.button_box = QtWidgets.QDialogButtonBox(TrackerDialog)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setObjectName("button_box")
        self.layout.addWidget(self.button_box, 2, 1, 1, 1)
        self.name_edit = QtWidgets.QLineEdit(TrackerDialog)
        self.name_edit.setObjectName("name_edit")
        self.layout.addWidget(self.name_edit, 0, 1, 1, 1)
        self.info_text = QtWidgets.QLabel(TrackerDialog)
        self.info_text.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.info_text.setObjectName("info_text")
        self.layout.addWidget(self.info_text, 0, 0, 1, 1)
        self.info_text_2 = QtWidgets.QLabel(TrackerDialog)
        self.info_text_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTop|QtCore.Qt.AlignTrailing)
        self.info_text_2.setObjectName("info_text_2")
        self.layout.addWidget(self.info_text_2, 1, 0, 1, 1)
        self.description_edit = QtWidgets.QPlainTextEdit(TrackerDialog)
        self.description_edit.setObjectName("description_edit")
        self.layout.addWidget(self.description_edit, 1, 1, 1, 1)

        self.retranslateUi(TrackerDialog)
        self.button_box.accepted.connect(TrackerDialog.accept)
        self.button_box.rejected.connect(TrackerDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(TrackerDialog)

    def retranslateUi(self, TrackerDialog):
        _translate = QtCore.QCoreApplication.translate
        TrackerDialog.setWindowTitle(_translate("TrackerDialog", "Create new OptiCORD change tracker..."))
        self.name_edit.setPlaceholderText(_translate("TrackerDialog", "Change being tracked (e.g. CP01a deflator changes)"))
        self.info_text.setText(_translate("TrackerDialog", "Name:"))
        self.info_text_2.setText(_translate("TrackerDialog", "Description:"))
        self.description_edit.setPlaceholderText(_translate("TrackerDialog", "e.g. CP01a deflator changes as part of CEDAR defect CDX00000001"))
