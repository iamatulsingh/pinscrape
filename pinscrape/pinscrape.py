import json
import os
import cv2
import numpy as np

from requests import get
from bs4 import BeautifulSoup as soup
from concurrent.futures import ThreadPoolExecutor

from pydotmap import DotMap


class PinterestImageScraper:

    def __init__(self):
        self.json_data_list = []
        self.unique_img = []
        self.error_stack = []

    # ---------------------------------------- GET GOOGLE RESULTS ---------------------------------
    @staticmethod
    def get_pinterest_links(body):
        searched_urls = []
        html = soup(body, 'html.parser')
        all_urls = []
        links = html.select('#b_results cite')
        for link in links:
            link = link.text
            all_urls.append(link.replace(' › ', '/'))
            if "pinterest" in link and not "ideas" in link:
                searched_urls.append(link.replace(' › ', '/'))

        return searched_urls, all_urls

    # -------------------------- save json data from source code of given pinterest url -------------
    def get_source(self, urls: list, proxies: dict, max_images: int) -> None:
        counter = 1
        for extracted_url in urls:
            try:
                res = get(extracted_url, proxies=proxies)
            except Exception as e:
                self.error_stack.append(e.args)
                continue
            html = soup(res.text, 'html.parser')
            json_data = html.find_all("script", attrs={"id": "__PWS_INITIAL_PROPS__"})
            if not len(json_data):
                json_data = html.find_all("script", attrs={"id": "__PWS_DATA__"})

            self.json_data_list.append(json.loads(json_data[0].string)) if len(json_data) else self.json_data_list.append({})
            # stops adding links if the limit has been reached
            if max_images is not None and max_images == counter:
                break

            counter += 1

    # --------------------------- READ JSON OF PINTEREST WEBSITE ----------------------
    def save_image_url(self, max_images: int) -> list:
        url_list = []
        for js in self.json_data_list:
            try:
                data = DotMap(js)
                urls = []
                if not data.initialReduxState and not data.props:
                    return []
                pins = data.initialReduxState.pins if data.initialReduxState else data.props.initialReduxState.pins
                for pin in pins:
                    if isinstance(pins[pin].images.get("orig"), list):
                        for i in pins[pin].images.get("orig"):
                            urls.append(i.get("url"))
                    else:
                        urls.append(pins[pin].images.get("orig").get("url"))

                for url in urls:
                    url_list.append(url)
                    if max_images is not None and max_images == len(url_list):
                        return list(set(url_list))
            except Exception as e:
                self.error_stack.append(e.args)
                continue

        return list(set(url_list))

    # ------------------------------ image hash calculation -------------------------
    def dhash(self, image, hashSize: int = 8):
        resized = cv2.resize(image, (hashSize + 1, hashSize))
        diff = resized[:, 1:] > resized[:, :-1]
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    # ------------------------------  save all downloaded images to folder ---------------------------
    def saving_op(self, var):
        url_list, folder_name = var
        if not os.path.exists(os.path.join(os.getcwd(), folder_name)):
                os.mkdir(os.path.join(os.getcwd(), folder_name))
        for img in url_list:
            result = get(img, stream=True).content
            file_name = img.split("/")[-1]
            file_path = os.path.join(os.getcwd(), folder_name, file_name)
            img_arr = np.asarray(bytearray(result), dtype="uint8")
            image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if not self.dhash(image) in self.unique_img:
                cv2.imwrite(file_path, image)
            self.unique_img.append(self.dhash(image))

    # ------------------------------  download images from image url list ----------------------------
    def download(self, url_list, num_of_workers, output_folder):
        idx = len(url_list) // num_of_workers if len(url_list) > 9 else len(url_list)
        param = []
        for i in range(num_of_workers):
            param.append((url_list[((i*idx)):(idx*(i+1))], output_folder))
        with ThreadPoolExecutor(max_workers=num_of_workers) as executor:
            executor.map(self.saving_op, param)

    # -------------------------- get user keyword and google search for that keywords ---------------------
    @staticmethod
    def start_scraping(max_images, key=None, proxies: dict = {}):
        assert key is not None, "Please provide keyword for searching images"
        keyword = key + " pinterest"
        keyword = keyword.replace("+", "%20")
        url = f'https://www.bing.com/search?q={keyword}&first=1&FORM=PERE'
        res = get(url, proxies=proxies, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"})
        searched_urls, links = PinterestImageScraper.get_pinterest_links(res.content)

        return searched_urls, key.replace(" ", "_"), res.status_code, links

    def scrape(self, key: str = None, output_folder: str = "", proxies: dict = {}, threads: int = 10, max_images: int = None) -> dict:
        extracted_urls, keyword, search_engine_status_code, links = PinterestImageScraper.start_scraping(max_images, key, proxies)
        self.unique_img = []
        self.json_data_list = []

        # for i in extracted_urls:
        self.get_source(extracted_urls, proxies, max_images)

        # get all urls of images and save in a list
        urls_list = self.save_image_url(max_images)

        return_data = {
            "isDownloaded": False,
            "search_engine_status_code": search_engine_status_code,
            "urls_list": urls_list,
            "searched_urls": links,
            "extracted_urls": extracted_urls,
            "keyword": key,
            "error_stack": self.error_stack,
        }

        # download images from saved images url
        if len(urls_list):
            try:
                out_folder = output_folder if output_folder else key
                self.download(urls_list, threads, out_folder)
            except KeyboardInterrupt:
                return return_data

            return_data["isDownloaded"] = True
            return return_data

        return return_data


scraper = PinterestImageScraper()


if __name__ == "__main__":
    details = scraper.scrape("messi", "output", {}, 10, None)

    if details["isDownloaded"]:
        print("\nDownloading completed !!")
    else:
        print("\nNothing to download !!")
