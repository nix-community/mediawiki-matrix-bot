#!/usr/bin/env python3

import sys

from setuptools import find_packages, setup

setup(
    name="mediawiki-matrix-bot",
    version="1.0.0",
    description="Matrix bot that publishes mediawiki recent changes",
    author="makefu",
    author_email="github@syntax-fehler.de",
    url="https://github.com/https://github.com/nix-community/mediawiki-matrix-bot",
    license="MIT",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "mediawiki-matrix-bot = mediawiki_matrix_bot:main",
        ]
    },
    extras_require={"dev": ["mypy"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Topic :: Utilities",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.6",
    ],
)
