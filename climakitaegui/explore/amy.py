import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import holoviews as hv
from matplotlib.figure import Figure
import param
from climakitae.util.colormap import read_ae_colormap

import logging  # Silence warnings

logging.getLogger("param").setLevel(logging.CRITICAL)
# Remove param's parameter descriptions from docstring because
# ANSI escape sequences in them complicate their rendering
param.parameterized.docstring_describe_params = False
# Docstring signatures are also hard to read and therefore removed
param.parameterized.docstring_signature = False


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
