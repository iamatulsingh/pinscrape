from pinscrape import scraper, Pinterest


keyword = "messi"
output_folder = "output"
proxies = {}
number_of_workers = 10
images_to_download = 1


def test_single_data():
    details = scraper.scrape(keyword, output_folder, proxies, number_of_workers, images_to_download)
    if details["isDownloaded"]:
        print("\nDownloading completed !!")
        print(f"\nTotal urls found: {len(details['extracted_urls'])}")
        print(f"\nTotal images downloaded (including duplicate images): {len(details['urls_list'])}")
        print(details)
    else:
        print("\nNothing to download !!", details)

    assert len(details['extracted_urls']) > 0

def test_v2():
    p = Pinterest()
    images_url = p.search(keyword, images_to_download)
    p.download(url_list=images_url, number_of_workers=number_of_workers, output_folder=output_folder)
    assert len(images_url) == images_to_download
