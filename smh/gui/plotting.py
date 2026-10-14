#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" The radial velocity tab view for the Spectroscopy Made Hard GUI. """

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import numpy as np
import os
import sys
from PySide6 import QtCore, QtWidgets

import mpl
from matplotlib import (gridspec, pyplot as plt)
# E. Holmbeck added this line to account for a newer version of matplotlib
plt.rcParams['errorbar.capsize'] = 3
from smh import (Session, isoutils)
from smh.linelists import LineList

import logging
logger = logging.getLogger(__name__)

__all__ = ["SummaryPlotDialog"]


def _star_prefixed_filename(session, filename):
    try:
        star_name = str(session.metadata["OBJECT"]).strip()
    except (AttributeError, KeyError, TypeError):
        star_name = ""
    star_name = "".join(
        "_" if char in '\\/:*?"<>|' else char for char in star_name
    ).strip(" ._")
    return "{}_{}".format(star_name, filename) if star_name else filename


def _add_save_button(dialog, layout, figure_widget, default_name):
    button = QtWidgets.QPushButton("Save Plot...", dialog)
    button.clicked.connect(
        lambda: _save_figure(dialog, figure_widget.figure, default_name)
    )
    layout.addWidget(button)


def _save_figure(dialog, figure, default_name):
    path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
        dialog,
        caption="Save plot",
        dir=default_name,
        filter="PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;All files (*)"
    )
    if not path:
        return

    if not os.path.splitext(path)[1]:
        extension = {
            "PNG (*.png)": ".png",
            "PDF (*.pdf)": ".pdf",
            "SVG (*.svg)": ".svg",
        }.get(selected_filter, ".png")
        path += extension

    figure.savefig(path)

class SummaryPlotDialog(QtWidgets.QDialog):
    def __init__(self, session, parent, ncap=False):
        super(SummaryPlotDialog, self).__init__()
        # Center it on the parent location
        rect = parent.geometry()
        x, y = rect.center().x(), rect.center().y()
        w = 1000
        h = 640
        self.setGeometry(x-w/2, y-h/2, w, h)
        vbox = QtWidgets.QVBoxLayout(self)
        figure_widget = mpl.MPLWidget(None, tight_layout=True)
        vbox.addWidget(figure_widget)
        if ncap:
            session.make_ncap_summary_plot(figure_widget.figure)
            _add_save_button(
                self, vbox, figure_widget,
                _star_prefixed_filename(session, "ncap_summary_plot.png")
            )
        else:
            session.make_summary_plot(figure_widget.figure)
            _add_save_button(
                self, vbox, figure_widget,
                _star_prefixed_filename(session, "summary_plot.png")
            )
        
class SNRPlotDialog(QtWidgets.QDialog):
    def __init__(self, session, parent, ncap=False):
        super(SNRPlotDialog, self).__init__()
        # Center it on the parent location
        rect = parent.geometry()
        x, y = rect.center().x(), rect.center().y()
        w = 1000
        h = 640
        self.setGeometry(x-w/2, y-h/2, w, h)
        vbox = QtWidgets.QVBoxLayout(self)
        figure_widget = mpl.MPLWidget(None, tight_layout=True)
        figure_widget.enable_interactive_zoom()
        vbox.addWidget(figure_widget)
        session.make_snr_plot(figure_widget.figure)
        _add_save_button(
            self, vbox, figure_widget,
            _star_prefixed_filename(session, "snr_plot.png")
        )
