#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
from os import path

from setuptools import setup

current_dir = path.abspath(path.dirname("__file__"))
with open(path.join(current_dir, "README.md"), encoding="utf-8") as file:
    long_description = file.read()


name = "openemailsequence"
package = "email_sequences"
description = "Email drip sequences for Django."
url = "https://github.com/eracle/OpenEmailSequence"
author = "eracle"
author_email = "eracle@openoutreach.app"
license = "MIT"
install_requires = ["Django>=5.0"]
keywords = "django email sequence drip campaign outreach"


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, "__init__.py")).read()
    return re.search("^__version__ = ['\"]([^'\"]+)['\"]", init_py, re.MULTILINE).group(1)  # type: ignore


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [
        dirpath
        for dirpath, dirnames, filenames in os.walk(package)
        if os.path.exists(os.path.join(dirpath, "__init__.py"))
    ]


def get_package_data(package):
    """
    Return all files under the root package, that are not in a
    package themselves.
    """
    walk = [
        (dirpath.replace(package + os.sep, "", 1), filenames)
        for dirpath, dirnames, filenames in os.walk(package)
        if not os.path.exists(os.path.join(dirpath, "__init__.py"))
    ]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename) for filename in filenames])
    return {package: filepaths}


if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    args = {"version": get_version(package)}
    print("You probably want to also tag the version now:")
    print("  git tag -a v{v} -m 'version v{v}'".format(v=args["version"]))
    print("  git push --tags")
    sys.exit()


setup(
    name=name,
    version=get_version(package),
    url=url,
    license=license,
    description=description,
    author=author,
    author_email=author_email,
    keywords=keywords,
    packages=get_packages(package),
    package_data=get_package_data(package),
    install_requires=install_requires,
    extras_require={"dev": ["pytest", "pytest-django", "factory-boy"]},
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
