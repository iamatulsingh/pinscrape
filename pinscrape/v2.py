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
    def __init__(self, user_agent: str = "", proxies: dict = None, sleep_time: float = None):
        self.errors = []
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0" \
            if not user_agent else user_agent
        self.BASE_URL = "https://in.pinterest.com"
        self.BASE_HEADERS = {
            'Host': self.BASE_URL.replace('https://', ''),
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Ch-Ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-Ch-Ua-Model': '""',
            'Sec-Ch-Ua-Mobile': '?0',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*, q=0.01',
            'X-Pinterest-Source-Url': '',
            'X-Pinterest-Appstate': 'active',
            'Accept-Language': 'en-US,en;q=0.9',
            'Screen-Dpr': '1',
            'X-Pinterest-Pws-Handler': 'www/search/[scope].js',
            'User-Agent': self.user_agent,
            'Sec-Ch-Ua-Platform-Version': '""',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': f'{self.BASE_URL}/',
            'Priority': 'u=1, i',
        }
        self.data_dir = "data"
        self.client_context = {}
        self.unique_images = []
        self.proxies = proxies if proxies else {}
        self.sleep_time = sleep_time

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
        self.session = requests.Session()

    def update_time_epoch(self) -> None:
        self.time_epoch = self.get_current_epoch()
        self.save_file("time_epoch.json", {"time_epoch": self.time_epoch})
        logging.info(f"New time epoch saved")

    def save_file(self, file_name: str, content: dict) -> None:
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
        if not path.exists(path.join(self.data_dir, file_name)):
            return {}
        with open(path.join(self.data_dir, file_name), "r") as f:
            data = json.load(f)
            return data

    @staticmethod
    def image_hash(image: cv2.Mat, hash_size: int = 8) -> int:
        resized = cv2.resize(image, (hash_size + 1, hash_size))
        diff = resized[:, 1:] > resized[:, :-1]
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    def get_pin_details(self, username: str, board: str) -> dict:
        headers = self.BASE_HEADERS.copy()
        headers['x-pinterest-appstate'] = 'active'
        headers['x-pinterest-pws-handler'] = 'www/[username]/[slug].js'
        headers['x-pinterest-source-url'] = f'/{username}/{board}/'
        headers['x-requested-with'] = 'XMLHttpRequest'

        params = {
            'source_url': f'/{username}/{board}/',
            'data': '{"options":{"field_set_key":"profile","username":"' + username + '"},"context":{}}',
            '_': str(int(time.time() * 1000)),
        }

        response = self.session.get(f'{self.BASE_URL}/resource/UserResource/get/', params=params,
                                    headers=headers, proxies=self.proxies)
        if response.status_code == 200:
            return response.json()

        return dict()

    def saving_image(self, var: list) -> None:
        url_list, folder_name = var
        makedirs(path.join(getcwd(), folder_name), exist_ok=True)
        for img in url_list:
            result = self.session.get(img, stream=True, proxies=self.proxies).content
            file_name = img.split("/")[-1]
            file_path = path.join(getcwd(), folder_name, file_name)
            img_arr = np.asarray(bytearray(result), dtype="uint8")
            image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if not self.image_hash(image) in self.unique_images:
                cv2.imwrite(file_path, image)
            self.unique_images.append(self.image_hash(image))

            if self.sleep_time:
                time.sleep(self.sleep_time)

    def download(self, url_list: list, number_of_workers: int, output_folder: str) -> None:
        idx = len(url_list) // number_of_workers if len(url_list) > 9 else len(url_list)
        param = []
        for i in range(number_of_workers):
            param.append((url_list[(i * idx):(idx * (i + 1))], output_folder))
        with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
            executor.map(self.saving_image, param)

    @staticmethod
    def get_current_epoch() -> int:
        current_time_seconds = time.time()
        return int(current_time_seconds * 1000)

    def fetch_cookies(self) -> str:
        cookie_res = requests.request("GET", f"{self.BASE_URL}/ideas/", data={}, proxies=self.proxies)
        if cookie_res.status_code != 200:
            logging.error(f"Failed attempt to get Cookies. Status code for cookie is {cookie_res.status_code}")
            exit()
        cookies = cookie_res.cookies
        cookie_header = '; '.join([f"{name}={value}" for name, value in cookies.items()])
        logging.info("Saving cookies")
        self.save_file("cookies.json", {"cookies": cookie_header})
        return cookie_header

    def search(self, query: str, page_size=26) -> list:
        source_url = f"/search/pins/?q={quote(query)}&rs=typed"
        _ = self.session.get(f"{self.BASE_URL}{source_url}")
        data = quote_plus(json.dumps({"options":
                                          {"applied_unified_filters": None, "appliedProductFilters": "---",
                                           "article": None,
                                           "auto_correction_disabled": False, "corpus": None,
                                           "customized_rerank_type": None,
                                           "domains": None, "filters": None, "journey_depth": None,
                                           "page_size": f"{page_size}", "price_max": None,
                                           "price_min": None, "query_pin_sigs": None, "query": quote(query),
                                           "redux_normalize_feed": True,
                                           "request_params": None, "rs": "typed", "scope": "pins",
                                           "selected_one_bar_modules": None,
                                           "source_id": None, "source_module_id": None, "seoDrawerEnabled": False,
                                           "source_url": quote_plus(source_url), "top_pin_id": None,
                                           "top_pin_ids": None},
                                      "context": {}}).replace(" ", ""))

        data = data.replace("%2520", "%20").replace("%252F", "%2F").replace("%253F", "%3F") \
            .replace("%252520", "%2520").replace("%253D", "%3D").replace("%2526", "%26")

        ts = self.time_epoch
        url = (f"{self.BASE_URL}/resource/BaseSearchResource/get/?source_url={quote_plus(source_url)}"
               f"&data={data}&_={ts}")
        payload = {}
        headers = self.BASE_HEADERS
        headers['X-Pinterest-Source-Url'] = source_url
        response = self.session.get(url, headers=headers, data=payload, proxies=self.proxies)

        if self.sleep_time:
            time.sleep(self.sleep_time)

        image_urls = []
        if response.status_code != 200:
            logging.warning(f"Image search has failed!, {response.status_code}, {response.text}")
            self.errors.append(f"Image search has failed!, {response.status_code}, {response.text}")
            return []
        try:
            json_data = response.json()
            results = json_data.get('resource_response', {}).get('data', {}).get('results', [])
            for result in results:
                image_urls.append(result['images']['orig']['url'])
            self.client_context = json_data['client_context']
            logging.info(f"Total {len(image_urls)} image(s) found.")
            return image_urls
        except requests.exceptions.JSONDecodeError as jde:
            self.errors.append(jde.args)
            return []


if __name__ == "__main__":
    download_limit = 1
    keyword = "loki"
    p = Pinterest(sleep_time=2)
    images_url = p.search(keyword, download_limit)
    p.download(url_list=images_url, number_of_workers=1, output_folder="output")
    board_details = p.get_pin_details(username='canva', board='design-trends')
    print(board_details)
    print(board_details.get('resource_response', {}).get('data', {}).get('created_at'))
