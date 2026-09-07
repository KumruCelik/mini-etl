from collections.abc import Callable, Iterator
from typing import Any

from mini_etl.core.record import Rapor, Record

AkisIslemi = Callable[[Iterator[Record], Rapor], Iterator[Record]]


class Transform:
    """Bir kayıt akışını başka bir akışa dönüştüren işlem."""

    def __init__(self, islem: AkisIslemi, ad: str = "transform") -> None:
        self._islem = islem
        self.ad = ad

    def __call__(self, akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        """Akışı işleyip yeni akış döndürür."""
        return self._islem(akis, rapor)

    def __rshift__(self, other: "Transform") -> "Transform":
        """İki dönüşümü birleştirir: önce self, sonra other."""

        def islem(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
            return other(self(akis, rapor), rapor)

        return Transform(islem, ad=f"{self.ad} >> {other.ad}")


def esle(f: Callable[[Record], Record], ad: str = "esle") -> Transform:
    """Her kayda f uygular; hata veren kaydı reddeder."""

    def islem(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        for kayit in akis:
            try:
                sonuc = f(kayit)
            except Exception as hata:
                rapor.reddet(kayit, hata, ad)
                continue
            yield sonuc

    return Transform(islem, ad)


def filtrele(kosul: Callable[[Record], bool], ad: str = "filtrele") -> Transform:
    """Koşulu sağlayanları geçirir; koşul hata verirse kaydı reddeder."""

    def islem(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        for kayit in akis:
            try:
                gecsin = kosul(kayit)
            except Exception as hata:
                rapor.reddet(kayit, hata, ad)
                continue
            if gecsin:
                yield kayit

    return Transform(islem, ad)


def dogrula(
    kosul: Callable[[Record], bool],
    mesaj: str = "dogrulama basarisiz",
    ad: str = "dogrula",
) -> Transform:
    """Koşulu sağlamayan kaydı reddeder (elemez)."""

    def islem(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        for kayit in akis:
            try:
                gecerli = kosul(kayit)
            except Exception as hata:
                rapor.reddet(kayit, hata, ad)
                continue

            if not gecerli:
                rapor.reddet(kayit, ValueError(mesaj), ad)
                continue

            yield kayit

    return Transform(islem, ad)


def yeniden_adlandir(esleme: dict[str, str], ad: str = "yeniden_adlandir") -> Transform:
    """Sütun adlarını verilen eşlemeye göre değiştirir."""

    def cevir(kayit: Record) -> Record:
        yeni = {esleme.get(sutun, sutun): deger for sutun, deger in kayit.items()}
        if len(yeni) != len(kayit):
            raise ValueError("yeniden adlandirma sutun cakismasi yaratti")
        return yeni

    return esle(cevir, ad)


def tip_cevir(
    donusumler: dict[str, Callable[[str], Any]],
    ad: str = "tip_cevir",
) -> Transform:
    """Belirtilen alanları verilen fonksiyonla dönüştürür."""

    def cevir(kayit: Record) -> Record:
        yeni = dict(kayit)
        for sutun, f in donusumler.items():
            yeni[sutun] = f(kayit[sutun])
        return yeni

    return esle(cevir, ad)


def metinden_bool(deger: str) -> bool:
    """Metni bool'a çevirir; tanımadığı değerde hata verir."""
    kucuk = deger.strip().lower()
    if kucuk in {"1", "true", "evet", "yes"}:
        return True
    if kucuk in {"0", "false", "hayir", "no"}:
        return False
    raise ValueError(f"bool'a cevrilemedi: {deger!r}")
