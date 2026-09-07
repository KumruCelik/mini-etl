from dataclasses import dataclass, field
from typing import Any

from mini_etl.gunluk import KAYITCI

Record = dict[str, Any]


@dataclass
class HataKaydi:
    """Reddedilen bir satır ve reddedilme sebebi."""

    kayit: Record
    hata: str
    asama: str


@dataclass
class Rapor:
    """Bir çalıştırmanın özeti."""

    okunan: int = 0
    yazilan: int = 0
    reddedilen: int = 0
    sure: float = 0.0
    hatalar: list[HataKaydi] = field(default_factory=list)

    def oku(self) -> None:
        """Bir satır okunduğunu kaydeder."""
        self.okunan += 1

    def yaz(self, adet: int = 1) -> None:
        """Yazılan satır sayısını artırır."""
        self.yazilan += adet

    def reddet(self, kayit: Record, hata: Exception, asama: str) -> None:
        """Bir satırı reddeder ve sebebini saklar."""
        self.reddedilen += 1
        self.hatalar.append(
            HataKaydi(kayit=kayit, hata=f"{type(hata).__name__}: {hata}", asama=asama)
        )
        KAYITCI.debug("kayit reddedildi", extra={"ek": {"asama": asama}})
