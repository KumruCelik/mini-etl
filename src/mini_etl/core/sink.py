import csv
import json
import re
import sqlite3
import sys
from collections.abc import Iterator
from itertools import chain, islice
from pathlib import Path
from typing import Protocol, TextIO, runtime_checkable

from mini_etl.core.record import Record


@runtime_checkable
class Sink(Protocol):
    """Kayıt akışını bir yere yazan her şey."""

    def yaz(self, akis: Iterator[Record]) -> int:
        """Akışı yazar, yazılan kayıt sayısını döndürür."""
        ...


class CsvSink:
    """Kayıt akışını CSV dosyasına yazar."""

    def __init__(self, yol: Path | str) -> None:
        self.yol = Path(yol)

    def yaz(self, akis: Iterator[Record]) -> int:
        """Akışı CSV olarak yazar, yazılan satır sayısını döndürür."""
        ilk = next(akis, None)
        if ilk is None:
            return 0

        adet = 0
        with self.yol.open("w", encoding="utf-8", newline="") as f:
            yazici = csv.DictWriter(f, fieldnames=list(ilk.keys()))
            yazici.writeheader()
            yazici.writerow(ilk)
            adet = 1
            for kayit in akis:
                yazici.writerow(kayit)
                adet += 1
        return adet


class StdoutSink:
    """Kayıtları JSONL olarak ekrana (veya verilen akışa) yazar."""

    def __init__(self, hedef: TextIO | None = None) -> None:
        self.hedef = hedef if hedef is not None else sys.stdout

    def yaz(self, akis: Iterator[Record]) -> int:
        """Her kaydı bir JSON satırı olarak yazar."""
        adet = 0
        for kayit in akis:
            print(json.dumps(kayit, ensure_ascii=False), file=self.hedef)
            adet += 1
        return adet


def _guvenli_ad(ad: str) -> str:
    """SQL tanımlayıcısı olarak güvenli olup olmadığını kontrol eder."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ad):
        raise ValueError(f"gecersiz tablo/sutun adi: {ad!r}")
    return ad


class SqliteSink:
    """Kayıtları bir SQLite tablosuna parçalar hâlinde yazar."""

    def __init__(
        self,
        yol: Path | str,
        tablo: str = "kayitlar",
        parca: int = 500,
    ) -> None:
        self.yol = Path(yol)
        self.tablo = _guvenli_ad(tablo)
        self.parca = parca

    def yaz(self, akis: Iterator[Record]) -> int:
        """Akışı tabloya yazar, yazılan kayıt sayısını döndürür."""
        ilk = next(akis, None)
        if ilk is None:
            return 0

        sutunlar = [_guvenli_ad(s) for s in ilk]
        alanlar = ", ".join(f"{s} TEXT" for s in sutunlar)
        adlar = ", ".join(sutunlar)
        yer_tutucular = ", ".join("?" for _ in sutunlar)
        adet = 0

        baglanti = sqlite3.connect(self.yol)
        try:
            baglanti.execute(f"CREATE TABLE IF NOT EXISTS {self.tablo} ({alanlar})")
            ekle = f"INSERT INTO {self.tablo} ({adlar}) VALUES ({yer_tutucular})"

            tum = chain([ilk], akis)
            while grup := list(islice(tum, self.parca)):
                baglanti.executemany(ekle, [[k[s] for s in sutunlar] for k in grup])
                adet += len(grup)

            baglanti.commit()
        finally:
            baglanti.close()

        return adet
