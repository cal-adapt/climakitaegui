#!/usr/bin/env python
from setuptools import setup

# read the contents of your README file
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="climakitaegui",
    # other arguments omitted
    long_description=long_description,
    long_description_content_type="text/markdown",
)
