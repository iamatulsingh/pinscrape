import setuptools
from pinscrape._version import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as req:
    reqs = req.read().split("\n")

setuptools.setup(
    name="pinscrape",
    version=__version__,
    author="Atul Singh",
    author_email="atulsingh0401@gmail.com",
    description="Pinterest | a simple data scraper for pinterest",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iamatulsingh/pinscrape",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=reqs,
)
