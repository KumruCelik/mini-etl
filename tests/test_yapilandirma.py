from pathlib import Path

import pytest

from mini_etl.core.sink import SqliteSink, StdoutSink
from mini_etl.core.source import HttpSource, JsonlSource
from mini_etl.yapilandirma import (
    donusum_zinciri,
    dosyadan_yukle,
    hedef_kur,
    kaynak_kur,
)


def test_yamldan_kurulan_boru_calisiyor(tmp_path: Path) -> None:
    girdi = tmp_path / "g.csv"
    girdi.write_text("id,ad,yas\n1,kumru,22\n2,emre,\n", encoding="utf-8")
    cikti = tmp_path / "c.csv"
    ayar = tmp_path / "p.yaml"
    ayar.write_text(
        f"kaynak:\n"
        f"  tur: csv\n"
        f"  yol: {girdi}\n"
        f"donusumler:\n"
        f"  - tur: zorunlu\n"
        f"    sutun: yas\n"
        f"  - tur: yeniden_adlandir\n"
        f"    esleme:\n"
        f"      ad: isim\n"
        f"  - tur: tip_cevir\n"
        f"    alanlar:\n"
        f"      yas: int\n"
        f"hedef:\n"
        f"  tur: csv\n"
        f"  yol: {cikti}\n",
        encoding="utf-8",
    )

    rapor = dosyadan_yukle(ayar).calistir()

    assert rapor.okunan == 2
    assert rapor.yazilan == 1
    assert cikti.read_text(encoding="utf-8").splitlines()[0] == "id,isim,yas"


def test_bilinmeyen_kaynak_turu_hata_veriyor() -> None:
    with pytest.raises(ValueError):
        kaynak_kur({"tur": "parquet", "yol": "x"})


def test_bilinmeyen_hedef_turu_hata_veriyor() -> None:
    with pytest.raises(ValueError):
        hedef_kur({"tur": "kafka"})


def test_hedef_turleri_dogru_nesne_uretiyor(tmp_path: Path) -> None:
    sqlite = hedef_kur({"tur": "sqlite", "yol": str(tmp_path / "v.db")})
    ekran = hedef_kur({"tur": "stdout"})

    assert isinstance(sqlite, SqliteSink)
    assert isinstance(ekran, StdoutSink)


def test_jsonl_ve_http_kaynaklari_kuruluyor(tmp_path: Path) -> None:
    jsonl = kaynak_kur({"tur": "jsonl", "yol": str(tmp_path / "a.jsonl")})
    http = kaynak_kur({"tur": "http", "url": "http://ornek", "deneme": 5})

    assert isinstance(jsonl, JsonlSource)
    assert isinstance(http, HttpSource)
    assert http.deneme == 5


def test_sec_ve_dogrula_adimlari_calisiyor(tmp_path: Path) -> None:
    girdi = tmp_path / "g.csv"
    girdi.write_text("id,ad,yas\n1,kumru,22\n2,,26\n", encoding="utf-8")
    cikti = tmp_path / "c.csv"
    ayar = tmp_path / "p.yaml"
    ayar.write_text(
        f"kaynak:\n  tur: csv\n  yol: {girdi}\n"
        "donusumler:\n"
        "  - tur: dogrula\n    sutun: ad\n"
        "  - tur: sec\n    sutunlar: [id, ad]\n"
        f"hedef:\n  tur: csv\n  yol: {cikti}\n",
        encoding="utf-8",
    )

    rapor = dosyadan_yukle(ayar).calistir()

    assert rapor.okunan == 2
    assert rapor.yazilan == 1
    assert rapor.reddedilen == 1
    assert cikti.read_text(encoding="utf-8").splitlines()[0] == "id,ad"


def test_bilinmeyen_donusum_turu_hata_veriyor() -> None:
    with pytest.raises(ValueError):
        donusum_zinciri([{"tur": "ucmak"}])
