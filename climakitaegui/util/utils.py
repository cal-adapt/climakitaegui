def hdd_cdd_lineplot(annual_data, trendline, title="title"):
    """Plots annual CDD/HDD with trendline provided

    Parameters
    ----------
    annual_data: xr.DataArray
    trendline: xr.Dataset
    title: str

    Returns
    -------
    data: hvplot.line
    """
    return annual_data.hvplot.line(
        x="year",
        by="simulation",
        width=800,
        height=350,
        title=title,
        yformatter="%.0f",  # Remove scientific notation
    ) * trendline.hvplot.line(  # Add trendline
        x="year", color="black", line_dash="dashed", label="trendline"
    )


def hdh_cdh_lineplot(data):
    """Plots HDH/CDH

    Parameters
    ----------
    data: xr.DataArray

    Returns
    -------
    data: hvplot.line
    """
    return data.hvplot.line(
        x="time", by="simulation", title=data.name, ylabel=data.name + " (degF)"
    )
