"""Setup script for makebwpdf"""

import os.path
from setuptools import setup

cwd = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(cwd, "README.adoc")) as fh:
    long_desc = fh.read()

setup(
    name="makebwpdf",
    version="1.0.0",
    author="Pontus Lurcock",
    author_email="pont@talvi.net",
    description="Convert image files to bilevel PDFs.",
    long_description=long_desc,
    long_description_content_type="text/asciidoc",
    url="https://github.com/pont-us/makebwpdf",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    packages=["makebwpdf"],
    entry_points={"console_scripts":
                  ["makebwpdf=makebwpdf.makebwpdf:main"],
                  },
)
