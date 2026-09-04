from collections.abc import Iterator

from mini_etl.core.record import Rapor, Record
from mini_etl.core.transform import Transform, esle, filtrele


def test_transform_verilen_islemi_calistiriyor() -> None:
    def buyut(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        for kayit in akis:
            yield {**kayit, "ad": kayit["ad"].upper()}

    t = Transform(buyut)

    sonuc = list(t(iter([{"ad": "kumru"}]), Rapor()))

    assert sonuc == [{"ad": "KUMRU"}]


def test_rshift_iki_donusumu_sirayla_uyguluyor() -> None:
    def buyut(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        for kayit in akis:
            yield {**kayit, "ad": kayit["ad"].upper()}

    def unlem_ekle(akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        for kayit in akis:
            yield {**kayit, "ad": kayit["ad"] + "!"}

    zincir = Transform(buyut) >> Transform(unlem_ekle)

    sonuc = list(zincir(iter([{"ad": "kumru"}]), Rapor()))

    assert sonuc == [{"ad": "KUMRU!"}]


def test_esle_her_kayda_uyguluyor() -> None:
    donusum = esle(lambda k: {**k, "ad": k["ad"].upper()})

    sonuc = list(donusum(iter([{"ad": "kumru"}, {"ad": "yavuz"}]), Rapor()))

    assert sonuc == [{"ad": "KUMRU"}, {"ad": "YAVUZ"}]


def test_filtrele_kosulu_saglamayanlari_atiyor() -> None:
    donusum = filtrele(lambda k: int(k["yas"]) >= 18)

    sonuc = list(donusum(iter([{"yas": "20"}, {"yas": "15"}, {"yas": "30"}]), Rapor()))

    assert sonuc == [{"yas": "20"}, {"yas": "30"}]


def test_esle_ve_filtrele_zincirlenebiliyor() -> None:
    suz = filtrele(lambda k: int(k["yas"]) >= 18)
    isaretle = esle(lambda k: {**k, "yetiskin": True})
    hat = suz >> isaretle

    sonuc = list(hat(iter([{"yas": "20"}, {"yas": "15"}, {"yas": "30"}]), Rapor()))

    assert sonuc == [
        {"yas": "20", "yetiskin": True},
        {"yas": "30", "yetiskin": True},
    ]


def test_esle_bozuk_kaydi_reddediyor() -> None:
    rapor = Rapor()
    donusum = esle(lambda k: {**k, "yas": int(k["yas"]) + 1})

    sonuc = list(donusum(iter([{"yas": "20"}, {"yas": "abc"}, {"yas": "30"}]), rapor))

    assert len(sonuc) == 2
    assert rapor.reddedilen == 1


def test_reddedilen_kaydin_sebebi_ve_asamasi_saklaniyor() -> None:
    rapor = Rapor()
    donusum = esle(lambda k: {**k, "yas": int(k["yas"]) + 1})

    list(donusum(iter([{"yas": "abc"}]), rapor))

    hata = rapor.hatalar[0]

    assert hata.kayit == {"yas": "abc"}
    assert hata.asama == "esle"
    assert "ValueError" in hata.hata


def test_filtrele_elemeyi_reddetmekten_ayiriyor() -> None:
    rapor = Rapor()
    donusum = filtrele(lambda k: int(k["yas"]) > 18)

    sonuc = list(donusum(iter([{"yas": "20"}, {"yas": "15"}, {"yas": "abc"}]), rapor))

    assert len(sonuc) == 1
    assert rapor.reddedilen == 1
