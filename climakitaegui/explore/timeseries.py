import param
import pandas as pd
import panel as pn
import hvplot.xarray
from climakitae.explore.timeseries import TimeSeriesParameters, TimeSeries


def timeseries_visualize(choices):
    """
    Uses holoviz 'panel' library to display the parameters and view defined in
    an instance of _TimeSeriesParams.
    """
    smooth_text = "Smoothing applies a running mean to remove noise from the data."
    resample_text = "The resample window and period define the length of time over which to calculate the extreme."

    return pn.Column(
        pn.Row(
            pn.Column(
                pn.widgets.StaticText(name="", value="Transformation Options"),
                choices.param.anomaly,
                choices.param.reference_range,
                choices.param.remove_seasonal_cycle,
                choices.param.separate_seasons,
                choices.param.smoothing,
                choices.param.num_timesteps,
                pn.Spacer(height=10),
            ),
            pn.Spacer(width=50),
            pn.Column(
                pn.widgets.CheckBoxGroup.from_param(choices.param.extremes),
                choices.param.percentile,
                pn.Row(
                    choices.param.resample_window,
                    choices.param.resample_period,
                    width=320,
                ),
                pn.widgets.StaticText(name="", value=smooth_text),
                pn.widgets.StaticText(name="", value=resample_text),
            ),
        ),
        choices.view,
    )


class TimeSeriesParameters(TimeSeriesParameters):
    @param.depends(
        "anomaly",
        "reference_range",
        "separate_seasons",
        "smoothing",
        "num_timesteps",
        "remove_seasonal_cycle",
        "extremes",
        "resample_window",
        "resample_period",
        "percentile",
        watch=False,
    )
    def view(self):
        """
        Does the main work of timeseries.explore(). Updating a plot in real-time
        to enable the user to preview the results of any timeseries transforms.
        """
        to_plot = self.transform_data()

        if self.separate_seasons:
            menu_list = ["scenario", "time.season"]
        else:
            menu_list = ["scenario"]

        # Resample period user-friendly (used in title)
        resample_per_str = str(self.resample_period)[
            :-1
        ]  # Remove plural (i.e. "months" --> "month")

        # Percentile string user-friendly (used in title)
        percentile_int = int(self.percentile * 100)
        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )
        percentrile_str = ordinal(percentile_int)

        # Smoothing string user-friendly (used in title)
        if self.smoothing == "Running Mean":
            smoothing_str = "Smoothed "
        else:
            smoothing_str = ""

        # Get start and end years of input data
        # Use that to build a title
        pd_datetime = pd.DatetimeIndex(self.data.time.values)
        year1, year2 = str(pd_datetime[0].year), str(pd_datetime[-1].year)
        new_title = smoothing_str + "Difference for " + year1 + " - " + year2

        if self.extremes == []:
            plot_by = "simulation"
            if self.anomaly:
                if (
                    self.smoothing == "Running Mean"
                ):  # Smoothed, anomaly timeseries, no extremes
                    new_title = (
                        smoothing_str
                        + "Difference for ".lower()
                        + year1
                        + " - "
                        + year2
                        + " with a "
                        + str(self.num_timesteps)
                        + " timesteps running mean"
                    )
                else:  # Unsmoothed, anomaly timeseries, no extremes
                    new_title = (
                        smoothing_str + "Difference for " + year1 + " - " + year2
                    )
            else:
                if (
                    self.smoothing == "Running Mean"
                ):  # Smoothed, timeseries, no extremes
                    new_title = (
                        smoothing_str
                        + "Timeseries for ".lower()
                        + year1
                        + " - "
                        + year2
                        + " with a "
                        + str(self.num_timesteps)
                        + " timesteps running mean"
                    )
                else:  # Unsmoothed, timeseries, no extremes
                    new_title = (
                        smoothing_str + "Timeseries for " + year1 + " - " + year2
                    )

        elif self.extremes != []:
            plot_by = ["simulation", "extremes"]
            if self.smoothing == "None":
                if self.extremes == "Percentile":  # Unsmoothed, percentile extremes
                    new_title = (
                        smoothing_str
                        + percentrile_str
                        + " percentile extremes over a "
                        + str(self.resample_window)
                        + "-"
                        + resample_per_str
                        + " window"
                    )
                else:  # Unsmoothed, min/max/mean extremes
                    new_title = (
                        smoothing_str
                        + "Extremes over a "
                        + str(self.resample_window)
                        + "-"
                        + resample_per_str
                        + " window"
                    )
            elif self.smoothing != "None":
                if self.extremes == "Percentile":  # Smoothed, percentile extremes
                    new_title = (
                        smoothing_str
                        + percentrile_str
                        + " percentile extremes over a "
                        + str(self.resample_window)
                        + "-"
                        + resample_per_str
                        + " window"
                    )
                else:  # Smoothed, min/max/mean extremes
                    new_title = (
                        smoothing_str
                        + "Extremes over a "
                        + str(self.resample_window)
                        + "-"
                        + resample_per_str
                        + " window"
                    )

        obj = to_plot.hvplot.line(
            x="time",
            widget_location="bottom",
            by=plot_by,
            groupby=menu_list,
            title=new_title,
        )
        return obj


class TimeSeries(TimeSeries):
    def __init__(self, data):
        self.choices = TimeSeriesParameters(data)

    def explore(self):
        """Create an interactive visualization of the timeseries data, dependant on the attributes set in previous steps. Allows user to directly modify the data in the GUI. Only works in a jupyter notebook environment.

        Returns
        -------
        panel.layout.base.Column

        """
        return timeseries_visualize(self.choices)
