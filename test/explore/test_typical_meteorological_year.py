import numpy as np
import pandas as pd
import panel
import xarray as xr

from climakitaegui.explore.typical_meteorological_year import plot_one_var_cdf


def test_plot_one_var_cdf():
    """Test that plot runs and returns object."""
    # Create placeholder CDF results.
    test_data = np.arange(0, 1023, 1)
    test_data = np.expand_dims(test_data, [0, 1, 2]) * np.ones(
        (1, 12, 2, len(test_data))
    )
    dims = ["simulation", "month", "data", "bin_number"]
    coords = {
        "data": ["bins", "probability"],
        "simulation": ["sim1"],
        "month": list(range(1, 13)),
    }
    test = xr.DataArray(
        name="temperature",
        data=test_data,
        dims=dims,
        coords=coords,
    ).to_dataset()
    test["temperature"].attrs["units"] = "C"

    # Call plotting code
    test_plot = plot_one_var_cdf(test, "temperature")
    assert isinstance(test_plot, panel.layout.base.Column)
