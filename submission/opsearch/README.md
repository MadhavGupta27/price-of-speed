# OPSEARCH submission package

Target journal: **OPSEARCH** (Journal of the Operational Research Society of India, Springer).

| File | Purpose |
|---|---|
| `opsearch_upload.zip` | Upload bundle: `manuscript.tex`, `references.bib`, 8 figure PDFs, `sn-jnl.cls`, `sn-basic.bst` (flat folder, pdfLaTeX-safe) |
| `manuscript.pdf` | Compiled check copy of the manuscript (Springer Nature template, single column) |
| `cover_letter.pdf` / `.tex` | Cover letter to the Editor-in-Chief |
| `upload/` | Unzipped contents of the bundle |
| `src/` | Journal-only sources: template wrapper, abstract, declarations |
| `template/` | Official Springer Nature LaTeX template files (Version 3.1, December 2024) |

Rebuild after any change to the paper or results:

```bash
make submission
```

## Before uploading: fill in these placeholders

Edit `src/main_journal.tex`, `src/declarations.tex` and `cover_letter.tex`, then run `make submission`.

- [ ] **Institution name and city** (`\affil` in `src/main_journal.tex`; signature block in `cover_letter.tex`).
- [ ] **Corresponding author e-mail** (`\email{...}` in `src/main_journal.tex`; `cover_letter.tex`). The corresponding author is set to Madhav Gupta; change `\author*` if needed.
- [ ] **Repository URL** (`\RepoURL` in `src/main_journal.tex`), once the public GitHub repository exists.
- [ ] **Author contributions** (`src/declarations.tex`): confirm or replace the generic statement.
- [ ] **Acknowledgements**: edit or remove.

## Checks before submitting

- [ ] All six authors have read and approved the manuscript and the author order.
- [ ] Someone has spot-checked the key numbers against `results/` and the citations against the sources.
- [ ] Confirm the journal's current requirements on its "Submission guidelines" page (fees, review type, declarations).
- [ ] Keep Section 3.3 (required by Springer Nature policy).

## How to submit

1. The corresponding author creates an account in Springer's submission system from the OPSEARCH journal page ("Submit manuscript").
2. Choose article type "Original Research" (or the closest equivalent). Enter the title, abstract and keywords from `manuscript.pdf`, and add all six authors in order.
3. Upload `opsearch_upload.zip`, or the files in `upload/` individually as "LaTeX source" plus figures, and `cover_letter.pdf` as the cover letter.
4. Answer the declaration questions to match the manuscript's Declarations section.
5. Approve the system-built PDF, then submit. **Save the confirmation e-mail** as evidence of submission for the course.

Choose the standard (subscription) publication route if offered. Open access is optional and carries a fee only if chosen after acceptance.
