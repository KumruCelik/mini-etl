import csv
import json
import time
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from mini_etl.core.record import Record

TEKRARLANABILIR_KODLAR = frozenset({408, 425, 429, 500, 502, 503, 504})


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


def _tekrar_denenir_mi(hata: Exception) -> bool:
    """Hatanın yeniden denenmeye değer olup olmadığını söyler."""
    kod = getattr(hata, "code", None)
    if kod is None:
        return True  # ag/baglanti hatasi - gecici kabul edilir
    return int(kod) in TEKRARLANABILIR_KODLAR


def _retry_after(hata: Exception) -> float | None:
    """Yanıttaki Retry-After başlığını saniye olarak döndürür."""
    basliklar = getattr(hata, "headers", None)
    if basliklar is None:
        return None

    deger = basliklar.get("Retry-After")
    if deger is None:
        return None

    try:
        return float(deger)
    except (TypeError, ValueError):
        return None


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

    def _bekleme_suresi(self, hata: Exception, sayac: int) -> float:
        """Retry-After varsa onu, yoksa üstel geri çekilmeyi kullanır."""
        sunucudan = _retry_after(hata)
        if sunucudan is not None:
            return sunucudan

        # 2**sayac typeshed'de Any doner (2**-1 float verir); int'e bagliyoruz
        carpan: int = 2**sayac
        return self.bekleme * carpan

    def _dene(self) -> bytes:
        """Geçici hatalarda üstel artan aralıklarla yeniden dener."""
        son_hata: Exception = RuntimeError("hic denenmedi")

        for sayac in range(self.deneme):
            try:
                return self._getir(self.url, self.zaman_asimi)
            except Exception as hata:
                if not _tekrar_denenir_mi(hata):
                    raise
                son_hata = hata
                if sayac < self.deneme - 1:
                    self._bekle(self._bekleme_suresi(hata, sayac))

        raise son_hata

    def oku(self) -> Iterator[Record]:
        """Uç noktadaki JSON'u kayıt kayıt üretir."""
        veri = json.loads(self._dene())
        if isinstance(veri, dict):
            veri = [veri]
        yield from veri
