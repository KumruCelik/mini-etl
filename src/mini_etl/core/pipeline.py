import time
from collections.abc import Iterator

from mini_etl.core.record import Rapor, Record
from mini_etl.core.sink import Sink
from mini_etl.core.source import Source
from mini_etl.core.transform import Transform


class Pipeline:
    """Bir kaynağı, dönüşümü ve bir hedefi tek bir iş olarak birleştirir."""

    def __init__(
        self,
        kaynak: Source,
        hedef: Sink,
        donusum: Transform | None = None,
    ) -> None:
        self.kaynak = kaynak
        self.hedef = hedef
        self.donusum = donusum

    def _sayarak_oku(self, rapor: Rapor) -> Iterator[Record]:
        """Kaynaktan okur ve geçen her kaydı rapora bildirir."""
        for kayit in self.kaynak.oku():
            rapor.oku()
            yield kayit

    def calistir(self) -> Rapor:
        """Boru hattını uçtan uca çalıştırır ve raporu döndürür."""
        rapor = Rapor()
        baslangic = time.perf_counter()

        akis = self._sayarak_oku(rapor)
        if self.donusum is not None:
            akis = self.donusum(akis, rapor)

        rapor.yaz(self.hedef.yaz(akis))
        rapor.sure = time.perf_counter() - baslangic
        return rapor
