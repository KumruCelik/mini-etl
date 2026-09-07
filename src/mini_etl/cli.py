"""mini-etl komut satırı arayüzü."""

import argparse
import sys
from pathlib import Path

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import Transform, esle, filtrele
from mini_etl.gunluk import KAYITCI, kur


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
    p.add_argument(
        "--log-seviye",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="gunluk seviyesi",
    )
    p.add_argument("--duz-log", action="store_true", help="JSON yerine duz metin")
    return p


def main(argv: list[str] | None = None) -> int:
    """Programı çalıştırır ve çıkış kodunu döndürür."""
    args = ayristirici().parse_args(argv)
    kur(seviye=args.log_seviye, json_bicim=not args.duz_log)

    if not args.girdi.exists():
        KAYITCI.error("girdi dosyasi bulunamadi", extra={"ek": {"yol": str(args.girdi)}})
        return 2

    rapor = Pipeline(
        kaynak=CsvSource(args.girdi),
        hedef=CsvSink(args.cikti),
        donusum=donusum_kur(args),
        hata_dosyasi=args.hatalar,
    ).calistir()

    return 1 if rapor.reddedilen else 0


if __name__ == "__main__":
    sys.exit(main())
