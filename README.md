[![Build Status](https://travis-ci.org/andycasey/smhr.svg?branch=master)](https://travis-ci.org/andycasey/smhr)

# Spectroscopy Made Harder
------------------------
Gotta pay back that tech debt.


## Authors
-------
 - Andrew R. Casey (Monash)
 - Alex Ji (University of Chicago)
 - Erika Holmbeck (Lawrence Livermore National Laboratory)

## Installation
------------

This version of SMHR requires Python 3.14 or newer. Clone the repository and change into its
directory before choosing one of the environment setup methods below:

```
git clone https://github.com/AYelland/smhr-rpa.git
cd smhr-rpa
```

### Creating a Python Environment

#### Conda

Create and activate a Conda environment, then install SMHR with pip. The
dependencies are declared in `pyproject.toml`; using pip here ensures that the
same dependency set is installed regardless of the Conda platform:

```
conda create -n smhr-rpa python=3.14 pip
conda activate smhr-rpa
python -m pip install .
```

#### pip and venv

Create a virtual environment with Python 3.14 or newer, activate it, and
install the project in editable mode:

```
python3.14 -m venv .venv
source .venv/bin/activate
pip install .
```

#### uv

Install [uv](https://docs.astral.sh/uv/), then let it create the environment and install the exact versions recorded in `uv.lock`:

```
uv sync
```

* Try running it:
```
# Using the `python` command...
python smh/gui/__main__.py

# or, using uv...
uv run smh/gui/__main__.py 
```

Note: There is a chance the GUI menu bar does not behave correctly on macOS. If this happens to you, try using `pythonw` instead of `python` if your Python distribution provides it.

* Install moog17scat (see below) and add it to your path.

MOOG
----
It is currently recommended that you use this version of MOOG: https://github.com/alexji/moog17scat

Follow the usual MOOG installation instructions. When you compile MOOG, make sure that you have not activated any anaconda environments, because it can mess up the gfortran flags.
Note that SMHR requires you to have an executable called `MOOGSILENT` callable from your `$PATH` environment variable. Specifically, it uses the version of MOOG that you get from `which MOOGSILENT`.

This version is modified from the 2017 February version of MOOG from Chris Sneden's website. It includes Jennifer Sobeck's scattering routines (turned on and off with the flag `scat`, which is not true in the default MOOG 2017) and the fixes to the Barklem damping that were implemented in the 2014 MOOG refactoring.
There is now a 2019 November version of MOOG, but it did not add anything different unless you use the HF molecule or work on combined spectra of globular clusters. It did also start forcing MOOG to read everything as loggf from linelists, rather than logging things if all the loggfs were positive. But in SMHR we add a fake line whenever this is detected, so it does impact anything here.

Note that Alex has recently (Nov 16, 2021) fixed a bug in moog17scat that existed since the beginning and resulted in continuum accuracy only at the 0.003 when scattering is on. He also fixed a bug in isotopes.
See the README for `moog17scat` if you have concerns.
(Note May 2022: Alex has updated the master branch of moog17scat so this is done by default.)


VERSION HISTORY:
----------------
- The current master branch is python 3.
- March 5, 2024: starting from 4b7732ceaff1ba1bff9e5c36b891b2c0a8ab03a3, Alex has updated the mean abundances. Two important changes: (1) on the stellar parameters tab the average [Fe I,II/H] was previously reported as the median abundance. It now shows the mean abundance in parentheses. (2) on the review tab and in previous abundance summaries, I had mistakenly applied a weight based on the statistical uncertainty instead of using the straight mean abundance. It now uses no weights to calculate the mean.
- Alex has ported SMHR to python 3 in branch `py38-mpl313`. It now uses pyside2 and updated libraries for matplotlib. It is also way easier to install, not relying on some obscure libraries that were no longer maintained. Also added damping selection.
- The branch `refactor-scatterplot` has an updated and improved GUI (as of Jan 2020). These have not been merged into master yet but should be soon.
- Until Feb 2022, the `master` branch was frozen to a version from about July 2019.
- v0.22 (formerly branch `better-errors`) is a frozen version that is the result of a big update on May 30, 2019. It is considered a stable version.
- v0.2 is a frozen development version, v0.21 is a slightly more recently frozen version. 
- v0.1 is the current stable version. Things are working and it is being used for papers.

Note v0.1 and v0.2 files are not compatible, but there is a script to convert old save files into new save files.
There is not a way to convert files from the old SMH to new SMHR.
