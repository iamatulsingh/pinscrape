# pinscrape
[![built with Python](https://img.shields.io/badge/built%20with-Python3.6+-red.svg)](https://www.python.org/)



### This package can be use to scrape images from pinterest just by using any search keywords. Install it just by using <br><br>
`pip install pinscrape`
### How do you run it?
```python
python pinscrape.py
```
### Config

Line 153:
```python
`scrape("pfp", "output", {}, 10)` <br/>
```

```diff
+ `"pfp"` is keyword
+ `"output"` is path to a folder where you want to save images
+ `{}` is proxy list if you want to add one (optional)
+ `10` is a number of threads you want to use for downloading those images (optional)
+ `15` is the maximum number of images you want to download (optional)
```
