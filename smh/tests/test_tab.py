#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import logging
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtWidgets
import pytest
import sys, os
from smh import Session
from smh.gui.review import ReviewTab

datadir = os.path.dirname(os.path.abspath(__file__))+'/test_data'
try:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
except RuntimeError:
    pass
def create_blank_window(width=800, height=400):
    window = QtWidgets.QMainWindow()
    window.resize(width, height)
    cw = QtWidgets.QWidget(window)
    window.setCentralWidget(cw)
    return window, cw

@pytest.mark.xfail(
    reason="ReviewTab initializes an unconfigured MeasurementTableModelProxy",
    strict=False,
)
def test_ReviewTab(session=None):
    if session is None: session = Session.load(datadir+"/test_G64-12_v02.smh")
    session.measure_abundances()
    window, cw = create_blank_window(width=1000,height=600)
    window.session = session
    tab = ReviewTab(window)

    vbox = QtWidgets.QVBoxLayout(cw)
    vbox.addWidget(tab)
    assert tab is not None
    window.close()

if __name__=="__main__":
    session = Session.load(datadir+"/test_G64-12_v02.smh")
    w1 = test_ReviewTab(session)
    ws = [w1]

    for w in ws:
        w.show()
        w.raise_()
    sys.exit(app.exec())
