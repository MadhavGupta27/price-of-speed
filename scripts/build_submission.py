"""Assemble the flat OPSEARCH upload folder from the shared paper sources.

    uv run python scripts/build_submission.py

Reads submission/opsearch/src/main_journal.tex (Springer Nature sn-jnl template),
inlines every \\input (journal-specific files, paper/sections/*, generated macros
and tables), copies the referenced figures, merges paper/references.bib and
paper/lit.bib, adds the class and bibliography style, then compiles with Tectonic
and zips the result:

  submission/opsearch/upload/             manuscript.tex, references.bib, figures, sn-jnl.cls, sn-basic.bst
  submission/opsearch/manuscript.pdf      compiled check copy
  submission/opsearch/opsearch_upload.zip upload bundle
"""

import re
import shutil
import subprocess
import zipfile

from orpaper.config import ROOT

PAPER = ROOT / "paper"
SUB = ROOT / "submission/opsearch"
UP = SUB / "upload"
# pdfLaTeX-safe replacements for non-ASCII characters (journal systems compile with pdfLaTeX)
ASCII_TEX = {"ć": "{\\'c}", "ü": '{\\"u}', "ø": "{\\o}", "Ø": "{\\O}", "é": "{\\'e}", "á": "{\\'a}",
             "à": "{\\`a}", "ö": '{\\"o}', "ä": '{\\"a}', "ñ": "{\\~n}", "č": "{\\v c}", "š": "{\\v s}",
             "ł": "{\\l}", "í": "{\\'i}", "ó": "{\\'o}", "ç": "{\\c c}", "\u2010": "-", "\u2013": "--",
             "\u2014": "---", "\u2019": "'", "\u2018": "`", "\u201c": "``", "\u201d": "''"}


def to_ascii_tex(text):
    for ch, rep in ASCII_TEX.items():
        text = text.replace(ch, rep)
    bad = sorted({ch for ch in text if ord(ch) > 127})
    if bad:
        raise ValueError(f"Unmapped non-ASCII characters: {bad} -- add them to ASCII_TEX")
    return text


INPUT = re.compile(r"\\input\{([^}]+)\}")
GRAPHIC = re.compile(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}")


def resolve(name):
    """Locate an \\input target: journal sources first, then the shared paper tree."""
    for base in (SUB, PAPER):
        for cand in (base / name, base / f"{name}.tex"):
            if cand.is_file():
                return cand
    raise FileNotFoundError(name)


def inline(text, depth=0):
    if depth > 5:
        raise RecursionError("nested \\input too deep")
    out, pos = [], 0
    for m in INPUT.finditer(text):
        # skip commented-out \input lines
        line_start = text.rfind("\n", 0, m.start()) + 1
        if text[line_start:m.start()].lstrip().startswith("%"):
            continue
        out.append(text[pos:m.start()])
        body = resolve(m.group(1)).read_text()
        out.append(f"% ---- begin {m.group(1)}\n{inline(body, depth + 1)}% ---- end {m.group(1)}\n")
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def main():
    if UP.exists():
        shutil.rmtree(UP)
    UP.mkdir(parents=True)

    tex = inline((SUB / "src/main_journal.tex").read_text())
    tex = tex.replace("\\IfFileExists{figures/", "\\IfFileExists{")  # figures sit next to manuscript.tex
    # sn-jnl's table environment conflicts with adjustbox around tabulars; the journal's
    # single-column text block fits the tables without it (overfull boxes are reported below).
    tex = re.sub(r"\\begin\{adjustbox\}\{max width=\\linewidth\}(% ---- begin generated/tab_[a-z0-9_]+\.tex)",
                 r"\1", tex)
    tex = re.sub(r"(% ---- end generated/tab_[a-z0-9_]+\.tex\n)\\end\{adjustbox\}", r"\1", tex)

    figs = sorted({m.group(2) for m in GRAPHIC.finditer(tex)})
    for f in figs:
        src = PAPER / "figures" / (f if f.endswith(".pdf") else f + ".pdf")
        shutil.copy(src, UP / src.name)
    (UP / "manuscript.tex").write_text(to_ascii_tex(tex))

    bib = (PAPER / "references.bib").read_text() + "\n" + (PAPER / "lit.bib").read_text()
    (UP / "references.bib").write_text(to_ascii_tex(bib))
    for f in ("sn-jnl.cls", "sn-basic.bst"):
        shutil.copy(SUB / "template" / f, UP / f)

    subprocess.run(["tectonic", "-X", "compile", "manuscript.tex", "--keep-logs"], cwd=UP, check=True)
    shutil.copy(UP / "manuscript.pdf", SUB / "manuscript.pdf")
    log = (UP / "manuscript.log").read_text(errors="ignore")
    undefined = re.findall(r"Warning: (?:Citation|Reference) `([^']+)' .*undefined", log)
    overfull = [float(x) for x in re.findall(r"Overfull \\hbox \(([0-9.]+)pt too wide", log)]
    for f in UP.glob("manuscript.*"):
        if f.suffix not in (".tex", ".pdf"):
            f.unlink()
    with zipfile.ZipFile(SUB / "opsearch_upload.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(UP.iterdir()):
            if f.name != "manuscript.pdf":
                z.write(f, f.name)
    print(f"figures: {len(figs)}; undefined refs/cites: {sorted(set(undefined)) or 'none'}; "
          f"overfull boxes: {len(overfull)} (max {max(overfull, default=0):.1f}pt)")
    print(f"Wrote {SUB / 'manuscript.pdf'} and {SUB / 'opsearch_upload.zip'}")


if __name__ == "__main__":
    main()
