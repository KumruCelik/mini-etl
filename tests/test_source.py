from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from mini_etl.core.source import CsvSource, HttpSource, JsonlSource, Source


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


def test_jsonl_bos_satirlari_atliyor(tmp_path: Path) -> None:
    yol = tmp_path / "bosluklu.jsonl"
    yol.write_text('{"id": "1"}\n\n{"id": "2"}\n', encoding="utf-8")

    kayitlar = list(JsonlSource(yol).oku())

    assert kayitlar == [{"id": "1"}, {"id": "2"}]


def test_http_source_kayitlari_uretiyor() -> None:
    def sahte(url: str, zaman_asimi: float) -> bytes:
        return b'[{"id": "1"}, {"id": "2"}]'

    kaynak = HttpSource("http://ornek", getir=sahte)

    assert list(kaynak.oku()) == [{"id": "1"}, {"id": "2"}]


def test_http_source_gecici_hatadan_sonra_basariyor() -> None:
    cagri = 0
    beklemeler: list[float] = []

    def sahte(url: str, zaman_asimi: float) -> bytes:
        nonlocal cagri
        cagri += 1
        if cagri < 3:
            raise OSError("gecici")
        return b'[{"id": "1"}]'

    kaynak = HttpSource("http://ornek", getir=sahte, bekle=beklemeler.append)

    assert list(kaynak.oku()) == [{"id": "1"}]
    assert cagri == 3
    assert beklemeler == [0.5, 1.0]


def test_http_source_tum_denemeler_basarisizsa_son_hatayi_veriyor() -> None:
    cagri = 0

    def sahte(url: str, zaman_asimi: float) -> bytes:
        nonlocal cagri
        cagri += 1
        raise OSError("kalici")

    kaynak = HttpSource("http://ornek", getir=sahte, bekle=lambda _: None)

    with pytest.raises(OSError):
        list(kaynak.oku())

    assert cagri == 3


def test_http_source_protokole_uyuyor() -> None:
    assert isinstance(HttpSource("http://ornek"), Source)


def test_http_source_kalici_hatayi_tekrar_denemiyor() -> None:
    cagri = 0

    def sahte(url: str, zaman_asimi: float) -> bytes:
        nonlocal cagri
        cagri += 1
        raise HTTPError(url, 404, "bulunamadi", Message(), None)

    kaynak = HttpSource("http://ornek", getir=sahte, bekle=lambda _: None)

    with pytest.raises(HTTPError):
        list(kaynak.oku())

    assert cagri == 1


def test_http_source_sunucu_hatasini_tekrar_deniyor() -> None:
    cagri = 0

    def sahte(url: str, zaman_asimi: float) -> bytes:
        nonlocal cagri
        cagri += 1
        if cagri < 3:
            raise HTTPError(url, 503, "mesgul", Message(), None)
        return b'[{"id": "1"}]'

    kaynak = HttpSource("http://ornek", getir=sahte, bekle=lambda _: None)

    assert list(kaynak.oku()) == [{"id": "1"}]
    assert cagri == 3


def test_http_source_retry_after_basligina_uyuyor() -> None:
    cagri = 0
    beklemeler: list[float] = []

    def sahte(url: str, zaman_asimi: float) -> bytes:
        nonlocal cagri
        cagri += 1
        if cagri == 1:
            basliklar = Message()
            basliklar["Retry-After"] = "2"
            raise HTTPError(url, 429, "cok istek", basliklar, None)
        return b'[{"id": "1"}]'

    kaynak = HttpSource("http://ornek", getir=sahte, bekle=beklemeler.append)

    assert list(kaynak.oku()) == [{"id": "1"}]
    assert beklemeler == [2.0]


def test_retry_after_sayiya_cevrilemezse_ustel_geri_cekilme() -> None:
    cagri = 0
    beklemeler: list[float] = []

    def sahte(url: str, zaman_asimi: float) -> bytes:
        nonlocal cagri
        cagri += 1
        if cagri == 1:
            basliklar = Message()
            basliklar["Retry-After"] = "Wed, 21 Oct 2026 07:28:00 GMT"
            raise HTTPError(url, 429, "cok istek", basliklar, None)
        return b'[{"id": "1"}]'

    kaynak = HttpSource("http://ornek", getir=sahte, bekle=beklemeler.append)

    assert list(kaynak.oku()) == [{"id": "1"}]
    assert beklemeler == [0.5]


def test_http_source_tek_nesneyi_liste_yapiyor() -> None:
    def sahte(url: str, zaman_asimi: float) -> bytes:
        return b'{"id": "1", "ad": "kumru"}'

    kaynak = HttpSource("http://ornek", getir=sahte)

    assert list(kaynak.oku()) == [{"id": "1", "ad": "kumru"}]
