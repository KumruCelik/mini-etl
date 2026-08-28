from dev_setup.main import top_n


def test_normal():
    assert top_n(["a", "b", "a"], 2) == [("a", 2), ("b", 1)]


def test_bos_liste():
    assert top_n([], 3) == []


def test_n_eleman_sayisindan_buyuk():
    assert len(top_n(["a", "b"], 10)) == 2
