#api_client.py start file

import requests
import time
from typing import Dict, List, Optional

class FourChanAPIClient:
    """Handles all 4chan API requests with rate limiting."""

    BASE_URL = "https://a.4cdn.org"

    def __init__(self, rate_limit_seconds: float = 1.0):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': '4chan Tracker/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        self.last_request_time = 0
        self.rate_limit = rate_limit_seconds
        self._cache_headers: Dict[str, Dict[str, str]] = {}

    def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)

    def get_catalog(self, board: str) -> List[Dict]:
        """Get catalog.json for a board."""
        self._rate_limit()
        url = f"{self.BASE_URL}/{board}/catalog.json"
        request_headers = {}
        cached = self._cache_headers.get(url, {})
        if cached.get('etag'):
            request_headers['If-None-Match'] = cached['etag']
        if cached.get('last_modified'):
            request_headers['If-Modified-Since'] = cached['last_modified']
        try:
            response = self.session.get(url, headers=request_headers, timeout=8)
            if response.status_code == 304:
                self.last_request_time = time.time()
                return []
            response.raise_for_status()
            self._cache_headers[url] = {
                'etag': response.headers.get('ETag', ''),
                'last_modified': response.headers.get('Last-Modified', '')
            }
            self.last_request_time = time.time()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get catalog for /{board}/: {e}")
            return []

    def get_threads(self, board: str) -> List[Dict]:
        """Get threads.json for a board."""
        self._rate_limit()
        url = f"{self.BASE_URL}/{board}/threads.json"
        request_headers = {}
        cached = self._cache_headers.get(url, {})
        if cached.get('etag'):
            request_headers['If-None-Match'] = cached['etag']
        if cached.get('last_modified'):
            request_headers['If-Modified-Since'] = cached['last_modified']
        try:
            response = self.session.get(url, headers=request_headers, timeout=8)
            if response.status_code == 304:
                self.last_request_time = time.time()
                return []
            response.raise_for_status()
            self._cache_headers[url] = {
                'etag': response.headers.get('ETag', ''),
                'last_modified': response.headers.get('Last-Modified', '')
            }
            self.last_request_time = time.time()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get threads for /{board}/: {e}")
            return []

    #end file
