import panel as pn
import param
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import cartopy.feature as cfeature
from shapely.geometry import box, Polygon
import cartopy.crs as ccrs
from climakitae.core.data_interface import _get_subarea, DataParameters


def _add_res_to_ax(
    poly, ax, rotation, xy, label, color="black", crs=ccrs.PlateCarree()
):
    """Add resolution line and label to axis

    Parameters
    ----------
    poly: geometry to plot
    ax: matplotlib axis
    color: matplotlib color
    rotation: int
    xy: tuple
    label: str
    crs: projection
    """
    ax.add_geometries(
        [poly], crs=ccrs.PlateCarree(), edgecolor=color, facecolor="white"
    )
    ax.annotate(
        label,
        xy=xy,
        rotation=rotation,
        color="black",
        xycoords=crs._as_mpl_transform(ax),
    )


def _map_view(selections, stations_gdf):
    """View the current location selections on a map
    Updates dynamically

    Parameters
    ----------
    selections: DataParameters
        User data selections
    stations_gpd: gpd.DataFrame
        DataFrame with station coordinates

    Returns
    -------
    mpl_pane: pn.Pane
    """

    _wrf_bb = {
        "45 km": Polygon(
            [
                (-123.52125549316406, 9.475631713867188),
                (-156.8231658935547, 35.449039459228516),
                (-102.43182373046875, 67.32866668701172),
                (-84.18701171875, 26.643436431884766),
            ]
        ),
        "9 km": Polygon(
            [
                (-116.69509887695312, 22.267112731933594),
                (-138.42117309570312, 43.23344802856445),
                (-110.90779113769531, 57.5806770324707),
                (-94.9368896484375, 31.627288818359375),
            ]
        ),
        "3 km": Polygon(
            [
                (-117.80029, 29.978943),
                (-127.95593, 40.654625),
                (-120.79376, 44.8999),
                (-111.23247, 33.452168),
            ]
        ),
    }

    fig0 = Figure(figsize=(2.25, 2.25))
    proj = ccrs.Orthographic(-118, 40)
    crs_proj4 = proj.proj4_init  # used below
    xy = ccrs.PlateCarree()
    ax = fig0.add_subplot(111, projection=proj)
    mpl_pane = pn.pane.Matplotlib(fig0, dpi=120)

    # Get geometry of selected location
    subarea_gpd = _get_subarea(
        selections.area_subset,
        selections.cached_area,
        selections.latitude,
        selections.longitude,
        selections._geographies,
        selections._geography_choose,
    )
    # Set plot extent
    ca_extent = [-125, -114, 31, 43]  # Zoom in on CA
    us_extent = [
        -130,
        -100,
        25,
        50,
    ]  # Western USA + a lil bit of baja (viva mexico)
    na_extent = [-150, -88, 8, 66]  # North America extent (largest extent)
    if selections.area_subset == "lat/lon":
        extent = na_extent  # default
        # Dynamically update extent depending on borders of lat/lon selection
        for extent_i in [ca_extent, us_extent, na_extent]:
            # Construct a polygon from the extent
            geom_extent = Polygon(
                box(extent_i[0], extent_i[2], extent_i[1], extent_i[3])
            )
            # Check if user selections for lat/lon are contained in the extent
            if geom_extent.contains(subarea_gpd.geometry.values[0]):
                # If so, set the extent to the smallest extent possible
                # Such that the lat/lon selection is contained within the map's boundaries
                extent = extent_i
                break
    elif (selections.resolution == "3 km") or ("CA" in selections.area_subset):
        extent = ca_extent
    elif (selections.resolution == "9 km") or (selections.area_subset == "states"):
        extent = us_extent
    elif selections.area_subset == "none":
        extent = na_extent
    else:  # Default for all other selections
        extent = ca_extent
    ax.set_extent(extent, crs=xy)

    # Set size of markers for stations depending on map boundaries
    match extent:
        case _ if extent == ca_extent:
            scatter_size = 4.5
        case _ if extent == us_extent:
            scatter_size = 2.5
        case _ if extent == na_extent:
            scatter_size = 1.5
        case _:
            raise ValueError("extent not set correctly")

    match selections.resolution:
        case "45 km":
            _add_res_to_ax(
                poly=_wrf_bb["45 km"],
                ax=ax,
                color="green",
                rotation=28,
                xy=(-154, 33.8),
                label="45 km",
            )
        case "9 km":
            _add_res_to_ax(
                poly=_wrf_bb["9 km"],
                ax=ax,
                color="red",
                rotation=32,
                xy=(-134, 42),
                label="9 km",
            )
        case "3 km":
            _add_res_to_ax(
                poly=_wrf_bb["3 km"],
                ax=ax,
                color="darkorange",
                rotation=32,
                xy=(-127, 40),
                label="3 km",
            )
        case _:
            raise ValueError('resolution needs to be "45 km", "9 km", "3 km"')

    # Add user-selected geometries
    match selections.area_subset:
        case "lat/lon":
            ax.add_geometries(
                subarea_gpd["geometry"].values,
                crs=ccrs.PlateCarree(),
                edgecolor="b",
                facecolor="None",
            )
        case selections.area_subset if selections.area_subset != "none":
            subarea_gpd.to_crs(crs_proj4).plot(ax=ax, color="deepskyblue", zorder=2)
            mpl_pane.param.trigger("object")

    # Overlay the weather stations as points on the map
    if selections.data_type == "Station":
        # Subset the stations gpd to get just the user's selected stations
        # We need the stations gpd because it has the coordinates, which will be used to make the plot
        stations_selection_gdf = stations_gdf.loc[
            stations_gdf["station"].isin(selections.station)
        ]
        stations_selection_gdf = stations_selection_gdf.to_crs(
            crs_proj4
        )  # Convert to map projection
        ax.scatter(
            stations_selection_gdf.LON_X.values,
            stations_selection_gdf.LAT_Y.values,
            transform=ccrs.PlateCarree(),
            zorder=15,
            color="black",
            s=scatter_size,  # Scatter size is dependent on extent of map
        )

    # Add state lines, international borders, and coastline
    ax.add_feature(cfeature.STATES, linewidth=0.5, edgecolor="gray")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor="darkgray")
    ax.add_feature(cfeature.BORDERS, edgecolor="darkgray")
    return mpl_pane


class DataParametersWithPanes(DataParameters):
    """Extends DataParameters class to include panel widgets that display the time scale and a map overview"""

    def __init__(self, **params):
        # Set default values
        super().__init__(**params)

    @param.depends(
        "time_slice",
        "scenario_ssp",
        "scenario_historical",
        "downscaling_method",
        "approach",
        watch=False,
    )
    def scenario_view(self):
        """
        Displays a timeline to help the user visualize the time ranges
        available, and the subset of time slice selected.
        """

        fig0 = Figure(figsize=(2, 2))

        if (
            self.scenario_historical == ["n/a"]
            or self.scenario_ssp == ["n/a"]
            or self.approach == "Warming Level"
        ):
            mpl_pane = pn.pane.Matplotlib(fig0, dpi=120)

        else:
            # Set time range of historical data
            match self.downscaling_method:
                case "Dynamical":
                    historical_climate_range = self.historical_climate_range_wrf
                case "Statistical":
                    historical_climate_range = self.historical_climate_range_loca
                case "Dynamical+Statistical":
                    historical_climate_range = (
                        self.historical_climate_range_wrf_and_loca
                    )
                case _:
                    raise ValueError(
                        'downscaling_method needs to be "Dynamical", "Statistical", or "Dynamical+Statistical"'
                    )
            historical_central_year = sum(historical_climate_range) / 2
            historical_x_width = historical_central_year - historical_climate_range[0]

            ax = fig0.add_subplot(111)
            ax.spines["right"].set_color("none")
            ax.spines["left"].set_color("none")
            ax.yaxis.set_major_locator(ticker.NullLocator())
            ax.spines["top"].set_color("none")
            ax.xaxis.set_ticks_position("bottom")
            ax.set_xlim(1950, 2100)
            ax.set_ylim(0, 1)
            ax.tick_params(labelsize=11)
            ax.xaxis.set_major_locator(ticker.AutoLocator())
            ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
            mpl_pane = pn.pane.Matplotlib(fig0, dpi=120)

            y_offset = 0.15
            if (self.scenario_ssp is not None) and (
                self.scenario_historical is not None
            ):
                for scen in self.scenario_ssp + self.scenario_historical:
                    if ["SSP" in one for one in self.scenario_ssp]:
                        if scen in [
                            "Historical Climate",
                            "Historical Reconstruction",
                        ]:
                            continue

                    if scen == "Historical Reconstruction":
                        color = "darkblue"
                        if "Historical Climate" in self.scenario_historical:
                            center = historical_central_year
                            x_width = historical_x_width
                            ax.annotate(
                                "Reconstruction",
                                xy=(1967 - 6, y_offset + 0.06),
                                fontsize=9,
                            )
                        else:
                            center = 1986  # 1950-2022
                            x_width = 36
                            ax.annotate(
                                "Reconstruction",
                                xy=(1955 - 6, y_offset + 0.06),
                                fontsize=9,
                            )

                    elif scen == "Historical Climate":
                        color = "c"
                        center = historical_central_year
                        x_width = historical_x_width
                        ax.annotate(
                            "Historical",
                            xy=(historical_climate_range[0] - 6, y_offset + 0.06),
                            fontsize=9,
                        )

                    elif "SSP" in scen:
                        center = 2057.5  # 2015-2100
                        x_width = 42.5
                        scenario_label = scen[:10]
                        if "2-4.5" in scen:
                            color = "#f69320"
                        elif "3-7.0" in scen:
                            color = "#df0000"
                        elif "5-8.5" in scen:
                            color = "#980002"
                        if "Historical Climate" in self.scenario_historical:
                            ax.errorbar(
                                x=historical_central_year,
                                y=y_offset,
                                xerr=historical_x_width,
                                linewidth=8,
                                color="c",
                            )
                            ax.annotate(
                                "Historical",
                                xy=(historical_climate_range[0] - 6, y_offset + 0.06),
                                fontsize=9,
                            )

                        ax.annotate(scen[:10], xy=(2035, y_offset + 0.06), fontsize=9)

                    ax.errorbar(
                        x=center, y=y_offset, xerr=x_width, linewidth=8, color=color
                    )

                    y_offset += 0.28

            ax.fill_betweenx(
                [0, 1],
                self.time_slice[0],
                self.time_slice[1],
                alpha=0.8,
                facecolor="lightgrey",
            )
        return mpl_pane

    @param.depends(
        "downscaling_method",
        "resolution",
        "latitude",
        "longitude",
        "area_subset",
        "cached_area",
        "data_type",
        "stations",
        watch=False,
    )
    def map_view(self):
        """Create a map of the location selections"""
        return _map_view(selections=self, stations_gdf=self._stations_gdf)


class Select(DataParametersWithPanes):
    """Class for storing and displaying data retrieval parameters interactively.
    DataParameters class can be used instead if you don't need to visually show
    the parameters.
    """

    def show(self):
        # Show panel visually
        select_panel = _display_select(self)
        return select_panel


def _selections_param_to_panel(self):
    """For the Select object, get parameters and parameter
    descriptions formatted as panel widgets

    Returns
    -------
    dict
    """
    area_subset = pn.widgets.Select.from_param(
        self.param.area_subset, name="Subset the data by...", width=225
    )
    area_average_text = pn.widgets.StaticText(
        value="Compute an area average across grid cells within your selected region?",
        name="",
    )
    area_average = pn.widgets.RadioBoxGroup.from_param(
        self.param.area_average, inline=True
    )
    cached_area = pn.widgets.MultiSelect.from_param(
        self.param.cached_area, name="Location selection", width=225
    )
    data_type_text = pn.widgets.StaticText(
        value="",
        name="Data Type",
    )
    data_type = pn.widgets.RadioBoxGroup.from_param(
        self.param.data_type, inline=False, name=""
    )
    data_warning = pn.widgets.StaticText.from_param(
        self.param._data_warning, name="", styles={"color": "red"}
    )
    downscaling_method_text = pn.widgets.StaticText(value="", name="Downscaling Method")
    downscaling_method = pn.widgets.RadioBoxGroup.from_param(
        self.param.downscaling_method, inline=False
    )
    historical_selection_text = pn.widgets.StaticText(
        value="<br>Estimates of recent historical climatic conditions",
        name="Historical Data",
    )
    historical_selection = pn.widgets.CheckBoxGroup.from_param(
        self.param.scenario_historical
    )
    station_data_info = pn.widgets.StaticText.from_param(
        self.param._station_data_info, name="", styles={"color": "red"}
    )
    ssp_selection_text = pn.widgets.StaticText(
        value="<br> Shared Socioeconomic Pathways (SSPs) represent different global emissions scenarios",
        name="Future Model Data",
    )
    ssp_selection = pn.widgets.CheckBoxGroup.from_param(self.param.scenario_ssp)
    resolution_text = pn.widgets.StaticText(
        value="",
        name="Model Grid-Spacing",
    )
    resolution = pn.widgets.RadioBoxGroup.from_param(
        self.param.resolution, inline=False
    )
    approach = pn.widgets.RadioBoxGroup.from_param(
        self.param.approach, inline=False, name=""
    )
    approach_text = pn.widgets.StaticText(
        value="",
        name="Approach",
    )
    timescale_text = pn.widgets.StaticText(value="", name="Timescale")
    timescale = pn.widgets.RadioBoxGroup.from_param(
        self.param.timescale, name="", inline=False
    )
    time_slice = pn.widgets.RangeSlider.from_param(
        self.param.time_slice, name="", width=250
    )
    time_slice_text = pn.widgets.StaticText(
        value="How do you want to time-slice the data?", name="Years"
    )
    units_text = pn.widgets.StaticText(name="Variable Units", value="")
    units = pn.widgets.RadioBoxGroup.from_param(self.param.units, inline=False)
    variable = pn.widgets.Select.from_param(self.param.variable, name="", width=225)
    variable_text = pn.widgets.StaticText(name="Variable Type", value="")
    variable_description = pn.widgets.StaticText.from_param(
        self.param.extended_description, name=""
    )
    variable_type = pn.widgets.RadioBoxGroup.from_param(
        self.param.variable_type, inline=True, name=""
    )
    warming_level = pn.widgets.CheckBoxGroup.from_param(
        self.param.warming_level, inline=True, name=""
    )
    warming_level_text = pn.widgets.StaticText(
        value="",
        name="Warming Level (°C)",
    )
    warming_level_window = pn.widgets.IntSlider.from_param(
        self.param.warming_level_window, name="", width=240
    )
    warming_level_window_text = pn.widgets.StaticText(
        value="e.g. 15 means a 30yr window",
        name="Years around Global Warming Level (+/-)",
    )
    all_touched = pn.widgets.Checkbox.from_param(
        self.param.all_touched, name="Include cells touching edge of the selection area"
    )

    widgets_dict = {
        "area_average": area_average,
        "area_subset": area_subset,
        "cached_area": cached_area,
        "data_type": data_type,
        "data_type_text": data_type_text,
        "data_warning": data_warning,
        "downscaling_method": downscaling_method,
        "historical_selection": historical_selection,
        "latitude": self.param.latitude,
        "longitude": self.param.longitude,
        "resolution": resolution,
        "station_data_info": station_data_info,
        "ssp_selection": ssp_selection,
        "approach": approach,
        "timescale": timescale,
        "time_slice": time_slice,
        "units": units,
        "variable": variable,
        "variable_description": variable_description,
        "variable_type": variable_type,
        "warming_level": warming_level,
        "warming_level_window": warming_level_window,
        "all_touched": all_touched,
    }
    text_dict = {
        "area_average_text": area_average_text,
        "downscaling_method_text": downscaling_method_text,
        "historical_selection_text": historical_selection_text,
        "resolution_text": resolution_text,
        "approach_text": approach_text,
        "ssp_selection_text": ssp_selection_text,
        "units_text": units_text,
        "time_slice_text": time_slice_text,
        "timescale_text": timescale_text,
        "variable_text": variable_text,
        "warming_level_text": warming_level_text,
        "warming_level_window_text": warming_level_window_text,
    }

    return widgets_dict | text_dict


def _display_select(self):
    """
    Called by Select at the beginning of the workflow, to capture user
    selections. Displays panel of widgets from which to make selections.
    Modifies DataParameters object, which is used by retrieve() to build an
    appropriate xarray Dataset.

    Returns
    -------
    pn.Card
    """
    # Get formatted panel widgets for each parameter
    widgets = _selections_param_to_panel(self)

    # These are top-level choices
    # This is the first thing the user will see in the panel
    top_level_choices = pn.Column(
        pn.Row(
            pn.Column(
                widgets["data_type_text"],
                widgets["data_type"],
                width=200,
            ),
            pn.Column(widgets["approach_text"], widgets["approach"], width=200),
            pn.Column(
                widgets["downscaling_method_text"],
                widgets["downscaling_method"],
                width=200,
            ),
        ),
    )

    # Choices for variable, unit, timescale, and resolution
    variable_stuff = pn.Row(
        pn.Column(
            widgets["variable_text"],
            widgets["variable_type"],
            widgets["variable"],
            widgets["variable_description"],
            width=300,
        ),
        pn.Column(
            pn.Row(
                pn.Column(widgets["units_text"], widgets["units"], width=100),
                pn.Column(widgets["timescale_text"], widgets["timescale"], width=100),
                pn.Column(widgets["resolution_text"], widgets["resolution"], width=100),
            ),
            pn.Column(widgets["station_data_info"], width=300),
        ),
    )

    # Options for a warming level approach
    warming_level_approach = pn.Column(
        pn.widgets.StaticText(
            value='Options only valid if retrievel method is set to "Warming Level"',
            name="WARMING LEVELS APPROACH",
        ),
        pn.Row(
            pn.Column(
                widgets["warming_level_window_text"],
                widgets["warming_level_window"],
                width=270,
            ),
            pn.Column(
                widgets["warming_level_text"],
                widgets["warming_level"],
                width=250,
            ),
        ),
    )

    # Options for a time-based approach
    time_approach = pn.Column(
        pn.widgets.StaticText(
            value='Options only valid if retrievel method is set to "Time"',
            name="TIME-BASED APPROACH",
        ),
        pn.Row(
            pn.Column(
                widgets["time_slice_text"],
                widgets["time_slice"],
                widgets["historical_selection_text"],
                widgets["historical_selection"],
                widgets["ssp_selection_text"],
                widgets["ssp_selection"],
                width=300,
            ),
            pn.Column(self.scenario_view, widgets["data_warning"], width=300),
        ),
    )

    # Location options
    col_1_location = pn.Column(
        self.map_view,
        widgets["area_subset"],
        widgets["cached_area"],
        widgets["latitude"],
        widgets["longitude"],
        widgets["area_average_text"],
        widgets["area_average"],
        widgets["all_touched"],
        pn.Spacer(
            height=150
        ),  # Need to add empty space to make card larger to fit all the stations
        width=310,
    )
    col_2_location = pn.Column(
        pn.Spacer(height=10),
        pn.widgets.StaticText(
            value="",
            name="Stations",
        ),
        pn.widgets.CheckBoxGroup.from_param(self.param.stations, name=""),
        width=300,
        margin=(0, 0, 0, 15),
    )

    # Combine panel elements to create the card for the location options
    loc_card = pn.Card(
        pn.Row(col_1_location, col_2_location),
        title="Location Options for the Selected Data",
        collapsible=False,
        width=635,
        height=775,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )

    # Combine panel elements to create the card for the data options
    data_card = pn.Card(
        top_level_choices,
        pn.layout.Divider(margin=(-10, 0, 0, 0)),
        variable_stuff,
        pn.layout.Divider(margin=(-10, 0, 0, 0)),
        warming_level_approach,
        pn.layout.Divider(margin=(-10, 0, 0, 0)),
        time_approach,
        title="Data Options in the Cal-Adapt Analytics Engine",
        collapsible=False,
        width=635,
        height=775,
        styles={
            "header_background": "lightgrey",
            "border-radius": "5px",
            "border": "2px solid black",
            "margin": "10px",
        },
    )

    # Combine both cards for the complete panel object
    card = pn.Row(data_card, loc_card)

    return card
