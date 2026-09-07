import csv
import json
import time
import urllib.request
from collections.abc import Callable, Iterator
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


def _http_getir(url: str, zaman_asimi: float) -> bytes:
    """Adresi okur ve ham baytları döndürür."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"desteklenmeyen adres: {url!r}")
    with urllib.request.urlopen(url, timeout=zaman_asimi) as cevap:
        return bytes(cevap.read())


class HttpSource:
    """Bir HTTP uç noktasından JSON kayıtları okur."""

    def __init__(
        self,
        url: str,
        deneme: int = 3,
        bekleme: float = 0.5,
        zaman_asimi: float = 10.0,
        getir: Callable[[str, float], bytes] = _http_getir,
        bekle: Callable[[float], None] = time.sleep,
    ) -> None:
        self.url = url
        self.deneme = deneme
        self.bekleme = bekleme
        self.zaman_asimi = zaman_asimi
        self._getir = getir
        self._bekle = bekle

    def _dene(self) -> bytes:
        """Başarısız olursa üstel artan aralıklarla yeniden dener."""
        son_hata: Exception = RuntimeError("hic denenmedi")

        for sayac in range(self.deneme):
            try:
                return self._getir(self.url, self.zaman_asimi)
            except Exception as hata:
                son_hata = hata
                if sayac < self.deneme - 1:
                    self._bekle(self.bekleme * (2**sayac))

        raise son_hata

    def oku(self) -> Iterator[Record]:
        """Uç noktadaki JSON'u kayıt kayıt üretir."""
        veri = json.loads(self._dene())
        if isinstance(veri, dict):
            veri = [veri]
        yield from veri
