# -*- coding: utf-8 -*-
"""Loads, validates, caches and searches the LER 2 data model published by
valideringsportalen.dk.

Security notes: only two fixed HTTPS GET requests are made, nothing about the
user's project or layers is sent, the response size is capped, the payload is
parsed as JSON only (never evaluated), and the UI shows every value as plain
text.
"""

import json
import os

from qgis.core import QgsApplication, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QObject, QUrl, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from .i18n import tr

BASE_URL = "https://valideringsportalen.dk/ler2-datamodel/"
FILES = {"objekttyper": "objekttyper.json", "kodelister": "kodelister.json"}
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT_MS = 15000


def fold(text):
    """Lower-case and transliterate so 'afloeb' also finds 'afløb'."""
    return (
        str(text).lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    )


def truthy(value):
    return str(value).strip().lower() in ("true", "ja", "yes", "1")


def cache_dir():
    return os.path.join(QgsApplication.qgisSettingsDirPath(), "ler2_vejledning")


def parse_json(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError(tr("err_too_large"))
    return json.loads(raw.decode("utf-8-sig"))


def validate(objekttyper, kodelister):
    if not isinstance(objekttyper, dict) or not isinstance(kodelister, dict):
        raise ValueError(tr("err_unexpected_format"))
    for name, obj in objekttyper.items():
        attrs = obj.get("attributter") if isinstance(obj, dict) else None
        if not isinstance(attrs, list) or not all(
            isinstance(a, dict) and "navn" in a for a in attrs
        ):
            raise ValueError(tr("err_invalid_type", name))
    for name, kl in kodelister.items():
        values = kl.get("vaerdier") if isinstance(kl, dict) else None
        if not isinstance(values, list) or not all(
            isinstance(v, dict) and "vaerdi" in v for v in values
        ):
            raise ValueError(tr("err_invalid_list", name))


class DataModel:
    def __init__(self, objekttyper, kodelister):
        self.objekttyper = objekttyper
        self.kodelister = kodelister
        self._index = None

    def type_names(self):
        return sorted(self.objekttyper, key=fold)

    def attributes(self, type_name):
        return self.objekttyper.get(type_name, {}).get("attributter", [])

    def kodeliste(self, name):
        return self.kodelister.get(name)

    def match_layer_name(self, layer_name):
        """Return the object type whose name is contained in the layer name
        (longest match wins), or None."""
        folded_layer = "".join(ch for ch in fold(layer_name) if ch.isalnum())
        best = None
        for name in self.objekttyper:
            key = "".join(ch for ch in fold(name) if ch.isalnum())
            if key and key in folded_layer and (best is None or len(key) > best[0]):
                best = (len(key), name)
        return best[1] if best else None

    def _build_index(self):
        attrs, values = [], []
        for type_name, obj in self.objekttyper.items():
            for attr in obj["attributter"]:
                hay = " ".join(
                    fold(x or "")
                    for x in (type_name, attr.get("navn"), attr.get("definition"),
                              attr.get("kodeliste"),
                              None if attr["navn"] == "noejagtighedsklasseVertikal"
                              else attr.get("betingelse"))
                )
                attrs.append((hay, type_name, attr))
        for list_name, kl in self.kodelister.items():
            for value in kl["vaerdier"]:
                hay = " ".join(
                    fold(x or "") for x in (value.get("vaerdi"), value.get("definition"))
                )
                values.append((hay, list_name, value))
        return attrs, values

    def _ensure_index(self):
        if self._index is None:
            self._index = self._build_index()
        return self._index

    @staticmethod
    def _filter(entries, query, limit, group=None):
        tokens = fold(query).split()
        results = []
        for hay, entry_group, item in entries:
            if group is not None and entry_group != group:
                continue
            if all(t in hay for t in tokens):
                results.append((entry_group, item))
                if len(results) >= limit:
                    break
        return results

    def search_attributes(self, query, limit=500):
        """Attributes across all object types matching every word in query."""
        return self._filter(self._ensure_index()[0], query, limit)

    def search_values(self, query, list_name=None, limit=1000):
        """Code list values (optionally within one list) matching the query."""
        return self._filter(self._ensure_index()[1], query, limit, list_name)


class DataLoader(QObject):
    """Cache-first loader that refreshes from the server in the background."""

    updated = pyqtSignal(object)  # DataModel with fresh data from the server
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw = {}
        self._errors = []
        self._pending = 0

    def load_cache(self):
        try:
            raws = {}
            for key, filename in FILES.items():
                with open(os.path.join(cache_dir(), filename), "rb") as f:
                    raws[key] = f.read()
            return self._build(raws)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _build(raws):
        objekttyper = parse_json(raws["objekttyper"])
        kodelister = parse_json(raws["kodelister"])
        validate(objekttyper, kodelister)
        return DataModel(objekttyper, kodelister)

    def refresh(self):
        if self._pending:
            return
        self._raw = {}
        self._errors = []
        self._pending = len(FILES)
        for key, filename in FILES.items():
            request = QNetworkRequest(QUrl(BASE_URL + filename))
            if hasattr(request, "setTransferTimeout"):
                request.setTransferTimeout(TIMEOUT_MS)
            reply = QgsNetworkAccessManager.instance().get(request)
            reply.finished.connect(lambda r=reply, k=key: self._on_reply(k, r))

    def _on_reply(self, key, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._errors.append(reply.errorString())
        else:
            self._raw[key] = bytes(reply.readAll())
        reply.deleteLater()

        self._pending -= 1
        if self._pending:
            return
        if self._errors:
            self.failed.emit("; ".join(self._errors))
            return
        try:
            model = self._build(self._raw)
        except (ValueError, KeyError) as exc:
            self.failed.emit(tr("err_invalid_response", exc))
            return
        self._save_cache()
        self.updated.emit(model)

    def _save_cache(self):
        try:
            os.makedirs(cache_dir(), exist_ok=True)
            for key, filename in FILES.items():
                path = os.path.join(cache_dir(), filename)
                with open(path + ".tmp", "wb") as f:
                    f.write(self._raw[key])
                os.replace(path + ".tmp", path)
        except OSError:
            pass  # caching is best-effort
