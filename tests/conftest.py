from pathlib import Path

import pytest


@pytest.fixture
def ornek_csv(tmp_path: Path) -> Path:
    """Üç sütunlu, iki satırlık örnek CSV dosyası."""
    yol = tmp_path / "ornek.csv"
    yol.write_text(
        "id,ad,sehir\n1,kumru,elazig\n2,elif,ankara\n",
        encoding="utf-8",
    )
    return yol


@pytest.fixture
def bos_csv(tmp_path: Path) -> Path:
    """Sadece başlık satırı olan CSV."""
    yol = tmp_path / "bos.csv"
    yol.write_text("id,ad\n", encoding="utf-8")
    return yol


@pytest.fixture
def ornek_jsonl(tmp_path: Path) -> Path:
    """Her satırı bir JSON nesnesi olan örnek dosya."""
    yol = tmp_path / "ornek.jsonl"
    yol.write_text(
        '{"id": "1", "ad": "kumru"}\n{"id": "2", "ad": "elif"}\n',
        encoding="utf-8",
    )
    return yol


@pytest.fixture
def virgullu_csv(tmp_path: Path) -> Path:
    """Bir alanın içinde virgül geçen CSV."""
    yol = tmp_path / "virgullu.csv"
    yol.write_text(
        'id,aciklama\n1,"HANDS, FISTS, FEET"\n',
        encoding="utf-8",
    )
    return yol
