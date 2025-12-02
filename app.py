import streamlit as st
import pandas as pd

# -----------------------------------
# TITLE
# -----------------------------------
st.title("Sistem Akuntansi Mini By Kelompok 5")
st.write("Aplikasi ini memungkinkan Anda mencatat transaksi, melihat laporan, dan mendownload data.")

# -----------------------------------
# SESSION STATE INIT
# -----------------------------------
if "transaksi" not in st.session_state:
    st.session_state.transaksi = pd.DataFrame(columns=["Tanggal", "Keterangan", "Kategori", "Debit", "Kredit"])

# -----------------------------------
# FORM INPUT TRANSAKSI
# -----------------------------------
st.subheader("Input Transaksi Baru")

with st.form("form_transaksi"):
    tanggal = st.date_input("Tanggal Transaksi")
    keterangan = st.text_input("Keterangan / Deskripsi")
    kategori = st.selectbox("Kategori", ["Pendapatan", "Beban", "Aset", "Liabilitas", "Ekuitas"])
    debit = st.number_input("Debit", min_value=0.0, value=0.0)
    kredit = st.number_input("Kredit", min_value=0.0, value=0.0)

    submit = st.form_submit_button("Simpan Transaksi")

    if submit:
        new_row = {
            "Tanggal": tanggal,
            "Keterangan": keterangan,
            "Kategori": kategori,
            "Debit": debit,
            "Kredit": kredit
        }

        st.session_state.transaksi = pd.concat(
            [st.session_state.transaksi, pd.DataFrame([new_row])],
            ignore_index=True
        )
        st.success("Transaksi berhasil disimpan!")

# -----------------------------------
# TAMPILKAN TABEL TRANSAKSI
# -----------------------------------
st.subheader("Daftar Transaksi")
if st.session_state.transaksi.empty:
    st.info("Belum ada transaksi. Silakan input transaksi terlebih dahulu.")
else:
    st.dataframe(st.session_state.transaksi)

# -----------------------------------
# LAPORAN SEDERHANA
# -----------------------------------
st.subheader("Laporan Keuangan Sederhana")

if not st.session_state.transaksi.empty:
    total_debit = st.session_state.transaksi["Debit"].sum()
    total_kredit = st.session_state.transaksi["Kredit"].sum()
    saldo = total_debit - total_kredit

    st.metric("Total Debit", f"Rp {total_debit:,.0f}")
    st.metric("Total Kredit", f"Rp {total_kredit:,.0f}")
    st.metric("Saldo", f"Rp {saldo:,.0f}")

# -----------------------------------
# DOWNLOAD DATA
# -----------------------------------
st.subheader("Download Data")

if not st.session_state.transaksi.empty:
    csv = st.session_state.transaksi.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="data_transaksi.csv",
        mime="text/csv"
    )
else:
    st.info("Tidak ada data untuk didownload.")
