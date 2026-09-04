"""Akış hâlinde işleme ile hepsini belleğe almanın bellek farkını ölçer."""

import argparse
import csv
import tempfile
import tracemalloc
from pathlib import Path

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import esle


def veri_uret(yol: Path, satir: int) -> None:
    """Deneme için belirtilen sayıda satır içeren bir CSV üretir."""
    with yol.open("w", encoding="utf-8", newline="") as f:
        yazici = csv.writer(f)
        yazici.writerow(["id", "ad", "yas"])
        for i in range(satir):
            yazici.writerow([i, f"kisi{i}", 18 + (i % 60)])


def akisla(girdi: Path, cikti: Path) -> int:
    """mini-etl ile akış hâlinde işler; tepe belleği bayt olarak döndürür."""
    tracemalloc.start()

    Pipeline(
        kaynak=CsvSource(girdi),
        hedef=CsvSink(cikti),
        donusum=esle(lambda k: {**k, "yas": str(int(k["yas"]) + 1)}),
    ).calistir()

    _, tepe = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return tepe


def hepsini_belege_al(girdi: Path, cikti: Path) -> int:
    """Önce tüm dosyayı listeye alır, sonra yazar; tepe belleği döndürür."""
    tracemalloc.start()

    with girdi.open(encoding="utf-8", newline="") as f:
        kayitlar = [dict(satir) for satir in csv.DictReader(f)]

    kayitlar = [{**k, "yas": str(int(k["yas"]) + 1)} for k in kayitlar]

    with cikti.open("w", encoding="utf-8", newline="") as f:
        yazici = csv.DictWriter(f, fieldnames=list(kayitlar[0].keys()))
        yazici.writeheader()
        yazici.writerows(kayitlar)

    _, tepe = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return tepe


def mb(bayt: int) -> str:
    """Baytı okunabilir MB metnine çevirir."""
    return f"{bayt / 1024 / 1024:.2f} MB"


def main() -> None:
    """Ölçümü çalıştırır ve tabloyu basar."""
    p = argparse.ArgumentParser(description="Bellek karsilastirmasi")
    p.add_argument("--satir", type=int, default=200_000, help="uretilecek satir sayisi")
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as gecici:
        klasor = Path(gecici)
        girdi = klasor / "girdi.csv"

        veri_uret(girdi, args.satir)
        boyut = girdi.stat().st_size

        akis_tepe = akisla(girdi, klasor / "akis.csv")
        liste_tepe = hepsini_belege_al(girdi, klasor / "liste.csv")

    print(f"satir sayisi      : {args.satir:,}")
    print(f"dosya boyutu      : {mb(boyut)}")
    print(f"akis (mini-etl)   : {mb(akis_tepe)}")
    print(f"hepsini belege al : {mb(liste_tepe)}")
    print(f"oran              : {liste_tepe / akis_tepe:.0f}x")


if __name__ == "__main__":
    main()
