from pinscrape import pinscrape
is_downloaded = pinscrape.scraper.scrape("messi", "output", {}, 10)

if is_downloaded:
    print("\nDownloading completed !!")
else:
    print("\nNothing to download !!")
