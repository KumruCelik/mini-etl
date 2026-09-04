from collections.abc import Callable, Iterator

from mini_etl.core.record import Record

AkisIslemi = Callable[[Iterator[Record]], Iterator[Record]]


class Transform:
    """Bir kayıt akışını başka bir akışa dönüştüren işlem."""

    def __init__(self, islem: AkisIslemi) -> None:
        self._islem = islem

    def __call__(self, akis: Iterator[Record]) -> Iterator[Record]:
        """Akışı işleyip yeni akış döndürür."""
        return self._islem(akis)

    def __rshift__(self, other: "Transform") -> "Transform":
        """İki dönüşümü birleştirir: önce self, sonra other."""
        return Transform(lambda akis: other(self(akis)))


def esle(f: Callable[[Record], Record]) -> Transform:
    """Her kayda f uygular."""

    def islem(akis: Iterator[Record]) -> Iterator[Record]:
        for kayit in akis:
            yield f(kayit)

    return Transform(islem)


def filtrele(kosul: Callable[[Record], bool]) -> Transform:
    """Koşulu sağlayan kayıtları geçirir, diğerlerini atar."""

    def islem(akis: Iterator[Record]) -> Iterator[Record]:
        for kayit in akis:
            if kosul(kayit):
                yield kayit

    return Transform(islem)
