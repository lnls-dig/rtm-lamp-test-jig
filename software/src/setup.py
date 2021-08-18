#!/usr/bin/env python3

import os
from setuptools import setup, Extension

cdce906_mod = Extension("libcdce906", sources = ["cdce906_cfg.c"])

setup(
    name = "rtm-lamp-test",
    version = "0.0.1",
    author = "Augusto Fraga Giachero",
    author_email = "afg@augustofg.net",
    description = ("Utilities to test and configure RTM-LAMP boards."),
    license = "GPLv3",
    keywords = "rtm-lamp test jig",
    url = "https://github.com/lnls-dig/rtm-lamp-test-jig",
    packages = ["rtm_lamp_libs"],
    entry_points = {
        'console_scripts': [
            'rtm-lamp-test=rtm_lamp_libs.rtm_lamp_test:main',
        ],
    },
    long_description = "Utilities to test and configure RTM-LAMP boards.",
    install_requires = ["smbus2"],
    ext_modules = [cdce906_mod],
    platforms = ["Linux"],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: GPLv3 License"
    ],
)
