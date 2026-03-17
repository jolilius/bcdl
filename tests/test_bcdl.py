import csv
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

import bcdl


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

ITEM_A = {
    "band_name": "Artist One",
    "album_title": "Album One",
    "item_url": "https://artistone.bandcamp.com/album/album-one",
    "tralbum_type": "a",
}
ITEM_B = {
    "band_name": "Artist Two",
    "item_title": "Track Two",
    "tralbum_url": "https://artisttwo.bandcamp.com/track/track-two",
    "tralbum_type": "t",
}
ITEM_NO_URL = {
    "band_name": "Ghost Artist",
    "album_title": "Phantom Album",
}


def _make_page_html(fan_id: int, items: dict, last_token: str | None) -> str:
    blob = {
        "fan_data": {"fan_id": fan_id},
        "collection_data": {
            "last_token": last_token,
            "item_count": len(items),
        },
        "item_cache": {"collection": items},
    }
    return f'<div id="pagedata" data-blob=\'{json.dumps(blob)}\'></div>'


def _mock_get(html: str):
    resp = MagicMock()
    resp.status_code = 200
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp


def _mock_post(items: list, more_available: bool = False, last_token: str | None = None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "items": items,
        "more_available": more_available,
        "last_token": last_token,
    }
    return resp


# ---------------------------------------------------------------------------
# get_page_data
# ---------------------------------------------------------------------------

class TestGetPageData:
    def test_returns_parsed_blob(self):
        html = _make_page_html(42, {"k": ITEM_A}, None)
        with patch("requests.get", return_value=_mock_get(html)):
            data = bcdl.get_page_data("testuser")
        assert data["fan_data"]["fan_id"] == 42

    def test_raises_on_missing_pagedata(self):
        resp = _mock_get("<html><body>nothing</body></html>")
        with patch("requests.get", return_value=resp):
            with pytest.raises(ValueError, match="testuser"):
                bcdl.get_page_data("testuser")

    def test_raises_on_http_error(self):
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("404")
        with patch("requests.get", return_value=resp):
            with pytest.raises(requests.HTTPError):
                bcdl.get_page_data("testuser")


# ---------------------------------------------------------------------------
# get_all_collection_items
# ---------------------------------------------------------------------------

class TestGetAllCollectionItems:
    def test_single_page_no_pagination(self):
        html = _make_page_html(1, {"a": ITEM_A, "b": ITEM_B}, last_token=None)
        with patch("requests.get", return_value=_mock_get(html)):
            items = bcdl.get_all_collection_items("testuser")
        assert len(items) == 2

    def test_pagination_fetches_all_items(self):
        html = _make_page_html(1, {"a": ITEM_A}, last_token="token1")
        page2 = _mock_post([ITEM_B], more_available=False)

        with patch("requests.get", return_value=_mock_get(html)):
            with patch("requests.post", return_value=page2) as mock_post:
                items = bcdl.get_all_collection_items("testuser")

        assert len(items) == 2
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert payload["fan_id"] == 1
        assert payload["older_than_token"] == "token1"

    def test_pagination_stops_when_no_more(self):
        html = _make_page_html(1, {"a": ITEM_A}, last_token="token1")
        page2 = _mock_post([ITEM_B], more_available=True, last_token="token2")
        page3 = _mock_post([], more_available=False)

        with patch("requests.get", return_value=_mock_get(html)):
            with patch("requests.post", side_effect=[page2, page3]):
                items = bcdl.get_all_collection_items("testuser")

        assert len(items) == 2  # empty batch stops pagination


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------

class TestExportCsv:
    def test_writes_correct_rows(self, tmp_path):
        out = tmp_path / "collection.csv"
        bcdl.export_csv([ITEM_A, ITEM_B], str(out))

        rows = list(csv.DictReader(out.open()))
        assert len(rows) == 2

        assert rows[0]["artist"] == "Artist One"
        assert rows[0]["title"] == "Album One"
        assert rows[0]["url"] == ITEM_A["item_url"]
        assert rows[0]["item_type"] == "a"

        # ITEM_B uses item_title and tralbum_url
        assert rows[1]["title"] == "Track Two"
        assert rows[1]["url"] == ITEM_B["tralbum_url"]

    def test_missing_url_writes_empty_string(self, tmp_path):
        out = tmp_path / "collection.csv"
        bcdl.export_csv([ITEM_NO_URL], str(out))
        rows = list(csv.DictReader(out.open()))
        assert rows[0]["url"] == ""

    def test_creates_header_row(self, tmp_path):
        out = tmp_path / "collection.csv"
        bcdl.export_csv([], str(out))
        header = out.read_text().strip()
        assert header == "artist,title,url,item_type"


# ---------------------------------------------------------------------------
# download_item
# ---------------------------------------------------------------------------

class TestDownloadItem:
    def test_calls_yt_dlp_with_url(self):
        proc = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=proc) as mock_run:
            result = bcdl.download_item(ITEM_A, 1, 3)
        assert result is True
        cmd = mock_run.call_args.args[0]
        assert "yt-dlp" in cmd
        assert ITEM_A["item_url"] in cmd

    def test_passes_cookies_flag(self):
        proc = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=proc) as mock_run:
            bcdl.download_item(ITEM_A, 1, 3, cookies_file="cookies.txt")
        cmd = mock_run.call_args.args[0]
        assert "--cookies" in cmd
        assert "cookies.txt" in cmd

    def test_returns_false_on_yt_dlp_failure(self):
        proc = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=proc):
            result = bcdl.download_item(ITEM_A, 1, 3)
        assert result is False

    def test_skips_item_without_url(self):
        with patch("subprocess.run") as mock_run:
            result = bcdl.download_item(ITEM_NO_URL, 1, 3)
        assert result is False
        mock_run.assert_not_called()

    def test_uses_tralbum_url_fallback(self):
        proc = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=proc) as mock_run:
            bcdl.download_item(ITEM_B, 1, 3)
        cmd = mock_run.call_args.args[0]
        assert ITEM_B["tralbum_url"] in cmd
