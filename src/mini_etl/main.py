def top_n(values: list[str], n: int) -> list[tuple[str, int]]:
    """Frekansa göre en sık geçen n değeri döndürür."""
    sayac: dict[str, int] = {}
    for v in values:
        sayac[v] = sayac.get(v, 0) + 1

    siralanmis = sorted(sayac.items(), key=lambda cift: cift[1], reverse=True)
    return siralanmis[:n]
