"""
Test cases for the climakitaegui.core.data_interface module.
"""

from unittest.mock import MagicMock, patch

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.pyplot as plt
import param
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from shapely.geometry import Point, Polygon

from climakitaegui.core.data_interface import (
    DataParametersWithPanes,
    Select,
    _add_res_to_ax,
    _display_select,
    _map_view,
    _selections_param_to_panel,
)


def _create_mock_axes():
    """Create a mock axes with all required methods."""
    mock_ax = MagicMock(spec=Axes)
    mock_ax.set_extent = MagicMock()
    mock_ax.add_feature = MagicMock()
    mock_ax.scatter = MagicMock()
    mock_ax.add_geometries = MagicMock()
    mock_ax.annotate = MagicMock()

    mock_spines = {
        "right": MagicMock(),
        "top": MagicMock(),
        "left": MagicMock(),
        "bottom": MagicMock(),
    }
    mock_ax.spines = mock_spines
    return mock_ax


def _create_mock_figure():
    """Create a mock figure with canvas."""
    mock_fig = MagicMock(spec=Figure)
    mock_fig.canvas = MagicMock()
    return mock_fig


class TestAddResToAx:
    """Test the _add_res_to_ax function that adds resolution lines to a map."""

    @pytest.fixture
    def setup_map(self):
        """Set up test fixtures."""
        fig = Figure()
        proj = ccrs.Orthographic(-118, 40)
        ax = fig.add_subplot(111, projection=proj)
        poly = Polygon([(-123, 9), (-156, 35), (-102, 67), (-84, 26)])
        return fig, ax, poly

    def test_add_res_to_ax(self, setup_map):
        """Test that _add_res_to_ax adds geometries and annotations to the axis."""
        _, ax, poly = setup_map

        with patch.object(ax, "add_geometries") as mock_add_geometries, patch.object(
            ax, "annotate"
        ) as mock_annotate:

            _add_res_to_ax(poly, ax, 28, (-154, 33.8), "45 km", "green")

            # Check that add_geometries was called with the right arguments
            mock_add_geometries.assert_called_once()
            args, kwargs = mock_add_geometries.call_args
            assert len(args[0]) == 1  # One polygon
            assert kwargs["edgecolor"] == "green"
            assert kwargs["facecolor"] == "white"

            # Check that annotate was called with the right arguments
            mock_annotate.assert_called_once()
            args, kwargs = mock_annotate.call_args
            assert args[0] == "45 km"  # Label
            assert kwargs["xy"] == (-154, 33.8)  # Position
            assert kwargs["rotation"] == 28  # Rotation
            assert kwargs["color"] == "black"  # Color


class TestMapView:
    """Test the _map_view function that creates a map of location selections."""

    @pytest.fixture
    def setup_map_view(self):
        """Set up test fixtures."""
        # Create a mock DataParameters object
        selections = MagicMock()
        selections.area_subset = "none"
        selections.resolution = "45 km"
        selections.data_type = "Grid"

        # Create a mock stations dataframe
        geometry = [Point(x, y) for x, y in [(-122, 37), (-118, 34)]]
        stations_gdf = gpd.GeoDataFrame(
            {
                "station": ["Station1", "Station2"],
                "LON_X": [-122, -118],
                "LAT_Y": [37, 34],
                "geometry": geometry,
            },
            crs="EPSG:4326",
        )

        return selections, stations_gdf

    @patch("climakitaegui.core.data_interface._add_res_to_ax")
    @patch("climakitaegui.core.data_interface.pn.pane.Matplotlib")
    @patch("climakitaegui.core.data_interface._get_subarea")
    @patch("climakitaegui.core.data_interface.Figure")
    def test_map_view_grid_data(
        self,
        mock_figure,
        mock_get_subarea,
        mock_matplotlib_pane,
        mock_add_res,
        setup_map_view,
    ):
        """Test _map_view with grid data."""
        selections, stations_gdf = setup_map_view

        # Setup mocks with all required methods
        mock_fig = _create_mock_figure()
        mock_ax = _create_mock_axes()
        mock_figure.return_value = mock_fig
        mock_fig.add_subplot.return_value = mock_ax

        # Mock the Matplotlib pane
        mock_pane = MagicMock()
        mock_matplotlib_pane.return_value = mock_pane

        # Call the function
        _ = _map_view(selections, stations_gdf)

        # Verify the correct calls were made
        mock_ax.set_extent.assert_called_once()
        mock_ax.add_feature.assert_called()
        mock_ax.scatter.assert_not_called()
        mock_add_res.assert_called()

    @patch("climakitaegui.core.data_interface._add_res_to_ax")
    @patch("climakitaegui.core.data_interface.pn.pane.Matplotlib")
    @patch("climakitaegui.core.data_interface._get_subarea")
    @patch("climakitaegui.core.data_interface.Figure")
    def test_map_view_station_data(
        self,
        mock_figure,
        mock_get_subarea,
        mock_matplotlib_pane,
        mock_add_res,
        setup_map_view,
    ):
        """Test _map_view with station data."""
        selections, stations_gdf = setup_map_view

        # Setup mocks
        mock_fig = _create_mock_figure()
        mock_ax = _create_mock_axes()
        mock_figure.return_value = mock_fig
        mock_fig.add_subplot.return_value = mock_ax

        # Mock the Matplotlib pane
        mock_pane = MagicMock()
        mock_matplotlib_pane.return_value = mock_pane

        # Change data_type to Station
        selections.data_type = "Station"
        selections.station = ["Station1"]

        # Call the function
        _ = _map_view(selections, stations_gdf)

        # Verify the correct calls were made for station data
        mock_ax.set_extent.assert_called_once()
        mock_ax.add_feature.assert_called()
        mock_ax.scatter.assert_called_once()

    @patch("climakitaegui.core.data_interface._add_res_to_ax")
    @patch("climakitaegui.core.data_interface.pn.pane.Matplotlib")
    @patch("climakitaegui.core.data_interface._get_subarea")
    @patch("climakitaegui.core.data_interface.Figure")
    def test_map_view_resolution_display(
        self,
        mock_figure,
        mock_get_subarea,
        mock_matplotlib_pane,
        mock_add_res,
        setup_map_view,
    ):
        """Test that resolution boundaries are displayed correctly."""
        selections, stations_gdf = setup_map_view

        # Setup mocks
        mock_fig = _create_mock_figure()
        mock_ax = _create_mock_axes()
        mock_figure.return_value = mock_fig
        mock_fig.add_subplot.return_value = mock_ax

        # Mock the Matplotlib pane
        mock_pane = MagicMock()
        mock_matplotlib_pane.return_value = mock_pane

        # Test with different resolutions
        for resolution in ["45 km", "9 km", "3 km"]:
            selections.resolution = resolution
            _ = _map_view(selections, stations_gdf)

            # Verify _add_res_to_ax was called with the right parameters
            mock_add_res.assert_called()
            # Reset the mock for next iteration
            mock_add_res.reset_mock()


class TestDataParametersWithPanes:
    """Test the DataParametersWithPanes class."""

    @pytest.fixture
    def mock_data_params(self):
        """Set up test fixtures."""
        # Create a patched DataParametersWithPanes object
        with patch(
            "climakitaegui.core.data_interface.DataParameters.__init__"
        ) as mock_init:
            mock_init.return_value = None
            data_params = DataParametersWithPanes()
            # Set required attributes
            data_params.time_slice = (2020, 2050)
            data_params.scenario_ssp = ["SSP2-4.5"]
            data_params.scenario_historical = ["Historical Climate"]
            data_params.downscaling_method = "Dynamical"
            data_params.approach = "Time"
            data_params._stations_gdf = gpd.GeoDataFrame()
            data_params.area_subset = "none"
            data_params.resolution = "45 km"
            data_params.data_type = "Gridded"

            return data_params

    @patch("climakitaegui.core.data_interface.pn.pane.Matplotlib")
    @patch("climakitaegui.core.data_interface.Figure")
    def test_scenario_view(self, mock_figure, mock_matplotlib_pane, mock_data_params):
        """Test that scenario_view creates a figure with timeline."""
        # Setup mocks
        mock_fig = _create_mock_figure()
        mock_ax = _create_mock_axes()
        mock_ax.yaxis = MagicMock()
        mock_ax.xaxis = MagicMock()
        mock_figure.return_value = mock_fig
        mock_fig.add_subplot.return_value = mock_ax

        # Mock the Matplotlib pane
        mock_pane = MagicMock()
        mock_matplotlib_pane.return_value = mock_pane

        # Call the method
        _ = mock_data_params.scenario_view()

        # Verify the correct calls were made
        mock_figure.assert_called_once()
        mock_ax.set_xlim.assert_called_once_with(1950, 2100)
        mock_ax.errorbar.assert_called()
        mock_ax.fill_betweenx.assert_called_once()

    @patch("climakitaegui.core.data_interface._map_view")
    def test_map_view(self, mock_map_view, mock_data_params):
        """Test that map_view calls _map_view with correct parameters."""
        # Setup mock
        mock_map_view.return_value = MagicMock()

        # Call the method
        _ = mock_data_params.map_view()

        # Verify _map_view was called with the right parameters
        mock_map_view.assert_called_once_with(
            selections=mock_data_params, stations_gdf=mock_data_params._stations_gdf
        )


class TestSelect:
    """Test the Select class."""

    @patch("climakitaegui.core.data_interface._display_select")
    @patch("climakitaegui.core.data_interface.DataParametersWithPanes.__init__")
    def test_show(self, mock_init, mock_display_select):
        """Test that show calls _display_select."""
        # Setup mocks
        mock_init.return_value = None
        mock_display_select.return_value = MagicMock()

        # Create a Select object
        select = Select()

        # Call the method
        _ = select.show()

        # Verify _display_select was called with the right parameters
        mock_display_select.assert_called_once_with(select)


class TestSelectionsParamToPanel:
    """Test the _selections_param_to_panel function."""

    @pytest.fixture
    def mock_self(self):
        """Create a mock self object with all required parameters."""

        # Create a real parameter class that Panel's from_param can work with
        class TestParams(param.Parameterized):
            """Test class mocking DataParams"""

            area_subset = param.String(default="none")
            area_average = param.Boolean(default=False)
            cached_area = param.String()
            data_type = param.String(default="Grid")
            _data_warning = param.String()
            downscaling_method = param.String(default="Dynamical")
            scenario_historical = param.List(default=["Historical Climate"])
            _station_data_info = param.String()
            scenario_ssp = param.List(default=["SSP2-4.5"])
            resolution = param.String(default="45 km")
            approach = param.String(default="Time")
            timescale = param.String(default="Annual")
            time_slice = param.Range(default=(2020, 2050))
            units = param.String(default="°C")
            variable = param.String(default="tas")
            extended_description = param.String()
            variable_type = param.String(default="Average")
            warming_level = param.String(default="2°C")
            warming_level_window = param.Integer(default=15)
            latitude = param.Number()
            longitude = param.Number()
            stations = param.List()
            all_touched = param.Boolean(default=False)

        # Create a mock with real param object
        mock_self = MagicMock()
        mock_self.param = TestParams.param

        # Optional: Add specific behavior for selection widgets
        return mock_self

    @patch("panel.widgets.IntSlider.from_param")
    @patch("panel.widgets.Select.from_param")
    @patch("panel.widgets.RadioBoxGroup.from_param")
    @patch("panel.widgets.MultiSelect.from_param")
    @patch("panel.widgets.StaticText")
    @patch("panel.widgets.CheckBoxGroup.from_param")
    @patch("panel.widgets.RangeSlider.from_param")
    def test_selections_param_to_panel(
        self,
        mock_range_slider,
        mock_checkbox,
        mock_static_text,
        mock_multi_select,
        mock_radio_box,
        mock_select,
        mock_int_slider,
        mock_self,
    ):
        """Test that _selections_param_to_panel creates all the necessary widgets."""
        # Set up return values for all the mocked widgets
        for mock_widget in [
            mock_range_slider,
            mock_checkbox,
            mock_multi_select,
            mock_radio_box,
            mock_select,
            mock_int_slider,
        ]:
            mock_widget.return_value = MagicMock()

        mock_static_text.return_value = MagicMock()

        # Call the function
        _ = _selections_param_to_panel(mock_self)

        # Verify all widgets were created
        assert mock_select.called
        assert mock_radio_box.called
        assert mock_multi_select.called
        assert mock_static_text.called
        assert mock_checkbox.called
        assert mock_range_slider.called
        assert mock_int_slider.called


class TestDisplaySelect:
    """Test the _display_select function."""

    @pytest.fixture
    def mock_self(self):
        """Create a mock self object for display select testing."""
        mock_self = MagicMock()
        mock_self.map_view = MagicMock()
        mock_self.scenario_view = MagicMock()
        mock_self.param.stations = MagicMock()
        return mock_self

    @patch("climakitaegui.core.data_interface._selections_param_to_panel")
    @patch("panel.Column")
    @patch("panel.Row")
    @patch("panel.Card")
    @patch("panel.layout.Divider")
    @patch("panel.Spacer")
    @patch("panel.widgets.StaticText")
    @patch("panel.widgets.CheckBoxGroup.from_param")
    def test_display_select(
        self,
        mock_checkbox,
        mock_static_text,
        mock_spacer,
        mock_divider,
        mock_card,
        mock_row,
        mock_column,
        mock_selections_param,
        mock_self,
    ):
        """Test that _display_select creates the panel layout."""
        # Mock the widgets dictionary
        mock_widgets = {
            "area_average": MagicMock(),
            "area_subset": MagicMock(),
            "cached_area": MagicMock(),
            "data_type": MagicMock(),
            "data_type_text": MagicMock(),
            "data_warning": MagicMock(),
            "downscaling_method": MagicMock(),
            "historical_selection": MagicMock(),
            "latitude": MagicMock(),
            "longitude": MagicMock(),
            "resolution": MagicMock(),
            "station_data_info": MagicMock(),
            "ssp_selection": MagicMock(),
            "approach": MagicMock(),
            "timescale": MagicMock(),
            "time_slice": MagicMock(),
            "units": MagicMock(),
            "variable": MagicMock(),
            "variable_description": MagicMock(),
            "variable_type": MagicMock(),
            "warming_level": MagicMock(),
            "warming_level_window": MagicMock(),
            "area_average_text": MagicMock(),
            "downscaling_method_text": MagicMock(),
            "historical_selection_text": MagicMock(),
            "resolution_text": MagicMock(),
            "approach_text": MagicMock(),
            "ssp_selection_text": MagicMock(),
            "units_text": MagicMock(),
            "time_slice_text": MagicMock(),
            "timescale_text": MagicMock(),
            "variable_text": MagicMock(),
            "warming_level_text": MagicMock(),
            "warming_level_window_text": MagicMock(),
            "all_touched": MagicMock(),
        }
        mock_selections_param.return_value = mock_widgets

        # Call the function
        _ = _display_select(mock_self)

        # Verify the correct panel layout components were created
        assert mock_card.called
        assert mock_row.called
        assert mock_column.called
        assert mock_checkbox.called


# Optional: Define a parametrized test for multiple resolutions
@pytest.mark.parametrize(
    "expected_label",
    ["45 km", "9 km", "3 km"],
)
def test_resolution_labels(expected_label):
    """Test that resolution labels are correctly displayed."""
    fig = Figure()
    proj = ccrs.Orthographic(-118, 40)
    ax = fig.add_subplot(111, projection=proj)
    poly = Polygon([(-123, 9), (-156, 35), (-102, 67), (-84, 26)])

    with patch.object(ax, "add_geometries") as _, patch.object(
        ax, "annotate"
    ) as mock_annotate:

        _add_res_to_ax(poly, ax, 28, (-154, 33.8), expected_label, "green")

        # Check that the label matches the expected value
        args, _ = mock_annotate.call_args
        assert args[0] == expected_label
