import streamlit as st
import pandas as pd

st.title("Sistem Akuntansi Mini By Kelompok 5")
st.write("Aplikasi ini memungkinkan Anda mencatat transaksi, melihat jurnal, dan buku besar setiap akun.")

if "transaksi" not in st.session_state:
    st.session_state.transaksi = pd.DataFrame(columns=[
        "Tanggal", "Keterangan", 
        "Akun Debit", "Akun Kredit", 
        "Debit", "Kredit"
    ])

st.subheader("Input Transaksi Baru")

with st.form("form_transaksi"):
    tanggal = st.date_input("Tanggal Transaksi")
    keterangan = st.text_input("Keterangan / Deskripsi")

    akun_debit = st.text_input("Nama Akun Debit")
    akun_kredit = st.text_input("Nama Akun Kredit")

    debit = st.number_input("Jumlah Debit", min_value=0.0, value=0.0)
    kredit = st.number_input("Jumlah Kredit", min_value=0.0, value=0.0)

    submit = st.form_submit_button("Simpan Transaksi")

    if submit:
        if debit == 0 and kredit == 0:
            st.error("Debit atau Kredit harus diisi.")
        elif debit != kredit:
            st.error("Jumlah debit dan kredit harus seimbang (double entry).")
        else:
            new_row = {
                "Tanggal": tanggal,
                "Keterangan": keterangan,
                "Akun Debit": akun_debit,
                "Akun Kredit": akun_kredit,
                "Debit": debit,
                "Kredit": kredit
            }

            st.session_state.transaksi = pd.concat(
                [st.session_state.transaksi, pd.DataFrame([new_row])],
                ignore_index=True
            )
            st.success("Transaksi berhasil disimpan!")

st.subheader("Jurnal Umum")

if st.session_state.transaksi.empty:
    st.info("Belum ada transaksi.")
else:
    st.dataframe(st.session_state.transaksi)

st.subheader("Buku Besar (Ledger) Per Akun")

if not st.session_state.transaksi.empty:
    
    akun_debit_list = st.session_state.transaksi["Akun Debit"].unique()
    akun_kredit_list = st.session_state.transaksi["Akun Kredit"].unique()

    daftar_akun = sorted(set(akun_debit_list) | set(akun_kredit_list))

    for akun in daftar_akun:
        st.markdown(f"### 📘 Akun: **{akun}**")

        
        ledger_rows = []

        for _, row in st.session_state.transaksi.iterrows():
            if row["Akun Debit"] == akun:
                ledger_rows.append({
                    "Tanggal": row["Tanggal"],
                    "Keterangan": row["Keterangan"],
                    "Debit": row["Debit"],
                    "Kredit": 0
                })
            if row["Akun Kredit"] == akun:
                ledger_rows.append({
                    "Tanggal": row["Tanggal"],
                    "Keterangan": row["Keterangan"],
                    "Debit": 0,
                    "Kredit": row["Kredit"]
                })

        df_ledger = pd.DataFrame(ledger_rows)

        
        df_ledger["Saldo"] = df_ledger["Debit"] - df_ledger["Kredit"]
        df_ledger["Saldo"] = df_ledger["Saldo"].cumsum()

        st.dataframe(df_ledger)

st.subheader("Download Data Jurnal")

if not st.session_state.transaksi.empty:
    csv = st.session_state.transaksi.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="data_jurnal.csv",
        mime="text/csv"
    )
else:
    st.info("Tidak ada data untuk didownload.")
