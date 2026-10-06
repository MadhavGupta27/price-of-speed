import pandas as pd
import pytest

from orpaper.biblio import merge_citations, normalise_doi, prisma_counts, shortlist_core


def test_prisma_counts():
    log = pd.DataFrame({
        "source_db": ["EBSCO"] * 5,
        "duplicate": ["no", "yes", "no", "no", ""],
        "decision": ["include", "", "exclude", "include", ""],
        "exclusion_reason": ["", "", "student thesis", "", ""],
        "document_type": ["article", "article", "thesis", "article", "article"],
    })
    c = prisma_counts(log)
    assert c["identified"] == 5
    assert c["duplicates_removed"] == 1
    assert c["screened"] == 4
    assert c["included"] == 2
    assert c["excluded_by_reason"] == {"student thesis": 1}
    assert c["pending"] == 1


def test_normalise_doi():
    assert normalise_doi("https://doi.org/10.1/ABC") == "10.1/abc"
    assert normalise_doi(float("nan")) == ""


def test_merge_by_doi_then_title():
    recs = pd.DataFrame({"TI": ["Paper One", "Paper: Two!", "Paper Three"],
                         "DI": ["10.1/a", "", ""], "PY": [2020, 2021, 2022]})
    pop = pd.DataFrame({"Title": ["paper one (preprint)", "Paper Two", "Other"],
                        "DOI": ["10.1/A", "", ""], "Cites": [10, 5, 99]})
    m = merge_citations(recs, pop, "2026-10-06")
    assert m["GS_TC"].tolist()[:2] == [10, 5]
    assert pd.isna(m["GS_TC"].iloc[2])
    assert m["GS_match"].tolist() == ["doi", "title", "UNMATCHED"]


def test_shortlist_favours_citations_per_year():
    recs = pd.DataFrame({"TI": ["old", "new"], "PY": [2010, 2024], "GS_TC": [100, 30]})
    s = shortlist_core(recs, n=1, current_year=2025)
    assert s["TI"].iloc[0] == "new"  # 15/yr beats ~6.25/yr
