from bmaya.lib.Qt import QtCompat, QtWidgets

import maya.OpenMayaUI as omui


def getMayaMainWindow():
    return QtCompat.wrapInstance(long(omui.MQtUtil.mainWindow()),
                                      QtWidgets.QWidget)