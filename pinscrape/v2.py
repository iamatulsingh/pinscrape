import json
import time
import logging
import requests
import cv2
import numpy as np
from pathlib import Path
from urllib.parse import quote, quote_plus
from concurrent.futures import ThreadPoolExecutor

from .models import SearchResponse, BoardResponse
from .utils import image_hash, ensure_dir, current_epoch_ms


class Pinterest:
    BASE_URL = "https://in.pinterest.com"

    def __init__(self, user_agent: str = "", proxies: dict = None, sleep_time: float = None):
        self.errors = []
        self.sleep_time = sleep_time
        self.proxies = proxies or {}
        self.unique_images = []

        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
        )

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

        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

        self.time_epoch = self._load_epoch()
        self.session = requests.Session()

    # -----------------------------
    # Epoch persistence
    # -----------------------------

    def _load_epoch(self) -> int:
        file = self.data_dir / "time_epoch.json"
        if file.exists():
            data = json.loads(file.read_text())
            saved = data.get("time_epoch")
            if saved:
                if float(saved) < current_epoch_ms():
                    return self._save_epoch()
                return int(saved)
        return self._save_epoch()

    def _save_epoch(self) -> int:
        epoch = current_epoch_ms()
        (self.data_dir / "time_epoch.json").write_text(json.dumps({"time_epoch": epoch}))
        return epoch

    # -----------------------------
    # Pinterest API calls
    # -----------------------------

    def search(self, query: str, page_size=26):
        source_url = f"/search/pins/?q={quote(query)}&rs=typed"

        # Warm-up request (critical)
        self.session.get(f"{self.BASE_URL}{source_url}", headers=self.BASE_HEADERS)

        payload = {
            "options": {
                "applied_unified_filters": None,
                "appliedProductFilters": "---",
                "article": None,
                "auto_correction_disabled": False,
                "corpus": None,
                "customized_rerank_type": None,
                "domains": None,
                "filters": None,
                "journey_depth": None,
                "page_size": f"{page_size}",
                "price_max": None,
                "price_min": None,
                "query_pin_sigs": None,
                "query": quote(query),
                "redux_normalize_feed": True,
                "request_params": None,
                "rs": "typed",
                "scope": "pins",
                "selected_one_bar_modules": None,
                "source_id": None,
                "source_module_id": None,
                "seoDrawerEnabled": False,
                "source_url": quote_plus(source_url),
                "top_pin_id": None,
                "top_pin_ids": None
            },
            "context": {}
        }

        encoded = quote_plus(json.dumps(payload).replace(" ", ""))
        encoded = (
            encoded.replace("%2520", "%20")
            .replace("%252F", "%2F")
            .replace("%253F", "%3F")
            .replace("%252520", "%2520")
            .replace("%253D", "%3D")
            .replace("%2526", "%26")
        )

        url = (
            f"{self.BASE_URL}/resource/BaseSearchResource/get/"
            f"?source_url={quote_plus(source_url)}&data={encoded}&_={self.time_epoch}"
        )

        headers = self.BASE_HEADERS.copy()
        headers["X-Pinterest-Source-Url"] = source_url

        response = self.session.get(url, headers=headers, proxies=self.proxies)

        if self.sleep_time:
            time.sleep(self.sleep_time)

        if response.status_code != 200:
            logging.warning(f"Image search failed: {response.status_code}")
            return []

        data = SearchResponse(**response.json())
        results = data.resource_response.data.results
        return [r.images["orig"].url for r in results]

    def get_pin_details(self, username: str, board: str):
        headers = self.BASE_HEADERS.copy()
        headers['x-pinterest-appstate'] = 'active'
        headers['x-pinterest-pws-handler'] = 'www/[username]/[slug].js'
        headers['x-pinterest-source-url'] = f'/{username}/{board}/'
        headers['x-requested-with'] = 'XMLHttpRequest'

        params = {
            'source_url': f'/{username}/{board}/',
            'data': json.dumps({"options": {"field_set_key": "profile", "username": username}, "context": {}}),
            '_': str(current_epoch_ms()),
        }

        response = self.session.get(
            f'{self.BASE_URL}/resource/UserResource/get/',
            params=params,
            headers=headers,
            proxies=self.proxies
        )

        if response.status_code != 200:
            return None

        data = BoardResponse(**response.json())
        return data.resource_response.data.created_at

    # -----------------------------
    # Image downloading
    # -----------------------------

    def _save_image(self, url: str, folder: Path):
        try:
            # Pinterest requires headers for image downloads
            headers = {
                "User-Agent": self.user_agent,
                "Referer": "https://www.pinterest.com/",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            }

            response = self.session.get(url, headers=headers, proxies=self.proxies)
            if response.status_code != 200:
                logging.warning(f"Failed to download image: {url} ({response.status_code})")
                return

            img_arr = np.frombuffer(response.content, dtype=np.uint8)
            image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

            if image is None:
                logging.warning(f"cv2 failed to decode image: {url}")
                return

            h = image_hash(image)
            if h in self.unique_images:
                return

            url_str = str(url)
            filename = folder / url_str.split("/")[-1]
            cv2.imwrite(str(filename), image)
            self.unique_images.append(h)

            if self.sleep_time:
                time.sleep(self.sleep_time)

        except Exception as e:
            logging.error(f"Error saving image {url}: {e}")

    def download(self, url_list: list, number_of_workers: int, output_folder: str):
        folder = ensure_dir(output_folder)
        with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
            executor.map(lambda u: self._save_image(u, folder), url_list)


if __name__ == "__main__":
    download_limit = 1
    keyword = "loki"

    p = Pinterest(sleep_time=2)

    print(f"\nSearching for: {keyword}")
    images_url = p.search(keyword, download_limit)
    print(f"Found {len(images_url)} image(s). Downloading…")

    p.download(url_list=images_url, number_of_workers=1, output_folder="output")

    print("\nFetching board details…")
    created_at = p.get_pin_details(username="canva", board="design-trends")
    print(f"Board created_at: {created_at}")
