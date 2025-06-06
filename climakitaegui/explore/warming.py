import param
import panel as pn
import xarray as xr
import numpy as np
import hvplot.xarray
import hvplot.pandas
import holoviews as hv
from holoviews import opts
import holoviews.plotting.bokeh
import matplotlib.pyplot as plt
from scipy.stats import pearson3
from climakitae.core.data_interface import DataInterface
from climakitae.core.data_load import load
from climakitae.core.paths import (
    ssp119_file,
    ssp126_file,
    ssp245_file,
    ssp370_file,
    ssp585_file,
    hist_file,
)
from climakitae.explore.threshold_tools import _get_distr_func, _get_fitted_distr
from climakitae.explore.warming import WarmingLevels as BaseWarmingLevels
from climakitae.explore.warming import WarmingLevelChoose as BaseWarmingLevelChoose
from climakitae.util.colormap import read_ae_colormap
from climakitae.util.utils import read_csv_file, area_average
from climakitaegui.core.data_interface import (
    DataParametersWithPanes,
    _selections_param_to_panel,
)
from climakitaegui.core.data_view import compute_vmin_vmax

hv.extension("bokeh")


class WarmingLevels(BaseWarmingLevels):
    def __init__(self, **params):
        super().__init__(**params)
        self.wl_params = WarmingLevelChoose()

    def choose_data(self):
        return warming_levels_select(self.wl_params)

    def visualize(self):
        print("Loading in GWL snapshots...")
        self.gwl_snapshots = load(self.gwl_snapshots, progress_bar=True)
        self.wl_viz = WarmingLevelVisualize(
            gwl_snapshots=self.gwl_snapshots,
            wl_params=self.wl_params,
            warming_levels=self.wl_params.warming_levels,
        )
        self.wl_viz.compute_stamps()
        return warming_levels_visualize(self.wl_viz)


def _get_cmap(variable, variable_descriptions, vmin):
    """Set colormap depending on variable and minimum value in data
    See read_ae_colormap function for more info on function output

    Parameters
    ----------
    variable: str
        Display name of variable
    variable_descriptions: pd.DataFrame
        climakitae package data with variable descriptions and corresponding colormaps
    vmin: float
        minimum value of data

    Returns
    -------
    cmap: list
        Colormap

    """

    # Moisture/precip-related variables
    moisture_variables = [
        "Precipitation (total)",
        "Water Vapor Mixing Ratio at 2m",
        "Snowfall (snow and ice)",
        "Precipitation (cumulus portion only)",
        "Precipitation (grid-scale portion only)",
        "Subsurface runoff",
        "Surface runoff",
        "Snow water equivalent",
        "Snowfall",
        "Precipitation (convective only)",
    ]

    # Get colormap based on variable
    cmap_name = variable_descriptions[
        variable_descriptions["display_name"] == variable
    ]["colormap"].values[0]

    # Force reset to diverging if data is diverging but default variable colormap is not
    if (vmin < 0) and ("ae_diverging" not in cmap_name):
        if variable in moisture_variables:
            cmap_name = "ae_diverging_r"  # Reverse diverging colormap
        else:
            cmap_name = "ae_diverging"

    # Force reset diverging cmap to ae_orange or ae_blue if minimum value is greater than 0
    if (cmap_name == "ae_diverging") and (vmin >= 0):
        # Set to reverse diverging for moisture related variables
        if variable in moisture_variables:
            cmap_name = "ae_blue"
        else:
            cmap_name = "ae_orange"

    # Read colormap hex
    cmap = read_ae_colormap(cmap=cmap_name, cmap_hex=True)
    return cmap


def _select_one_gwl(one_gwl, snapshots):
    """
    This needs to happen in two places. You have to drop the sims
    which are nan because they don't reach that warming level, else the
    plotting functions and cross-sim statistics will get confused.
    But it's important that you drop it from a copy, or it may modify the
    original data.
    """
    all_plot_data = snapshots.sel(warming_level=one_gwl).copy()
    all_plot_data = all_plot_data.dropna("all_sims", how="all")
    return all_plot_data


def _check_single_spatial_dims(da):
    """
    This checks needs to happen to determine whether or not the plots in postage stamps should be image plots or bar plots, depending on whether or not one of the spatial dimensions is <= a length of 1.
    """
    if set(["lat", "lon"]).issubset(set(da.dims)):
        if len(da.lat) <= 1 or len(da.lon) <= 1:
            return True
    elif set(["x", "y"]).issubset(set(da.dims)):
        if len(da.x) <= 1 or len(da.y) <= 1:
            return True
    return False


class WarmingLevelChoose(BaseWarmingLevelChoose, DataParametersWithPanes):
    def __init__(self, **params):
        super().__init__(**params)


def _select_one_gwl(one_gwl, snapshots):
    """
    This needs to happen in two places. You have to drop the sims
    which are nan because they don't reach that warming level, else the
    plotting functions and cross-sim statistics will get confused.
    But it's important that you drop it from a copy, or it may modify the
    original data.
    """
    all_plot_data = snapshots.sel(warming_level=one_gwl).copy()
    all_plot_data = all_plot_data.dropna("all_sims", how="all")
    return all_plot_data


def _check_single_spatial_dims(da):
    """
    This checks needs to happen to determine whether or not the plots in postage stamps should be image plots or bar plots, depending on whether or not one of the spatial dimensions is <= a length of 1.
    """
    if set(["lat", "lon"]).issubset(set(da.dims)):
        if len(da.lat) <= 1 or len(da.lon) <= 1:
            return True
    elif set(["x", "y"]).issubset(set(da.dims)):
        if len(da.x) <= 1 or len(da.y) <= 1:
            return True
    return False


def warming_levels_select(self):
    """
    An initial pared-down version of the Select panel, with fewer options exposed,
    to help the user select a variable and location for further warming level steps.
    """
    widgets = _selections_param_to_panel(self)

    data_choices = pn.Column(
        widgets["variable_text"],
        widgets["variable"],
        widgets["variable_description"],
        widgets["units_text"],
        widgets["units"],
        widgets["timescale_text"],
        widgets["timescale"],
        widgets["resolution_text"],
        widgets["resolution"],
        width=250,
    )

    col_1_location = pn.Column(
        self.map_view,
        widgets["area_subset"],
        widgets["cached_area"],
        widgets["latitude"],
        widgets["longitude"],
        width=220,
    )

    gwl_specific = pn.Row(
        pn.Column(
            pn.widgets.StaticText(
                value=self.param.window.doc,
                name="",
            ),
            pn.widgets.IntSlider.from_param(self.param.window, name=""),
            width=250,
        ),
        pn.Column(
            pn.widgets.StaticText(value=self.param.anom.doc, name=""),
            pn.widgets.RadioBoxGroup.from_param(self.param.anom, name="", inline=True),
            width=220,
        ),
    )

    most_things = pn.Row(data_choices, col_1_location)

    # Panel overall structure:
    all_things = pn.Column(
        pn.Row(
            pn.Column(
                widgets["downscaling_method_text"],
                widgets["downscaling_method"],
                width=270,
            ),
            pn.Column(
                widgets["data_warning"],
                width=120,
            ),
        ),
        most_things,
        gwl_specific,
    )

    return pn.Card(
        all_things,
        title="Choose Data to Explore at Global Warming Levels",
        collapsible=False,
        width=600,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )


class WarmingLevelVisualize(param.Parameterized):
    """Create Warming Levels panel GUI"""

    ## Intended to be accessed through WarmingLevels class.
    ## Allows the user to toggle between several data options.
    ## Produces dynamically updating gwl snapshot maps.

    # Read in GMT context plot data
    ssp119_data = read_csv_file(ssp119_file, index_col="Year")
    ssp126_data = read_csv_file(ssp126_file, index_col="Year")
    ssp245_data = read_csv_file(ssp245_file, index_col="Year")
    ssp370_data = read_csv_file(ssp370_file, index_col="Year")
    ssp585_data = read_csv_file(ssp585_file, index_col="Year")
    hist_data = read_csv_file(hist_file, index_col="Year")

    warmlevel = param.Selector(
        default=1.5, objects=[1.5, 2, 3, 4], doc="Warming level in degrees Celcius."
    )
    ssp = param.Selector(
        default="All",
        objects=[
            "All",
            "SSP 1-1.9",
            "SSP 1-2.6",
            "SSP 2-4.5",
            "SSP 3-7.0",
            "SSP 5-8.5",
        ],
        doc="Shared Socioeconomic Pathway.",
    )

    def __init__(self, gwl_snapshots, wl_params, warming_levels):
        """
        Two things are passed in where this is initialized, and come in through
        *args, and **params
            wl_params: an instance of WarmingLevelParameters
            gwl_snapshots: xarray DataArray -- anomalies at each warming level
        """
        # super().__init__(*args, **params)
        super().__init__()
        self.gwl_snapshots = gwl_snapshots
        self.wl_params = wl_params
        self.warming_levels = warming_levels
        some_dims = self.gwl_snapshots.dims  # different names depending on WRF/LOCA
        some_dims = list(some_dims)
        some_dims.remove("warming_level")
        self.mins = self.gwl_snapshots.min(some_dims).compute()
        self.maxs = self.gwl_snapshots.max(some_dims).compute()

        # Need the DataInterface class to get the variable descriptions table
        self.variable_descriptions = DataInterface().variable_descriptions

    def compute_stamps(self):
        self.main_stamps = GCM_PostageStamps_MAIN_compute(self)
        self.stats_stamps = GCM_PostageStamps_STATS_compute(self)

    @param.depends("warmlevel", watch=True)
    def GCM_PostageStamps_MAIN(self):
        return self.main_stamps[str(float(self.warmlevel))]

    @param.depends("warmlevel", watch=True)
    def GCM_PostageStamps_STATS(self):
        return self.stats_stamps[str(float(self.warmlevel))]

    @param.depends("warmlevel", "ssp", watch=True)
    def GMT_context_plot(self):
        """Display GMT plot using package data that updates whenever the warming level or SSP is changed by the user."""
        ## Plot dimensions
        width = 575
        height = 300

        ## Plot figure
        hist_t = np.arange(1950, 2015, 1)
        cmip_t = np.arange(2015, 2100, 1)

        ## https://pyam-iamc.readthedocs.io/en/stable/tutorials/ipcc_colors.html
        c119 = "#00a9cf"
        c126 = "#003466"
        c245 = "#f69320"
        c370 = "#df0000"
        c585 = "#980002"

        ipcc_data = self.hist_data.hvplot(
            y="Mean", color="k", label="Historical", width=width, height=height
        ) * self.hist_data.hvplot.area(
            x="Year",
            y="5%",
            y2="95%",
            alpha=0.1,
            color="k",
            ylabel="°C",
            xlabel="",
            ylim=[-1, 5],
            xlim=[1950, 2100],
        )
        match self.ssp:
            case "All":
                ipcc_data = (
                    ipcc_data
                    * self.ssp119_data.hvplot(y="Mean", color=c119, label="SSP1-1.9")
                    * self.ssp126_data.hvplot(y="Mean", color=c126, label="SSP1-2.6")
                    * self.ssp245_data.hvplot(y="Mean", color=c245, label="SSP2-4.5")
                    * self.ssp370_data.hvplot(y="Mean", color=c370, label="SSP3-7.0")
                    * self.ssp585_data.hvplot(y="Mean", color=c585, label="SSP5-8.5")
                )
            case "SSP 1-1.9":
                ipcc_data = ipcc_data * self.ssp119_data.hvplot(
                    y="Mean", color=c119, label="SSP1-1.9"
                )
            case "SSP 1-2.6":
                ipcc_data = ipcc_data * self.ssp126_data.hvplot(
                    y="Mean", color=c126, label="SSP1-2.6"
                )
            case "SSP 2-4.5":
                ipcc_data = ipcc_data * self.ssp245_data.hvplot(
                    y="Mean", color=c245, label="SSP2-4.5"
                )
            case "SSP 3-7.0":
                ipcc_data = ipcc_data * self.ssp370_data.hvplot(
                    y="Mean", color=c370, label="SSP3-7.0"
                )
            case "SSP 5-8.5":
                ipcc_data = ipcc_data * self.ssp585_data.hvplot(
                    y="Mean", color=c585, label="SSP5-8.5"
                )
            case _:
                raise ValueError(
                    'ssp needs to be one of "All", "SSP 1-1.9", "SSP 1-2.6", "SSP 2-4.5", "SSP 3-7.0", "SSP 5-8.5"'
                )

        # SSP intersection lines
        cmip_t = np.arange(2015, 2101, 1)

        # Warming level connection lines & additional labeling
        warmlevel_line = hv.HLine(self.warmlevel).options(
            color="black", line_width=1.0
        ) * hv.Text(
            x=1964,
            y=self.warmlevel + 0.25,
            fontsize=8,
            text=".    " + str(self.warmlevel) + "°C warming level",
        )

        # Create plot
        to_plot = ipcc_data * warmlevel_line

        if self.ssp != "All":
            # Label to give addional plot info
            info_label = "Intersection information"

            # Add interval line and shading around selected SSP
            ssp_dict = {
                "SSP 1-1.9": (self.ssp119_data, c119),
                "SSP 1-2.6": (self.ssp126_data, c126),
                "SSP 2-4.5": (self.ssp245_data, c245),
                "SSP 3-7.0": (self.ssp370_data, c370),
                "SSP 5-8.5": (self.ssp585_data, c585),
            }

            ssp_selected = ssp_dict[self.ssp][0]  # data selected
            ssp_color = ssp_dict[self.ssp][1]  # color corresponding to ssp selected

            # Shading around selected SSP
            ci_label = "90% interval"
            ssp_shading = ssp_selected.hvplot.area(
                x="Year", y="5%", y2="95%", alpha=0.28, color=ssp_color, label=ci_label
            )
            to_plot = to_plot * ssp_shading

            # If the mean/upperbound/lowerbound does not cross threshold,
            # set to 2100 (not visible)
            if (np.argmax(ssp_selected["Mean"] > self.warmlevel)) > 0:
                # Add dashed line
                label1 = "Warming level reached"
                year_warmlevel_reached = (
                    ssp_selected.where(ssp_selected["Mean"] > self.warmlevel)
                    .dropna()
                    .index[0]
                )

                ssp_int = hv.Curve(
                    [[year_warmlevel_reached, -2], [year_warmlevel_reached, 10]],
                    label=label1,
                ).opts(opts.Curve(color=ssp_color, line_dash="dashed", line_width=1))
                ssp_int = ssp_int * hv.Text(
                    x=year_warmlevel_reached - 2,
                    y=4.5,
                    text=str(int(year_warmlevel_reached)),
                    rotation=90,
                    label=label1,
                ).opts(opts.Text(fontsize=8, color=ssp_color))
                to_plot *= ssp_int  # Add to plot

            if (np.argmax(ssp_selected["95%"] > self.warmlevel)) > 0 and (
                np.argmax(ssp_selected["5%"] > self.warmlevel)
            ) > 0:
                # Make 95% CI line
                x_95 = cmip_t[0] + np.argmax(ssp_selected["95%"] > self.warmlevel)
                ssp_firstdate = hv.Curve([[x_95, -2], [x_95, 10]], label=ci_label).opts(
                    opts.Curve(color=ssp_color, line_width=1)
                )
                to_plot *= ssp_firstdate

                # Make 5% CI line
                x_5 = cmip_t[0] + np.argmax(ssp_selected["5%"] > self.warmlevel)
                ssp_lastdate = hv.Curve([[x_5, -2], [x_5, 10]], label=ci_label).opts(
                    opts.Curve(color=ssp_color, line_width=1)
                )
                to_plot *= ssp_lastdate

                ## Bar to connect firstdate and lastdate of threshold cross
                bar_y = -0.5
                yr_len = [(x_95, bar_y), (x_5, bar_y)]
                yr_rng = np.argmax(ssp_selected["5%"] > self.warmlevel) - np.argmax(
                    ssp_selected["95%"] > self.warmlevel
                )
                if yr_rng > 0:
                    interval = hv.Curve(
                        [[x_95, bar_y], [x_5, bar_y]], label=ci_label
                    ).opts(opts.Curve(color=ssp_color, line_width=1)) * hv.Text(
                        x=x_95 + 5,
                        y=bar_y + 0.25,
                        text=str(yr_rng) + "yrs",
                        label=ci_label,
                    ).opts(
                        opts.Text(fontsize=8, color=ssp_color)
                    )

                    to_plot *= interval

        to_plot.opts(
            opts.Overlay(
                title="Global mean surface temperature change relative to 1850-1900",
                fontsize=12,
            )
        )
        to_plot.opts(legend_position="bottom", fontsize=10)
        return to_plot


def GCM_PostageStamps_MAIN_compute(wl_viz):
    # Make plots by warming level. Add to dictionary
    warm_level_dict = {}
    for warmlevel in wl_viz.warming_levels:

        # Get data for just that warming level
        # Rename simulation dimension to make the plot titles more intuitive
        data_to_plot = wl_viz.gwl_snapshots.sel(warming_level=warmlevel).rename(
            {"all_sims": "simulation"}
        )

        # If allllll the simulations don't reach the warming level, print a message
        if data_to_plot.isnull().all().item():
            warm_level_dict[warmlevel] = pn.widgets.StaticText(
                value=("<b>No simulations reach this warming level</b>"),
                width=300,
                style={
                    "border": "1.2px red solid",
                    "padding": "5px",
                    "border-radius": "4px",
                    "font-size": "13px",
                },
            )
            continue

        # If some of the simulations reach the warming level, but not ALL, remove that simulation
        # This is so an empty plot isn't generated
        for sim in data_to_plot.simulation.values:
            if data_to_plot.sel(simulation=sim).isnull().all().item() == True:
                data_to_plot = data_to_plot.where(
                    data_to_plot["simulation"] != sim, drop=True
                )

        # Get min and max to use for colorbar
        vmin, vmax, sopt = compute_vmin_vmax(data_to_plot.min(), data_to_plot.max())

        # Get cmap
        cmap = _get_cmap(wl_viz.wl_params.variable, wl_viz.variable_descriptions, vmin)

        # If there are less than or equal to four simulations, make postage stamps
        if len(data_to_plot.simulation.values) <= 4:

            # if there's only one data point, make a scatter plot
            if _check_single_spatial_dims(data_to_plot):
                wl_plots = (
                    data_to_plot.hvplot.scatter(
                        x="lon",
                        y="lat",
                        marker="s",
                        s=150,
                        frame_width=220,
                        hover_cols=data_to_plot.name,
                    )
                    .layout()
                    .cols(2)
                )
                wl_plots.opts(toolbar="right")  # Set toolbar location
                wl_plots.opts(
                    title=data_to_plot.name
                    + " for "
                    + str(warmlevel)
                    + "°C Warming by Simulation"
                )  # Add suptitle

                # Add titles to each subplot
                # this removes the default "simulation:" at the beginning
                for pl, sim_name in zip(wl_plots, data_to_plot.simulation.values):
                    pl.opts(title=sim_name)

            # Otherwise, create postage stamp plots
            else:
                wl_plots = (
                    data_to_plot.hvplot.quadmesh(
                        x="lon",
                        y="lat",
                        col_wrap="simulation",
                        clim=(vmin, vmax),
                        cmap=cmap,
                        symmetric=sopt,
                        colorbar=False,
                        shared_axis=True,
                        rasterize=True,  # set to True, otherwise hvplot has a bug where hovertool leaves a question mark
                        frame_width=220,
                    )
                    .layout()
                    .cols(2)
                )

                wl_plots.opts(toolbar="right")  # Set toolbar location
                wl_plots.opts(
                    title=data_to_plot.name
                    + " for "
                    + str(warmlevel)
                    + "°C Warming by Simulation"
                )  # Add suptitle

                # Add titles to each subplot
                # this removes the default "simulation:" at the beginning
                for pl, sim_name in zip(wl_plots, data_to_plot.simulation.values):
                    pl.opts(title=sim_name)

                # Add a shared colorbar to the right of the plots
                shared_colorbar = (
                    wl_plots.values()[0]
                    .clone()
                    .opts(
                        colorbar=True,
                        frame_width=0,
                        frame_height=500,
                        show_frame=False,
                        shared_axes=False,
                        xaxis=None,
                        yaxis=None,
                        toolbar=None,
                        title="",
                        colorbar_opts={
                            "width": 20,
                            "height": 400,
                            "title": data_to_plot.name
                            + " ("
                            + data_to_plot.attrs["units"]
                            + ")",
                        },
                    )
                )

                # Create panel object: combine plot with shared colorbar
                wl_plots = pn.Row(wl_plots + shared_colorbar)

            # Add to dictionary
            warm_level_dict[warmlevel] = wl_plots

        # If there are more than 4 simulations, make a dropdown
        else:

            # if there's only one data point, make a scatter plot
            if _check_single_spatial_dims(data_to_plot):
                wl_plot = data_to_plot.hvplot.scatter(
                    x="lon",
                    y="lat",
                    hover_cols=data_to_plot.name,
                    col_wrap="simulation",
                    clabel=data_to_plot.name + " (" + data_to_plot.attrs["units"] + ")",
                    marker="s",
                    s=150,
                    frame_width=450,
                    widget_location="bottom",
                )

            else:
                wl_plot = data_to_plot.hvplot.quadmesh(
                    x="lon",
                    y="lat",
                    col_wrap="simulation",
                    clim=(vmin, vmax),
                    cmap=cmap,
                    clabel=data_to_plot.name + " (" + data_to_plot.attrs["units"] + ")",
                    rasterize=True,
                    frame_width=450,
                    widget_location="bottom",
                )

            # Add to dictionary
            warm_level_dict[warmlevel] = pn.Row(wl_plot)

    return warm_level_dict


def GCM_PostageStamps_STATS_compute(wl_viz):
    """
    Compute helper for stats postage stamps.
    Returns dictionary of warming levels to stats visuals.
    """
    # Get data to plot
    warm_level_dict = {}
    for warmlevel in wl_viz.warming_levels:
        all_plot_data = _select_one_gwl(warmlevel, wl_viz.gwl_snapshots)
        if all_plot_data.all_sims.size != 0:

            # compute stats
            def get_name(simulation, my_func_name):
                method, GCM, run, scenario = simulation.split("_")
                return (
                    my_func_name
                    + ": \n"
                    + method
                    + " "
                    + GCM
                    + " "
                    + run
                    + "\n"
                    + scenario.split("+")[1][
                        1:
                    ]  # The [1:] removes the first value, which is a space
                )

            def arg_median(data):
                """
                Returns the simulation closest to the median.
                """
                return str(
                    data.loc[
                        data == data.quantile(0.5, "all_sims", method="nearest")
                    ].all_sims.values[0]
                )

            def find_sim(all_plot_data, area_avgs, stat_funcs, my_func):
                if my_func == "Median":
                    one_sim = all_plot_data.sel(all_sims=stat_funcs[my_func](area_avgs))
                else:
                    which_sim = area_avgs.reduce(stat_funcs[my_func], dim="all_sims")
                    one_sim = all_plot_data.isel(all_sims=which_sim.values)
                one_sim.all_sims.values = get_name(
                    one_sim.all_sims.values.item(),
                    my_func,
                )
                return one_sim

            area_avgs = area_average(all_plot_data)
            stat_funcs = {
                "Minimum": np.argmin,
                "Maximum": np.argmax,
                "Median": arg_median,
            }
            stats = xr.concat(
                [
                    find_sim(all_plot_data, area_avgs, stat_funcs, one_func)
                    for one_func in stat_funcs
                ],
                dim="all_sims",
            ).rename({"all_sims": "simulation"})

            # Get min and max to use for colorbar
            vmin, vmax, sopt = compute_vmin_vmax(
                all_plot_data.min(), all_plot_data.max()
            )

            # Get cmap
            cmap = _get_cmap(
                wl_viz.wl_params.variable, wl_viz.variable_descriptions, vmin
            )

            # Colorbar label and plot suptitle
            clabel = all_plot_data.name + " (" + all_plot_data.attrs["units"] + ")"
            title = "Cross-Simulation Statistics for " + str(warmlevel) + "°C Warming"

            if _check_single_spatial_dims(all_plot_data):
                only_sims = area_average(stats)
                wl_plots = only_sims.hvplot.bar(
                    x="simulation", xlabel="Simulation", ylabel=clabel, title=title
                ).opts(multi_level=False, show_legend=False)

            else:
                wl_plots = (
                    stats.hvplot.quadmesh(
                        x="lon",
                        y="lat",
                        col_wrap="simulation",
                        clim=(vmin, vmax),
                        cmap=cmap,
                        symmetric=sopt,
                        colorbar=False,
                        shared_axis=True,
                        rasterize=True,  # set to True, otherwise hvplot has a bug where hovertool leaves a question mark
                        frame_width=260,
                    )
                    .layout()
                    .cols(2)
                )

                wl_plots.opts(toolbar="right")  # Set toolbar location
                wl_plots.opts(title=title)  # Add suptitle

                # Add titles to each subplot
                # this removes the default "simulation:" at the beginning
                for pl, sim_name in zip(wl_plots, stats.simulation.values):
                    pl.opts(title=sim_name)

                # Add a shared colorbar to the right of the plots
                shared_colorbar = (
                    wl_plots.values()[0]
                    .clone()
                    .opts(
                        colorbar=True,
                        frame_width=0,
                        frame_height=500,
                        show_frame=False,
                        shared_axes=False,
                        xaxis=None,
                        yaxis=None,
                        toolbar=None,
                        title="",
                        colorbar_opts={
                            "width": 20,
                            "height": 300,
                            "title": clabel,
                        },
                    )
                )

                # Create panel object: combine plot with shared colorbar
                wl_plots = pn.Row(wl_plots + shared_colorbar)

            warm_level_dict[warmlevel] = wl_plots

        # This means that there does not exist any simulations that reach this degree of warming (WRF models).
        else:
            # Pass in a dummy visualization for now to stay consistent with viz data structures
            warm_level_dict[warmlevel] = pn.widgets.StaticText(
                value=("<b>No simulations reach this warming level</b>"),
                width=300,
                style={
                    "border": "1.2px red solid",
                    "padding": "5px",
                    "border-radius": "4px",
                    "font-size": "13px",
                },
            )

    return warm_level_dict


def warming_levels_visualize(wl_viz):
    # Create panel doodad!
    GMT_plot = pn.Card(
        pn.Column(
            (
                "Shading around selected global emissions scenario shows the 90% interval"
                " across different simulations. Dotted line indicates when the multi-model"
                " ensemble reaches the selected warming level, while solid vertical lines"
                " indicate when the earliest and latest simulations of that scenario reach"
                " the warming level. Figure and data are reproduced from the"
                " [IPCC AR6 Summary for Policymakers Fig 8]"
                "(https://www.ipcc.ch/report/ar6/wg1/figures/summary-for-policymakers/figure-spm-8/)."
            ),
            pn.widgets.Select.from_param(wl_viz.param.ssp, name="Scenario", width=250),
            wl_viz.GMT_context_plot,
        ),
        title="When do different scenarios reach the warming level?",
        collapsible=False,
        width=850,
        height=600,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )

    postage_stamps_MAIN = pn.Column(
        pn.widgets.StaticText(
            value=(
                "Panels show the 30-year average centered on the year that each "
                "GCM run (each panel) reaches the specified warming level. "
                "If you selected 'Yes' to return an anomaly, you will see the difference "
                "from average over the 1981-2010 historical reference period."
                "An empty plot indicates the warming level was never reached for that simulation."
            ),
            width=800,
        ),
        wl_viz.GCM_PostageStamps_MAIN,
    )

    postage_stamps_STATS = pn.Column(
        pn.widgets.StaticText(
            value=(
                "Panels show the median, minimum, or maximum conditions"
                " across all models. These statistics are computed from the data"
                " in the first panel."
            ),
            width=800,
        ),
        wl_viz.GCM_PostageStamps_STATS,
    )

    map_tabs = pn.Card(
        pn.Row(
            pn.widgets.StaticText(name="", value="Warming level (°C)"),
            pn.widgets.RadioButtonGroup.from_param(wl_viz.param.warmlevel, name=""),
            width=230,
        ),
        pn.Tabs(
            ("Maps of individual simulations", postage_stamps_MAIN),
            (
                "Maps of cross-model statistics: median/max/min",
                postage_stamps_STATS,
            ),
            dynamic=True,
        ),
        title="Regional response at selected warming level",
        width=850,
        height=800,
        collapsible=False,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )

    warming_panel = pn.Column(GMT_plot, map_tabs)
    return warming_panel


def _make_hvplot(data, clabel, clim, cmap, sopt, title, width=225, height=210):
    """Make single map"""
    if len(data.x) > 1 and len(data.y) > 1:
        # If data has more than one grid cell, make a pretty map
        _plot = data.hvplot.image(
            x="x",
            y="y",
            grid=True,
            width=width,
            height=height,
            xaxis=None,
            yaxis=None,
            clabel=clabel,
            clim=clim,
            cmap=cmap,
            symmetric=sopt,
            title=title,
        )
    else:
        # Make a scatter plot if it's just one grid cell
        _plot = data.hvplot.scatter(
            x="x",
            y="y",
            hover_cols=data.name,
            grid=True,
            width=width,
            height=height,
            xaxis=None,
            yaxis=None,
            clabel=clabel,
            clim=clim,
            cmap=cmap,
            symmetric=sopt,
            title=title,
            s=150,  # Size of marker
        )
    return _plot


def fit_models_and_plots(new_data, trad_data, dist_name):
    """
    Given a xr.DataArray and a distribution name, fit the distribution to the data, and generate
    a plot denoting a histogram of the data and the fitted distribution to the data.
    """
    plt.figure(figsize=(10, 5))

    # Get and fit distribution for new method data and traditional method data
    func = _get_distr_func(dist_name)
    new_fitted_dist = _get_fitted_distr(new_data, dist_name, func)
    trad_fitted_dist = _get_fitted_distr(trad_data, dist_name, func)

    # Get params from distribution
    new_params = new_fitted_dist[0].values()
    trad_params = trad_fitted_dist[0].values()

    # Create histogram for new method data and traditional method data
    counts, bins = np.histogram(new_data)
    plt.hist(
        bins[:-1],
        5,
        weights=counts / sum(counts),
        label="New GWL counts",
        lw=3,
        fc=(1, 0, 0, 0.5),
    )

    counts, bins = np.histogram(trad_data)
    plt.hist(
        bins[:-1],
        5,
        weights=counts / sum(counts),
        label="Traditional counts",
        lw=3,
        fc=(0, 0, 1, 0.5),
    )

    # Plotting pearson3 PDFs
    skew, loc, scale = new_params
    x = np.linspace(func.ppf(0.01, skew), func.ppf(0.99, skew), 5000)
    plt.plot(x, func.pdf(x, skew), "r-", lw=2, alpha=0.6, label="pearson3 curve new")
    new_left, new_right = pearson3.interval(0.95, skew, loc, scale)

    skew, loc, scale = trad_params
    x = np.linspace(func.ppf(0.01, skew), func.ppf(0.99, skew), 5000)
    plt.plot(x, func.pdf(x, skew), "b-", lw=2, alpha=0.6, label="pearson3 curve trad.")
    trad_left, trad_right = pearson3.interval(0.95, skew, loc, scale)

    # Plotting confidence intervals
    plt.axvline(new_left, color="r", linestyle="dashed", label="95% CI new")
    plt.axvline(new_right, color="r", linestyle="dashed")
    plt.axvline(trad_left, color="b", linestyle="dashed", label="95% CI trad.")
    plt.axvline(trad_right, color="b", linestyle="dashed")

    # Plotting rest of chart attributes
    plt.xlabel("Log of Extreme Heat Days Count")
    plt.ylabel("Probability Density")
    plt.legend()
    plt.title("Fitting Pearson3 Distributions to Log-Scaled Extreme Heat Days Counts")
    plt.xlim(left=0.5, right=max(max(new_data), max(trad_data)))
    plt.ylim(top=1)
    plt.show()

    return new_params, trad_params
