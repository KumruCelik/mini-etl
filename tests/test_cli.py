from pathlib import Path

import pytest

from mini_etl.cli import main


@pytest.fixture
def girdi(tmp_path: Path) -> Path:
    """id, ad, yas sütunlu; bir satırında yas boş olan CSV."""
    yol = tmp_path / "g.csv"
    yol.write_text("id,ad,yas\n1,kumru,22\n2,emre,\n3,ayse,31\n", encoding="utf-8")
    return yol


def test_cli_dosyayi_kopyaliyor(girdi: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "c.csv"

    kod = main([str(girdi), str(cikti)])

    assert kod == 0
    assert len(cikti.read_text(encoding="utf-8").splitlines()) == 4


def test_cli_zorunlu_bos_kaydi_eliyor(girdi: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "c.csv"

    kod = main([str(girdi), str(cikti), "--zorunlu", "yas"])

    assert kod == 0
    assert len(cikti.read_text(encoding="utf-8").splitlines()) == 3


def test_cli_sec_sutunlari_kisitliyor(girdi: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "c.csv"

    main([str(girdi), str(cikti), "--sec", "id,ad"])

    assert cikti.read_text(encoding="utf-8").splitlines()[0] == "id,ad"


def test_cli_eksik_girdi_iki_donduruyor(tmp_path: Path) -> None:
    kod = main([str(tmp_path / "yok.csv"), str(tmp_path / "c.csv")])

    assert kod == 2


def test_cli_reddedilen_varsa_bir_donduruyor(girdi: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "c.csv"
    hatalar = tmp_path / "h.jsonl"

    kod = main([str(girdi), str(cikti), "--zorunlu", "olmayan", "--hatalar", str(hatalar)])

    assert kod == 1
    assert len(hatalar.read_text(encoding="utf-8").splitlines()) == 3


def test_cli_iki_bayrak_zincirleniyor(girdi: Path, tmp_path: Path) -> None:
    cikti = tmp_path / "c.csv"

    kod = main([str(girdi), str(cikti), "--zorunlu", "yas", "--sec", "id,ad"])

    satirlar = cikti.read_text(encoding="utf-8").splitlines()

    assert kod == 0
    assert satirlar == ["id,ad", "1,kumru", "3,ayse"]
