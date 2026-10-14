#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" The radial velocity tab view for the Spectroscopy Made Hard GUI. """

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)
import copy
from PySide6 import QtCore, QtWidgets, QtGui

import logging
logger = logging.getLogger(__name__)

__all__ = ["GlobalMaskEditorDialog"]

class GlobalMaskEditorDialog(QtWidgets.QDialog):
    """
    Dialog for creating and editing the named global continuum mask
    profiles stored under `normalization: masks:` in the session
    defaults. These are applied to every order's continuum fit (see
    NormalizationTab.fit_continuum and update_continuum_mask), unlike
    the per-order `exclude` regions edited by click-dragging on the plot.
    """

    KIND_LABELS = {
        "obs_wavelength": "Observed wavelength (\u00c5)",
        "rest_wavelength": "Rest wavelength (\u00c5)",
        # "pixel": "Pixel index",
    }
    KINDS = list(KIND_LABELS.keys())

    def __init__(self, masks, current_mask_name, parent=None):
        """
        masks:
            A dict of {profile_name: {"rest_wavelength": [[a, b], ...],
            "obs_wavelength": [...], "pixel": [...]}}, as read from
            `session.setting(("normalization", "masks"))`.

        current_mask_name:
            The profile currently selected in the main tab's combo box,
            used to pre-select a profile and as the default "set as
            default" state when the dialog opens.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit global continuum masks")
        self.resize(560, 420)

        # Work on a deep copy so Cancel leaves the caller's dict untouched.
        self._masks = copy.deepcopy(masks)
        self._active_profile_name = None  # tracks what's loaded in the table

        layout = QtWidgets.QVBoxLayout(self)

        # --- Profile selector row -------------------------------------
        profile_row = QtWidgets.QHBoxLayout()
        profile_row.addWidget(QtWidgets.QLabel("Profile:"))

        self.profile_combo = QtWidgets.QComboBox(self)
        self.profile_combo.addItems(list(self._masks.keys()))
        profile_row.addWidget(self.profile_combo)

        self.new_profile_btn = QtWidgets.QPushButton("New...", self)
        self.duplicate_profile_btn = QtWidgets.QPushButton("Duplicate...", self)
        self.rename_profile_btn = QtWidgets.QPushButton("Rename...", self)
        self.delete_profile_btn = QtWidgets.QPushButton("Delete", self)
        for btn in (self.new_profile_btn, self.duplicate_profile_btn,
                    self.rename_profile_btn, self.delete_profile_btn):
            profile_row.addWidget(btn)
        profile_row.addStretch(1)
        layout.addLayout(profile_row)

        # --- Region table -------------------------------------------------
        self.table = QtWidgets.QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(
            ["Kind", "Start (\u00C5)", "End (\u00C5)", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.table)

        self.add_row_btn = QtWidgets.QPushButton("Add region", self)
        self.add_row_btn.clicked.connect(lambda: self._add_table_row())
        layout.addWidget(self.add_row_btn, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        # --- Add a description of rest_wavelength, obs_wavelength, & pixel ----
        self.line_above_desc = QtWidgets.QFrame()
        self.line_above_desc.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_above_desc.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(self.line_above_desc)

        desc = QtWidgets.QLabel(
            # "All wavelengths include heliocentric and barycentri
            # c corrections.\n"
            "'rest_wavelength' = rest-frame wavelength of the star\n"
            "'obs_wavelength'  = rest-frame wavelength + radial-velocity shift"
            # "'pixel'           = pixel index in the spectrum array"
        )
        desc.setWordWrap(True)
        desc.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        layout.addWidget(desc)
        
        self.line_below_desc = QtWidgets.QFrame()
        self.line_below_desc.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_below_desc.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(self.line_below_desc)

        # --- Default profile + persistence options ----------------------
        self.set_as_default_checkbox = QtWidgets.QCheckBox(
            "Use this profile as the default for new sessions", self)
        layout.addWidget(self.set_as_default_checkbox)

        self.save_to_disk_checkbox = QtWidgets.QCheckBox(
            "Also write these profiles to the defaults file (persists "
            "across sessions)", self)
        layout.addWidget(self.save_to_disk_checkbox)

        # --- OK / Cancel ---------------------------------------------------
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
                | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            self)
        layout.addWidget(button_box)

        # --- Signals ---------------------------------------------------
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        self.new_profile_btn.clicked.connect(self._on_new_profile)
        self.duplicate_profile_btn.clicked.connect(self._on_duplicate_profile)
        self.rename_profile_btn.clicked.connect(self._on_rename_profile)
        self.delete_profile_btn.clicked.connect(self._on_delete_profile)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        # Select the profile that was active in the main tab, and force
        # a load (setCurrentIndex may be a no-op if it's already index 0,
        # which wouldn't otherwise emit currentTextChanged).
        index = self.profile_combo.findText(current_mask_name)
        self.profile_combo.setCurrentIndex(max(index, 0))
        self._on_profile_changed(self.profile_combo.currentText())

        self.set_as_default_checkbox.setChecked(
            self.profile_combo.currentText() == current_mask_name)

    # -- Table <-> dict synchronization ----------------------------------

    def _load_profile_into_table(self, name):
        self.table.setRowCount(0)
        profile = self._masks.get(name, {})
        for kind in self.KINDS:
            for region in profile.get(kind, []):
                self._add_table_row(kind, region[0], region[1])

    def _current_table_profile(self):
        """ Build a {kind: [[start, end], ...]} dict from the table. """
        profile = {}
        for row in range(self.table.rowCount()):
            kind_combo = self.table.cellWidget(row, 0)
            start_edit = self.table.cellWidget(row, 1)
            end_edit = self.table.cellWidget(row, 2)
            kind = kind_combo.currentText()
            try:
                start = float(start_edit.text())
                end = float(end_edit.text())
            except ValueError:
                continue  # incomplete row; drop it silently
            profile.setdefault(kind, []).append([start, end])
        return profile

    def _add_table_row(self, kind="rest_wavelength", start="", end=""):
        row = self.table.rowCount()
        self.table.insertRow(row)

        kind_combo = QtWidgets.QComboBox(self.table)
        kind_combo.addItems(self.KINDS)
        kind_combo.setCurrentText(kind)
        self.table.setCellWidget(row, 0, kind_combo)

        start_edit = QtWidgets.QLineEdit(str(start), self.table)
        end_edit = QtWidgets.QLineEdit(str(end), self.table)
        self.table.setCellWidget(row, 1, start_edit)
        self.table.setCellWidget(row, 2, end_edit)

        def _update_validators(new_kind, start_edit=start_edit, end_edit=end_edit):
            if new_kind == "pixel":
                start_edit.setValidator(QtGui.QIntValidator(start_edit))
                end_edit.setValidator(QtGui.QIntValidator(end_edit))
            else:
                start_edit.setValidator(QtGui.QDoubleValidator(start_edit))
                end_edit.setValidator(QtGui.QDoubleValidator(end_edit))
        kind_combo.currentTextChanged.connect(_update_validators)
        _update_validators(kind)

        remove_btn = QtWidgets.QPushButton("Remove", self.table)
        remove_btn.clicked.connect(self._make_remove_handler(remove_btn))
        self.table.setCellWidget(row, 3, remove_btn)

    def _make_remove_handler(self, button):
        # Looks up the button's current row at click time, rather than
        # capturing a row index that would go stale once other rows are
        # inserted or removed.
        def handler():
            for row in range(self.table.rowCount()):
                if self.table.cellWidget(row, 3) is button:
                    self.table.removeRow(row)
                    return
        return handler

    # -- Profile management -----------------------------------------------

    def _on_profile_changed(self, new_name):
        if self._active_profile_name is not None:
            self._masks[self._active_profile_name] = self._current_table_profile()
        self._active_profile_name = new_name
        self._load_profile_into_table(new_name)

    def _on_new_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self, "New profile", "Profile name:")
        if not ok or not name:
            return
        if name in self._masks:
            QtWidgets.QMessageBox.warning(
                self, "Edit global masks",
                "A profile with that name already exists.")
            return
        self._masks[name] = {}
        self.profile_combo.addItem(name)
        self.profile_combo.setCurrentText(name)

    def _on_duplicate_profile(self):
        current = self.profile_combo.currentText()
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Duplicate profile", "New profile name:",
            text="{}_copy".format(current))
        if not ok or not name:
            return
        if name in self._masks:
            QtWidgets.QMessageBox.warning(
                self, "Edit global masks",
                "A profile with that name already exists.")
            return
        self._on_profile_changed(current)  # flush edits before copying
        self._masks[name] = copy.deepcopy(self._masks[current])
        self.profile_combo.addItem(name)
        self.profile_combo.setCurrentText(name)

    def _on_rename_profile(self):
        current = self.profile_combo.currentText()
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename profile", "New name:", text=current)
        if not ok or not name or name == current:
            return
        if name in self._masks:
            QtWidgets.QMessageBox.warning(
                self, "Edit global masks",
                "A profile with that name already exists.")
            return
        self._masks[name] = self._masks.pop(current)
        self._active_profile_name = name  # avoid resurrecting `current`
        self.profile_combo.setItemText(self.profile_combo.currentIndex(), name)

    def _on_delete_profile(self):
        if self.profile_combo.count() <= 1:
            QtWidgets.QMessageBox.warning(
                self, "Edit global masks", "At least one profile must remain.")
            return
        current = self.profile_combo.currentText()
        response = QtWidgets.QMessageBox.question(
            self, "Delete profile",
            "Delete the profile '{}'? This cannot be undone.".format(current),
            QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No)
        if response != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        del self._masks[current]
        self._active_profile_name = None  # avoid resurrecting the deleted profile
        self.profile_combo.removeItem(self.profile_combo.currentIndex())

    # -- Accept / result -----------------------------------------------------

    def _on_accept(self):
        self._masks[self._active_profile_name] = self._current_table_profile()

        for name, profile in self._masks.items():
            for kind, regions in profile.items():
                for start, end in regions:
                    if start >= end:
                        QtWidgets.QMessageBox.warning(
                            self, "Edit global masks",
                            "In profile '{}', region [{}, {}] has start "
                            ">= end.".format(name, start, end))
                        return
        self.accept()

    def result_masks(self):
        """ The edited {profile_name: {kind: [[start, end], ...]}} dict. """
        return self._masks

    def result_default_mask_name(self):
        """ The profile flagged as the new session default, if any. """
        return self.profile_combo.currentText() \
            if self.set_as_default_checkbox.isChecked() else None

    def result_save_to_disk(self):
        return self.save_to_disk_checkbox.isChecked()