# mini-etl

CSV ve JSONL dosyalarını **akış hâlinde** okuyup dönüştüren, bozuk kayıtları
işi durdurmadan kenara ayıran küçük bir ETL kütüphanesi.

Çekirdek yalnızca Python standart kütüphanesini kullanır.

## Ne yapar

- **Akış hâlinde çalışır.** Dosyanın tamamı belleğe alınmaz; bellek kullanımı
  dosya boyutundan bağımsızdır.
- **Bozuk kayıt işi öldürmez.** Hata veren satır reddedilir, sebebi ve hangi
  aşamada olduğu kaydedilir, akış kalan kayıtlarla devam eder.
- **Elemek ile reddetmek ayrılır.** Koşulu sağlamayan kayıt elenir (normal iş);
  koşulun kendisi patlarsa kayıt reddedilir (arıza). Rapor ikisini ayrı sayar.
- **Dönüşümler zincirlenir.** `filtrele(...) >> esle(...)`

## Kurulum

```bash
uv sync --all-extras
```

## Kütüphane olarak

```python
from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import esle, filtrele

rapor = Pipeline(
    kaynak=CsvSource("girdi.csv"),
    hedef=CsvSink("cikti.csv"),
    donusum=filtrele(lambda k: int(k["yas"]) >= 18) >> esle(lambda k: {**k, "yetiskin": True}),
    hata_dosyasi="hatalar.jsonl",
).calistir()

print(rapor.okunan, rapor.yazilan, rapor.reddedilen)
```

Reddedilen kayıtlar `hatalar.jsonl` dosyasına satır satır yazılır:

```json
{"kayit": {"id": "2", "yas": "abc"}, "hata": "ValueError: ...", "asama": "esle"}
```

Dosya yalnızca en az bir kayıt reddedilirse oluşturulur.

## Komut satırı

```bash
uv run python -m mini_etl.cli girdi.csv cikti.csv --zorunlu yas --sec id,ad
```

| Seçenek | Ne yapar |
| --- | --- |
| `--sec ad,yas` | Yalnızca bu sütunları tutar |
| `--zorunlu yas` | Bu sütunu boş olan kayıtları eler |
| `--hatalar h.jsonl` | Reddedilen kayıtları bu dosyaya yazar |

Rapor `stderr`e basılır. Çıkış kodları:

| Kod | Anlamı |
| --- | --- |
| `0` | İş tamam, reddedilen yok |
| `1` | İş tamam, bazı kayıtlar reddedildi |
| `2` | Kullanım hatası (girdi dosyası yok) — iş hiç başlamadı |

## Bellek davranışı

`scripts/bellek.py` aynı işi iki yöntemle yapıp `tracemalloc` ile tepe belleği
ölçer.

| Satır | Dosya | Akış (mini-etl) | Hepsini belleğe al | Oran |
| --- | --- | --- | --- | --- |
| 20.000 | 0.36 MB | **0.23 MB** | 10.80 MB | 48x |
| 200.000 | 3.98 MB | **0.23 MB** | 108.17 MB | 479x |

Veri 10 kat arttığında naif yöntemin belleği 10 kat arttı; akışınki değişmedi.
Fark bir yüzde farkı değil, karmaşıklık farkı: `O(n)` yerine `O(1)`.

Kendin ölçmek için:

```bash
uv run python scripts/bellek.py --satir 500000
```

## Tasarım

Tasarım kararları, reddedilen alternatifler ve gerekçeleri
[DESIGN.md](DESIGN.md) dosyasında.

## Bilinen sınırlar

- Reddedilen kayıtlar bellekte biriktirilip iş sonunda yazılır. Reddedilen
  oranı çok yüksekse bellek şişer. Doğru çözüm hataları anında akıtmaktır.
- `CsvSink` sütun başlıklarını **ilk kaydın** anahtarlarından alır. Sonraki
  kayıtlarda farklı anahtarlar varsa yazım hata verir.
- Yalnızca CSV yazılabilir. `Sink` protokolü yeni format eklemeyi mümkün kılar
  (yeni sınıf, ~15 satır, çekirdekte değişiklik yok) ama bu sürümde yapılmadı.

## Geliştirme

```bash
make install   # bağımlılıklar
make lint      # ruff check + ruff format --check + mypy
make test      # pytest
```

`make lint` yerelde CI ile birebir aynı kontrolleri çalıştırır.
