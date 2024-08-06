import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import hvplot.pandas
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
    meteo_yr_df,
    title="Meteorological Year",
    cmap="ae_orange",
    clabel=None,
    width=500,
    height=250,
):
    """Create interactive (hvplot) meteorological year heatmap.

    Parameters
    ----------
    meteo_yr_df: pd.DataFrame
        Meteorological year dataframe, with hour of day as columns and day of year as index
        Output of either compute_severe_yr or compute_meteo_yr
    title: str, optional
        Title to give heatmap. Default to "Meteorological Year"
    cmap: matplotlib colormap name or AE colormap names, optional
        Colormap to apply to heatmap. Default to "ae_orange"
    clabel: str, optional
        Name of variable being plotted. Default to None.
        Will be applied to label of colorbar.
    width: int, optional
        Width of heatmap. Default to 500
    height: int, optional
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
    if len(meteo_yr_df) == 366:  # Leap year
        idx = idx
    elif len(meteo_yr_df) == 365:  # Normal year
        idx = [(i - 1, mon) for i, mon in idx]
    else:
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
    meteo_yr_df, title="Meteorological Year", cmap="ae_orange", clabel=None
):
    """Create static (matplotlib) meteorological year heatmap

    Parameters
    ----------
    meteo_yr_df: pd.DataFrame
        Meteorological year dataframe, with hour of day as columns and day of year as index
        Output of either compute_severe_yr or compute_meteo_yr
    title: str, optional
        Title to give heatmap. Default to "Meteorological Year"
    cmap: matplotlib colormap name or AE colormap names, optional
        Colormap to apply to heatmap. Default to "ae_orange"
    clabel: str, optional
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


def lineplot_from_amy_data(
    amy_data,
    computation_method=None,
    location_subset=None,
    warmlevel=None,
    variable=None,
):
    """Generate a lineplot of meteorological year data, with mon-day-hr on the x-axis

    Parameters
    ----------
    amy_data: pd.DataFrame
        Meteorological year dataframe, with hour of day as columns and day of year as index
        Output of either compute_severe_yr or compute_meteo_yr
    computation_method: str, optional
        Method used to compute the meteorological year.
        Used to add descriptive information to the plot title.
    location_subset: str, optional
        Location subset of data.
        Used to add descriptive information to the plot title.
    warmlevel: str, optional
        Warming level used to generate data.
        Used to add descriptive information to the plot title.
    variable: str, optional
        Name of data variable.
        Used to add descriptive information to the plot title.

    Returns
    --------
    matplotlib.figure.Figure
        Lineplot of the data

    """

    # Stack data
    amy_stacked = (
        pd.DataFrame(amy_data.stack()).rename(columns={0: "data"}).reset_index()
    )
    amy_stacked["Date"] = amy_stacked["Day of Year"] + " " + amy_stacked["Hour"]
    amy_stacked = amy_stacked.drop(columns=["Day of Year", "Hour"]).set_index("Date")

    # Set plot title, suptitle, and ylabel using original xr DataArray
    suptitle = "Average Meterological Year"
    title = ""
    if computation_method is not None:
        suptitle += ": " + computation_method
        if computation_method == "Warming Level Future":
            if warmlevel is not None:
                suptitle += " at " + str(warmlevel) + "°C "
        if computation_method == "Historical":
            suptitle += " Data"

    # Add months information
    try:  # Try leap year
        months = [
            datetime.datetime.strptime("2024." + idx_i, "%Y.%b-%d %I%p").strftime("%B")
            for idx_i in amy_stacked.index
        ]
    except:  # Try non leap year
        months = [
            datetime.datetime.strptime("2023." + idx_i, "%Y.%b-%d %I%p").strftime("%B")
            for idx_i in amy_stacked.index
        ]

    def check_if_all_identical(l):
        return all(i == l[0] for i in l)

    if check_if_all_identical(months):  # Add month to title
        title += "Month: " + months[0] + "\n"
    else:
        title += "Months: " + months[0] + "-" + months[-1] + "\n"

    if location_subset is not None:
        title += "Location Subset: " + location_subset

    # Make plot
    fig, axes = plt.subplots(1, 1, figsize=(7, 4))
    amy_lineplot = axes.plot(amy_stacked)
    axes.grid(alpha=0.25)
    plt.xticks(rotation=45)
    axes.xaxis.set_major_locator(MaxNLocator(10))
    axes.set_ylabel(variable)
    plt.suptitle(suptitle, fontsize=13, y=1.025)
    axes.set_title(title, fontsize=10, y=1)
    plt.close()
    return fig


# =========================== MAIN AVERAGE METEO YR OBJECT ==============================


class AverageMetYearParameters(DataParametersWithPanes):
    """An object that holds the data options parameters for the explore.tmy panel."""

    # Create dictionary of TMY advanced options depending on TMY type
    tmy_advanced_options_dict = {
        "Absolute": {
            "default": "Historical",
            "objects": ["Historical", "Warming Level Future"],
        },
        "Difference": {
            "default": "Warming Level Future",
            "objects": ["Warming Level Future", "Severe AMY"],
        },
    }

    # Create a dictionary that briefly explains the computation being perfomed
    computatation_description_dict = {
        "Absolute": {
            "Historical": "AMY computed using the historical baseline for 1981-2010.",
            "Warming Level Future": (
                "AMY computed using the 30-year future period"
                " centered around when the selected warming level is reached."
            ),
        },
        "Difference": {
            "Warming Level Future": (
                "AMY computed by taking the difference between"
                " the 30-year future period centered around the selected warming"
                " level and the historical baseline."
            ),
            "Severe AMY": (
                "AMY computed by taking the difference between the 90th percentile of the 30-year future"
                " period centered around the selected warming level and the historical baseline."
            ),
        },
    }

    # Define TMY params
    amy_type = param.Selector(default="Absolute", objects=["Absolute", "Difference"])

    # Define new advanced options param, that is dependent on the user selection in amy_type
    computation_method = param.Selector(objects=dict())

    # Define new computation description param
    # This will provide a string description of the computation option selected
    # and will update dynamically depending on the user selections
    tmy_computation_description = param.Selector(objects=dict())

    # Colormap
    cmap = param.Selector(objects=dict())

    # Warming level selection
    warmlevel = param.Selector(default=1.5, objects=[1.5, 2, 3])

    # 30-yr ranges to use for AMY computation
    warming_year_average_range = {
        1.5: (2034, 2063),
        2: (2047, 2076),
        3: (2061, 2090),
    }

    def __init__(self, *args, **params):
        super().__init__(*args, **params)

        # Location defaults
        self.area_subset = "CA counties"
        self.cached_area = ["Los Angeles County"]

        # Initialze tmy_adanced_options param
        self.param["computation_method"].objects = self.tmy_advanced_options_dict[
            self.amy_type
        ]["objects"]
        self.computation_method = self.tmy_advanced_options_dict[self.amy_type][
            "default"
        ]

        # Initialize tmy_computation_description param
        self.tmy_computation_description = self.computatation_description_dict[
            self.amy_type
        ][self.computation_method]

        # Postage data and anomalies defaults
        self.historical_tmy_data = retrieve_meteo_yr_data(
            self,
            year_start=1981,
            year_end=2010,
        ).compute()
        self.future_tmy_data = retrieve_meteo_yr_data(
            self,
            year_start=self.warming_year_average_range[self.warmlevel][0],
            year_end=self.warming_year_average_range[self.warmlevel][1],
        ).compute()

        # Colormap
        self.cmap = read_ae_colormap(cmap="ae_orange", cmap_hex=True)

        # Selectors defaults
        self.downscaling_method = "Dynamical"
        self.append_historical = "No"
        self.area_average = "Yes"
        self.resolution = "45 km"
        self.scenario_historical = ["Historical Climate"]
        self.scenario_ssp = []
        self.time_slice = (1981, 2010)
        self.timescale = "hourly"
        self.variable = "Air Temperature at 2m"
        self.simulation = ["ensmean"]

    # For reloading data and plots
    reload_data = param.Action(
        lambda x: x.param.trigger("reload_data"), label="Reload Data"
    )

    @param.depends("variable", "amy_type", watch=True)
    def _update_cmap(self):
        """Set colormap depending on variable"""
        cmap_name = self._variable_descriptions[
            (self._variable_descriptions["display_name"] == self.variable)
            & (self._variable_descriptions["timescale"] == "hourly")
        ].colormap.values[0]

        # Set to diverging colormap if difference is selected
        if self.amy_type == "Difference":
            cmap_name = "ae_diverging"

        # Read colormap hex
        self.cmap = read_ae_colormap(cmap=cmap_name, cmap_hex=True)

    @param.depends("computation_method", "reload_data", "warmlevel", watch=True)
    def _update_data_to_be_returned(self):
        """Update self so that the correct data is returned by DataParameters.retrieve()"""

        self.downscaling_method = "Dynamical"

        if self.computation_method == "Historical":
            self.scenario_historical = ["Historical Climate"]
            self.scenario_ssp = []
            self.time_slice = (1981, 2010)

        elif self.computation_method == "Warming Level Future":
            self.scenario_ssp = ["SSP 3-7.0 -- Business as Usual"]
            self.scenario_historical = []
            self.time_slice = self.warming_year_average_range[self.warmlevel]

        self.simulation = ["ensmean"]
        self.append_historical = False
        self.area_average = "Yes"
        self.timescale = "hourly"

    @param.depends("reload_data", watch=True)
    def _update_tmy_data(self):
        """If the button was clicked and the location or variable was changed,
        reload the tmy data from AWS"""

        self.historical_tmy_data = retrieve_meteo_yr_data(
            self,
            year_start=1981,
            year_end=2010,
        ).compute()
        self.future_tmy_data = retrieve_meteo_yr_data(
            self,
            year_start=self.warming_year_average_range[self.warmlevel][0],
            year_end=self.warming_year_average_range[self.warmlevel][1],
        ).compute()

    # Create a function that will update computation_method when amy_type is modified
    @param.depends("amy_type", watch=True)
    def _update_computation_method(self):
        self.param["computation_method"].objects = self.tmy_advanced_options_dict[
            self.amy_type
        ]["objects"]
        self.computation_method = self.tmy_advanced_options_dict[self.amy_type][
            "default"
        ]

    @param.depends("amy_type", "computation_method", watch=True)
    def _update_tmy_computatation_description(self):
        self.tmy_computation_description = self.computatation_description_dict[
            self.amy_type
        ][self.computation_method]

    @param.depends("reload_data", watch=False)
    def _tmy_hourly_heatmap(self):
        # update heatmap df and title with selections
        if len(self.cached_area) == 1:
            cached_area_str = self.cached_area[0]
        elif len(self.cached_area) == 2:
            if self.area_subset == "states":
                cached_area_str = " ".join(self.cached_area)
            elif self.area_subset == "CA counties":
                names = [name.split(" County")[0] for name in self.cached_area]
                cached_area_str = "{} and {} Counties".format(names[0], names[1])
            elif self.area_subset == "CA watersheds":
                cached_area_str = "{} and {} Watersheds".format(
                    self.cached_area[0], self.cached_area[1]
                )
            else:
                cached_area_str = " and ".join(self.cached_area)
        else:
            cached_area_str = "Selected {}".format(self.area_subset)

        # add new line if `cached_area_str` is too long
        if len(cached_area_str) > 40:
            cached_area_str = "\n" + cached_area_str

        days_in_year = 366
        if self.amy_type == "Absolute":
            if self.computation_method == "Historical":
                df = compute_amy(self.historical_tmy_data, days_in_year=days_in_year)
                title = "Average Meteorological Year: {}\nAbsolute {} Baseline".format(
                    cached_area_str, self.computation_method
                )
                clabel = (
                    self.variable + " (" + self.historical_tmy_data.attrs["units"] + ")"
                )
            else:
                df = compute_amy(self.future_tmy_data, days_in_year=days_in_year)
                title = "Average Meteorological Year: {}\nAbsolute {} at {}°C".format(
                    cached_area_str, self.computation_method, self.warmlevel
                )
                clabel = self.variable + " (" + self.units + ")"
        elif self.amy_type == "Difference":
            cmap = read_ae_colormap("ae_diverging", cmap_hex=True)
            if self.computation_method == "Warming Level Future":
                df = compute_amy(
                    self.future_tmy_data, days_in_year=days_in_year
                ) - compute_amy(self.historical_tmy_data, days_in_year=days_in_year)
                title = "Average Meteorological Year: {}\nDifference between {} at {}°C and Historical Baseline".format(
                    cached_area_str, self.computation_method, self.warmlevel
                )
                clabel = self.variable + " (" + self.units + ")"
            else:
                df = compute_severe_yr(
                    self.future_tmy_data, days_in_year=days_in_year
                ) - compute_amy(self.historical_tmy_data, days_in_year=days_in_year)
                title = "Severe Meteorological Year: {}\nDifference between {} at 90th percentile and Historical Baseline".format(
                    cached_area_str, self.computation_method
                )
                clabel = self.variable + " (" + self.units + ")"
        else:
            title = "Average Meteorological Year for\n{}".format(cached_area_str)
        heatmap = meteo_yr_heatmap(
            meteo_yr_df=df,
            title=title,
            cmap=self.cmap,
            clabel=self.variable + "(" + self.units + ")",
        )

        return heatmap


# =========================== OBJECT VISUALIZATION USING PARAM ==============================


def amy_visualize(self):
    """
    Creates a new AMY focus panel object to display user selections
    """
    user_options = pn.Card(
        pn.Row(
            pn.Column(
                pn.widgets.StaticText(
                    name="", value="Average Meteorological Year Type"
                ),
                pn.widgets.RadioButtonGroup.from_param(self.param.amy_type),
                pn.widgets.Select.from_param(
                    self.param.computation_method, name="Computation Options"
                ),
                pn.widgets.StaticText.from_param(
                    self.param.tmy_computation_description, name=""
                ),
                pn.widgets.StaticText(name="", value="Warming level (°C)"),
                pn.widgets.RadioButtonGroup.from_param(self.param.warmlevel),
                pn.widgets.Select.from_param(self.param.variable, name="Data variable"),
                pn.widgets.StaticText.from_param(
                    self.param.extended_description, name=""
                ),
                pn.widgets.StaticText(name="", value="Variable Units"),
                pn.widgets.RadioButtonGroup.from_param(self.param.units),
                pn.widgets.StaticText(name="", value="Model Resolution"),
                pn.widgets.RadioButtonGroup.from_param(self.param.resolution),
                width=280,
            ),
            pn.Column(
                self.param.area_subset,
                self.param.latitude,
                self.param.longitude,
                self.param.cached_area,
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
    )

    tmy_panel = pn.Column(pn.Row(user_options, tmy_tabs))
    return tmy_panel
