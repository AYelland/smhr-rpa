#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" The radial velocity tab view for the Spectroscopy Made Hard GUI. """

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import numpy as np
import os
import sys
from PySide6 import QtCore, QtGui, QtWidgets
import yaml

import mpl
from matplotlib import (gridspec, pyplot as plt)

from smh import (Session, specutils)
import smh
from smh.linelists import LineList

import logging
logger = logging.getLogger(__name__)

__all__ = ["RVTab"]


c = 299792458e-3 # km/s

class RVTab(QtWidgets.QWidget):

    def __init__(self, parent):
        """
        Create a tab for correcting spectra for radial velocity.

        :param parent:
            The parent widget.
        """

        super(RVTab, self).__init__(parent)

        self.parent = parent

        # Create the overall RV tab.
        sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sp.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sp)

        # Create a top-level horizontal layout to contain a matplotlib figure and
        # a vertical layout of settings..
        rv_tab_layout = QtWidgets.QHBoxLayout(self)
        rv_tab_layout.setContentsMargins(20, 20, 20, 0)

        # This vertical layout will be for input settings.
        rv_settings_vbox = QtWidgets.QVBoxLayout()
        rv_settings_vbox.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        # A two-tab setting for 'template' and 'normalization' settings in the
        # radial velocity determination.
        rv_settings_tabs = QtWidgets.QTabWidget(self)

        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(rv_settings_tabs.sizePolicy().hasHeightForWidth())

        rv_settings_tabs.setSizePolicy(sp)
        rv_settings_tabs.setMinimumSize(QtCore.QSize(300, 240))
        rv_settings_tabs.setMaximumSize(QtCore.QSize(300, 240))

        rv_settings_tabs.setMovable(True)
        rv_settings_tabs.setObjectName("rv_settings_tabs")


        # A tab containing template settings.
        template_tab = QtWidgets.QWidget()
        template_tab.setObjectName("tv_template_tab")

        # TODO: Should template_tab and template_tab_widget actually be one entity?
        template_tab_widget = QtWidgets.QWidget(template_tab)
        template_tab_widget.setGeometry(QtCore.QRect(0, 0, 300, 210))

        template_tab_layout = QtWidgets.QVBoxLayout(template_tab_widget)
        template_tab_layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        template_tab_layout.setContentsMargins(10, 10, 10, 10)

        # Add a label at the top of the template settings tab.
        label = QtWidgets.QLabel(template_tab_widget)
        label.setMaximumSize(QtCore.QSize(240, 16777215))
        label.setText("Template spectrum filename:")
        template_tab_layout.addWidget(label)

        # Inner horizontal layout for the template path and select.
        template_path_layout = QtWidgets.QHBoxLayout()

        # Template path line edit (read-only).
        self.template_path = QtWidgets.QLineEdit(template_tab_widget)
        self.template_path.setObjectName("rv_template_path")
        self.template_path.setReadOnly(True)
        template_path_layout.addWidget(self.template_path)

        # Template path select button.
        rv_select_template_btn = QtWidgets.QPushButton(template_tab_widget)
        rv_select_template_btn.setObjectName("rv_select_template_btn")
        rv_select_template_btn.setText("...")
        template_path_layout.addWidget(rv_select_template_btn)

        # Add this horizontal layout to the template tab.
        template_tab_layout.addLayout(template_path_layout)

        # Add a label for the wavelength regions
        label = QtWidgets.QLabel(template_tab_widget)
        label.setMaximumSize(QtCore.QSize(240, 16777215))
        label.setText("Wavelength region:")
        template_tab_layout.addWidget(label)

        # Wavelength region for CCF.
        wl_region_layout = QtWidgets.QHBoxLayout()
        self.wl_region = QtWidgets.QComboBox(template_tab_widget)
        self.wl_region.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.wl_region.setObjectName("rv_wl_region")
        wl_region_layout.addWidget(self.wl_region)

        # Edit button for the wavelength regions.
        rv_wl_region_edit = QtWidgets.QPushButton(template_tab_widget)
        rv_wl_region_edit.setMaximumSize(QtCore.QSize(80, 16777215))
        rv_wl_region_edit.setObjectName("rv_wl_region_edit")
        wl_region_layout.addWidget(rv_wl_region_edit)
        template_tab_layout.addLayout(wl_region_layout)
        rv_wl_region_edit.setText("Edit list")

        # Add a horizontal line.
        hr = QtWidgets.QFrame(template_tab_widget)
        hr.setFrameShape(QtWidgets.QFrame.HLine)
        hr.setFrameShadow(QtWidgets.QFrame.Sunken)
        template_tab_layout.addWidget(hr)

        # Add a flexible spacer.
        template_tab_layout.addItem(QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        # Add a cross-correlate button.
        rv_cross_correlate_btn = QtWidgets.QPushButton(template_tab_widget)
        rv_cross_correlate_btn.setObjectName("rv_cross_correlate_btn")
        rv_cross_correlate_btn.setText("Cross-correlate")
        template_tab_layout.addWidget(rv_cross_correlate_btn)

        # End of the template tab.
        rv_settings_tabs.addTab(template_tab, "Template")

        # Start the normalization tab.
        norm_tab = QtWidgets.QWidget()
        norm_tab.setObjectName("rv_normalization_tab")

        norm_tab_widget = QtWidgets.QWidget(norm_tab)
        norm_tab_widget.setGeometry(QtCore.QRect(0, 0, 300, 210))

        norm_tab_layout = QtWidgets.QVBoxLayout(norm_tab_widget)
        norm_tab_layout.setContentsMargins(10, 10, 10, 10)

        # Start the grid layout for the normalization tab.
        norm_tab_grid_layout = QtWidgets.QGridLayout()


        # Normalization function.
        label = QtWidgets.QLabel(norm_tab_widget)
        label.setText("Function")
        norm_tab_grid_layout.addWidget(label, 0, 0, 1, 1)
        
        # Put the normalization function combo box in a horizontal layout with a
        # spacer.
        hbox = QtWidgets.QHBoxLayout()
        hbox.addItem(QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.norm_function = QtWidgets.QComboBox(norm_tab_widget)
        self.norm_function.setObjectName("rv_norm_function")
        hbox.addWidget(self.norm_function)
        norm_tab_grid_layout.addLayout(hbox, 0, 1, 1, 1)

        norm_functions = ("polynomial", "spline")
        for each in norm_functions:
            self.norm_function.addItem(each.title())


        # Normalization function order.
        label = QtWidgets.QLabel(norm_tab_widget)
        label.setText("Order")
        norm_tab_grid_layout.addWidget(label, 1, 0, 1, 1)
        
        # Put the normalization order combo box in a horizontal layout with a spacer
        hbox = QtWidgets.QHBoxLayout()
        hbox.addItem(QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.norm_order = QtWidgets.QComboBox(norm_tab_widget)
        self.norm_order.setMaximumSize(QtCore.QSize(50, 16777215))
        self.norm_order.setObjectName("rv_norm_order")
        hbox.addWidget(self.norm_order)
        norm_tab_grid_layout.addLayout(hbox, 1, 1, 1, 1)

        norm_orders = range(1, 10)
        for order in norm_orders:
            self.norm_order.addItem("{0:.0f}".format(order))


        # Maximum number of iterations.
        label = QtWidgets.QLabel(norm_tab_widget)
        label.setText("Maximum iterations")
        norm_tab_grid_layout.addWidget(label, 2, 0, 1, 1)

        # Put the maxium number of iterations in a horizontal layout with a spacer.
        hbox = QtWidgets.QHBoxLayout()
        hbox.addItem(QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.norm_max_iter = QtWidgets.QComboBox(norm_tab_widget)
        self.norm_max_iter.setMaximumSize(QtCore.QSize(50, 16777215))
        self.norm_max_iter.setObjectName("rv_norm_max_iter")
        hbox.addWidget(self.norm_max_iter)
        norm_tab_grid_layout.addLayout(hbox, 2, 1, 1, 1)

        norm_max_iters = range(1, 10)
        for iteration in norm_max_iters:
            self.norm_max_iter.addItem("{0:.0f}".format(iteration))


        # Low sigma clipping.
        label = QtWidgets.QLabel(norm_tab_widget)
        label.setText("Low sigma clip")
        norm_tab_grid_layout.addWidget(label, 3, 0, 1, 1)

        # Put the low sigma line edit box in a horizontal layout with a spacer.
        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(-1, -1, 5, -1)
        hbox.addItem(QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.norm_low_sigma = QtWidgets.QLineEdit(norm_tab_widget)
        self.norm_low_sigma.setMaximumSize(QtCore.QSize(40, 16777215))
        self.norm_low_sigma.setAlignment(QtCore.Qt.AlignCenter)
        self.norm_low_sigma.setObjectName("rv_norm_low_sigma")
        self.norm_low_sigma.setValidator(
            QtGui.QDoubleValidator(0, 1000, 2, self.norm_low_sigma))
        hbox.addWidget(self.norm_low_sigma)
        norm_tab_grid_layout.addLayout(hbox, 3, 1, 1, 1)


        # High sigma clipping.
        label = QtWidgets.QLabel(norm_tab_widget)
        label.setText("High sigma clip")
        norm_tab_grid_layout.addWidget(label, 4, 0, 1, 1)

        # Put the high sigma line edit box in a horizontal layout with a spacer.
        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(-1, -1, 5, -1)
        hbox.addItem(QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.norm_high_sigma = QtWidgets.QLineEdit(norm_tab_widget)
        self.norm_high_sigma.setMaximumSize(QtCore.QSize(40, 16777215))
        self.norm_high_sigma.setAlignment(QtCore.Qt.AlignCenter)
        self.norm_high_sigma.setObjectName("rv_norm_high_sigma")
        self.norm_high_sigma.setValidator(
            QtGui.QDoubleValidator(0, 1000, 2, self.norm_high_sigma))
        hbox.addWidget(self.norm_high_sigma)
        norm_tab_grid_layout.addLayout(hbox, 4, 1, 1, 1)
        

        # Knot spacing.
        label = QtWidgets.QLabel(norm_tab_widget)
        norm_tab_grid_layout.addWidget(label, 5, 0, 1, 1)
        label.setText(u"Knot spacing (Å)")

        # Put the knot spacing lint edit box in a horizontal layout with a spacer
        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(-1, -1, 5, -1)
        hbox.addItem(QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.norm_knot_spacing = QtWidgets.QLineEdit(norm_tab_widget)
        self.norm_knot_spacing.setMaximumSize(QtCore.QSize(40, 16777215))
        self.norm_knot_spacing.setAlignment(QtCore.Qt.AlignCenter)
        self.norm_knot_spacing.setObjectName("rv_norm_knot_spacing")
        self.norm_knot_spacing.setValidator(
            QtGui.QIntValidator(0, 10000, self.norm_knot_spacing))
        hbox.addWidget(self.norm_knot_spacing)
        norm_tab_grid_layout.addLayout(hbox, 5, 1, 1, 1)

        # End of the grid in the normalization tab.
        norm_tab_layout.addLayout(norm_tab_grid_layout)
        norm_tab_layout.addItem(QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        rv_settings_tabs.addTab(norm_tab, "Order normalization")
        rv_settings_vbox.addWidget(rv_settings_tabs)


        # Horizontal layout for the radial velocity measured/corrected.
        hbox = QtWidgets.QHBoxLayout()
        hbox.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        hbox.setContentsMargins(10, 0, 10, -1)

        label = QtWidgets.QLabel(self)
        label.setText("Radial velocity:")
        hbox.addWidget(label)

        # Radial velocity measured.
        self.rv_applied = QtWidgets.QLineEdit(self)
        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(self.rv_applied.sizePolicy().hasHeightForWidth())
        self.rv_applied.setSizePolicy(sp)
        self.rv_applied.setMinimumSize(QtCore.QSize(50, 16777215))
        self.rv_applied.setAlignment(QtCore.Qt.AlignCenter)
        self.rv_applied.setValidator(
            QtGui.QDoubleValidator(-1e6, 1e6, 2, self.rv_applied))
        self.rv_applied.textChanged.connect(self.check_state)
        self.rv_applied.returnPressed.connect(self.correct_radial_velocity)

        hbox.addWidget(self.rv_applied)

        # Units/uncertainty label.
        label = QtWidgets.QLabel(self)
        label.setObjectName("rv_measured_units_label")
        label.setText("km/s")
        hbox.addWidget(label)

        # Correct for radial velocity button.
        rv_correct_btn = QtWidgets.QPushButton(self)
        rv_correct_btn.setObjectName("rv_correct_btn")
        rv_correct_btn.setText("Correct")
        hbox.addWidget(rv_correct_btn)
        rv_settings_vbox.addLayout(hbox)

        # The cross-correlate and correct button.
        rv_ccc_btn = QtWidgets.QPushButton(self)
        sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(rv_ccc_btn.sizePolicy().hasHeightForWidth())
        rv_ccc_btn.setSizePolicy(sp)
        rv_ccc_btn.setMinimumSize(QtCore.QSize(300, 0))
        rv_ccc_btn.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(QtGui.QFont.Weight.Bold)
        rv_ccc_btn.setFont(font)
        rv_ccc_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        rv_ccc_btn.setDefault(True)
        rv_ccc_btn.setObjectName("rv_ccc_btn")
        rv_ccc_btn.setText("Cross-correlate and correct")

        rv_settings_vbox.addWidget(rv_ccc_btn)

        # Display the velocity corrections
        grid_layout = QtWidgets.QGridLayout()
        rv_settings_vbox.addLayout(grid_layout)
        rv_summary_rows = [
            ("Radial Velocity",                 "rv_measured",  "km/s"),
            ("Radial velocity uncertainty",     "rv_uncertainty", "km/s"),
            ("Heliocentric correction",         "heliocentric_correction", "km/s"),
            ("Barycentric velocity correction", "barycentric_correction", "km/s"),
        ]
        self.rv_summary_labels = {}

        for row, (desc, key, units) in enumerate(rv_summary_rows):
            desc_label = QtWidgets.QLabel(desc, self)
            grid_layout.addWidget(desc_label, row, 0, 1, 1,
                                alignment=QtCore.Qt.AlignLeft)

            value_label = QtWidgets.QLabel(self)
            value_label.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
            self._set_rv_summary_value(value_label, np.nan)  # placeholder on init
            grid_layout.addWidget(value_label, row, 1, 1, 1,
                                alignment=QtCore.Qt.AlignRight)
            self.rv_summary_labels[key] = value_label  # <-- store reference

            units_label = QtWidgets.QLabel(units, self)
            grid_layout.addWidget(units_label, row, 2, 1, 1,
                                alignment=QtCore.Qt.AlignLeft)

        # Add a spacer after the big button.
        rv_settings_vbox.addItem(QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        rv_tab_layout.addLayout(rv_settings_vbox)

        # Create a matplotlib widget.
        self.rv_plot = mpl.MPLWidget(None, tight_layout=True)
        sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(self.rv_plot.sizePolicy().hasHeightForWidth())
        rv_tab_layout.addWidget(self.rv_plot)


        gs_top = gridspec.GridSpec(3, 1, height_ratios=[2, 1, 1])
        gs_top.update(hspace=0)
        gs_bottom = gridspec.GridSpec(3, 1)
        self.ax_order = self.rv_plot.figure.add_subplot(gs_top[0])
        self.ax_order_norm = self.rv_plot.figure.add_subplot(gs_top[1])
        self.ax_ccf = self.rv_plot.figure.add_subplot(gs_bottom[2])

        # Pseudo-legend.
        self.ax_order.text(0.99, 0.9, "Data", color="k",
            transform=self.ax_order.transAxes, horizontalalignment="right")
        self.ax_order.text(0.99, 0.8, "Continuum", color="r", 
            transform=self.ax_order.transAxes, horizontalalignment="right")
        self.ax_order.text(0.99, 0.7, "Template", color="b", 
            transform=self.ax_order.transAxes, horizontalalignment="right")

        # Ticks, etc
        self.ax_order.set_xticklabels([])
        self.ax_order_norm.set_yticks([0, 1])
        self.ax_order_norm.set_ylim(0, 1.2)

        self.ax_order_norm.set_xlabel(u"Wavelength (Å)")
        self.ax_order.set_ylabel("Flux")

        # Draw an initial line for data and continuum.
        self.ax_order.plot([np.nan], [np.nan], c='k', drawstyle='steps-mid')
        self.ax_order.plot([np.nan], [np.nan], c='r', zorder=2)
        self.ax_order.set_ylim([0, 1])

        self.ax_order_norm.axhline(1, linestyle=":", c="#666666", zorder=-1)
        self.ax_order_norm.plot([np.nan], [np.nan], c='k', drawstyle='steps-mid')
        self.ax_order_norm.plot([np.nan], [np.nan], c='b') # Template.
        self.ax_order_norm.set_ylabel("Normalized flux")


        self.ax_ccf.plot([np.nan], [np.nan], c='k')
        self.ax_ccf.set_xlabel("Velocity (km/s)")
        self.ax_ccf.set_ylabel("CCF")
        self.ax_ccf.set_yticks([0, 0.5, 1.0])

        # Keep an input cache.
        self._populate_widgets()

        # Create signals for buttons.
        rv_cross_correlate_btn.clicked.connect(self.cross_correlate) 
        rv_correct_btn.clicked.connect(self.correct_radial_velocity)
        rv_ccc_btn.clicked.connect(self.cross_correlate_and_correct)
        rv_wl_region_edit.clicked.connect(self.launch_rvregion_dialog)

        # Create signals for when any of these things change.
        rv_select_template_btn.clicked.connect(self.select_template)
        self.wl_region.currentIndexChanged.connect(self.update_wl_region)
        self.norm_low_sigma.textChanged.connect(
            self.update_normalization_low_sigma)
        self.norm_high_sigma.textChanged.connect(
            self.update_normalization_high_sigma)
        self.norm_knot_spacing.textChanged.connect(
            self.update_normalization_knot_spacing)
        self.norm_function.currentIndexChanged.connect(
            self.update_normalization_function)
        self.norm_order.currentIndexChanged.connect(
            self.update_normalization_order)
        self.norm_max_iter.currentIndexChanged.connect(
            self.update_normalization_max_iterations)

        # Update the background to show whether certain items are valid.
        self.norm_low_sigma.textChanged.connect(self.check_state)
        self.norm_high_sigma.textChanged.connect(self.check_state)
        self.norm_knot_spacing.textChanged.connect(self.check_state)
        
        # Draw the template straight up if we can.
        self.draw_template(refresh=True)

        return None


    def _set_rv_summary_value(self, label, value):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            label.setText("—")
        else:
            label.setText("{0:+.2f}".format(float(value)))

    def _update_rv_summary(self, rv_dict):
        """
        Refresh the RV summary grid (and any other RV-dependent widgets)
        from the given rv metadata dictionary.
        """
        self._set_rv_summary_value(
            self.rv_summary_labels["rv_measured"], rv_dict.get("rv_measured", np.nan))
        self._set_rv_summary_value(
            self.rv_summary_labels["rv_uncertainty"], rv_dict.get("rv_uncertainty", np.nan))
        self._set_rv_summary_value(
            self.rv_summary_labels["heliocentric_correction"], rv_dict.get("heliocentric_correction", np.nan))
        self._set_rv_summary_value(
            self.rv_summary_labels["barycentric_correction"], rv_dict.get("barycentric_correction", np.nan))

        self.rv_applied.setText(
            "{0:+.1f}".format(float(rv_dict.get("rv_measured", np.nan))))
    
    def check_state(self, *args, **kwargs):
        """
        Update the background color of a QLineEdit object based on whether the
        input is valid.
        """

        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if state == QtGui.QValidator.Acceptable:
            color = 'none' # normal background color
        elif state == QtGui.QValidator.Intermediate:
            color = '#fff79a' # yellow
        else:
            color = '#f6989d' # red
        sender.setStyleSheet('QLineEdit { background-color: %s }' % color)

    def _populate_widgets(self):
        """
        Populate widgets with values from the current SMH session.
        Fresh sessions are populated from the SMH defaults file.
        """
        if self.parent.session is None:
            return None
        rv_dict = self.parent.session.metadata["rv"]

        # The cache allows us to store things that won't necessarily go into the
        # session, but will update views, etc. For example, previewing continua
        # before actually using it in cross-correlation, etc.
        self._cache = {
            "input": rv_dict.copy()
        }

        # Wavelength regions should just be a single range.
        try:
            self._cache["input"]["wavelength_region"] \
                = self._cache["input"]["wavelength_regions"][0]
        except KeyError:
            self._cache["input"]["wavelength_regions"] = self.parent.session.setting(("rv","wavelength_regions"))
            rv_dict["wavelength_regions"] = self.parent.session.setting(("rv","wavelength_regions"))
            self._cache["input"]["wavelength_region"] \
                = self._cache["input"]["wavelength_regions"][0]
        del self._cache["input"]["wavelength_regions"]

        # Sometimes template_spectrum in a specutils.Spectrum1D
        if isinstance(rv_dict.get("template_spectrum",""), str) \
        and not os.path.exists(rv_dict.get("template_spectrum", "")):
            rv_dict["template_spectrum"] = ""

        # Template filename.
        self.template_path.setReadOnly(False)
        if isinstance(rv_dict.get("template_spectrum", ""), str):
            self.template_path.setText(
                os.path.basename(rv_dict["template_spectrum"]))
            rv_dict["template_spectrum_path"] = rv_dict["template_spectrum"]
            self._cache["input"]["template_spectrum_path"] = rv_dict["template_spectrum"]
        else:
            template_spectrum_path = rv_dict.get("template_spectrum_path","")
            self.template_path.setText(
                os.path.basename(template_spectrum_path))
        self.template_path.setReadOnly(True)

        # Wavelength regions.
        # Clear combo box
        self.wl_region.clear()
        for each in rv_dict["wavelength_regions"]:
            self.wl_region.addItem(u"{0:.0f}-{1:.0f} Å".format(*each))

        # Normalization function.
        norm_functions = [self.norm_function.itemText(i).lower() \
            for i in range(self.norm_function.count())]
        self.norm_function.setCurrentIndex(norm_functions.index(
            rv_dict["normalization"]["function"].lower()))

        # Normalization order.
        norm_orders = [int(self.norm_order.itemText(i)) \
            for i in range(self.norm_order.count())]
        self.norm_order.setCurrentIndex(norm_orders.index(
            rv_dict["normalization"]["order"]))

        # Normalization maximum iterations.
        norm_max_iters = [int(self.norm_max_iter.itemText(i)) \
            for i in range(self.norm_max_iter.count())]
        self.norm_max_iter.setCurrentIndex(norm_max_iters.index(
            rv_dict["normalization"]["max_iterations"]))

        # Normalization low and high sigma clip:
        self.norm_low_sigma.setText(
            str(rv_dict["normalization"]["low_sigma_clip"]))
        self.norm_high_sigma.setText(
            str(rv_dict["normalization"]["high_sigma_clip"]))
        
        # Normalization knot spacing.
        self.norm_knot_spacing.setText(
            str(rv_dict["normalization"]["knot_spacing"]))

        # RV
        # self.rv_applied.setText("{0:+.1f}".format(\
        #         float(rv_dict.get("rv_measured",np.nan))))

        self._update_rv_summary(rv_dict)

        return None


    def update_normalization_function(self):
        """ Update the normalization function. """

        function = self.norm_function.currentText()

        indices = range(5, 10)
        if function == "Spline":
            if int(self.norm_order.currentText()) > 5:
                # Limit it to 5.
                self.norm_order.setCurrentIndex(4) # Index 4 = Order '5'

            # Disable the other entries.
            for i in indices:
                item = self.norm_order.model().item(i)
                if item is not None:
                    item.setEnabled(False)

        else:
            # Enable order entries greater than 5.
            for i in indices:
                item = self.norm_order.model().item(i)
                if item is not None:
                    item.setEnabled(True)

        self._cache["input"]["normalization"]["function"] = function
        self.fit_and_redraw_normalized_order()


    def update_normalization_order(self):
        """ Update the normalization order. """
        self._cache["input"]["normalization"]["order"] \
            = int(self.norm_order.currentText())
        self.fit_and_redraw_normalized_order()


    def update_normalization_max_iterations(self):
        """ Update the maximum number of iterations during normalization. """
        self._cache["input"]["normalization"]["max_iterations"] \
            = int(self.norm_max_iter.currentText())
        self.fit_and_redraw_normalized_order()


    def update_normalization_low_sigma(self):
        """ Update the low sigma clipping during normalization. """
        low_sigma = self.norm_low_sigma.text()
        if low_sigma:
            self._cache["input"]["normalization"]["low_sigma_clip"] \
                = float(low_sigma)
            self.fit_and_redraw_normalized_order()


    def update_normalization_high_sigma(self):
        """ Update the high sigma clipping during normalization. """
        high_sigma = self.norm_high_sigma.text()
        if high_sigma:
            self._cache["input"]["normalization"]["high_sigma_clip"] \
                = float(high_sigma)
            self.fit_and_redraw_normalized_order()


    def update_normalization_knot_spacing(self):
        """ Update the knot spacing used for normalization. """
        knot_spacing = self.norm_knot_spacing.text()
        if knot_spacing:
            self._cache["input"]["normalization"]["knot_spacing"] \
                = float(knot_spacing)
            self.fit_and_redraw_normalized_order()



    def fit_and_redraw_normalized_order(self):
        """
        Fit and redraw the continuum, and the normalized order.
        """

        self.fit_continuum()
        self.redraw_continuum()
        self.redraw_normalized_order(True)
        return None


    def fit_continuum(self):
        """
        Fit and draw the continuum.
        """

        self._cache["normalized_order"], self._cache["continuum"], _, __ \
            = self._cache["overlap_order"].fit_continuum(full_output=True,
                **self._cache["input"]["normalization"])
        return None


    def redraw_continuum(self, refresh=False):
        """
        Redraw the continuum.

        :param refresh: [optional]
            Force the figure to update.
        """

        self.ax_order.lines[1].set_data([
            self._cache["overlap_order"].dispersion,
            self._cache["continuum"]
        ])
        if refresh:
            self.rv_plot.draw()
        return None


    def redraw_normalized_order(self, refresh=False):
        """
        Redraw the normalized order.

        :param refresh: [optional]
            Force the figure to update.
        """

        # Redshift the normalized order by the 'RV-applied', if it exists.
        try:
            rv_applied = self.parent.session.metadata["rv"]["rv_applied"]
        except (AttributeError, KeyError):
            rv_applied = 0
            
        self.ax_order_norm.lines[1].set_data([
            self._cache["normalized_order"].dispersion * (1 + rv_applied/c),
            self._cache["normalized_order"].flux,
        ])
        self.ax_order_norm.set_xlim(self._cache["input"]["wavelength_region"])

        if refresh:
            self.rv_plot.draw()

        return None


    def select_template(self):
        """
        Select the template spectrum filename from disk.
        """

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self.parent,
            caption="Select template spectrum", dir="", filter="*.fits")
        if not path:
            return False

        # Set the text.
        self.template_path.setReadOnly(False)
        self.template_path.setText(path)
        self.template_path.setReadOnly(True)

        # Update the data cache.
        self._cache["input"]["template_spectrum"] = path
        self._cache["input"]["template_spectrum_path"] = path

        # Update the figure containing the template.
        self.draw_template(refresh=True)
        
        return True


    def cross_correlate(self):
        """
        Normalize and cross-correlate the observed spectrum with the template.
        """
        
        kwds = self._cache["input"].copy()
        kwds["normalization_kwargs"] = kwds.pop("normalization")
        
        # Do we have a template spectrum?
        if isinstance(kwds.get("template_spectrum",""), str) \
        and not os.path.exists(kwds.get("template_spectrum", "")):
            selected_valid_template = self.select_template()
            if not selected_valid_template:
                return None

            # Keep this as the default value.
            self.parent.session.update_default_setting(
                ("rv", "template_spectrum"),
                self._cache["input"]["template_spectrum"])

            kwds["template_spectrum"] = self._cache["input"]["template_spectrum"]

        # Perform the cross-correlation.
        rv, rv_uncertainty = self.parent.session.rv_measure(**kwds)
        logger.info("rv uncertainty: {:.1f}".format(rv_uncertainty))
        print("rv uncertainty: {:.1f}".format(rv_uncertainty))

        # Update the measured radial velocity in the GUI.
        # self.rv_applied.setText("{0:+.1f}".format(rv))
        rv_dict = self.parent.session.metadata["rv"]
        rv_dict["rv_measured"] = rv
        rv_dict["rv_uncertainty"] = rv_uncertainty
        self._update_rv_summary(rv_dict)


        # Draw the CCF in the bottom panel.
        self.redraw_ccf(refresh=True)

        return None


    def redraw_ccf(self, refresh=False):
        """
        Draw the CCF stored in the session.
        """

        try:
            v, ccf = self.parent.session.metadata["rv"]["ccf"]
        except (AttributeError, KeyError):
            return None

        self.ax_ccf.lines[0].set_data([v, ccf])

        rv_measured = self.parent.session.metadata["rv"]["rv_measured"]
        
        self.ax_ccf.set_xlim(rv_measured - 1000, rv_measured + 1000)
        self.ax_ccf.set_ylim(0, 1.2)

        self.ax_ccf.axvline(rv_measured, c='r')

        if refresh:
            self.rv_plot.draw()
        return None


    def correct_radial_velocity(self):
        """
        Correct the radial velocity of the observed spectra.
        """
        if "rv_applied" in  self.parent.session.metadata["rv"]:
            rv_diff = float(self.rv_applied.text()) + self.parent.session.metadata["rv"]["rv_applied"]
        else:
            rv_diff = 0.0
        
        # rv_applied is set in this function
        self.parent.session.rv_correct(self.rv_applied.text())
        
        # Redshift the normalized order; will look for rv_applied.
        self.redraw_normalized_order(True)
        
        # Enable and update the normalization tab.
        self.parent.tabs.setTabEnabled(self.parent.tabs.indexOf(self) + 1, True)

        # New function E. Holmbeck added to keep masks; this shifts the masks by the rv_diff;
        # Basically, if the saved rv_applied is different from what is in the text box, shift it by that much
        #self.parent.normalization_tab.update_rv_applied()
        self.parent.normalization_tab.update_rv_applied_keep_masks(rv_diff)
        
        # Enable relevant menu actions.
        self.parent._action_fit_balmer_lines.setEnabled(True)

        return None


    def cross_correlate_and_correct(self):
        """
        Normalize and cross-correlate the observed spectrum with a template,
        then correct the observed spectrum with that velocity.
        """

        self.cross_correlate()
        self.correct_radial_velocity()

        return None


    def update_from_new_session(self):

        # Update cache.
        self._populate_widgets()

        # Update plots.

        self.draw_template()
        self.update_wl_region(verbose=False)
        self.rv_plot.draw()


    def update_wl_region(self, verbose=True):
        """
        Re-draw the order selected and the continuum fit, as well as the preview
        of the normalized spectrum.
        """

        if self.parent.session is None: return

        # Parse and cache the wavelength region.
        current_text = self.wl_region.currentText()
        if current_text == "": return
        wavelength_region = [float(_) \
                   for _ in current_text.split(" ")[0].split("-")]
        self._cache["input"]["wavelength_region"] = wavelength_region

        # Get the right order.
        try:
            self._cache["overlap_order"], _, __ = \
                self.parent.session._get_overlap_order([wavelength_region])

        except ValueError:
            if verbose:
                raise

            self._cache["overlap_order"] = self.parent.session.input_spectra[0]

        # Draw this order in the top axes.
        self.ax_order.lines[0].set_data([
            self._cache["overlap_order"].dispersion,
            self._cache["overlap_order"].flux,
        ])

        # Update the limits for this axis.
        self.ax_order.set_xlim(wavelength_region)
        flux_limits = (
            np.nanmin(self._cache["overlap_order"].flux),
            np.nanmax(self._cache["overlap_order"].flux)
        )
        self.ax_order.set_ylim(
            flux_limits[0],
            flux_limits[1] + (np.ptp(flux_limits) * 0.10)
        )

        # TODO: This may require some updating.
        print("Assuming that the session has not just been loaded and it has a CCF/norm order, etc")

        # Update the continuum fit.
        self.fit_and_redraw_normalized_order()

        return None



    def draw_template(self, refresh=False):
        """
        Draw the template spectrum in the figure.
        """

        try:
            template = self._cache["input"]["template_spectrum"]
        except:
            return

        if not isinstance(template, specutils.Spectrum1D):
            try:
                path = self._cache["input"]["template_spectrum_path"]
            except:
                return
            if not os.path.exists(path): return
            template = specutils.Spectrum1D.read(path)

        self.ax_order_norm.lines[2].set_data([
            template.dispersion,
            template.flux
        ])

        if refresh:
            self.rv_plot.draw()

        return None


    def launch_rvregion_dialog(self):
        dialog = RVRegionDialog(self)
        code = dialog.exec()
        logger.debug("RVRegionDialog Code: {}".format(code))
        self._populate_widgets()
        self.draw_template()
        self.update_wl_region()
        self.rv_plot.draw()

        return code
    
class RVRegionDialog(QtWidgets.QDialog):
    def __init__(self, rv_tab, *args):
        """
        Initialise a dialog to set new RV correction regions.

        :param session:
            The session that will be inspected for transitions.
        """

        super(RVRegionDialog, self).__init__(*args)

        self.rv_tab = rv_tab

        self.setGeometry(900, 900, 900, 600)
        screen = self.screen() if self.screen() else QtWidgets.QApplication.primaryScreen()
        self.move(screen.geometry().center() - self.rect().center())
        sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, 
            QtWidgets.QSizePolicy.MinimumExpanding)
        sp.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sp)

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.setObjectName("RVRegionDialog")
        self.setAutoFillBackground(False)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()

        ## Left column
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.addItem(spacerItem)
        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setObjectName("listWidget")
        sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sp)
        self.verticalLayout_2.addWidget(self.listWidget)
        self.button_savedefault = QtWidgets.QPushButton(self)
        self.button_savedefault.setObjectName("button_savedefault")
        self.button_savesession = QtWidgets.QPushButton(self)
        self.button_savesession.setObjectName("button_savesession")
        self.verticalLayout_2.addWidget(self.button_savedefault)
        self.verticalLayout_2.addWidget(self.button_savesession)
        self.verticalLayout_2.addItem(spacerItem1)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)
        self.button_savedefault.clicked.connect(self.save_as_default)
        self.button_savesession.clicked.connect(self.save_to_session)

        ## Right column MPL widget
        self.verticalLayout = QtWidgets.QVBoxLayout()
        blank_widget = QtWidgets.QWidget(self)
        sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(blank_widget.sizePolicy().hasHeightForWidth())
        blank_widget.setSizePolicy(sp)
        blank_widget.setObjectName("blank_widget")
        self.mpl_plot = mpl.MPLWidget(blank_widget, tight_layout=True,
                                      autofocus=True)
        self.mpl_plot.setObjectName("mpl_plot")

        layout = QtWidgets.QVBoxLayout(blank_widget)
        layout.addWidget(self.mpl_plot, 1)
        self.verticalLayout.addWidget(blank_widget)

        # Copied from above; TODO refactor?
        gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])
        self.ax_order = self.mpl_plot.figure.add_subplot(gs[0])
        self.ax_order_norm = self.mpl_plot.figure.add_subplot(gs[1])
        self.ax_order.text(0.99, 0.9, "Data", color="k",
            transform=self.ax_order.transAxes, horizontalalignment="right")
        self.ax_order.text(0.99, 0.8, "Continuum", color="r", 
            transform=self.ax_order.transAxes, horizontalalignment="right")
        self.ax_order.text(0.99, 0.7, "Template", color="b", 
            transform=self.ax_order.transAxes, horizontalalignment="right")
        self.ax_order.set_xticklabels([])
        self.ax_order_norm.set_yticks([0, 1])
        self.ax_order_norm.set_ylim(0, 1.2)
        self.ax_order_norm.set_xlabel(u"Wavelength (Å)")
        self.ax_order.set_ylabel("Flux")
        self.ax_order.plot([np.nan], [np.nan], c='k', drawstyle='steps-mid')
        self.ax_order.plot([np.nan], [np.nan], c='r', zorder=2)
        self.ax_order.set_ylim([0, 1])
        self.ax_order_norm.axhline(1, linestyle=":", c="#666666", zorder=-1)
        self.ax_order_norm.plot([np.nan], [np.nan], c='k', drawstyle='steps-mid')
        self.ax_order_norm.plot([np.nan], [np.nan], c='b') # Template.
        self.ax_order_norm.set_ylabel("Normalized flux")

        # Right column wavelength regions
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("Lower Wavelength")
        self.horizontalLayout_4.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("Upper Wavelength")
        self.horizontalLayout_4.addWidget(self.label_2)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.text_lower_wl = QtWidgets.QLineEdit(self)
        self.text_lower_wl.setObjectName("Lower Wavelength Value")
        self.horizontalLayout_3.addWidget(self.text_lower_wl)
        self.text_upper_wl = QtWidgets.QLineEdit(self)
        self.text_upper_wl.setObjectName("Upper Wavelength Value")
        self.horizontalLayout_3.addWidget(self.text_upper_wl)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        # Signals for wavelength region
        self.text_lower_wl.textChanged.connect(self.wl_value_changed)
        self.text_upper_wl.textChanged.connect(self.wl_value_changed)

        # Right column buttons
        self.button_savetolist = QtWidgets.QPushButton(self)
        self.button_savetolist.setObjectName("button_savetolist")
        self.verticalLayout.addWidget(self.button_savetolist)
        self.verticalLayout.addItem(spacerItem2)
        self.button_exit = QtWidgets.QPushButton(self)
        self.button_exit.setObjectName("button_exit")
        self.verticalLayout.addWidget(self.button_exit)
        self.horizontalLayout_2.addLayout(self.verticalLayout)
        self.horizontalLayout.addLayout(self.horizontalLayout_2)
        self.button_savetolist.clicked.connect(self.save_to_list)
        self.button_exit.clicked.connect(self.accept)

        # Set labels for everything
        self.setWindowTitle("RVRegionDialog")
        self.label.setText("Lower Wavelength (Å)")
        self.label_2.setText("Upper Wavelength (Å)")
        self.button_savedefault.setText("Save as Default")
        self.button_savesession.setText("Save to Session")
        self.button_savetolist.setText("Save to List")
        self.button_exit.setText("Exit")
        QtCore.QMetaObject.connectSlotsByName(self)
        
        ## put wavelength regions into the listWidget
        wavelength_regions = self.rv_tab.parent.session.setting(["rv","wavelength_regions"])
        for each in wavelength_regions:
            self.listWidget.addItem(u"{0:.0f}-{1:.0f} Å".format(*each))
        self.listWidget.currentItemChanged.connect(self.list_selection_changed)
        self.listWidget.setSortingEnabled(False)
        self.listWidget.setCurrentRow(0)

        # allow right-click to delete menu
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.list_context_menu)
        
        self.draw_template(refresh=True)
        self.update_wl_region()
        self.mpl_plot.draw()

        return None

    def list_context_menu(self, pos):
        """
        """
        menu = QtWidgets.QMenu(self.listWidget)
        delete_action = menu.addAction("Delete")
        any_selected = len(self.listWidget.selectionModel().selectedRows()) > 0
        if not any_selected:
            delete_action.setEnabled(False)
        action = menu.exec(self.listWidget.mapToGlobal(pos))
        if action == delete_action:
            self.delete_current_line()
        return None
    def get_regions_from_list(self):
        N = self.listWidget.count()
        regions = []
        for i in range(N):
            wl1,wl2 = self.listWidget.item(i).text().split(' ')[0].split('-')
            regions.append((float(wl1),float(wl2)))
        return regions
    def save_as_default(self):
        regions = self.get_regions_from_list()
        raise NotImplementedError
    def save_to_session(self):
        regions = self.get_regions_from_list()
        self.rv_tab.parent.session.metadata["rv"]["wavelength_regions"] = regions
        logger.debug("Saved wavelength regions to session: {}".format(regions))
    def save_to_list(self):
        wavelength_region = self.get_wavelength_region()
        if wavelength_region==None: return None
        self.listWidget.addItem(u"{0:.0f}-{1:.0f} Å".format(*wavelength_region))

    def delete_current_line(self):
        self.listWidget.takeItem(self.listWidget.currentRow())
        return None

    def get_wavelength_region(self):
        try:
            wl_lower = float(self.text_lower_wl.text())
        except ValueError:
            wl_lower = None
            self.text_lower_wl.setStyleSheet(\
                'QLineEdit { background-color: %s }' % '#f6989d') #red
        else:
            self.text_lower_wl.setStyleSheet(\
                'QLineEdit { background-color: %s }' % 'none')
        try:
            wl_upper = float(self.text_upper_wl.text())
        except ValueError:
            wl_upper = None
            self.text_upper_wl.setStyleSheet(\
                'QLineEdit { background-color: %s }' % '#f6989d') #red
        else:
            self.text_upper_wl.setStyleSheet(\
                'QLineEdit { background-color: %s }' % 'none')

        if wl_lower is None or wl_upper is None: return None
        if wl_lower >= wl_upper: return None
        return (wl_lower, wl_upper)
    def wl_value_changed(self):
        self.listWidget.setCurrentRow(-1)
        self.update_wl_region()
    def list_selection_changed(self):
        current_item = self.listWidget.currentItem()
        if current_item is None: return
        current_text = current_item.text()
        wl1,wl2 = current_text.split(" ")[0].split("-")
        self.text_lower_wl.setText(wl1)
        self.text_upper_wl.setText(wl2)
        self.update_wl_region()

    def update_wl_region(self):
        """
        Re-draw the order selected and the continuum fit, as well as the preview
        of the normalized spectrum.
        """

        # Parse and cache the wavelength region.
        wavelength_region = self.get_wavelength_region()
        if wavelength_region==None: return

        self.rv_tab._cache["input"]["wavelength_region"] = wavelength_region

        # Get the right order.
        self.rv_tab._cache["overlap_order"], _, __ = \
            self.rv_tab.parent.session._get_overlap_order([wavelength_region])

        # Draw this order in the top axes.
        self.ax_order.lines[0].set_data([
            self.rv_tab._cache["overlap_order"].dispersion,
            self.rv_tab._cache["overlap_order"].flux,
        ])

        # Update the limits for this axis.
        self.ax_order.set_xlim(wavelength_region)
        flux_limits = (
            np.nanmin(self.rv_tab._cache["overlap_order"].flux),
            np.nanmax(self.rv_tab._cache["overlap_order"].flux)
        )
        self.ax_order.set_ylim(
            flux_limits[0],
            flux_limits[1] + (np.ptp(flux_limits) * 0.10)
        )

        # Update the continuum fit.
        self.fit_and_redraw_normalized_order()

        return None

    def fit_and_redraw_normalized_order(self):
        """
        Fit and redraw the continuum, and the normalized order.
        """

        self.rv_tab.fit_continuum()
        self.redraw_continuum()
        self.redraw_normalized_order(True)
        return None
    

    def redraw_continuum(self, refresh=False):
        """
        Redraw the continuum.

        :param refresh: [optional]
            Force the figure to update.
        """

        self.ax_order.lines[1].set_data([
            self.rv_tab._cache["overlap_order"].dispersion,
            self.rv_tab._cache["continuum"]
        ])
        if refresh:
            self.mpl_plot.draw()
        return None


    def redraw_normalized_order(self, refresh=False):
        """
        Redraw the normalized order.

        :param refresh: [optional]
            Force the figure to update.
        """

        # Redshift the normalized order by the 'RV-applied', if it exists.
        try:
            rv_applied = self.rv_tab.parent.session.metadata["rv"]["rv_applied"]
        except (AttributeError, KeyError):
            rv_applied = 0
            
        self.ax_order_norm.lines[1].set_data([
            self.rv_tab._cache["normalized_order"].dispersion * (1 + rv_applied/c),
            self.rv_tab._cache["normalized_order"].flux,
        ])
        self.ax_order_norm.set_xlim(self.rv_tab._cache["input"]["wavelength_region"])

        if refresh:
            self.mpl_plot.draw()

        return None


    def draw_template(self, refresh=False):
        """
        Draw the template spectrum in the figure.
        """

        try:
            template = self.rv_tab._cache["input"]["template_spectrum"]
        except AttributeError:
            return

        if not isinstance(template, specutils.Spectrum1D):
            try:
                path = self.rv_tab._cache["input"]["template_spectrum_path"]
            except (AttributeError, KeyError):
                return
            if not os.path.exists(path): return
            template = specutils.Spectrum1D.read(path)

        self.ax_order_norm.lines[2].set_data([
            template.dispersion,
            template.flux
        ])

        if refresh:
            self.mpl_plot.draw()

        return None


if __name__ == "__main__":

    # This is just for development testing.
    app = QtWidgets.QApplication(sys.argv)
    #window = RVRegionDialog(None)
    #window.exec()
    widget = QtWidgets.QWidget(None)

    with open(Session._default_settings_path, "rb") as fp:
        try:
            defaults = yaml.load(fp,yaml.FullLoader)
        except AttributeError:
            defaults = yaml.load(fp)
    datadir = os.path.dirname(os.path.abspath(__file__))+'/../tests/test_data'
    session = Session([datadir+"/spectra/hd122563.fits"])
    widget.session = session
    session.metadata.update(defaults)

    ll = LineList.read(os.path.dirname(os.path.abspath(__file__))+'/../tests/test_data/linelists/lin4554new')
    session.metadata['line_list'] = ll
    
    rv_tab = RVTab(widget)
    rv_tab.update_from_new_session()
    rv_tab.template_path = QtWidgets.QLineEdit()
    rv_tab.template_path.setText(datadir+'/spectra/hd122563.fits')
    
    dialog = RVRegionDialog(rv_tab)

    dialog.exec()
