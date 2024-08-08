from climakitaegui.core.data_interface import Select
from climakitae.core.data_load import load
from climakitae.core.data_view import view
from climakitae.core.data_export import export

try:
    from importlib.metadata import version as _version
except ImportError:
    # if the fallback library is missing, we are doomed.
    from importlib_metadata import version as _version  # type: ignore[no-redef]

try:
    __version__ = _version("climakitaegui")
except Exception:
    # Local copy or not installed with setuptools.
    # Disable minimum version checks on downstream libraries.
    __version__ = "999"


__all__ = (
    # Classes
    "Select",
    # Methods
    "load",
    "view",
    "export",
    # Constants
    "__version__",
)
