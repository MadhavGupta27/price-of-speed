"""Merge screening decisions (biblio/screening/decisions_*.json) into the screening log.

    uv run python scripts/merge_screening.py

Each decisions file holds one object per record: openalex_id, decision, exclusion_reason,
uncertain, and coding fields (problem, method, data, region, finding). Writes
biblio/screening_log.csv (PRISMA input) and biblio/screened_records.csv (records + coding).
"""

import glob
import json

import pandas as pd

from orpaper.config import ROOT


def main():
    files = sorted(glob.glob(str(ROOT / "biblio/screening/decisions_*.json")))
    dec = pd.concat([pd.DataFrame(json.load(open(f))) for f in files])
    rec = pd.read_csv(ROOT / "biblio/openalex_records.csv")
    missing = set(rec["openalex_id"]) - set(dec["openalex_id"])
    if missing or dec["openalex_id"].duplicated().any():
        raise SystemExit(f"Screening incomplete: {len(missing)} records missing, "
                         f"{int(dec['openalex_id'].duplicated().sum())} duplicated decisions")
    # Records flagged uncertain were re-screened by an independent second pass
    # (biblio/screening/second_pass.json); its decision is adopted (adjudication rule).
    sp_file = ROOT / "biblio/screening/second_pass.json"
    if sp_file.exists():
        sp = pd.DataFrame(json.load(open(sp_file))).set_index("openalex_id")
        dec = dec.set_index("openalex_id")
        changed = (dec.loc[sp.index, "decision"] != sp["decision"]).sum()
        dec.loc[sp.index, "decision"] = sp["decision"]
        dec.loc[sp.index, "exclusion_reason"] = sp["exclusion_reason"]
        dec.loc[sp.index, "second_pass_rationale"] = sp["rationale"]
        dec = dec.reset_index()
        print(f"second pass: {len(sp)} flagged records re-screened, {int(changed)} decisions changed")
    m = rec.merge(dec, on="openalex_id", how="left")
    log = pd.DataFrame({
        "record_id": m["openalex_id"], "source_db": "OpenAlex", "search_page": "", "title": m["title"],
        "authors": m["authors"], "year": m["year"], "journal": m["journal"], "doi": m["doi"],
        "document_type": "journal article", "duplicate": m["duplicate"].map({True: "yes", False: "no"}),
        "decision": m["decision"], "exclusion_reason": m["exclusion_reason"].fillna(""),
        "screener": "LLM-assisted (Claude), title/abstract; flagged records second-pass reviewed",
        "notes": m["uncertain"].map({True: "flagged; resolved by second-pass review", False: ""})})
    log.to_csv(ROOT / "biblio/screening_log.csv", index=False)
    m.to_csv(ROOT / "biblio/screened_records.csv", index=False)
    print(log["decision"].value_counts().to_dict(), "uncertain:", int(m["uncertain"].sum()))


if __name__ == "__main__":
    main()
