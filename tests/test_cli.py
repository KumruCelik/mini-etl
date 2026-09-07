import json
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


def test_cli_ozeti_json_gunluk_olarak_yaziyor(
    girdi: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([str(girdi), str(tmp_path / "c.csv")])

    son_satir = capsys.readouterr().err.splitlines()[-1]
    govde = json.loads(son_satir)

    assert govde["mesaj"] == "bitti"
    assert govde["okunan"] == 3


def test_cli_config_ile_calisiyor(tmp_path: Path) -> None:
    girdi = tmp_path / "g.csv"
    girdi.write_text("id,ad\n1,kumru\n", encoding="utf-8")
    cikti = tmp_path / "c.csv"
    ayar = tmp_path / "p.yaml"
    ayar.write_text(
        f"kaynak:\n  tur: csv\n  yol: {girdi}\nhedef:\n  tur: csv\n  yol: {cikti}\n",
        encoding="utf-8",
    )

    kod = main(["--config", str(ayar)])

    assert kod == 0
    assert cikti.read_text(encoding="utf-8").splitlines() == ["id,ad", "1,kumru"]


def test_cli_olmayan_config_iki_donduruyor(tmp_path: Path) -> None:
    assert main(["--config", str(tmp_path / "yok.yaml")]) == 2


def test_cli_argumansiz_cagri_iki_donduruyor() -> None:
    assert main([]) == 2
