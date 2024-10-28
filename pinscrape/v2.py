import requests
import json
import time
import cv2
import numpy as np
import logging

from urllib.parse import quote_plus, quote
from concurrent.futures import ThreadPoolExecutor
from os import path, makedirs, getcwd


class Pinterest:
    def __init__(self, user_agent: str = "", proxies: dict = None):
        self.errors = []
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.71 Safari/537.36" \
                        if not user_agent else user_agent
        self.BASE_URL = "https://www.pinterest.com"
        self.BASE_HEADERS = {
            'Host': 'www.pinterest.com',
            'Sec-Ch-Ua': '"Chromium";v="129", "Not=A?Brand";v="8"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br',
            'Priority': 'u=0, i',
            'Connection': 'keep-alive',
        }
        self.data_dir = "data"
        self.client_context = {}
        self.unique_images = []
        self.cookies = self.read_file("cookies.json").get("cookies", "")
        self.proxies = proxies if proxies else {}

        if not self.cookies:
            self.cookies = self.fetch_cookies()
        else:
            logging.debug("Using saved cookies")

        self.time_epoch = self.read_file("time_epoch.json").get('time_epoch', '')
        if not self.time_epoch:
            self.time_epoch = self.get_current_epoch()
            self.save_file("time_epoch.json", {"time_epoch": self.time_epoch})
            logging.info(f"New time epoch saved")
        else:
            current_epoch = self.get_current_epoch()
            if float(self.time_epoch) < current_epoch:
                self.update_time_epoch()
            else:
                logging.info(f"Using saved time epoch")

    def update_time_epoch(self) -> None:
        """
        update_time_epoch will update current time epoch
        :return: None
        """
        self.time_epoch = self.get_current_epoch()
        self.save_file("time_epoch.json", {"time_epoch": self.time_epoch})
        logging.info(f"New time epoch saved")

    def save_file(self, file_name: str, content: dict) -> None:
        """
        save_file will save file with dict/list as content
        :param file_name: file name that will be used to save a file
        :param content: content should be dict/list
        :return: None
        """
        makedirs(self.data_dir, exist_ok=True)
        if path.exists(path.join(self.data_dir, file_name)):
            with open(path.join(self.data_dir, file_name), "r") as f:
                data = json.load(f)
                for key in list(content.keys()):
                    data[key] = content[key]
        else:
            data = content

        with open(path.join(self.data_dir, file_name), "w") as f:
            json.dump(data, f)

    def read_file(self, file_name: str) -> dict:
        """
        read_file will read file and return its content.
        :param file_name: file that needs to be read
        :return: dict content of the file
        """
        if not path.exists(path.join(self.data_dir, file_name)):
            return {}

        with open(path.join(self.data_dir, file_name), "r") as f:
            data = json.load(f)
            return data

    @staticmethod
    def image_hash(image: cv2.Mat, hash_size: int = 8) -> int:
        """
        image_hash will return the hash of an image
        :param image: multi-dimension array of image data
        :param hash_size: image hash size
        :return: integer hash value representing the differences between adjacent pixels
        """
        resized = cv2.resize(image, (hash_size + 1, hash_size))
        diff = resized[:, 1:] > resized[:, :-1]
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    def saving_image(self, var: list) -> None:
        """
        saving_image downloads and save image(s) on the disk
        :param var: list of params passed through thread
        :return: None
        """
        url_list, folder_name = var
        makedirs(path.join(getcwd(), folder_name), exist_ok=True)
        for img in url_list:
            result = requests.request("GET", img, stream=True, proxies=self.proxies).content
            file_name = img.split("/")[-1]
            file_path = path.join(getcwd(), folder_name, file_name)
            img_arr = np.asarray(bytearray(result), dtype="uint8")
            image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if not self.image_hash(image) in self.unique_images:
                cv2.imwrite(file_path, image)
            self.unique_images.append(self.image_hash(image))

    def download(self, url_list: list, number_of_workers: int, output_folder: str) -> None:
        """
        download create number of workers to initiate download
        :param url_list: list of urls
        :param number_of_workers: number of workers you want to use
        :param output_folder: output folder name to which all files will be saved
        :return: None
        """
        idx = len(url_list) // number_of_workers if len(url_list) > 9 else len(url_list)
        param = []
        for i in range(number_of_workers):
            param.append((url_list[(i * idx):(idx * (i + 1))], output_folder))
        with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
            executor.map(self.saving_image, param)

    @staticmethod
    def get_current_epoch() -> int:
        """
        get_current_epoch will set current time epoch
        :return: time epoch integer
        """
        current_time_seconds = time.time()
        return int(current_time_seconds * 1000)

    def fetch_cookies(self) -> str:
        """
        fetch_cookies will get the fresh cookies
        :return: cookie string
        """
        cookie_res = requests.request("GET", f"{self.BASE_URL}/ideas/", data={}, proxies=self.proxies)
        if cookie_res.status_code != 200:
            logging.error(f"Failed attempt to get Cookies. Status code for cookie is {cookie_res.status_code}")
            exit()

        # Extract cookies from the response
        cookies = cookie_res.cookies

        # Format cookies for the Cookie header
        cookie_header = '; '.join([f"{name}={value}" for name, value in cookies.items()])

        logging.info("Saving cookies")
        self.save_file("cookies.json", {"cookies": cookie_header})
        return cookie_header

    def search(self, query: str, page_size=26) -> list:
        """
        search query about the keyword on pinterest
        :param query: keyword that will be searched on pinterest
        :param page_size: total number of images to get (try to avoid big numbers here).
        :return: list of image urls
        """
        source_url = f"/search/pins/?q={quote(query)}&rs=typed"
        data = quote_plus(json.dumps({"options":
                    {"applied_unified_filters": None, "appliedProductFilters": "---" , "article": None,
                     "auto_correction_disabled": False, "corpus": None, "customized_rerank_type": None,
                     "domains":None, "filters": None, "journey_depth": None, "page_size": f"{page_size}", "price_max": None,
                     "price_min": None, "query_pin_sigs": None,"query": quote(query), "redux_normalize_feed": True,
                     "request_params": None, "rs": "typed", "scope": "pins", "selected_one_bar_modules": None,
                     "source_id": None, "source_module_id": None,
                     "source_url": quote_plus(source_url), "top_pin_id": None, "top_pin_ids": None},
                "context":{}}).replace(" ", ""))

        data = data.replace("%2520", "%20").replace("%252F", "%2F").replace("%253F", "%3F")\
            .replace("%252520", "%2520").replace("%253D", "%3D").replace("%2526", "%26")

        ts = self.time_epoch
        url = (f"{self.BASE_URL}/resource/BaseSearchResource/get/?source_url={quote_plus(source_url)}"
               f"&data={data}&_={ts}")
        payload = {}
        headers = self.BASE_HEADERS
        headers['Cookies'] = self.cookies
        response = requests.request("GET", url, headers=headers, data=payload, proxies=self.proxies)
        image_urls = []
        if response.status_code != 200:
            logging.warning(f"Image search has failed!, {response.status_code}, {response.text}")
            self.errors.append(f"Image search has failed!, {response.status_code}, {response.text}")
            return []

        msg = f"Response Headers: {response.headers}"
        msg += f"Response Content-Type: {response.headers.get('Content-Type')}"
        msg += f"Response: {response.text}"
        msg += f"Status Code: {response.headers}"

        try:
            json_data = response.json()
            results = json_data.get('resource_response', {}).get('data', {}).get('results', [])
            for result in results:
                image_urls.append(result['images']['orig']['url'])
            self.client_context = json_data['client_context']
            logging.info(f"Total {len(image_urls)} image(s) found.")
            return image_urls
        except requests.exceptions.JSONDecodeError:
            self.errors.append(msg)
            return []


if __name__ == "__main__":
    download_limit = 26
    keyword = "loki"
    p = Pinterest()
    images_url = p.search(keyword, download_limit)
    p.download(url_list=images_url, number_of_workers=1, output_folder="output")
