from climakitaegui.explore.typical_meteorological_year import plot_one_var_cdf


def test_plot_one_var_cdf(self):
    """Test that plot runs and returns object."""
    # Create test dataset
    test_data = np.arange(0, 365 * 3, 1)
    test_data = test_data * np.ones((2, len(test_data)))
    test = xr.DataArray(
        name="temperature",
        data=test_data,
        coords={
            "simulation": ["sim1", "sim2"],
            "time": pd.date_range(start="2001-01-01", end="2003-12-31"),
        },
    ).to_dataset()
    test["temperature"].attrs["units"] = "C"
    result = get_cdf(test)

    test_plot = plot_one_var_cdf(result, "temperature")

    assert isinstance(test_plot, panel.layout.base.Column)
