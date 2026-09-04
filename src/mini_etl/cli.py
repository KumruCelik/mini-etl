"""mini-etl komut satırı arayüzü."""

import argparse
import sys
from pathlib import Path

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import Transform, esle, filtrele


def sutun_sec(sutunlar: list[str]) -> Transform:
    """Sadece verilen sütunları tutar."""
    return esle(lambda k: {s: k[s] for s in sutunlar}, ad="sec")


def dolu_olsun(sutun: str) -> Transform:
    """Verilen sütunu boş olan kayıtları eler."""
    return filtrele(lambda k: str(k[sutun]).strip() != "", ad="zorunlu")


def donusum_kur(args: argparse.Namespace) -> Transform | None:
    """Bayraklardan bir dönüşüm zinciri kurar."""
    adimlar: list[Transform] = []

    if args.zorunlu:
        adimlar.append(dolu_olsun(args.zorunlu))
    if args.sec:
        adimlar.append(sutun_sec(args.sec.split(",")))

    if not adimlar:
        return None

    zincir = adimlar[0]
    for adim in adimlar[1:]:
        zincir = zincir >> adim
    return zincir


def ayristirici() -> argparse.ArgumentParser:
    """Komut satırı seçeneklerini tanımlar."""
    p = argparse.ArgumentParser(
        prog="mini-etl",
        description="CSV dosyalarini akis halinde okur, donusturur ve yazar.",
    )
    p.add_argument("girdi", type=Path, help="okunacak CSV dosyasi")
    p.add_argument("cikti", type=Path, help="yazilacak CSV dosyasi")
    p.add_argument("--sec", help="sadece bu sutunlari tut (virgulle ayrilmis)")
    p.add_argument("--zorunlu", help="bu sutunu bos olan kayitlari ele")
    p.add_argument("--hatalar", type=Path, help="reddedilen kayitlar icin JSONL dosyasi")
    return p


def main(argv: list[str] | None = None) -> int:
    """Programı çalıştırır ve çıkış kodunu döndürür."""
    args = ayristirici().parse_args(argv)

    if not args.girdi.exists():
        print(f"hata: girdi dosyasi bulunamadi: {args.girdi}", file=sys.stderr)
        return 2

    rapor = Pipeline(
        kaynak=CsvSource(args.girdi),
        hedef=CsvSink(args.cikti),
        donusum=donusum_kur(args),
        hata_dosyasi=args.hatalar,
    ).calistir()

    print(
        f"okunan={rapor.okunan} yazilan={rapor.yazilan} "
        f"reddedilen={rapor.reddedilen} sure={rapor.sure:.3f}s",
        file=sys.stderr,
    )
    return 1 if rapor.reddedilen else 0


if __name__ == "__main__":
    sys.exit(main())
