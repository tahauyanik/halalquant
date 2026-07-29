import streamlit as st
import yfinance as ticker_data
import pandas as pd
import io
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# --- PAGE CONFIG (neutral, no internal version numbers) ---
st.set_page_config(
    page_title="HalalQuant | Independent Financial Screening",
    page_icon="📊",
    layout="wide"
)

# --- CUSTOM BRAND STYLING (matches the Excel report's dark green) ---
st.markdown("""
<style>
    h1 {
        color: #1B4D3E !important;
        font-family: 'Arial', sans-serif;
        font-weight: 700;
    }
    h3 {
        color: #4A5568 !important;
        font-weight: 400;
    }
    div.stButton > button:first-child {
        background-color: #1B4D3E !important;
        color: white !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #143d31 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("HalalQuant")
st.subheader("An Independent Analytical Engine for Quantitative Ratio Screening")

st.warning("""
🚨 **METHODOLOGY & LEGAL DISCLAIMER:** 
This application is an independent analytical simulation that screens quarterly financial 
data based on global mathematical ratio filters.
* **Official Index Compliance:** This software does not directly reflect the official BIST 
Compliance Index or Shariah Board decisions.
* **Sample Variance:** For instance, companies like EREGL and TKNSA are included in the 
official compliance index, but may yield different results here due to data mapping 
differences on third-party sources (Yahoo Finance).
* **Investment Decision:** These results are absolutely not investment advice, binding 
statements, or religious fatwas. Please rely on official stock exchange announcements 
for binding decisions.
""")

@st.cache_data(ttl=1800)
def fetch_financial_data(ticker_symbol):
    try:
        company = ticker_data.Ticker(ticker_symbol)
        return {
            "balance_sheet": company.quarterly_balance_sheet,
            "financials": company.quarterly_financials,
            "history": company.history(period="1y", auto_adjust=False),
            "info": company.info
        }
    except Exception:
        return None

girdi_liste = st.text_input(
    "BIST Ticker Symbols (Separate with commas):", 
    "BIMAS, ASELS, MGROS, THYAO, HEKTS"
)

if st.button("Run Screening"):
    kodlar = [k.strip().upper() for k in girdi_liste.split(",") if k.strip()]
    if not kodlar:
        st.error("Please enter at least one valid ticker symbol.")
    else:
        st.info("⏳ Processing financial metrics over 12-month average prices...")
        toplu_sonuclar = []

        for g in kodlar:
            ticker_symbol = f"{g}.IS" if not g.endswith(".IS") else g
            try:
                data_pack = fetch_financial_data(ticker_symbol)

                if not data_pack:
                    st.warning(f"⚠️ Connection error for {ticker_symbol}. Skipped.")
                    continue

                bilanco_tablosu = data_pack["balance_sheet"]
                gelir_tablosu = data_pack["financials"]
                gecmis_fiyatlar = data_pack["history"]
                shares_outstanding = data_pack["info"].get('sharesOutstanding')

                if (bilanco_tablosu.empty or gelir_tablosu.empty or 
                    gecmis_fiyatlar.empty or not shares_outstanding):
                    st.warning(f"⚠️ {ticker_symbol} data is incomplete. Skipped.")
                    continue

                py_f = float(gecmis_fiyatlar['Close'].mean() * shares_outstanding)

                # 1. DEBT FILTER
                borc_orani, borc_gecti, borc_veri_var = None, False, False
                if 'Total Debt' in bilanco_tablosu.index:
                    ham_borc = bilanco_tablosu.loc['Total Debt']
                    val_borc = ham_borc.iloc[0] if hasattr(ham_borc, 'iloc') else ham_borc
                    if not pd.isna(val_borc) and val_borc is not None:
                        borc_orani = (float(val_borc) / py_f) * 100
                        borc_veri_var = True
                        if borc_orani <= 33: borc_gecti = True

                # 2. INTEREST REVENUE FILTER
                total_revenue = None
                for row in ['Total Revenue', 'Operating Revenue']:
                    if row in gelir_tablosu.index:
                        ham_rev = gelir_tablosu.loc[row]
                        val_rev = ham_rev.iloc[0] if hasattr(ham_rev, 'iloc') else ham_rev
                        if not pd.isna(val_rev) and float(val_rev) > 0:
                            total_revenue = float(val_rev)
                            break

                faiz_geliri = 0
                faiz_satiri_bulundu = False
                for row in ['Interest Income', 'Non Operating Interest Income', 'Interest Income Non Operating']:
                    if row in gelir_tablosu.index:
                        ham_faiz = gelir_tablosu.loc[row]
                        deger = ham_faiz.iloc[0] if hasattr(ham_faiz, 'iloc') else ham_faiz
                        if not pd.isna(deger) and deger is not None:
                            faiz_geliri += float(deger)
                            faiz_satiri_bulundu = True

                faiz_orani, faiz_gecti, faiz_veri_var = None, False, False
                if total_revenue and faiz_satiri_bulundu:
                    faiz_orani = (faiz_geliri / total_revenue) * 100
                    faiz_veri_var = True
                    if faiz_orani <= 5: faiz_gecti = True

                # 3. CASH & LIQUIDITY FILTER
                nakit_orani, nakit_gecti, nakit_veri_var = None, False, False
                for row in ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']:
                    if row in bilanco_tablosu.index:
                        ham_nakit = bilanco_tablosu.loc[row]
                        val_n = ham_nakit.iloc[0] if hasattr(ham_nakit, 'iloc') else ham_nakit
                        if not pd.isna(val_n) and val_n is not None:
                            nakit_orani = (float(val_n) / py_f) * 100
                            nakit_veri_var = True
                            if nakit_orani <= 33: nakit_gecti = True
                            break

                # 4. RECEIVABLES FILTER
                alacak_orani, alacak_gecti, alacak_veri_var = None, False, False
                for row in ['Receivables', 'Accounts Receivable', 'Gross Accounts Receivable']:
                    if row in bilanco_tablosu.index:
                        ham_alacak = bilanco_tablosu.loc[row]
                        val_a = ham_alacak.iloc[0] if hasattr(ham_alacak, 'iloc') else ham_alacak
                        if not pd.isna(val_a) and val_a is not None:
                            alacak_orani = (float(val_a) / py_f) * 100
                            alacak_veri_var = True
                            if alacak_orani <= 33: alacak_gecti = True
                            break

                # FINAL COMPLIANCE DECISION
                veri_eksik = not (borc_veri_var and faiz_veri_var and nakit_veri_var and alacak_veri_var)
                if veri_eksik: nihai_sonuc = "INSUFFICIENT DATA"
                elif borc_gecti and faiz_gecti and nakit_gecti and alacak_gecti: nihai_sonuc = "COMPLIANT"
                else: nihai_sonuc = "NON-COMPLIANT"

                toplu_sonuclar.append({
                    "Ticker": g, "Avg Market Cap (1Y)": f"{py_f:,.0f}",
                    "Debt Ratio (%33)": f"%{borc_orani:.2f}" if borc_veri_var else "N/A",
                    "Interest Ratio (%5)": f"%{faiz_orani:.2f}" if faiz_veri_var else "N/A",
                    "Cash Ratio (%33)": f"%{nakit_orani:.2f}" if nakit_veri_var else "N/A",
                    "Receivables Ratio (%33)": f"%{alacak_orani:.2f}" if alacak_veri_var else "N/A",
                    "FINAL STATUS": nihai_sonuc,
                    "_b": borc_gecti if borc_veri_var else None, "_f": faiz_gecti if faiz_veri_var else None,
                    "_n": nakit_gecti if nakit_veri_var else None, "_a": alacak_gecti if alacak_veri_var else None
                })
            except Exception as e:
                st.warning(f"⚠️ Unexpected error while screening {g}: {e}")

        if toplu_sonuclar:
            df_gosterim = pd.DataFrame(toplu_sonuclar).drop(columns=["_b", "_f", "_n", "_a"])
            st.dataframe(df_gosterim, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_gosterim.to_excel(writer, index=False, sheet_name='Quarterly Shariah Analysis')
                worksheet = writer.sheets['Quarterly Shariah Analysis']

                bg_baslik = PatternFill("solid", fgColor="1B4D3E")
                bg_yesil = PatternFill("solid", fgColor="D4EDDA")
                bg_kirmizi = PatternFill("solid", fgColor="F8D7DA")
                bg_gri = PatternFill("solid", fgColor="E2E3E5")

                f_beyaz = Font(name="Arial", size=11, bold=True, color="FFFFFF")
                f_kalin = Font(name="Arial", size=11, bold=True)
                f_normal = Font(name="Arial", size=11)

                for c_idx in range(1, 8):
                    cell = worksheet.cell(row=1, column=c_idx)
                    cell.fill = bg_baslik
                    cell.font = f_beyaz
                    cell.alignment = Alignment(horizontal="center")

                for idx, veri in enumerate(toplu_sonuclar):
                    r_idx = idx + 2
                    for c_idx in range(1, 8):
                        worksheet.cell(row=r_idx, column=c_idx).font = f_normal

                    worksheet.cell(row=r_idx, column=3).fill = bg_yesil if veri["_b"] else (bg_kirmizi if veri["_b"]==False else bg_gri)
                    worksheet.cell(row=r_idx, column=4).fill = bg_yesil if veri["_f"] else (bg_kirmizi if veri["_f"]==False else bg_gri)
                    worksheet.cell(row=r_idx, column=5).fill = bg_yesil if veri["_n"] else (bg_kirmizi if veri["_n"]==False else bg_gri)
                    worksheet.cell(row=r_idx, column=6).fill = bg_yesil if veri["_a"] else (bg_kirmizi if veri["_a"]==False else bg_gri)

                    c_durum = worksheet.cell(row=r_idx, column=7)
                    c_durum.font = f_kalin
                    c_durum.fill = bg_yesil if veri["FINAL STATUS"] == "COMPLIANT" else (bg_kirmizi if veri["FINAL STATUS"] == "NON-COMPLIANT" else bg_gri)

                for col_idx in range(1, 8):
                    col_letter = get_column_letter(col_idx)
                    max_len = max(len(str(cell.value or '')) for cell in worksheet[col_letter])
                    worksheet.column_dimensions[col_letter].width = max(max_len + 4, 16)

            st.markdown("---")
            st.download_button(
                label="📥 Download Excel Report",
                data=buffer.getvalue(),
                file_name="halalquant_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Data could not be fetched.")
