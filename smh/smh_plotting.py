from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["make_summary_plot"]

import os
import logging
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.ticker import MultipleLocator, ScalarFormatter

from . import specutils
from . import spectral_models

logger = logging.getLogger(__name__)

# Colour-blind-friendly palette
COLORS = ["#FF6F00", "#0072B2", "#009E73", "#D61310", "#DFB600", "#7A553F"]

# Panel name -> (row index/slice, column index/slice) in the 4x2 plot grid
PANEL_LAYOUT = {
    "top_left":     (slice(0, 2), 0),
    "top_right":    (slice(0, 2), 1),
    "middle":       (2, slice(0, 2)),
    "bottom_left":  (3, 0),
    "bottom_right": (3, 1),
}

def _wavelength(spec):
    """Support both old (`dispersion`) and new (`spectral_axis`) specutils."""
    return getattr(spec, "spectral_axis", None) if hasattr(spec, "spectral_axis") \
        else spec.dispersion

def _label_Teff(ax, spectra_filenames, template_starnames, Tlit, Teff,
                spectra_colors):
    metadata = {
        name: (lit, eff)
        for name, lit, eff in zip(template_starnames, Tlit, Teff)
    }
    selected = [
        (name, *metadata[name])
        for name in spectra_filenames
        if name in metadata
    ]
    selected.sort(key=lambda item: item[1])

    temp_lit = [[r"$T_{\rm lit}$", 'k']]
    temp_eff = [[r"$T_{\rm eff}$", 'k']]

    for spec_name, _Tlit, _Teff in selected:
        color = spectra_colors[spec_name]
        temp_lit.append([str(_Tlit), color])
        temp_eff.append([str(_Teff), color])

    coord = 90
    for i,(entrylit, entryeff) in enumerate(zip(temp_lit, temp_eff)):
        ax.annotate(entrylit[0], xy=(4858.33, 0), xytext=(40, coord),
                    textcoords='offset points', size=10, color=entrylit[1])
        ax.annotate(entryeff[0], xy=(4858.33, 0), xytext=(270, coord),
                    textcoords='offset points', size=10, color=entryeff[1])
        coord -= 15

def _add_info_table(ax, names, colors, Tlit, Teff, FeH):
    """
    Draw a table spanning `ax` that acts as both legend and annotation.
    Columns are spectra (header cell filled with the line colour);
    rows are the literature/fitted parameters.
    """
    ax.axis("off")

    col_labels = ["", "This star"] + list(names)
    rows = [
        ["T_lit",  "—"] + [str(t) for t in Tlit],
        ["T_eff",  "—"] + [str(t) for t in Teff],
        ["[Fe/H]", "—"] + [str(f) for f in FeH],
    ]

    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc="center",
                     loc="center", bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    # First column (row labels) narrower and borderless; others share the rest
    n_cols = len(col_labels)
    n_rows = len(rows) + 1  # include the header row
    cell_width = 1.0 / (n_cols - 1)
    cell_height = 1.0 / n_rows
    header_colors = [None, "k"] + list(colors)

    for (row, col), cell in table.get_celld().items():
        cell.set_width(cell_width)
        cell.set_height(cell_height)
        cell.set_linewidth(0.6)
        cell.set_edgecolor("lightgray")
        cell.get_text().set_fontfamily("DejaVu Sans")
        if col == 0:
            cell.set_text_props(color='k', weight="bold")
        if col > 0:
            cell.set_text_props(color=header_colors[col], weight="bold")
    return table

def make_summary_plot(summary_figure, normalized_spectrum, figure=None):
    """
    :param summary_figure:
        A dict containing information about how to plot the summary figure
    :param normalized_spectrum:
        specutils.Spectrum1D
    :param figure:
        matplotlib figure object to make plot in.
        The function will adjust the figure object.
        If not specified (None), creates a new figure and returns it.
    """
    ## Parse and validate inputs
    entries = summary_figure["spectra_filenames"]
    template_starnames = [e[0] for e in entries]
    Tlit = [int(e[1]) for e in entries]
    Teff = [int(e[2]) for e in entries]
    FeH = [float(e[3]) for e in entries]

    for key in PANEL_LAYOUT:
        for name in summary_figure[key]["spectra_to_plot"]:
            assert name in template_starnames, name

    ## Load spectra (colour is tied to position in the input list)
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "spectra") # HACK data path
    spectra_objects, spectra_colors = {}, {}
    for i, name in enumerate(template_starnames):
        fname = os.path.join(data_dir, f"{name}.fits")
        if os.path.exists(fname):
            spectra_objects[name] = specutils.Spectrum1D.read(fname)
            spectra_colors[name] = COLORS[i % len(COLORS)]
        else:
            logger.warning("Could not find spectrum data file %s", fname)

    ## Only tabulate spectra that were actually loaded, ordered by T_lit
    order = [i for i in np.argsort(Tlit) if template_starnames[i] in spectra_objects]
    t_starnames = [template_starnames[i] for i in order]
    t_colors = [spectra_colors[n] for n in t_starnames]
    t_Tlit = [Tlit[i] for i in order]
    t_Teff = [Teff[i] for i in order]
    t_FeH = [FeH[i] for i in order]

    ## Figure and axes
    if figure is None:
        figure = plt.figure(figsize=(10, 8))
    figure.patch.set_facecolor("w")

    outer = GridSpec(
        2, 1, figure=figure, height_ratios=[1, 8],
        left=0.10, right=0.95, top=0.97, bottom=0.07, hspace=0.12
    )
    ax_table = figure.add_subplot(outer[0])
    plot_gs = GridSpecFromSubplotSpec(4, 2, subplot_spec=outer[1])

    ## Add table of literature/fitted parameters for template stars
    _add_info_table(ax_table, t_starnames, t_colors, t_Tlit, t_Teff, t_FeH)

    ## Spectra panels 
    formatter = ScalarFormatter(useOffset=False)
    for key, (r, c) in PANEL_LAYOUT.items():
        cfg = summary_figure[key]
        ax = figure.add_subplot(plot_gs[r, c])

        ### Plot the target star of interest (black)
        ax.plot(_wavelength(normalized_spectrum), normalized_spectrum.flux,
                "k", lw=3)
        ### Plot the template spectra (coloured)
        for name in cfg["spectra_to_plot"]:
            if name in spectra_objects:
                spec = spectra_objects[name]
                ax.plot(_wavelength(spec), spec.flux, color=spectra_colors[name], lw=2)

        if cfg["label"]=="H-beta":
            _label_Teff(
                ax, cfg["spectra_to_plot"], template_starnames, Tlit, Teff,
                spectra_colors
            )

        ax.set_ylabel(cfg["label"])
        ax.set_xlim(cfg["wavelength_range"])
        ax.set_ylim(cfg["ylim"])
        ax.xaxis.set_major_formatter(formatter)
        ax.tick_params(which="both", direction="in", top=True, right=True)

    return figure

def make_snr_plot(normalized_spectrum, figure=None):
    if figure==None: 
        figure = plt.figure(figsize=(10,8))
    figure.subplots_adjust(left=0.10, right=0.95)
    figure.patch.set_facecolor("w")
    
    ax = figure.add_subplot(111)
    ax.plot(_wavelength(normalized_spectrum), np.sqrt(normalized_spectrum.ivar), lw=1, color='k')
    ax.set_xlabel("Wavelength (A)", fontdict={"fontsize":12})
    ax.set_ylabel("SNR = sqrt(ivar)", fontdict={"fontsize":12})
    ax.set_xticklabels(ax.get_xticks(), fontdict={"fontsize":12})
    ax.set_yticklabels(ax.get_yticks(), fontdict={"fontsize":12})
    ax.tick_params(which="both", direction="in", top=True, right=True)
    return figure

def make_synthesis_plot(
        plotdata, default_err=0.1,
        plot_resid=True, plot_data_err=True,
        xlim=None, ylim=(0,1.2), r_ylim=(-.1,.1),
        xmajlocator=1, ymajlocator=.1, r_ymajlocator=.05,
        xminlocator=.1, yminlocator=.1, r_yminlocator=.01,
        fig=None, ax=None, ax_residual=None, figsize=None
    ):
    if isinstance(plotdata, spectral_models.SpectralSynthesisModel):
        plotdata = plotdata.export_plot_data(default_err)
    elem, orig_p, logeps_err, model, data = plotdata
    abund0 = orig_p["log_eps({})".format(elem)]
    
    # Get proper plotting axes
    if ax is None:
        assert ax_residual is None
        if plot_resid:
            fig = plt.figure(figsize=figsize)
            gs = GridSpec(2, 1, height_ratios=[3,1])
            ax = fig.add_subplot(gs[0])
            ax_residual = fig.add_subplot(gs[1])
        else:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111)
    else:
        fig = ax.get_figure()
        if plot_resid:
            assert ax_residual is not None
    
    # Set up limits and labeling
    if xlim is None:
        xlim = (min(model["wl"][0], data["wl"][0]), max(model["wl"][-1], data["wl"][-1]))
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.xaxis.set_major_locator(MultipleLocator(xmajlocator))
    ax.xaxis.set_minor_locator(MultipleLocator(xminlocator))
    ax.yaxis.set_major_locator(MultipleLocator(ymajlocator))
    ax.yaxis.set_minor_locator(MultipleLocator(yminlocator))
    ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    if plot_resid:
        ax_residual.plot(xlim, [0,0], 'k:', lw=1)
        ax_residual.set_xlim(xlim)
        ax_residual.set_ylim(r_ylim)
        ax_residual.xaxis.set_major_locator(MultipleLocator(xmajlocator))
        ax_residual.xaxis.set_minor_locator(MultipleLocator(xminlocator))
        ax_residual.yaxis.set_major_locator(MultipleLocator(r_ymajlocator))
        ax_residual.yaxis.set_minor_locator(MultipleLocator(r_yminlocator))
        ax_residual.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            
    # Plot no elem model
    noelem_kwargs={'color':'b','linestyle':':','lw':1}
    noelem_label="No {}".format(elem)
    ax.plot(model["wl"], model["f_none"], label=noelem_label, **noelem_kwargs)
    if plot_resid:
        ax_residual.plot(data["wl"], data["r_none"], **noelem_kwargs)
    
    # Plot data
    data_kwargs={'fmt':'o-', 'color':'k', 'ecolor':'k', 'label':None}
    if plot_data_err:
        yerr = data["err"]
    else:
        yerr = None
    ax.errorbar(data["wl"], data["flux"], yerr=yerr, **data_kwargs)
    
    # Plot +/- error models
    error_kwargs={'color':'r','linestyle':':','lw':1}
    for suffix in ["-err", "+err"]:
        ax.plot(model["wl"], np.array(model["f_"+suffix]), label=None, **error_kwargs)
        if plot_resid:
            ax_residual.plot(data["wl"], data["r_"+suffix], label=None, **error_kwargs)
    
    # Plot fit model
    fit_kwargs={'color':'r','linestyle':'-','lw':1}
    fit_label=r"A({})={:5.2f}$\pm${:.2f}".format(elem, abund0, logeps_err)
    ax.plot(model["wl"], model["f_fit"], label=fit_label, **fit_kwargs)
    if plot_resid:
        ax_residual.plot(data["wl"], data["r_fit"], **fit_kwargs)
    
    return fig
