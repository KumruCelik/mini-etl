import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.record import Rapor, Record
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import esle, filtrele

ANAHTAR = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=4,
)

DEGER = st.text(
    alphabet=st.characters(exclude_categories=("Cc", "Cs", "Zl", "Zp")),
    max_size=8,
)


@st.composite
def kayit_listesi(draw: st.DrawFn) -> list[dict[str, str]]:
    """Aynı anahtarlara sahip 1-10 kayıtlık listeler üretir."""
    anahtarlar = draw(st.lists(ANAHTAR, min_size=1, max_size=3, unique=True))
    kayit = st.fixed_dictionaries(dict.fromkeys(anahtarlar, DEGER))
    return draw(st.lists(kayit, min_size=1, max_size=10))


@given(kayitlar=kayit_listesi())
def test_yaz_oku_gidis_donus(kayitlar: list[dict[str, str]]) -> None:
    """Yazılan her kayıt, geri okununca aynı çıkmalı."""
    with tempfile.TemporaryDirectory() as klasor:
        yol = Path(klasor) / "t.csv"

        CsvSink(yol).yaz(iter(kayitlar))
        geri = list(CsvSource(yol).oku())

    assert geri == kayitlar


def bos_deger_varsa_patla(kayit: Record) -> Record:
    """Boş değer içeren kaydı reddettirir."""
    if any(deger == "" for deger in kayit.values()):
        raise ValueError("bos deger")
    return kayit


@given(kayitlar=kayit_listesi())
def test_hicbir_kayit_kaybolmuyor(kayitlar: list[dict[str, str]]) -> None:
    """Okunan her kayıt ya yazılmış ya reddedilmiş olmalı."""
    with tempfile.TemporaryDirectory() as klasor:
        yol = Path(klasor)
        girdi = yol / "g.csv"
        CsvSink(girdi).yaz(iter(kayitlar))

        rapor = Pipeline(
            kaynak=CsvSource(girdi),
            hedef=CsvSink(yol / "c.csv"),
            donusum=esle(bos_deger_varsa_patla),
        ).calistir()

    assert rapor.okunan == rapor.yazilan + rapor.reddedilen


@given(kayitlar=kayit_listesi())
def test_zincirleme_birlesme_ozelligi(kayitlar: list[dict[str, str]]) -> None:
    """(a >> b) >> c ile a >> (b >> c) aynı sonucu vermeli."""
    a = esle(lambda k: {**k, "x": "1"})
    b = filtrele(lambda k: "" not in k.values())
    c = esle(lambda k: {**k, "y": "2"})

    sol = list(((a >> b) >> c)(iter(kayitlar), Rapor()))
    sag = list((a >> (b >> c))(iter(kayitlar), Rapor()))

    assert sol == sag
