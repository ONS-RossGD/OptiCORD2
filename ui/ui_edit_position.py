# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'd:\GIT\OptiCORD v2 (Development)\ui\edit_position.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_PositionDialog(object):
    def setupUi(self, PositionDialog):
        PositionDialog.setObjectName("PositionDialog")
        PositionDialog.resize(400, 300)
        self.layout = QtWidgets.QGridLayout(PositionDialog)
        self.layout.setObjectName("layout")
        self.description_edit = QtWidgets.QPlainTextEdit(PositionDialog)
        self.description_edit.setObjectName("description_edit")
        self.layout.addWidget(self.description_edit, 1, 1, 1, 1)
        self.info_text_2 = QtWidgets.QLabel(PositionDialog)
        self.info_text_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTop|QtCore.Qt.AlignTrailing)
        self.info_text_2.setObjectName("info_text_2")
        self.layout.addWidget(self.info_text_2, 1, 0, 1, 1)
        self.info_text = QtWidgets.QLabel(PositionDialog)
        self.info_text.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.info_text.setObjectName("info_text")
        self.layout.addWidget(self.info_text, 0, 0, 1, 1)
        self.name_edit = QtWidgets.QLineEdit(PositionDialog)
        self.name_edit.setObjectName("name_edit")
        self.layout.addWidget(self.name_edit, 0, 1, 1, 1)
        self.frame = QtWidgets.QFrame(PositionDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout = QtWidgets.QGridLayout(self.frame)
        self.gridLayout.setObjectName("gridLayout")
        self.delete_button = QtWidgets.QPushButton(self.frame)
        self.delete_button.setObjectName("delete_button")
        self.gridLayout.addWidget(self.delete_button, 0, 0, 1, 1)
        self.button_box = QtWidgets.QDialogButtonBox(self.frame)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setObjectName("button_box")
        self.gridLayout.addWidget(self.button_box, 0, 2, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 0, 1, 1, 1)
        self.layout.addWidget(self.frame, 2, 0, 1, 2)

        self.retranslateUi(PositionDialog)
        self.button_box.accepted.connect(PositionDialog.accept)
        self.button_box.rejected.connect(PositionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(PositionDialog)

    def retranslateUi(self, PositionDialog):
        _translate = QtCore.QCoreApplication.translate
        PositionDialog.setWindowTitle(_translate("PositionDialog", "Edit position..."))
        self.description_edit.setPlaceholderText(_translate("PositionDialog", "e.g. First supertask carrying deflator changes"))
        self.info_text_2.setText(_translate("PositionDialog", "Description:"))
        self.info_text.setText(_translate("PositionDialog", "Name:"))
        self.name_edit.setToolTip(_translate("PositionDialog", "Cannot contain characters: \"\\\", \"/\""))
        self.name_edit.setPlaceholderText(_translate("PositionDialog", "e.g. supertask 12-11-2021"))
        self.delete_button.setText(_translate("PositionDialog", "Delete"))
