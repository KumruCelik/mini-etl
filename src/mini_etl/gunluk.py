"""Yapılandırılmış günlükleme."""

import json
import logging
import sys
from typing import TextIO

KAYITCI = logging.getLogger("mini_etl")


class JsonBicimleyici(logging.Formatter):
    """Her günlük satırını tek satırlık JSON olarak biçimlendirir."""

    def format(self, record: logging.LogRecord) -> str:
        """Kaydı JSON metnine çevirir."""
        govde: dict[str, object] = {
            "zaman": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "seviye": record.levelname,
            "mesaj": record.getMessage(),
        }

        ek = getattr(record, "ek", None)
        if isinstance(ek, dict):
            govde.update(ek)

        if record.exc_info:
            govde["hata"] = self.formatException(record.exc_info)

        return json.dumps(govde, ensure_ascii=False)


def kur(
    seviye: str = "INFO",
    json_bicim: bool = True,
    akis: TextIO | None = None,
) -> None:
    """mini_etl günlükçüsünü yapılandırır."""
    isleyici = logging.StreamHandler(akis if akis is not None else sys.stderr)

    if json_bicim:
        isleyici.setFormatter(JsonBicimleyici())
    else:
        isleyici.setFormatter(DuzBicimleyici())

    KAYITCI.handlers.clear()
    KAYITCI.addHandler(isleyici)
    KAYITCI.setLevel(seviye.upper())
    KAYITCI.propagate = False


class DuzBicimleyici(logging.Formatter):
    """İnsan için okunabilir tek satır üretir."""

    def format(self, record: logging.LogRecord) -> str:
        """Kaydı `SEVIYE mesaj anahtar=deger` biçimine çevirir."""
        satir = f"{record.levelname} {record.getMessage()}"

        ek = getattr(record, "ek", None)
        if isinstance(ek, dict):
            satir += " " + " ".join(f"{a}={d}" for a, d in ek.items())

        return satir
