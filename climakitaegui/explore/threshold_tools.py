import geoviews as gv
from holoviews import opts
import hvplot.pandas
import hvplot.xarray
import panel as pn
import cartopy.crs as ccrs
from climakitae.util.colormap import read_ae_colormap


def plot_exceedance_count(exceedance_count):
    """Create panel column object with embedded plots

    Plots each simulation as a different color line.
    Drop down option to select different scenario.
    Currently can only plot for one location, so is expecting input to already be subsetted or an area average.

    Parameters
    ----------
    exceedance_count: xarray.DataArray

    Returns
    -------
    panel.Column
    """
    plot_obj = exceedance_count.hvplot.line(
        x="time",
        widget_location="bottom",
        by="simulation",
        groupby=["scenario"],
        title="",
        fontsize={"ylabel": "10pt"},
        legend="right",
    )
    return pn.Column(plot_obj)


def get_geospatial_plot(
    ds,
    data_variable,
    bar_min=None,
    bar_max=None,
    border_color="black",
    line_width=0.5,
    cmap="ae_orange",
    hover_fill_color="blue",
):
    """Returns an interactive map from inputed dataset and selected data variable.

    Parameters
    ----------
    ds: xr.Dataset
        Data to plot
    data_variable: str
        Valid variable option in input dataset
        Valid options: "d_statistic","p_value","return_value","return_prob","return_period"
    bar_min: float, optional
        Colorbar minimum value
    bar_max: float, optional
        Colorbar maximum value
    border_color: str, optional
        Color for state lines and international borders
        Default to black
    cmap: matplotlib colormap name or AE colormap names, optional
        Colormap to apply to data
        Default to "ae_orange" for mapped data or color-blind friendly "categorical_cb" for timeseries data.
    hover_fill_color: str, optional
        Default to "blue"

    Returns
    -------
    holoviews.core.overlay.Overlay
        Map of input data
    """

    if cmap in [
        "categorical_cb",
        "ae_orange",
        "ae_diverging",
        "ae_blue",
        "ae_diverging_r",
    ]:
        cmap = read_ae_colormap(cmap=cmap, cmap_hex=True)

    data_variables = [
        "d_statistic",
        "p_value",
        "return_value",
        "return_prob",
        "return_period",
    ]
    if data_variable not in data_variables:
        raise ValueError(
            "invalid data variable type. expected one of the following: %s"
            % data_variables
        )

    if data_variable == "p_value":
        variable_name = "p-value"
    else:
        variable_name = data_variable.replace("_", " ").replace("'", "")

    def _rename_distr_abbrev(distr):
        """Makes abbreviated distribution name human-readable"""
        distr_abbrev = ["gev", "gumbel", "weibull", "pearson3", "genpareto"]
        distr_readable = [
            "GEV",
            "Gumbel",
            "Weibull",
            "Pearson Type III",
            "Generalized Pareto",
        ]
        return distr_readable[distr_abbrev.index(distr)]

    distr_name = _rename_distr_abbrev(ds.attrs["distribution"])

    borders = gv.Path(gv.feature.states.geoms(scale="50m", as_element=False)).opts(
        color=border_color, line_width=line_width
    ) * gv.feature.coastline.geoms(scale="50m").opts(
        color=border_color, line_width=line_width
    )

    if data_variable in ["d_statistic", "p_value"]:
        attribute_name = (
            (ds[data_variable].attrs["stat test"])
            .replace("{", "")
            .replace("}", "")
            .replace("'", "")
        )

    if data_variable in ["return_value"]:
        attribute_name = (
            (ds[data_variable].attrs["return period"])
            .replace("{", "")
            .replace("}", "")
            .replace("'", "")
        )

    if data_variable in ["return_prob"]:
        attribute_name = (
            (ds[data_variable].attrs["threshold"])
            .replace("{", "")
            .replace("}", "")
            .replace("'", "")
        )

    if data_variable in ["return_period"]:
        attribute_name = (
            (ds[data_variable].attrs["return value"])
            .replace("{", "")
            .replace("}", "")
            .replace("'", "")
        )

    cmap_label = variable_name
    variable_unit = ds[data_variable].attrs["units"]
    if variable_unit:
        cmap_label = " ".join([cmap_label, "({})".format(variable_unit)])

    geospatial_plot = (
        ds.hvplot.quadmesh(
            "lon",
            "lat",
            data_variable,
            clim=(bar_min, bar_max),
            projection=ccrs.PlateCarree(),
            ylim=(30, 50),
            xlim=(-130, -100),
            title="{} for a {}\n({} distribution)".format(
                variable_name, attribute_name, distr_name
            ),
            cmap=cmap,
            clabel=cmap_label,
            hover_fill_color=hover_fill_color,
        )
        * borders
    )
    return geospatial_plot
