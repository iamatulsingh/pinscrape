from pinscrape import pinscrape
details = pinscrape.scraper.scrape("messi", "output", {}, 10)

if details["isDownloaded"]:
    print("\nDownloading completed !!")
    print(details)
else:
    print("\nNothing to download !!")
