# mini-etl

CSV, JSONL ve HTTP kaynaklarını **akış hâlinde** okuyup dönüştüren, bozuk
kayıtları işi durdurmadan kenara ayıran küçük bir ETL kütüphanesi.

`mini_etl.core` yalnızca Python standart kütüphanesini kullanır.

## Ne yapar

- **Akış hâlinde çalışır.** Dosyanın tamamı belleğe alınmaz; bellek kullanımı
  dosya boyutundan bağımsızdır.
- **Bozuk kayıt işi öldürmez.** Hata veren satır reddedilir, sebebi ve hangi
  aşamada olduğu kaydedilir, akış kalan kayıtlarla devam eder.
- **Elemek ile reddetmek ayrılır.** Koşulu sağlamayan kayıt elenir (normal iş);
  koşulun kendisi patlarsa kayıt reddedilir (arıza). Rapor ikisini ayrı sayar.
- **Boru hattı veri olarak tanımlanabilir.** YAML dosyasıyla, kod yazmadan.

## Bileşenler

| Kaynak | Ne yapar |
| --- | --- |
| `CsvSource` | CSV dosyasını satır satır okur |
| `JsonlSource` | Her satırı bir JSON nesnesi olan dosyayı okur |
| `HttpSource` | HTTP uç noktasından JSON okur; geçici hatalarda (`429`, `5xx`, ağ) yeniden dener, `4xx`'te durur, `Retry-After`'a uyar |

| Dönüşüm | Ne yapar |
| --- | --- |
| `esle(f)` | Her kayda `f` uygular |
| `filtrele(kosul)` | Koşulu sağlamayanları **eler** |
| `dogrula(kosul, mesaj)` | Koşulu sağlamayanları **reddeder** |
| `yeniden_adlandir(esleme)` | Sütun adlarını değiştirir; çakışmayı reddeder |
| `tip_cevir(alanlar)` | Alanları verilen fonksiyonla çevirir |

Dönüşümler `>>` ile zincirlenir: `dogrula(...) >> tip_cevir(...)`

| Hedef | Ne yapar |
| --- | --- |
| `CsvSink` | CSV dosyasına yazar |
| `SqliteSink` | SQLite tablosuna parçalar hâlinde yazar |
| `StdoutSink` | JSONL olarak `stdout`'a yazar |

## Kurulum

```bash
uv sync --all-extras
```

## Kütüphane olarak

```python
from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import dogrula, tip_cevir

rapor = Pipeline(
    kaynak=CsvSource("girdi.csv"),
    hedef=CsvSink("cikti.csv"),
    donusum=dogrula(lambda k: k["id"] != "", "id bos olamaz") >> tip_cevir({"yas": int}),
    hata_dosyasi="hatalar.jsonl",
).calistir()

print(rapor.okunan, rapor.yazilan, rapor.reddedilen)
```

Reddedilen kayıtlar `hatalar.jsonl` dosyasına satır satır yazılır:

```json
{"kayit": {"id": "2", "yas": "abc"}, "hata": "ValueError: ...", "asama": "tip_cevir"}
```

Dosya yalnızca en az bir kayıt reddedilirse oluşturulur.

## YAML yapılandırma

```yaml
kaynak:
  tur: csv          # csv | jsonl | http
  yol: girdi.csv

donusumler:         # listede yazıldığı sırayla uygulanır
  - tur: zorunlu
    sutun: yas
  - tur: yeniden_adlandir
    esleme:
      ad: isim
  - tur: tip_cevir
    alanlar:
      yas: int      # int | float | str | bool

hedef:
  tur: stdout       # csv | sqlite | stdout

hatalar: bozuk.jsonl
```

```bash
uv run python -m mini_etl.cli --config pipeline.yaml
```

Yapılandırma **veri** olarak okunur: `yaml.safe_load` kullanılır ve tip
çeviriciler `eval` yerine bir beyaz listeden çözülür.

## Komut satırı

```bash
uv run python -m mini_etl.cli girdi.csv cikti.csv --zorunlu yas --sec id,ad
```

| Seçenek | Ne yapar |
| --- | --- |
| `--config p.yaml` | Boru hattını YAML dosyasından kurar |
| `--sec ad,yas` | Yalnızca bu sütunları tutar |
| `--zorunlu yas` | Bu sütunu boş olan kayıtları eler |
| `--hatalar h.jsonl` | Reddedilen kayıtları bu dosyaya yazar |
| `--log-seviye` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--duz-log` | JSON yerine insan okunabilir günlük |

Çıkış kodları:

| Kod | Anlamı |
| --- | --- |
| `0` | İş tamam, reddedilen yok |
| `1` | İş tamam, bazı kayıtlar reddedildi |
| `2` | Kurulum hatası — iş hiç başlamadı |

## Günlükleme

Günlükler `stderr`'e yazılır. Varsayılan biçim tek satırlık JSON:

```json
{"zaman": "...", "seviye": "INFO", "mesaj": "bitti", "okunan": 3, "yazilan": 2}
```

Kütüphane olarak kullanıldığında günlükçü sessizdir; açmak için:

```python
from mini_etl.gunluk import kur

kur(seviye="DEBUG")
```

`DEBUG` seviyesinde her reddedilen kayıt ayrı ayrı görünür.

## Bellek davranışı

`scripts/bellek.py` aynı işi iki yöntemle yapıp `tracemalloc` ile tepe belleği
ölçer.

| Satır | Dosya | Akış (mini-etl) | Hepsini belleğe al | Oran |
| --- | --- | --- | --- | --- |
| 20.000 | 0.36 MB | **0.23 MB** | 10.80 MB | 48x |
| 200.000 | 3.98 MB | **0.23 MB** | 108.17 MB | 479x |

Veri 10 kat arttığında naif yöntemin belleği 10 kat arttı; akışınki değişmedi.
Fark bir yüzde farkı değil, karmaşıklık farkı: `O(n)` yerine `O(1)`.

```bash
uv run python scripts/bellek.py --satir 500000
```

## Tasarım

Tasarım kararları, reddedilen alternatifler ve gerekçeleri
[DESIGN.md](DESIGN.md) dosyasında.

## Bilinen sınırlar

- Reddedilen kayıtlar bellekte biriktirilip iş sonunda yazılır. Akış garantisi
  yalnızca **başarılı** kayıtlar için geçerli.
- `HttpSource` yanıtın tamamını belleğe alır; akış garantisi taşımaz.
- Yeniden denemede jitter yok (thundering herd riski).
- `CsvSink` ve `SqliteSink` sütunları **ilk kayıttan** alır. Sonraki kayıtlarda
  farklı anahtarlar varsa yazım hata verir.
- Paralellik yok: tek süreç, tek çekirdek.

## Geliştirme

```bash
make install   # bağımlılıklar
make lint      # ruff check + ruff format --check + mypy
make test      # pytest + kapsam
```

`make lint` yerelde CI ile birebir aynı kontrolleri çalıştırır.
