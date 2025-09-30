from climakitaegui.explore.thresholds import (
    ThresholdParameters,
    thresholds_visualize,
)
from climakitaegui.explore.warming import WarmingLevels


class Thresholds(ThresholdParameters):
    """Display Thresholds panel."""

    option = 1

    def __init__(self, option):
        super().__init__()
        self.option = option

    def show(self):
        return thresholds_visualize(
            self,
            option=self.option,
        )


def thresholds(option=1):
    return Thresholds(option=option)


def warming_levels():
    return WarmingLevels()
