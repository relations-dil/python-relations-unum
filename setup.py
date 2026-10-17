#!/usr/bin/env python

import os
from setuptools import setup

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

version = os.environ.get("BUILD_VERSION")

if version is None:
    with open("VERSION", "r") as version_file:
        version = version_file.read().strip()

setup(
    name="relations-unum",
    version=version,
    package_dir = {'': 'lib'},
    py_modules = [
        'relations_unum'
    ],
    install_requires=[
        'relations-dil>=0.6.20',
        'relations-unifist>=0.1.0'
    ],
    url="https://github.com/relations-dil/python-relations-unum",
    author="Gaffer Fitch",
    author_email="relations@gaf3.com",
    description="Source for locally using multiple Unifist sources as a single Unum",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license_files=('LICENSE.txt',),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ]
)
