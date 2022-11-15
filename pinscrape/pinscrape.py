import re
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

    # ---------------------------------------- GET GOOGLE RESULTS ---------------------------------
    @staticmethod
    def get_pinterest_links(body, max_images):
        searched_urls = []
        html = soup(body, 'html.parser')
        links = html.select('#main > div > div > div > a')
        for link in links:
            link = link.get('href')
            link = re.sub(r'/url\?q=', '', link)
            if link[0] != "/" and "pinterest" in link:
                searched_urls.append(link)
                #stops adding links if the limit has been reached
                if max_images is not None and max_images == len(searched_urls):
                    break

        return searched_urls

    # -------------------------- save json data from source code of given pinterest url -------------
    def get_source(self, url, proxies):
        try:
            res = get(url, proxies=proxies)
        except Exception as e:
            return
        html = soup(res.text, 'html.parser')
        json_data = html.find_all("script", attrs={"id": "__PWS_DATA__"})
        for a in json_data:
            self.json_data_list.append(a.string)

    # --------------------------- READ JSON OF PINTEREST WEBSITE ----------------------
    def save_image_url(self, max_images):
        url_list = [i for i in self.json_data_list if i.strip()]
        if not len(url_list):
            return url_list
        url_list = []
        for js in self.json_data_list:
            try:
                data = DotMap(json.loads(js))
                urls = []
                for pin in data.props.initialReduxState.pins:
                    if isinstance(data.props.initialReduxState.pins[pin].images.get("orig"), list):
                        for i in data.props.initialReduxState.pins[pin].images.get("orig"):
                            urls.append(i.get("url"))
                    else:
                        urls.append(data.props.initialReduxState.pins[pin].images.get("orig").get("url"))

                for url in urls:
                    url_list.append(url)

                    #if the maximum has been achieved, return early
                    if max_images is not None and max_images == len(url_list):
                        return list(set(url_list))
                    

            except Exception as e:
                continue
        
        return list(set(url_list))

    # ------------------------------ image hash calculation -------------------------
    def dhash(self, image, hashSize=8):
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
    def start_scraping(max_images, key=None, proxies={}):
        assert key != None, "Please provide keyword for searching images"
        keyword = key + " pinterest"
        keyword = keyword.replace("+", "%20")
        url = f'http://www.google.co.in/search?hl=en&q={keyword}'
        res = get(url, proxies=proxies)
        searched_urls = PinterestImageScraper.get_pinterest_links(res.content,max_images)

        return searched_urls, key.replace(" ", "_")


    def scrape(self, key=None, output_folder="", proxies={}, threads=10, max_images: int = None):
        extracted_urls, keyword = PinterestImageScraper.start_scraping(max_images,key, proxies)

        for i in extracted_urls:
            self.get_source(i, proxies)

        # get all urls of images and save in a list
        url_list = self.save_image_url(max_images)
        return_data = {
            "isDownloaded": False,
            "url_list": url_list,
            "extracted_urls": extracted_urls,
            "keyword": key
        }

        # download images from saved images url
        if len(url_list):
            try:
                out_folder = output_folder if output_folder else key
                self.download(url_list, threads, out_folder)
            except KeyboardInterrupt:
                return return_data
            
            return_data["isDownloaded"] = True
            return return_data
        
        return return_data


scraper = PinterestImageScraper()

if __name__ == "__main__":
    details = scraper.scrape("messi", "output")

    if details["isDownloaded"]:
        print("\nDownloading completed !!")
    else:
        print("\nNothing to download !!")
