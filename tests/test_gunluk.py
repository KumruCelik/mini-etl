import io
import json
import logging

from mini_etl.gunluk import KAYITCI, kur


def test_gunluk_satiri_gecerli_json() -> None:
    tampon = io.StringIO()
    kur(akis=tampon)

    KAYITCI.info("deneme")

    govde = json.loads(tampon.getvalue())

    assert govde["mesaj"] == "deneme"
    assert govde["seviye"] == "INFO"
    assert "zaman" in govde


def test_ek_alanlar_ciktiya_giriyor() -> None:
    tampon = io.StringIO()
    kur(akis=tampon)

    KAYITCI.info("bitti", extra={"ek": {"okunan": 3, "yazilan": 2}})

    govde = json.loads(tampon.getvalue())

    assert govde["okunan"] == 3
    assert govde["yazilan"] == 2


def test_seviye_altindaki_mesajlar_yazilmiyor() -> None:
    tampon = io.StringIO()
    kur(seviye="WARNING", akis=tampon)

    KAYITCI.info("gorunmemeli")
    KAYITCI.warning("gorunmeli")

    satirlar = tampon.getvalue().splitlines()

    assert len(satirlar) == 1
    assert json.loads(satirlar[0])["mesaj"] == "gorunmeli"


def test_kur_iki_kez_cagrilinca_satir_tekrarlanmiyor() -> None:
    tampon = io.StringIO()
    kur(akis=tampon)
    kur(akis=tampon)

    KAYITCI.info("bir kez")

    assert len(tampon.getvalue().splitlines()) == 1

    logging.getLogger("mini_etl").handlers.clear()


def test_duz_bicim_anahtar_deger_yaziyor() -> None:
    tampon = io.StringIO()
    kur(json_bicim=False, akis=tampon)

    KAYITCI.info("bitti", extra={"ek": {"okunan": 3}})

    assert tampon.getvalue().strip() == "INFO bitti okunan=3"


def test_istisna_bilgisi_ciktiya_giriyor() -> None:
    tampon = io.StringIO()
    kur(akis=tampon)

    try:
        raise ValueError("deneme hatasi")
    except ValueError:
        KAYITCI.exception("patladi")

    govde = json.loads(tampon.getvalue())

    assert govde["mesaj"] == "patladi"
    assert "ValueError: deneme hatasi" in govde["hata"]
