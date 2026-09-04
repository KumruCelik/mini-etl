from pathlib import Path

from mini_etl.core.sink import CsvSink, Sink
from mini_etl.core.source import CsvSource


def test_yazilan_dosya_geri_okunabiliyor(tmp_path: Path) -> None:
    kayitlar = [{"id": "1", "ad": "kumru"}, {"id": "2", "ad": "elif"}]
    yol = tmp_path / "cikti.csv"

    adet = CsvSink(yol).yaz(iter(kayitlar))

    assert adet == 2
    assert list(CsvSource(yol).oku()) == kayitlar


def test_bos_akis_donduruyor(tmp_path: Path) -> None:
    yol = tmp_path / "bos.csv"

    adet = CsvSink(yol).yaz(iter([]))

    assert adet == 0


def test_baslik_ilk_kaydin_anahtarlarindan_geliyor(tmp_path: Path) -> None:
    yol = tmp_path / "cikti.csv"

    CsvSink(yol).yaz(iter([{"id": "1", "ad": "kumru"}]))

    ilk_satir = yol.read_text(encoding="utf-8").splitlines()[0]

    assert ilk_satir == "id,ad"


def test_csvsink_sink_protokole_uyuyor(tmp_path: Path) -> None:
    hedef = CsvSink(tmp_path / "x.csv")

    assert isinstance(hedef, Sink)
