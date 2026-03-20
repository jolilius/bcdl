import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

import bcdl

ITEM_C_WITH_ID = {
    "band_name": "Artist Three",
    "album_title": "Album Three",
    "item_url": "https://artistthree.bandcamp.com/album/album-three",
    "tralbum_type": "a",
    "sale_item_id": 33333333,
}


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

ITEM_A_WITH_ID = {
    "band_name": "Artist One",
    "album_title": "Album One",
    "item_url": "https://artistone.bandcamp.com/album/album-one",
    "tralbum_type": "a",
    "sale_item_id": 11111111,
}
ITEM_B_WITH_ID = {
    "band_name": "Artist Two",
    "item_title": "Track Two",
    "tralbum_url": "https://artisttwo.bandcamp.com/track/track-two",
    "tralbum_type": "t",
    "sale_item_id": 22222222,
}
ITEM_NO_SALE_ID = {
    "band_name": "Mystery Artist",
    "album_title": "No ID Album",
    "item_url": "https://mystery.bandcamp.com/album/no-id",
    "tralbum_type": "a",
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
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc) as mock_run:
            result = bcdl.download_item(ITEM_A, 1, 3)
        assert result is True
        cmd = mock_run.call_args.args[0]
        assert "yt-dlp" in cmd
        assert ITEM_A["item_url"] in cmd

    def test_passes_cookies_flag(self):
        proc = MagicMock(returncode=0)
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc) as mock_run:
            bcdl.download_item(ITEM_A, 1, 3, cookies_file="cookies.txt")
        cmd = mock_run.call_args.args[0]
        assert "--cookies" in cmd
        assert "cookies.txt" in cmd

    def test_returns_false_on_yt_dlp_failure(self):
        proc = MagicMock(returncode=1)
        proc.stderr = ""
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
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc) as mock_run:
            bcdl.download_item(ITEM_B, 1, 3)
        cmd = mock_run.call_args.args[0]
        assert ITEM_B["tralbum_url"] in cmd


# ---------------------------------------------------------------------------
# yt-dlp detection
# ---------------------------------------------------------------------------

class TestYtdlpDetection:
    def test_ytdlp_not_installed(self, capsys):
        with patch("shutil.which", return_value=None):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with pytest.raises(SystemExit) as exc:
                    bcdl.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Error: yt-dlp is not installed. Install it with: pip install yt-dlp" in captured.err

    def test_ytdlp_check_before_network(self, capsys):
        with patch("shutil.which", return_value=None):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("requests.get") as mock_get:
                    with pytest.raises(SystemExit):
                        bcdl.main()
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# load_state
# ---------------------------------------------------------------------------

class TestLoadState:
    def test_load_state_missing_file(self, tmp_path):
        result = bcdl.load_state(tmp_path / "nonexistent.json")
        assert result == {}

    def test_load_state_corrupt_json(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state_file.write_text("not json", encoding="utf-8")
        result = bcdl.load_state(state_file)
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_load_state_valid(self, tmp_path):
        state_file = tmp_path / "state.json"
        data = {"12345": {"artist": "Burial", "title": "Untrue"}}
        state_file.write_text(json.dumps(data), encoding="utf-8")
        result = bcdl.load_state(state_file)
        assert result == data


# ---------------------------------------------------------------------------
# save_state
# ---------------------------------------------------------------------------

class TestSaveState:
    def test_save_state_creates_file(self, tmp_path):
        state_file = tmp_path / "state.json"
        data = {"99999": {"artist": "Test", "title": "Album"}}
        bcdl.save_state(data, state_file)
        assert state_file.exists()
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        assert loaded == data

    def test_save_state_creates_parent_dir(self, tmp_path):
        state_file = tmp_path / "nested" / "subdir" / "state.json"
        data = {"1": {"artist": "A", "title": "B"}}
        bcdl.save_state(data, state_file)
        assert state_file.exists()
        assert json.loads(state_file.read_text(encoding="utf-8")) == data

    def test_save_state_atomic_uses_replace(self, tmp_path):
        state_file = tmp_path / "state.json"
        data = {"1": {"artist": "A", "title": "B"}}
        with patch("os.replace") as mock_replace:
            bcdl.save_state(data, state_file)
        mock_replace.assert_called_once()


# ---------------------------------------------------------------------------
# State integration with main()
# ---------------------------------------------------------------------------

class TestStateIntegration:
    def test_state_written_after_download(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_A_WITH_ID]):
                    with patch("bcdl.download_with_retry", return_value=(True, "")):
                        bcdl.main()
        state_file = tmp_path / ".bcdl" / "testuser.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert "11111111" in state
        entry = state["11111111"]
        assert entry["artist"] == "Artist One"
        assert entry["title"] == "Album One"
        assert "downloaded_at" in entry

    def test_skip_already_downloaded(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state_dir = tmp_path / ".bcdl"
        state_dir.mkdir()
        state_file = state_dir / "testuser.json"
        state_file.write_text(json.dumps({
            "11111111": {
                "artist": "Artist One",
                "title": "Album One",
                "url": "https://artistone.bandcamp.com/album/album-one",
                "downloaded_at": "2026-03-19T12:00:00+00:00",
            }
        }), encoding="utf-8")
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_A_WITH_ID]):
                    with patch("bcdl.download_with_retry") as mock_download:
                        bcdl.main()
        mock_download.assert_not_called()
        captured = capsys.readouterr()
        assert "[skip] Artist One" in captured.out

    def test_no_state_entry_for_missing_sale_item_id(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_NO_SALE_ID]):
                    with patch("bcdl.download_with_retry", return_value=(True, "")):
                        bcdl.main()
        state_file = tmp_path / ".bcdl" / "testuser.json"
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            assert "" not in state
            assert "None" not in state

    def test_failed_download_not_recorded(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_A_WITH_ID]):
                    with patch("bcdl.download_with_retry", return_value=(False, "download error")):
                        bcdl.main()
        state_file = tmp_path / ".bcdl" / "testuser.json"
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            assert "11111111" not in state


# ---------------------------------------------------------------------------
# classify_yt_dlp_error
# ---------------------------------------------------------------------------

class TestClassifyYtdlpError:
    def test_transient_429(self):
        assert bcdl.classify_yt_dlp_error("ERROR: HTTP Error 429") == "transient"

    def test_transient_5xx(self):
        assert bcdl.classify_yt_dlp_error("ERROR: HTTP Error 503") == "transient"

    def test_transient_connection_reset(self):
        assert bcdl.classify_yt_dlp_error("Connection reset by peer") == "transient"

    def test_transient_timeout(self):
        assert bcdl.classify_yt_dlp_error("timed out") == "transient"

    def test_transient_remote_disconnected(self):
        assert bcdl.classify_yt_dlp_error("RemoteDisconnected") == "transient"

    def test_permanent_404(self):
        assert bcdl.classify_yt_dlp_error("ERROR: HTTP Error 404: Not Found") == "permanent"

    def test_permanent_401(self):
        assert bcdl.classify_yt_dlp_error("ERROR: HTTP Error 401") == "permanent"

    def test_permanent_403(self):
        assert bcdl.classify_yt_dlp_error("ERROR: HTTP Error 403") == "permanent"

    def test_permanent_unsupported(self):
        assert bcdl.classify_yt_dlp_error("ERROR: Unsupported URL") == "permanent"

    def test_unknown_error(self):
        assert bcdl.classify_yt_dlp_error("some random error text") == "unknown"

    def test_empty_stderr(self):
        assert bcdl.classify_yt_dlp_error("") == "unknown"

    def test_permanent_checked_before_transient(self):
        assert bcdl.classify_yt_dlp_error("HTTP Error 403\nHTTP Error 429") == "permanent"

    def test_transient_500(self):
        assert bcdl.classify_yt_dlp_error("ERROR: HTTP Error 500") == "transient"


# ---------------------------------------------------------------------------
# _extract_error_summary
# ---------------------------------------------------------------------------

class TestExtractErrorSummary:
    def test_extracts_error_line(self):
        result = bcdl._extract_error_summary("ERROR: HTTP Error 429 Too Many Requests")
        assert result == "HTTP Error 429 Too Many Requests"

    def test_truncates_long_lines(self):
        result = bcdl._extract_error_summary("ERROR: " + "x" * 200)
        assert len(result) <= 80

    def test_no_error_line(self):
        result = bcdl._extract_error_summary("some output without ERROR prefix")
        assert result == "unknown error"

    def test_empty_stderr(self):
        result = bcdl._extract_error_summary("")
        assert result == "unknown error"


# ---------------------------------------------------------------------------
# _run_yt_dlp
# ---------------------------------------------------------------------------

class TestRunYtDlp:
    def test_returns_returncode_and_stderr(self):
        mock_result = MagicMock(returncode=1, stderr="ERROR: HTTP Error 404")
        with patch("subprocess.run", return_value=mock_result):
            rc, stderr = bcdl._run_yt_dlp(["yt-dlp", "url"])
        assert rc == 1
        assert stderr == "ERROR: HTTP Error 404"

    def test_passes_devnull_and_pipe(self):
        mock_result = MagicMock(returncode=0, stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            bcdl._run_yt_dlp(["yt-dlp", "url"])
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("stdout") == subprocess.DEVNULL
        assert call_kwargs.get("stderr") == subprocess.PIPE
        assert call_kwargs.get("text") is True

    def test_success_returns_zero_empty_stderr(self):
        mock_result = MagicMock(returncode=0, stderr="")
        with patch("subprocess.run", return_value=mock_result):
            rc, stderr = bcdl._run_yt_dlp(["yt-dlp", "url"])
        assert rc == 0
        assert stderr == ""


# ---------------------------------------------------------------------------
# download_with_retry
# ---------------------------------------------------------------------------

class TestRetryLogic:
    def test_success_first_attempt(self):
        with patch("bcdl._run_yt_dlp", return_value=(0, "")) as mock_run:
            with patch("bcdl._backoff_delay"):
                success, reason = bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        assert success is True
        assert reason == ""
        assert mock_run.call_count == 1

    def test_transient_retry_then_success(self):
        with patch("bcdl._run_yt_dlp", side_effect=[(1, "ERROR: HTTP Error 429"), (0, "")]) as mock_run:
            with patch("bcdl._backoff_delay", return_value=5.0):
                success, reason = bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        assert success is True
        assert reason == ""
        assert mock_run.call_count == 2

    def test_permanent_no_retry(self):
        with patch("bcdl._run_yt_dlp", return_value=(1, "ERROR: HTTP Error 404: Not Found")) as mock_run:
            with patch("bcdl._backoff_delay"):
                success, reason = bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        assert success is False
        assert "HTTP Error 404" in reason
        assert mock_run.call_count == 1

    def test_unknown_no_retry(self):
        with patch("bcdl._run_yt_dlp", return_value=(1, "ERROR: something weird")) as mock_run:
            with patch("bcdl._backoff_delay"):
                success, reason = bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        assert success is False
        assert isinstance(reason, str)
        assert mock_run.call_count == 1

    def test_max_retries_exhausted(self):
        with patch("bcdl._run_yt_dlp", return_value=(1, "ERROR: HTTP Error 429")) as mock_run:
            with patch("bcdl._backoff_delay", return_value=5.0):
                success, reason = bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        assert success is False
        assert "retried 3x" in reason
        assert mock_run.call_count == 4  # initial + 3 retries

    def test_no_url_returns_false(self):
        item_no_url = {"band_name": "Ghost", "album_title": "Phantom"}
        with patch("bcdl._run_yt_dlp") as mock_run:
            success, reason = bcdl.download_with_retry(item_no_url, 1, 3)
        assert success is False
        assert "no URL" in reason
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# download_with_retry output
# ---------------------------------------------------------------------------

class TestDownloadOutput:
    def test_success_prints_ok(self, capsys):
        with patch("bcdl._run_yt_dlp", return_value=(0, "")):
            with patch("bcdl._backoff_delay"):
                bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        captured = capsys.readouterr()
        assert "[1/3]" in captured.out or "[ 1/ 3]" in captured.out or "1/3" in captured.out
        assert "Artist One" in captured.out
        assert ": OK" in captured.out

    def test_failure_prints_failed(self, capsys):
        with patch("bcdl._run_yt_dlp", return_value=(1, "ERROR: HTTP Error 404: Not Found")):
            with patch("bcdl._backoff_delay"):
                bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        captured = capsys.readouterr()
        assert "FAILED (" in captured.out

    def test_retry_prints_notice(self, capsys):
        with patch("bcdl._run_yt_dlp", side_effect=[(1, "ERROR: HTTP Error 429"), (0, "")]):
            with patch("bcdl._backoff_delay", return_value=10.0):
                bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        captured = capsys.readouterr()
        assert "[retry 1/3] waiting" in captured.out

    def test_no_raw_ytdlp_output(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            bcdl.download_with_retry(ITEM_A_WITH_ID, 1, 3)
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("stdout") == subprocess.DEVNULL


# ---------------------------------------------------------------------------
# main() summary
# ---------------------------------------------------------------------------

class TestMainSummary:
    def test_summary_three_counts(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Pre-populate state with ITEM_A_WITH_ID so it gets skipped
        state_dir = tmp_path / ".bcdl"
        state_dir.mkdir()
        state_file = state_dir / "testuser.json"
        state_file.write_text(json.dumps({
            "11111111": {
                "artist": "Artist One",
                "title": "Album One",
                "url": "https://artistone.bandcamp.com/album/album-one",
                "downloaded_at": "2026-03-19T12:00:00+00:00",
            }
        }), encoding="utf-8")
        # ITEM_A_WITH_ID will be skipped (in state), ITEM_B_WITH_ID downloaded, ITEM_C_WITH_ID failed
        download_side_effects = [(True, ""), (False, "HTTP Error 404")]
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_A_WITH_ID, ITEM_B_WITH_ID, ITEM_C_WITH_ID]):
                    with patch("bcdl.download_with_retry", side_effect=download_side_effects):
                        bcdl.main()
        captured = capsys.readouterr()
        assert "Done: 1 downloaded, 1 skipped, 1 failed." in captured.out

    def test_failed_items_listed(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_A_WITH_ID]):
                    with patch("bcdl.download_with_retry", return_value=(False, "HTTP Error 404")):
                        bcdl.main()
        captured = capsys.readouterr()
        assert "Artist One" in captured.out
        assert "Album One" in captured.out
        assert "HTTP Error 404" in captured.out

    def test_all_skipped_summary(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state_dir = tmp_path / ".bcdl"
        state_dir.mkdir()
        state_file = state_dir / "testuser.json"
        state_file.write_text(json.dumps({
            "11111111": {
                "artist": "Artist One", "title": "Album One",
                "url": "https://example.com", "downloaded_at": "2026-03-19T12:00:00+00:00",
            },
            "22222222": {
                "artist": "Artist Two", "title": "Track Two",
                "url": "https://example.com", "downloaded_at": "2026-03-19T12:00:00+00:00",
            },
        }), encoding="utf-8")
        with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
            with patch("sys.argv", ["bcdl", "testuser"]):
                with patch("bcdl.get_all_collection_items", return_value=[ITEM_A_WITH_ID, ITEM_B_WITH_ID]):
                    with patch("bcdl.download_with_retry") as mock_download:
                        bcdl.main()
        mock_download.assert_not_called()
        captured = capsys.readouterr()
        assert "0 downloaded, 2 skipped, 0 failed" in captured.out
