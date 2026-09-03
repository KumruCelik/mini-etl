from pathlib import Path

from mini_etl.core.source import CsvSource, JsonlSource, Source


def test_csv_basligi_sutun_adi_olarak_kullaniyor(ornek_csv: Path) -> None:
    kaynak = CsvSource(ornek_csv)

    kayitlar = list(kaynak.oku())

    assert kayitlar[0] == {"id": "1", "ad": "kumru", "sehir": "elazig"}


def test_iki_satirdan_iki_kayit_geliyor(ornek_csv: Path) -> None:
    kaynak = CsvSource(ornek_csv)

    kayitlar = list(kaynak.oku())

    assert len(kayitlar) == 2


def test_sadece_baslik_olan_dosya_bos_akis_veriyor(bos_csv: Path) -> None:
    kaynak = CsvSource(bos_csv)

    kayitlar = list(kaynak.oku())

    assert len(kayitlar) == 0


def test_oku_tembel_calisiyor(ornek_csv: Path) -> None:
    kaynak = CsvSource(ornek_csv)

    akis = kaynak.oku()
    ilk = next(akis)

    assert ilk["ad"] == "kumru"


def test_jsonl_her_satiri_kayit_olarak_veriyor(ornek_jsonl: Path) -> None:
    kaynak = JsonlSource(ornek_jsonl)

    kayitlar = list(kaynak.oku())

    assert len(kayitlar) == 2
    assert kayitlar[0] == {"id": "1", "ad": "kumru"}


def test_alan_ici_virgul_bozulmuyor(virgullu_csv: Path) -> None:
    kaynak = CsvSource(virgullu_csv)

    kayitlar = list(kaynak.oku())

    assert kayitlar[0]["aciklama"] == "HANDS, FISTS, FEET"


def test_kaynaklar_source_protokolune_uyuyor(ornek_csv: Path, ornek_jsonl: Path) -> None:
    json_kaynak = JsonlSource(ornek_jsonl)
    csv_kaynak = CsvSource(ornek_csv)

    assert isinstance(json_kaynak, Source)
    assert isinstance(csv_kaynak, Source)
