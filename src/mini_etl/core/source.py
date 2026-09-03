import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from mini_etl.core.record import Record


@runtime_checkable
class Source(Protocol):
    """Kayıt akışı üreten her şey."""

    def oku(self) -> Iterator[Record]:
        """Kayıtları tek tek üretir."""
        ...


class CsvSource:
    """Bir CSV dosyasını satır satır okur."""

    def __init__(self, yol: Path | str, ayirac: str = ",") -> None:
        self.yol = Path(yol)
        self.ayirac = ayirac

    def oku(self) -> Iterator[Record]:
        """Her satırı bir sözlük olarak üretir."""
        with self.yol.open(encoding="utf-8", newline="") as f:
            okuyucu = csv.DictReader(f, delimiter=self.ayirac)
            for satir in okuyucu:
                yield dict(satir)


class JsonlSource:
    """Her satırı bir JSON nesnesi olan dosyayı okur."""

    def __init__(self, yol: Path | str) -> None:
        self.yol = Path(yol)

    def oku(self) -> Iterator[Record]:
        """Her satırı bir kayıt olarak üretir."""
        with self.yol.open(encoding="utf-8") as f:
            for satir in f:
                temiz = satir.strip()
                if not temiz:
                    continue
                yield json.loads(temiz)
