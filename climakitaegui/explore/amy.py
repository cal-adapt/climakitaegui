import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import hvplot.pandas
import holoviews as hv
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import datetime
import param
import panel as pn
from climakitaegui.core.data_interface import DataParametersWithPanes
from climakitae.util.colormap import read_ae_colormap
from climakitae.explore.amy import (
    retrieve_meteo_yr_data,
    compute_amy,
    compute_severe_yr,
)

import logging  # Silence warnings

logging.getLogger("param").setLevel(logging.CRITICAL)
# Remove param's parameter descriptions from docstring because
# ANSI escape sequences in them complicate their rendering
param.parameterized.docstring_describe_params = False
# Docstring signatures are also hard to read and therefore removed
param.parameterized.docstring_signature = False


# =========================== HELPER FUNCTIONS: AMY/TMY PLOTTING ==============================


def meteo_yr_heatmap(
    meteo_yr_df: pd.DataFrame,
    title: str = "Meteorological Year",
    cmap: str = "ae_orange",
    clabel: str = None,
    width: int = 500,
    height: int = 250,
) -> hv.HeatMap:
    """Create interactive (hvplot) meteorological year heatmap.

    Parameters
    ----------
    meteo_yr_df : pd.DataFrame
        Meteorological year dataframe, with hour of day as columns and day of year as index
        Output of either compute_severe_yr or compute_meteo_yr
    title : str, optional
        Title to give heatmap. Default to "Meteorological Year"
    cmap : matplotlib colormap name or AE colormap names, optional
        Colormap to apply to heatmap. Default to "ae_orange"
    clabel : str, optional
        Name of variable being plotted. Default to None.
        Will be applied to label of colorbar.
    width : int, optional
        Width of heatmap. Default to 500
    height : int, optional
        Height of heatmap. Default to 250.

    Returns
    -------
    holoviews.element.raster.HeatMap
        Interactive heatmap

    """
    # Set colormap if it's an ae colormap
    # If using hvplot, set cmap_hex = True
    if cmap in ["ae_orange", "ae_diverging", "ae_blue"]:
        cmap = read_ae_colormap(cmap=cmap, cmap_hex=True)

    # Set yticks
    idx = [
        (31, "Feb-01"),
        (91, "Apr-01"),
        (152, "Jun-01"),
        (213, "Aug-01"),
        (274, "Oct-01"),
        (335, "Dec-01"),
    ]
    match len(meteo_yr_df):
        case 366:  # Leap year
            idx = idx
        case 365:  # Normal year
            idx = [(i - 1, mon) for i, mon in idx]
        case _:
            raise ValueError(
                "Length of dataframe is invalid. Must contain either 366 or 365 days."
            )

    to_plot = meteo_yr_df.reset_index(drop=True)  # Remove day of year index
    fig = to_plot.hvplot.heatmap(
        yticks=idx,
        frame_width=width,
        frame_height=height,
        ylabel="Day of Year",
        xlabel="Hour of Day",
        title=title,
        cmap=cmap,
        clabel=clabel,
    ).opts(xrotation=45)
    return fig


def meteo_yr_heatmap_static(
    meteo_yr_df: pd.DataFrame,
    title: str = "Meteorological Year",
    cmap: str = "ae_orange",
    clabel: str = None,
) -> Figure:
    """Create static (matplotlib) meteorological year heatmap

    Parameters
    ----------
    meteo_yr_df : pd.DataFrame
        Meteorological year dataframe, with hour of day as columns and day of year as index
        Output of either compute_severe_yr or compute_meteo_yr
    title : str, optional
        Title to give heatmap. Default to "Meteorological Year"
    cmap : matplotlib colormap name or AE colormap names, optional
        Colormap to apply to heatmap. Default to "ae_orange"
    clabel : str, optional
        Name of variable being plotted. Default to None.
        Will be applied to label of colorbar.

    Returns
    -------
    matplotlib.figure.Figure
        Static heatmap

    """
    # Set colormap if it's an ae colormap
    # If using hvplot, set cmap_hex = True
    if cmap in ["ae_orange", "ae_diverging", "ae_blue"]:
        cmap = read_ae_colormap(cmap=cmap, cmap_hex=False)

    fig, ax = plt.subplots(1, 1, figsize=(9, 5))
    heatmap = ax.imshow(
        meteo_yr_df.values, cmap=cmap, aspect=0.03, origin="lower"  # Flip y axis
    )

    # Set xticks
    ax.set_xticks(np.arange(len(meteo_yr_df.columns)))
    ax.set_xticklabels(meteo_yr_df.columns.values, rotation=45)

    # Set yticks
    if len(meteo_yr_df.index) == 366:  # Leap year
        first_days_of_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    else:  # Not a leap year
        first_days_of_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    ax.set_yticks(first_days_of_month)
    ax.set_yticklabels(meteo_yr_df.index[first_days_of_month])

    # Set title and labels
    ax.set_title(title)
    ax.set_ylabel(meteo_yr_df.index.name)
    ax.set_xlabel(meteo_yr_df.columns.name)

    # Make colorbar
    cax = fig.add_axes([0.92, 0.24, 0.02, 0.53])
    fig.colorbar(heatmap, cax=cax, orientation="vertical", label=clabel)

    plt.close()  # Close figure
    return fig


# =========================== OBJECT VISUALIZATION USING PARAM ==============================


def amy_visualize(self):
    """Creates a new AMY focus panel object to display user selections"""
    user_options = pn.Card(
        pn.Row(
            pn.Column(
                pn.widgets.StaticText(
                    name="", value="Average Meteorological Year Type"
                ),
                pn.widgets.RadioButtonGroup.from_param(self.param.amy_type, width=225),
                pn.widgets.Select.from_param(
                    self.param.computation_method, name="Computation Options", width=225
                ),
                pn.widgets.StaticText.from_param(
                    self.param.tmy_computation_description, name=""
                ),
                pn.widgets.StaticText(name="", value="Warming level (°C)"),
                pn.widgets.RadioButtonGroup.from_param(self.param.warmlevel, width=225),
                pn.widgets.Select.from_param(
                    self.param.variable, name="Data variable", width=225
                ),
                pn.widgets.StaticText.from_param(
                    self.param.extended_description, name=""
                ),
                pn.widgets.StaticText(name="", value="Variable Units"),
                pn.widgets.RadioButtonGroup.from_param(self.param.units, width=225),
                pn.widgets.StaticText(name="", value="Model Resolution"),
                pn.widgets.RadioButtonGroup.from_param(
                    self.param.resolution, width=225
                ),
                width=250,
            ),
            pn.Column(
                pn.widgets.Select.from_param(
                    self.param.area_subset, name="Subset the data by...", width=225
                ),
                pn.widgets.RangeSlider.from_param(self.param.latitude, width=225),
                pn.widgets.RangeSlider.from_param(self.param.longitude, width=225),
                pn.widgets.MultiSelect.from_param(
                    self.param.cached_area, name="Location selection", width=225
                ),
                self.map_view,
                pn.widgets.Button.from_param(
                    self.param.reload_data,
                    button_type="primary",
                    width=150,
                    height=30,
                ),
                width=270,
            ),
        ),
        title=" How do you want to investigate AMY?",
        collapsible=False,
        width=550,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )

    mthd_bx = pn.Column(
        pn.widgets.StaticText(
            value=(
                "An average meteorological year is calculated by selecting"
                " the 24 hours for every day that best represent multi-model mean"
                " conditions during a 30-year period – 1981-2010 for the historical"
                " baseline or centered on the year the warming level is reached."
                " Absolute average meteorolgoical year profiles represent data that"
                " is not bias corrected, please exercise caution when analyzing."
                " The 'severe' AMY is calculated using the 90th percentile of future"
                " warming level data at the selected warming level, and is compared"
                " to the historical baseline."
            ),
            width=700,
        ),
    )

    TMY = pn.Card(
        pn.widgets.StaticText(value="Absolute AMY", width=600, height=500),
        self._tmy_hourly_heatmap,
    )

    tmy_tabs = pn.Card(
        pn.Tabs(
            ("AMY Heatmap", self._tmy_hourly_heatmap),
            ("Methodology", mthd_bx),
        ),
        title=" Average Meteorological Year",
        width=725,
        collapsible=False,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )

    tmy_panel = pn.Column(pn.Row(user_options, tmy_tabs))
    return tmy_panel
