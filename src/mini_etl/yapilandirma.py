"""YAML yapılandırmasından boru hattı kurar."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink, Sink, SqliteSink, StdoutSink
from mini_etl.core.source import CsvSource, HttpSource, JsonlSource, Source
from mini_etl.core.transform import (
    Transform,
    dogrula,
    esle,
    filtrele,
    metinden_bool,
    tip_cevir,
    yeniden_adlandir,
)

TIPLER: dict[str, Callable[[str], Any]] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": metinden_bool,
}


def kaynak_kur(tanim: dict[str, Any]) -> Source:
    """Tanımdan bir kaynak nesnesi üretir."""
    tur = tanim["tur"]
    if tur == "csv":
        return CsvSource(tanim["yol"], tanim.get("ayirac", ","))
    if tur == "jsonl":
        return JsonlSource(tanim["yol"])
    if tur == "http":
        return HttpSource(tanim["url"], deneme=tanim.get("deneme", 3))
    raise ValueError(f"bilinmeyen kaynak turu: {tur!r}")


def hedef_kur(tanim: dict[str, Any]) -> Sink:
    """Tanımdan bir hedef nesnesi üretir."""
    tur = tanim["tur"]
    if tur == "csv":
        return CsvSink(tanim["yol"])
    if tur == "sqlite":
        return SqliteSink(tanim["yol"], tanim.get("tablo", "kayitlar"))
    if tur == "stdout":
        return StdoutSink()
    raise ValueError(f"bilinmeyen hedef turu: {tur!r}")


def _adim_kur(tanim: dict[str, Any]) -> Transform:
    """Tek bir dönüşüm adımı üretir."""
    tur = tanim["tur"]

    if tur == "sec":
        sutunlar = list(tanim["sutunlar"])
        return esle(lambda k: {s: k[s] for s in sutunlar}, ad="sec")

    if tur == "zorunlu":
        sutun = tanim["sutun"]
        return filtrele(lambda k: str(k[sutun]).strip() != "", ad="zorunlu")

    if tur == "dogrula":
        alan = tanim["sutun"]
        return dogrula(lambda k: str(k[alan]).strip() != "", f"{alan} bos olamaz")

    if tur == "yeniden_adlandir":
        return yeniden_adlandir(dict(tanim["esleme"]))

    if tur == "tip_cevir":
        return tip_cevir({a: TIPLER[t] for a, t in tanim["alanlar"].items()})

    raise ValueError(f"bilinmeyen donusum turu: {tur!r}")


def donusum_zinciri(tanimlar: list[dict[str, Any]]) -> Transform | None:
    """Tanım listesinden bir dönüşüm zinciri kurar."""
    adimlar = [_adim_kur(t) for t in tanimlar]
    if not adimlar:
        return None

    zincir = adimlar[0]
    for adim in adimlar[1:]:
        zincir = zincir >> adim
    return zincir


def boru_kur(yapilandirma: dict[str, Any]) -> Pipeline:
    """Yapılandırma sözlüğünden bir Pipeline kurar."""
    return Pipeline(
        kaynak=kaynak_kur(yapilandirma["kaynak"]),
        hedef=hedef_kur(yapilandirma["hedef"]),
        donusum=donusum_zinciri(yapilandirma.get("donusumler", [])),
        hata_dosyasi=yapilandirma.get("hatalar"),
    )


def dosyadan_yukle(yol: Path | str) -> Pipeline:
    """YAML dosyasından bir Pipeline kurar."""
    metin = Path(yol).read_text(encoding="utf-8")
    return boru_kur(yaml.safe_load(metin))
