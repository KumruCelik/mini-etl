import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

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
