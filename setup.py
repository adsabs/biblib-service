# mimic presence of 'setupy.py' - by reading config from pyproject.toml

# we are using ppsetuptools to read values and pass them to setup()
# however we also have to deal with idiosyncracies of ppsetuptools
# and of flint (which doesn't want to allow any entry inside
# [project.entry-points.console_scripts])

import inspect
import os

# important to import before importing ppsetuptools
import setuptools
import toml

orig_setup = setuptools.setup


def monkey(*args, **kwargs):
    del kwargs["license_files"]
    del kwargs["keywords"]

    try:
        caller_directory = os.path.abspath(os.path.dirname(inspect.stack()[1].filename))
        if not os.path.exists(os.path.join(caller_directory, "pyproject.toml")):
            raise
    except:  # noqa: E722
        caller_directory = "."

    with open(os.path.join(caller_directory, "pyproject.toml"), "r") as pptoml:
        pyproject_toml = pptoml.read()
        if isinstance(pyproject_toml, bytes):
            pyproject_toml = pyproject_toml.decode("utf-8")

    data = toml.loads(pyproject_toml)

    if "xsetup" in data:
        for key, value in data["xsetup"].items():
            if key not in kwargs or not kwargs[key]:
                kwargs[key] = value

    print("monkey patched setuptools, going to call setup() with those kwargs:")
    print("\n".join([str(x) for x in sorted(kwargs.items())]))

    orig_setup(*args, **kwargs)
    # raise ("To see values; for testing purposes")


setuptools.setup = monkey
import ppsetuptools  # noqa: E402

ppsetuptools.setup()

