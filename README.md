# pinscrape
[![built with Python3](https://img.shields.io/badge/built%20with-Python3.x-red.svg)](https://www.python.org/)

### This package can be use to scrape images from pinterest just by using any search keywords. Install it just by using <br><br>
`pip install pinscrape`
### How to use?
```
from pinscrape import pinscrape
details = pinscrape.scraper.scrape("messi", "output", {}, 10)

if details["isDownloaded"]:
    print("\nDownloading completed !!")
    print(f"\nTotal urls found: {len(details['extracted_urls'])}")
    print(f"\nTotal images downloaded (including duplicate images): {len(details['url_list'])}")
    print(details)
else:
    print("\nNothing to download !!")
```

`scrape("messi", "output", {}, 10)` <br/>
- `"messi"` is keyword
- `"output"` is path to a folder where you want to save images
- `{}` is proxy if you want to add
- `10` is a number of threads you want to use for downloading those images
