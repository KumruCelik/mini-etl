from collections.abc import Iterator

from mini_etl.core.record import Record
from mini_etl.core.transform import Transform, esle, filtrele


def test_transform_verilen_islemi_calistiriyor() -> None:
    def buyut(akis: Iterator[Record]) -> Iterator[Record]:
        for kayit in akis:
            yield {**kayit, "ad": kayit["ad"].upper()}

    t = Transform(buyut)

    sonuc = list(t(iter([{"ad": "kumru"}])))

    assert sonuc == [{"ad": "KUMRU"}]


def test_rshift_iki_donusumu_sirayla_uyguluyor() -> None:
    def buyut(akis: Iterator[Record]) -> Iterator[Record]:
        for kayit in akis:
            yield {**kayit, "ad": kayit["ad"].upper()}

    def unlem_ekle(akis: Iterator[Record]) -> Iterator[Record]:
        for kayit in akis:
            yield {**kayit, "ad": kayit["ad"] + "!"}

    zincir = Transform(buyut) >> Transform(unlem_ekle)

    sonuc = list(zincir(iter([{"ad": "kumru"}])))

    assert sonuc == [{"ad": "KUMRU!"}]


def test_esle_her_kayda_uyguluyor() -> None:
    donusum = esle(lambda k: {**k, "ad": k["ad"].upper()})

    sonuc = list(donusum(iter([{"ad": "kumru"}, {"ad": "elif"}])))

    assert sonuc == [{"ad": "KUMRU"}, {"ad": "ELIF"}]


def test_filtrele_kosulu_saglamayanlari_atiyor() -> None:
    donusum = filtrele(lambda k: int(k["yas"]) >= 18)

    sonuc = list(donusum(iter([{"yas": "20"}, {"yas": "15"}, {"yas": "30"}])))

    assert sonuc == [{"yas": "20"}, {"yas": "30"}]


def test_esle_ve_filtrele_zincirlenebiliyor() -> None:
    hat = filtrele(lambda k: int(k["yas"]) >= 18) >> esle(lambda k: {**k, "yetiskin": True})

    sonuc = list(hat(iter([{"yas": "20"}, {"yas": "15"}, {"yas": "30"}])))

    assert sonuc == [
        {"yas": "20", "yetiskin": True},
        {"yas": "30", "yetiskin": True},
    ]
