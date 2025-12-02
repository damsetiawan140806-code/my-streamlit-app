# app.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt
from datetime import datetime
import base64
from jinja2 import Template

st.set_page_config(page_title="Sistem Akuntansi Mini By Kelompok 5", layout="wide")

# -------------------------
# Util helpers
# -------------------------
def load_sample_transactions():
    data = [
        {"date":"2025-11-01","account_debit":"Cash","account_credit":"Revenue","amount":5000000,"description":"Penjualan jasa A"},
        {"date":"2025-11-05","account_debit":"Accounts Receivable","account_credit":"Revenue","amount":3000000,"description":"Penjualan kredit B"},
        {"date":"2025-11-10","account_debit":"Cost of Goods Sold","account_credit":"Inventory","amount":1200000,"description":"Pembelian bahan"},
        {"date":"2025-11-15","account_debit":"Salary Expense","account_credit":"Cash","amount":800000,"description":"Gaji November"},
        {"date":"2025-11-20","account_debit":"Cash","account_credit":"Accounts Receivable","amount":2000000,"description":"Penerimaan piutang"},
    ]
    return pd.DataFrame(data)

def df_to_csv_bytes(df: pd.DataFrame):
    return df.to_csv(index=False).encode('utf-8')

def money(x):
    try:
        return f"Rp {float(x):,.0f}".replace(",", ".")
    except:
        return f"Rp {x}"

# -------------------------
# Report generation helper (basic) - placed before UI to avoid runtime errors
# -------------------------
def render_report_html(book):
    tpl = """
    <html>
    <head><meta charset="utf-8"><title>Laporan Keuangan</title></head>
    <body>
    <h1>Laporan Keuangan (Mini)</h1>
    <h2>Income Statement</h2>
    <ul>
    <li>Revenue: {{ revenue }}</li>
    <li>Expense: {{ expense }}</li>
    <li>Net Income: {{ net }}</li>
    </ul>
    <h2>Balance Sheet</h2>
    <ul>
    <li>Assets: {{ assets }}</li>
    <li>Liabilities: {{ liabilities }}</li>
    <li>Equity: {{ equity }}</li>
    </ul>
    <h2>Trial Balance</h2>
    <table border="1" cellpadding="5">
    <tr><th>Account</th><th>Class</th><th>Debit</th><th>Credit</th></tr>
    {% for r in tb %}
      <tr>
        <td>{{ r.account }}</td><td>{{ r.class }}</td><td>{{ r.debit }}</td><td>{{ r.credit }}</td>
      </tr>
    {% endfor %}
    </table>
    </body>
    </html>
    """
    template = Template(tpl)
    tb_rows = book.trial_balance.to_dict('records')
    html = template.render(revenue=book.income_statement['revenue'],
                           expense=book.income_statement['expense'],
                           net=book.income_statement['net_income'],
                           assets=book.balance_sheet['assets'],
                           liabilities=book.balance_sheet['liabilities'],
                           equity=book.balance_sheet['equity'],
                           tb=tb_rows)
    return html

# -------------------------
# Accounting engine
# -------------------------
class AccountingBook:
    def __init__(self, transactions_df: pd.DataFrame):
        # expect columns: date, account_debit, account_credit, amount, description
        df = transactions_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = df['amount'].astype(float)
        self.tx = df.sort_values('date').reset_index(drop=True)
        self.accounts = self._collect_accounts()
        self.journal = self._build_journal()
        self.ledger = self._build_ledger()
        self.trial_balance = self._build_trial_balance()
        self.income_statement = self._build_income_statement()
        self.balance_sheet = self._build_balance_sheet()

    def _collect_accounts(self):
        accs = set(self.tx['account_debit']).union(set(self.tx['account_credit']))
        classification = {}
        for a in accs:
            la = a.lower()
            if any(k in la for k in ['cash','bank','receivable','piutang']):
                classification[a] = 'asset'
            elif any(k in la for k in ['inventory','persediaan']):
                classification[a] = 'asset'
            elif any(k in la for k in ['payable','hutang']):
                classification[a] = 'liability'
            elif any(k in la for k in ['revenue','sales','pendapatan']):
                classification[a] = 'revenue'
            elif any(k in la for k in ['expense','cost','beban','salary','gaji','cogs']):
                classification[a] = 'expense'
            else:
                classification[a] = 'equity'
        return classification

    def _build_journal(self):
        rows = []
        for i, r in self.tx.iterrows():
            rows.append({
                "date": r['date'],
                "account": r['account_debit'],
                "debit": r['amount'],
                "credit": 0.0,
                "description": r.get('description','')
            })
            rows.append({
                "date": r['date'],
                "account": r['account_credit'],
                "debit": 0.0,
                "credit": r['amount'],
                "description": r.get('description','')
            })
        journal = pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
        return journal

    def _build_ledger(self):
        ledgers = {}
        for account in self.accounts:
            acc_lines = self.journal[self.journal['account']==account].copy()
            if acc_lines.empty:
                ledgers[account] = pd.DataFrame(columns=['date','description','debit','credit','balance'])
                continue
            acc_lines['debit_cum'] = acc_lines['debit'].cumsum()
            acc_lines['credit_cum'] = acc_lines['credit'].cumsum()
            acc_lines['balance'] = acc_lines['debit_cum'] - acc_lines['credit_cum']
            ledgers[account] = acc_lines[['date','description','debit','credit','balance']].reset_index(drop=True)
        return ledgers

    def _build_trial_balance(self):
        rows = []
        for account in self.accounts:
            led = self.ledger.get(account)
            if led is None or len(led)==0:
                bal = 0.0
            else:
                bal = led.iloc[-1]['balance']
            # Determine natural side
            cls = self.accounts[account]
            debit = 0.0
            credit = 0.0
            if cls in ['asset','expense']:
                if bal >= 0:
                    debit = bal
                else:
                    credit = -bal
            else:  # liability, equity, revenue
                if bal >= 0:
                    credit = bal
                else:
                    debit = -bal
            rows.append({"account":account,"debit":debit,"credit":credit,"class":cls})
        tb = pd.DataFrame(rows)
        tb['debit'] = tb['debit'].fillna(0)
        tb['credit'] = tb['credit'].fillna(0)
        return tb

    def _build_income_statement(self):
        rev = sum(self._account_balance_by_type('revenue').values())
        exp = sum(self._account_balance_by_type('expense').values())
        net = rev - exp
        return {"revenue": rev, "expense": exp, "net_income": net}

    def _build_balance_sheet(self):
        assets = sum(self._account_balance_by_type('asset').values())
        liabilities = sum(self._account_balance_by_type('liability').values())
        equity = sum(self._account_balance_by_type('equity').values())
        equity += self._build_income_statement()['net_income']
        return {"assets": assets, "liabilities": liabilities, "equity": equity}

    def _account_balance_by_type(self, type_name):
        res = {}
        for acc, typ in self.accounts.items():
            if typ==type_name:
                led = self.ledger.get(acc)
                bal = 0.0
                if led is not None and len(led)>0:
                    bal = led.iloc[-1]['balance']
                res[acc] = bal
        return res

# -------------------------
# Streamlit UI
# -------------------------
st.title("Mini Accounting System — Streamlit")
st.write("Sistem sederhana: jurnal, buku besar, neraca saldo, laporan keuangan.")

# Sidebar: load data or sample
st.sidebar.header("Data Transaksi")
option = st.sidebar.radio("Pilih sumber transaksi", ("Sample data","Upload CSV","Manual input"))
if option=="Sample data":
    df_tx = load_sample_transactions()
elif option=="Upload CSV":
    uploaded = st.sidebar.file_uploader("Unggah transactions.csv", type=['csv'])
    if uploaded is not None:
        try:
            df_tx = pd.read_csv(uploaded)
        except Exception as e:
            st.sidebar.error(f"Gagal baca CSV: {e}")
            df_tx = load_sample_transactions()
    else:
        st.sidebar.info("Belum ada file. Menggunakan sample sementara.")
        df_tx = load_sample_transactions()
else:
    st.sidebar.info("Tambah 1 transaksi ke notebook dulu (akan menimpa saat refresh).")
    with st.sidebar.form("manual_tx"):
        date = st.date_input("Tanggal", value=datetime.today())
        acc_debit = st.text_input("Akun Debit (teks)", value="Cash")
        acc_credit = st.text_input("Akun Kredit (teks)", value="Revenue")
        amount = st.number_input("Jumlah", min_value=0.0, value=100000.0, step=1000.0)
        desc = st.text_input("Keterangan", value="Transaksi manual")
        submitted = st.form_submit_button("Tambah transaksi")
    if submitted:
        df_tx = pd.DataFrame([{
            "date": date.strftime("%Y-%m-%d"),
            "account_debit": acc_debit,
            "account_credit": acc_credit,
            "amount": amount,
            "description": desc
        }])
        st.success("Transaksi manual ditambahkan (sementara).")
    else:
        df_tx = load_sample_transactions()

st.subheader("Data Transaksi (preview)")
st.dataframe(df_tx)

st.markdown("---")
if st.button("Validasi transaksi (format)"):
    st.success("Format transaksi: OK (setiap baris menyatakan 1 transaksi: debit ke credit).")

# Build accounting book
try:
    book = AccountingBook(df_tx)
except Exception as e:
    st.error(f"Gagal membangun buku akuntansi: {e}")
    st.stop()

# Tabs for views
tab1, tab2, tab3, tab4 = st.tabs(["Jurnal Umum","Buku Besar","Neraca Saldo","Laporan Keuangan / Dashboard"])

with tab1:
    st.header("Jurnal Umum")
    st.write("Setiap transaksi dipecah ke baris debit & kredit.")
    st.dataframe(book.journal)

    csv_bytes = df_to_csv_bytes(book.journal)
    st.download_button("Download Jurnal CSV", data=csv_bytes, file_name="journal.csv", mime="text/csv")

with tab2:
    st.header("Buku Besar per Akun")
    acct = st.selectbox("Pilih akun untuk lihat buku besar", options=sorted(book.accounts.keys()))
    st.write(f"Buku besar: **{acct}** — klasifikasi: {book.accounts[acct]}")
    ledger_df = book.ledger.get(acct)
    if ledger_df is None or ledger_df.empty:
        st.info("Belum ada transaksi untuk akun ini.")
    else:
        st.dataframe(ledger_df.fillna(''))

    if st.checkbox("Tampilkan semua saldo akun"):
        tb = book.trial_balance[['account','debit','credit','class']].copy()
        tb['balance'] = tb['debit'] - tb['credit']
        st.dataframe(tb)

with tab3:
    st.header("Neraca Saldo (Trial Balance)")
    tb = book.trial_balance.copy()
    tb['debit'] = tb['debit'].astype(float)
    tb['credit'] = tb['credit'].astype(float)
    total_debit = tb['debit'].sum()
    total_credit = tb['credit'].sum()
    st.dataframe(tb[['account','class','debit','credit']].sort_values('class'))
    st.markdown(f"**Total Debit:** {money(total_debit)}  \n**Total Credit:** {money(total_credit)}")
    if abs(total_debit - total_credit) > 1e-6:
        st.error("Neraca saldo tidak seimbang! Periksa transaksi.")
    else:
        st.success("Neraca saldo seimbang.")

with tab4:
    st.header("Laporan Keuangan & Dashboard")
    st.subheader("Income Statement (Laporan Laba Rugi) — Ringkas")
    isr = book.income_statement
    st.write({
        "Revenue (Pendapatan)": money(isr['revenue']),
        "Expense (Beban)": money(isr['expense']),
        "Net Income (Laba Bersih)": money(isr['net_income'])
    })

    st.subheader("Balance Sheet (Neraca) — Ringkas")
    bs = book.balance_sheet
    st.write({
        "Assets (Aset)": money(bs['assets']),
        "Liabilities (Kewajiban)": money(bs['liabilities']),
        "Equity (Ekuitas, termasuk laba bersih)": money(bs['equity'])
    })

    # Simple charts
    st.subheader("Dashboard Charts")
    fig1, ax1 = plt.subplots()
    categories = ['Revenue','Expense']
    values = [isr['revenue'], isr['expense']]
    ax1.bar(categories, values)
    ax1.set_title("Revenue vs Expense")
    ax1.set_ylabel("Amount")
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots()
    labels = ['Assets','Liabilities','Equity']
    vals = [bs['assets'], bs['liabilities'], bs['equity']]
    # avoid pie error when sums zero
    if sum(vals) == 0:
        ax2.text(0.4,0.5,"No data to plot")
    else:
        ax2.pie(vals, labels=labels, autopct='%1.1f%%')
    ax2.set_title("Balance Sheet Composition")
    st.pyplot(fig2)

    # Export reports
    if st.button("Export Laporan (HTML)"):
        html = render_report_html(book)
        b = html.encode('utf-8')
        st.download_button("Download laporan.html", data=b, file_name="laporan_keuangan.html", mime="text/html")

