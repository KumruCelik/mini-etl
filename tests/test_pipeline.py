from pathlib import Path

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import esle, filtrele


def test_donusumsuz_boru_dosyayi_kopyaliyor(yas_csv: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "cikti.csv"

    rapor = Pipeline(
        kaynak=CsvSource(yas_csv),
        hedef=CsvSink(cikti),
    ).calistir()

    assert rapor.okunan == 3
    assert rapor.yazilan == 3
    assert len(list(CsvSource(cikti).oku())) == 3


def test_filtrelenen_kayitlar_yazilmiyor(yas_csv: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "cikti.csv"

    rapor = Pipeline(
        kaynak=CsvSource(yas_csv),
        hedef=CsvSink(cikti),
        donusum=filtrele(lambda k: int(k["yas"]) > 23),
    ).calistir()

    assert rapor.okunan == 3
    assert rapor.yazilan == 2
    assert [k["ad"] for k in CsvSource(cikti).oku()] == ["emre", "ayse"]


def test_esle_ciktiyi_degistiriyor(yas_csv: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "cikti.csv"

    Pipeline(
        kaynak=CsvSource(yas_csv),
        hedef=CsvSink(cikti),
        donusum=esle(lambda k: {**k, "yas": str(int(k["yas"]) + 1)}),
    ).calistir()

    assert [k["yas"] for k in CsvSource(cikti).oku()] == ["23", "27", "32"]


def test_bos_kaynak_sifir_rapor_veriyor(tmp_path: Path) -> None:
    girdi = tmp_path / "bos.csv"
    girdi.write_text("id,ad,yas\n", encoding="utf-8")
    cikti = tmp_path / "cikti.csv"

    rapor = Pipeline(
        kaynak=CsvSource(girdi),
        hedef=CsvSink(cikti),
    ).calistir()

    assert rapor.okunan == 0
    assert rapor.yazilan == 0
