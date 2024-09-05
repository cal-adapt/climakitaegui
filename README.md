Climakitaegui
=============
A python toolkit for adding graphical user interface and visualization tools to the [Climakitae python package](https://github.com/cal-adapt/climakitae). It does not work standalone - climakitae needs to be installed as well.

**Note:** This package is in active development and should be considered a work in progress. 

Documentation
-------------
Check out the official documentation on ReadTheDocs: https://climakitaegui.readthedocs.io/en/latest/ 

Installation
------------

Install the latest version in development directly with pip.

```
pip install https://github.com/cal-adapt/climakitaegui/archive/main.zip
```

Basic Usage
-----------

```
import climakitae as ck                           # Import the base climakitae package
import climakitaegui as ckg                       # Import the climakitaegui package
sel = ckg.Select().show()                         # Pull up selections GUI to make data settings
data = sel.retrieve()                             # Retrieve the data from the AWS catalog
data = ck.load(data)                              # Read the data into memory
ckg.view(data)                                    # Generate a basic visualization of the data
from climakitaegui.explore import warming_levels  # Import warming levels code
wl = warming_levels().show()                      # Explore Warming Levels GUI
```

Links
-----
* PyPI releases: https://pypi.org/project/climakitaegui/
* Source code: https://github.com/cal-adapt/climakitaegui
* Issue tracker: https://github.com/cal-adapt/climakitaegui/issues

Contributors
------------
[![Contributors](https://contrib.rocks/image?repo=cal-adapt/climakitaegui)](https://github.com/cal-adapt/climakitaegui/graphs/contributors)
