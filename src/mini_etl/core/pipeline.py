import json
import time
from collections.abc import Iterator
from pathlib import Path

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
        hata_dosyasi: Path | str | None = None,
    ) -> None:
        self.kaynak = kaynak
        self.hedef = hedef
        self.donusum = donusum
        self.hata_dosyasi = Path(hata_dosyasi) if hata_dosyasi is not None else None

    def _sayarak_oku(self, rapor: Rapor) -> Iterator[Record]:
        """Kaynaktan okur ve geçen her kaydı rapora bildirir."""
        for kayit in self.kaynak.oku():
            rapor.oku()
            yield kayit

    def _hatalari_yaz(self, rapor: Rapor) -> None:
        """Reddedilen kayıtları JSONL dosyasına yazar."""
        if self.hata_dosyasi is None or not rapor.hatalar:
            return

        with self.hata_dosyasi.open("w", encoding="utf-8") as f:
            for hata in rapor.hatalar:
                satir = {"kayit": hata.kayit, "hata": hata.hata, "asama": hata.asama}
                f.write(json.dumps(satir, ensure_ascii=False) + "\n")

    def calistir(self) -> Rapor:
        """Boru hattını uçtan uca çalıştırır ve raporu döndürür."""
        rapor = Rapor()
        baslangic = time.perf_counter()

        akis = self._sayarak_oku(rapor)
        if self.donusum is not None:
            akis = self.donusum(akis, rapor)

        rapor.yaz(self.hedef.yaz(akis))
        self._hatalari_yaz(rapor)
        rapor.sure = time.perf_counter() - baslangic
        return rapor
