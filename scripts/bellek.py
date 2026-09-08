"""Akış hâlinde işleme ile hepsini belleğe almanın bellek farkını ölçer.

Her yöntem ayrı bir süreçte çalışır: ru_maxrss sürecin tüm ömrü için bir
yüksek-su işaretidir, aynı süreçte iki yöntem ölçülemez.

İki bağımsız araçla ölçülür:
  - tracemalloc : yalnızca Python nesneleri, yalnızca bu süreç
  - ru_maxrss   : işletim sisteminin gördüğü gerçek tepe bellek
Saf Python kodunda ikisinin gösterdiği *fark* birbirine yakın olmalıdır.
"""

import argparse
import csv
import resource
import tempfile
import time
import tracemalloc
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import esle


def veri_uret(yol, satir):
    """Deneme için belirtilen sayıda satır içeren bir CSV üretir."""
    with yol.open("w", encoding="utf-8", newline="") as f:
        yazici = csv.writer(f)
        yazici.writerow(["id", "ad", "yas"])
        for i in range(satir):
            yazici.writerow([i, f"kisi{i}", 18 + (i % 60)])


def akisla(girdi, cikti):
    """mini-etl ile akış hâlinde işler."""
    Pipeline(
        kaynak=CsvSource(girdi),
        hedef=CsvSink(cikti),
        donusum=esle(lambda k: {**k, "yas": str(int(k["yas"]) + 1)}),
    ).calistir()


def hepsini_belege_al(girdi, cikti):
    """Önce tüm dosyayı listeye alır, sonra yazar."""
    with girdi.open(encoding="utf-8", newline="") as f:
        kayitlar = [dict(satir) for satir in csv.DictReader(f)]

    kayitlar = [{**k, "yas": str(int(k["yas"]) + 1)} for k in kayitlar]

    with cikti.open("w", encoding="utf-8", newline="") as f:
        yazici = csv.DictWriter(f, fieldnames=list(kayitlar[0].keys()))
        yazici.writeheader()
        yazici.writerows(kayitlar)


YONTEMLER = {"akis": akisla, "liste": hepsini_belege_al}


def _olc(yontem, girdi, cikti):
    """Bir yöntemi ölçer. Ayrı süreçte çalıştırılmak üzere yazıldı."""
    tracemalloc.start()
    baslangic = time.perf_counter()

    YONTEMLER[yontem](girdi, cikti)

    sure = time.perf_counter() - baslangic
    _, py_tepe = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    return {
        "sure": sure,
        "python_tepe": py_tepe / 1024 / 1024,
        "surec_tepe": rss_kb / 1024,
    }


def olc_ayri_surecte(yontem, girdi, cikti):
    """Ölçümü taze bir süreçte yapar ve sonucu geri alır."""
    with ProcessPoolExecutor(max_workers=1) as havuz:
        return havuz.submit(_olc, yontem, girdi, cikti).result()


def main():
    """Ölçümü çalıştırır ve tabloyu basar."""
    p = argparse.ArgumentParser(description="Bellek karsilastirmasi")
    p.add_argument("--satir", type=int, default=200_000, help="satir sayisi")
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as gecici:
        klasor = Path(gecici)
        girdi = klasor / "girdi.csv"
        veri_uret(girdi, args.satir)
        boyut = girdi.stat().st_size / 1024 / 1024

        akis = olc_ayri_surecte("akis", girdi, klasor / "akis.csv")
        liste = olc_ayri_surecte("liste", girdi, klasor / "liste.csv")

    print(f"satir sayisi : {args.satir:,}")
    print(f"dosya boyutu : {boyut:.2f} MB")
    print()
    print(f"{'yontem':<8}{'sure':>9}{'tracemalloc':>14}{'surec RSS':>12}")
    for ad, olcum in (("akis", akis), ("liste", liste)):
        print(
            f"{ad:<8}{olcum['sure']:>8.2f}s"
            f"{olcum['python_tepe']:>13.2f}M"
            f"{olcum['surec_tepe']:>11.1f}M"
        )
    print()
    tm_fark = liste["python_tepe"] - akis["python_tepe"]
    rss_fark = liste["surec_tepe"] - akis["surec_tepe"]
    print(f"tracemalloc farki : {tm_fark:>8.1f} MB")
    print(f"surec RSS farki   : {rss_fark:>8.1f} MB")
    print(f"uyum              : {min(tm_fark, rss_fark) / max(tm_fark, rss_fark):>8.0%}")


if __name__ == "__main__":
    main()
