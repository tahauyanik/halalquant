# HalalQuant

An independent analytical tool that screens BIST-listed (Turkish stock
exchange) companies against a set of quantitative, ratio-based
Islamic-finance screening criteria, using quarterly financial data
from Yahoo Finance.

**Live app:** _(add your Streamlit Cloud link here)_

## What it does

For each ticker entered, the app calculates four ratios against the
company's trailing 12-month average market capitalization (raw,
unadjusted closing prices):

| Filter | Threshold |
|---|---|
| Total debt / market cap | ≤ 33% |
| Interest income / total revenue | ≤ 5% |
| Cash & equivalents / market cap | ≤ 33% |
| Receivables / market cap | ≤ 33% |

A company passes only if all four ratios clear their threshold using
data from its most recently reported quarter. If any of the four
ratios cannot be calculated (missing data), the company is marked
**INSUFFICIENT DATA** rather than guessed at.

## Methodology note

This ratio structure (four ratios, 33%/5% thresholds) follows the
general style of screens used by index providers such as Dow Jones
Islamic Market and S&P Shariah. It is **not** identical to AAOIFI's
own Shari'ah Standard No. 21, which uses a 30% threshold, three
ratios, and no receivables ratio.

**This tool does not reflect the official BIST Katılım Endeksi
(Participation Index) determination.** The official index is based
on companies' own submissions (the KAFİF form) reviewed by the TKBB
Advisory Board, plus qualitative screening of each company's core
business activity — neither of which this tool has access to. As a
concrete example: EREGL and TKNSA are both current constituents of
the official BIST Katılım Endeksi, but may show a different result
here due to data-source differences.

**This is not investment advice, a religious ruling (fatwa), or a
binding statement of Shariah compliance.** For binding determinations,
refer to Borsa İstanbul's official announcements.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Running the tests

The four ratio calculations and the compliance decision live in
`screening_logic.py`, separate from the Streamlit UI, specifically so
they can be tested without a browser:

```bash
pip install pytest
pytest test_filters.py -v
```

Run this before pushing any change to `screening_logic.py` — it
covers the missing-data-vs-zero and NaN-fallback edge cases that
caused regressions during development.

## Project structure

```
app.py              — Streamlit UI: input, display, Excel export
screening_logic.py   — the four ratio filters + compliance decision (tested)
test_filters.py       — pytest suite for screening_logic.py
requirements.txt      — pinned dependencies for reproducible deploys
```

## License

MIT — see `LICENSE`.
