import io
import sqlite3
from pathlib import Path

import pytest

from mini_etl.core.sink import CsvSink, Sink, SqliteSink, StdoutSink
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


def test_stdout_sink_her_kaydi_json_satiri_olarak_yaziyor() -> None:
    tampon = io.StringIO()

    adet = StdoutSink(tampon).yaz(iter([{"ad": "kumru"}, {"sehir": "elazığ"}]))

    satirlar = tampon.getvalue().splitlines()

    assert adet == 2
    assert satirlar == ['{"ad": "kumru"}', '{"sehir": "elazığ"}']


def test_stdout_sink_bos_akista_sifir_donduruyor() -> None:
    tampon = io.StringIO()

    adet = StdoutSink(tampon).yaz(iter([]))

    assert adet == 0
    assert tampon.getvalue() == ""


def test_stdout_sink_protokole_uyuyor() -> None:
    assert isinstance(StdoutSink(io.StringIO()), Sink)


def test_sqlite_sink_kayitlari_yaziyor(tmp_path: Path) -> None:
    yol = tmp_path / "veri.db"
    kayitlar = [{"id": "1", "ad": "kumru"}, {"id": "2", "ad": "elif"}]

    adet = SqliteSink(yol).yaz(iter(kayitlar))

    baglanti = sqlite3.connect(yol)
    satirlar = baglanti.execute("SELECT id, ad FROM kayitlar ORDER BY id").fetchall()
    baglanti.close()

    assert adet == 2
    assert satirlar == [("1", "kumru"), ("2", "elif")]


def test_sqlite_sink_bos_akista_dosya_olusturmuyor(tmp_path: Path) -> None:
    yol = tmp_path / "veri.db"

    adet = SqliteSink(yol).yaz(iter([]))

    assert adet == 0
    assert not yol.exists()


def test_sqlite_sink_parcadan_buyuk_akisi_tam_yaziyor(tmp_path: Path) -> None:
    yol = tmp_path / "veri.db"
    kayitlar = [{"id": str(i)} for i in range(5)]

    adet = SqliteSink(yol, parca=2).yaz(iter(kayitlar))

    assert adet == 5


def test_sqlite_sink_guvensiz_tablo_adini_reddediyor(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SqliteSink(tmp_path / "veri.db", tablo="kayitlar; DROP TABLE x")
