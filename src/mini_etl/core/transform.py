from collections.abc import Callable, Iterator

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
