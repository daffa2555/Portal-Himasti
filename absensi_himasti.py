import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta
import urllib.parse
import bcrypt
import hashlib
import html
import bleach
import re

# ============================================================
# 0. KONFIGURASI
# ============================================================
st.set_page_config(page_title="HIMASTI Portal", page_icon="🛡️", layout="wide")

# ============================================================
# 1. KONEKSI DATABASE
# ============================================================
URL              = st.secrets["SUPABASE_URL"]
KEY              = st.secrets["SUPABASE_KEY"]
SUPERADMIN_USER  = st.secrets["superadmin"]["username"]
SUPERADMIN_HASH  = st.secrets["superadmin"]["password_hash"]

@st.cache_resource
def init_connection():
    return create_client(URL, KEY)

supabase = init_connection()
ABSEN_TABLE = "absensi"

# ============================================================
# 2. FUNGSI KEAMANAN
# ============================================================

# --- Hashing (SHA-256 untuk user biasa, bcrypt untuk superadmin) ---
def make_hashes(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_hashes(password: str, hashed_text: str) -> bool:
    return make_hashes(password) == hashed_text

# --- Sanitasi XSS ---
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong']

def sanitize_html(text: str) -> str:
    """Buang semua HTML berbahaya, hanya izinkan tag aman."""
    return bleach.clean(str(text), tags=ALLOWED_TAGS, strip=True)

def escape_text(text: str) -> str:
    """Escape karakter HTML agar tidak dirender sebagai tag."""
    return html.escape(str(text))

# --- Validasi Input ---
def is_valid_username(username: str) -> bool:
    """Hanya huruf, angka, underscore, 3-30 karakter."""
    return bool(re.match(r'^[a-z0-9_]{3,30}$', username))

def is_strong_password(password: str) -> bool:
    """Minimal 8 karakter, ada huruf dan angka."""
    return len(password) >= 8 and any(c.isdigit() for c in password) and any(c.isalpha() for c in password)

# --- Rate Limiting Login ---
MAX_ATTEMPTS    = 5
LOCKOUT_MINUTES = 10

def init_rate_limit():
    if "login_attempts"  not in st.session_state: st.session_state.login_attempts  = 0
    if "lockout_until"   not in st.session_state: st.session_state.lockout_until   = None

def is_locked_out() -> bool:
    init_rate_limit()
    if st.session_state.lockout_until:
        if datetime.now() < st.session_state.lockout_until:
            remaining = int((st.session_state.lockout_until - datetime.now()).total_seconds() // 60) + 1
            st.error(f"🔒 Akun terkunci. Coba lagi dalam **{remaining} menit**.")
            return True
        else:
            # Lockout selesai, reset
            st.session_state.login_attempts = 0
            st.session_state.lockout_until  = None
    return False

def record_failed_attempt():
    init_rate_limit()
    st.session_state.login_attempts += 1
    remaining_attempts = MAX_ATTEMPTS - st.session_state.login_attempts
    if st.session_state.login_attempts >= MAX_ATTEMPTS:
        st.session_state.lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        st.error(f"🚨 Terlalu banyak percobaan! Akun dikunci selama **{LOCKOUT_MINUTES} menit**.")
    else:
        st.warning(f"Username atau password salah. Sisa percobaan: **{remaining_attempts}**")

def reset_rate_limit():
    st.session_state.login_attempts = 0
    st.session_state.lockout_until  = None

# ============================================================
# 3. HELPER LAIN
# ============================================================
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def normalize_nim(raw_value: str) -> str:
    raw_value = urllib.parse.unquote(str(raw_value or "").strip())
    if not raw_value:
        return ""

    parsed_url = urllib.parse.urlparse(raw_value)
    query_data = urllib.parse.parse_qs(parsed_url.query)
    for key in ("nim", "NIM", "id", "data"):
        if query_data.get(key):
            return str(query_data[key][0]).strip()

    digit_match = re.search(r"\d{6,30}", raw_value)
    if digit_match:
        return digit_match.group(0)

    return raw_value.strip()

def decode_qr_from_image(image_file) -> str:
    try:
        import cv2
        import numpy as np
    except ModuleNotFoundError:
        raise RuntimeError("Dependency scanner QR belum terpasang. Jalankan: pip install -r requirements.txt")

    file_bytes = np.frombuffer(image_file.getvalue(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return ""

    detector = cv2.QRCodeDetector()
    decoded_text, _, _ = detector.detectAndDecode(image)
    return normalize_nim(decoded_text)

def get_kader_by_nim(nim: str):
    res = supabase.table("kader").select("*").eq("nim", nim).limit(1).execute()
    return res.data[0] if res.data else None

def get_error_message(error: Exception) -> str:
    return str(error).replace("\n", " ").strip()

def has_absen_today(nim: str) -> bool:
    start_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_day = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    try:
        res = (
            supabase.table(ABSEN_TABLE)
            .select("id")
            .eq("nim", nim)
            .gte("waktu", start_day)
            .lte("waktu", end_day)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False

def save_absen(nim: str, metode: str = "Manual"):
    nim = normalize_nim(nim)
    if not nim:
        return False, "NIM/QR tidak terbaca."

    kader = get_kader_by_nim(nim)
    if not kader:
        return False, f"NIM {escape_text(nim)} tidak ditemukan di tabel kader."

    if has_absen_today(nim):
        return False, f"{escape_text(kader['nama'])} sudah absen hari ini."

    now = datetime.now().isoformat(timespec="seconds")
    payload = {
        "nama": kader["nama"],
        "nim": kader["nim"],
        "waktu": now,
        "status": "Hadir",
        "metode": metode,
    }
    if kader.get("angkatan") is not None:
        payload["angkatan"] = kader["angkatan"]

    try:
        supabase.table(ABSEN_TABLE).insert(payload).execute()
    except Exception:
        minimal_payload = {
            "nama": kader["nama"],
            "nim": kader["nim"],
            "waktu": now,
        }
        try:
            supabase.table(ABSEN_TABLE).insert(minimal_payload).execute()
        except Exception as e:
            return False, f"Gagal menyimpan ke tabel {ABSEN_TABLE}: {get_error_message(e)}"

    return True, f"Absensi berhasil: {escape_text(kader['nama'])} ({escape_text(kader['nim'])})."

def load_absen_logs():
    try:
        res = supabase.table(ABSEN_TABLE).select("*").order("waktu", desc=True).execute()
        st.session_state.absen_table_error = ""
        return pd.DataFrame(res.data)
    except Exception as e:
        st.session_state.absen_table_error = get_error_message(e)

    try:
        res = supabase.table(ABSEN_TABLE).select("*").execute()
        df_absen = pd.DataFrame(res.data)
        st.session_state.absen_table_error = ""
        if not df_absen.empty and "waktu" in df_absen.columns:
            return df_absen.sort_values("waktu", ascending=False)
        return df_absen
    except Exception as e:
        st.session_state.absen_table_error = get_error_message(e)
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_maintenance_status() -> bool:
    try:
        res = supabase.table("settings").select("value").eq("key", "maintenance_mode").execute()
        return res.data[0]['value'] == "true" if res.data else False
    except:
        return False

# ============================================================
# 4. CSS CUSTOM
# ============================================================
st.markdown("""
<style>
:root {
  --ab-accent: #00d1b2;
  --ab-surface: rgba(255, 255, 255, 0.05);
  --ab-border: rgba(0, 209, 178, 0.2);
}
html, body, .stApp {
  font-family: system-ui, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
div[data-testid="stMetric"] {
  background: var(--ab-surface);
  border: 1px solid var(--ab-border);
  padding: clamp(12px, 2.5vw, 18px);
  border-radius: 12px;
}
.note-card {
  background: rgba(0, 209, 178, 0.06);
  border-left: 4px solid var(--ab-accent);
  padding: 12px 14px;
  border-radius: 8px;
  margin-bottom: 10px;
}
.warning-banner {
  background: rgba(255, 100, 0, 0.08);
  border-left: 4px solid #ff6400;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 10px;
}
.portal-sidebar-title,
.auth-heading {
  text-align: center;
  font-size: clamp(1.2rem, 4vw, 1.75rem);
  margin: 0.4em 0;
  line-height: 1.2;
}
.maintenance-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-top: clamp(40px, 10vh, 100px);
  padding: clamp(8px, 3vw, 20px);
  gap: 0.35rem;
}
.maintenance-screen .maintenance-icon {
  font-size: clamp(2.5rem, 12vw, 4.5rem);
  margin: 0;
  line-height: 1;
  font-weight: 400;
}
.maintenance-screen h2 {
  margin: 0.25em 0;
  font-size: clamp(1rem, 3.5vw, 1.35rem);
}
.maintenance-screen p {
  margin: 0;
  max-width: 28rem;
  padding: 0 0.5rem;
  font-size: clamp(0.85rem, 2.5vw, 1rem);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 5. INITIAL SESSION STATE
# ============================================================
if "logged_in"     not in st.session_state: st.session_state.logged_in     = False
if "user_data"     not in st.session_state: st.session_state.user_data     = None
if "auth_page"     not in st.session_state: st.session_state.auth_page     = "login"
init_rate_limit()

# ============================================================
# 6. MAINTENANCE GUARD
# ============================================================
is_maintenance = get_maintenance_status()

if is_maintenance:
    is_admin = (
        st.session_state.logged_in and
        st.session_state.get('user_data', {}).get('username') == SUPERADMIN_USER
    )
    if not is_admin:
        st.markdown("""
            <div class="maintenance-screen">
                <h1 class="maintenance-icon" aria-hidden="true">⚠️</h1>
                <h2>SYSTEM UNDER MAINTENANCE</h2>
                <p>HIMASTI Portal sedang dipoles. Kembali lagi nanti!</p>
            </div>
        """, unsafe_allow_html=True)
        st.stop()

# ============================================================
# 7. AREA TERAUTENTIKASI
# ============================================================
if st.session_state.logged_in:
    u_curr = st.session_state.user_data

    # Penentuan Role
    if u_curr['username'] == SUPERADMIN_USER:
        role = "Super Admin"
    else:
        try:
            res_r = supabase.table("users").select("role").eq("username", u_curr['username']).execute()
            role  = res_r.data[0]['role'] if res_r.data else "Anggota"
        except:
            role = "Anggota"

    # Sidebar
    with st.sidebar:
        st.markdown("<h2 class='portal-sidebar-title'>🛡️ PORTAL HIMASTI</h2>", unsafe_allow_html=True)
        st.divider()
        st.write(f"**User:** `{escape_text(u_curr['username'].upper())}`")
        st.write(f"**Role:** `{escape_text(role)}`")
        if st.button("🚪 Logout System"): logout()

    st.title("🏛️ Command Center")

    # Data Master
    try:
        df_kader = pd.DataFrame(supabase.table("kader").select("*").order("nama").execute().data)
        df_fin   = pd.DataFrame(supabase.table("keuangan").select("*").execute().data)
        saldo    = df_fin['nominal'].sum() if not df_fin.empty else 0
    except:
        df_kader, df_fin, saldo = pd.DataFrame(), pd.DataFrame(), 0

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("DATABASE KADER",   f"{len(df_kader)} Persons")
    m2.metric("TREASURY BALANCE", f"Rp {saldo:,.0f}")
    m3.metric("SYSTEM STATUS",    "Maintenance" if is_maintenance else "Active")

    # Pemetaan Tab
    role_tabs = {
        "Super Admin":  ["✅ Absensi", "📊 Analytics", "📋 Kader Data", "⚡ SP Control", "💰 Finance", "📂 Arsip Surat", "📜 Executive", "📢 Broadcast", "⚙️ Admin"],
        "Ketua":        ["✅ Absensi", "📊 Analytics", "📋 Kader Data", "⚡ SP Control", "📜 Executive", "📢 Broadcast"],
        "Wakil Ketua":  ["✅ Absensi", "📊 Analytics", "📋 Kader Data", "⚡ SP Control", "📜 Executive", "📢 Broadcast"],
        "Sekretaris":   ["✅ Absensi", "📊 Analytics", "📋 Kader Data", "⚡ SP Control", "📂 Arsip Surat", "📢 Broadcast"],
        "Bendahara":    ["✅ Absensi", "📊 Analytics", "📋 Kader Data", "💰 Finance"],
        "BPH":          ["✅ Absensi", "📊 Analytics", "📋 Kader Data", "⚡ SP Control", "📢 Broadcast"],
        "Anggota":      ["✅ Absensi", "📊 Analytics"],
    }
    tabs_list   = role_tabs.get(role, ["✅ Absensi", "📊 Analytics"])
    active_tabs = st.tabs(tabs_list)

    # ----------------------------------------------------------
    # TAB: ABSENSI
    # ----------------------------------------------------------
    if "✅ Absensi" in tabs_list:
        with active_tabs[tabs_list.index("✅ Absensi")]:
            st.subheader("✅ Absensi Kader")
            st.caption(f"Scan QR kader atau input NIM. Data akan divalidasi ke tabel kader lalu disimpan ke tabel {ABSEN_TABLE}.")

            c_scan, c_manual = st.columns(2)
            with c_scan:
                qr_image = st.camera_input("Scan QR Kader")
                if qr_image:
                    try:
                        nim_from_qr = decode_qr_from_image(qr_image)
                        if nim_from_qr:
                            ok, message = save_absen(nim_from_qr, metode="QR")
                            if ok:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("QR tidak terbaca. Pastikan QR berisi NIM dan gambar cukup jelas.")
                    except Exception as e:
                        st.error(f"Scanner QR bermasalah: {e}")

            with c_manual:
                with st.form("manual_absen_form"):
                    nim_manual = st.text_input("Input NIM Manual")
                    submitted_absen = st.form_submit_button("Catat Absensi")
                    if submitted_absen:
                        ok, message = save_absen(nim_manual, metode="Manual")
                        if ok:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            st.divider()
            df_recent_absen = load_absen_logs()
            if st.session_state.get("absen_table_error"):
                st.error(f"Tabel {ABSEN_TABLE} belum siap: {st.session_state.absen_table_error}")
                st.code("""
create table if not exists absensi (
  id bigint generated by default as identity primary key,
  nama text not null,
  nim text not null,
  waktu timestamp not null,
  status text,
  metode text,
  angkatan text
);
""".strip(), language="sql")
            if not df_recent_absen.empty:
                st.markdown("#### Log Terbaru")
                st.dataframe(df_recent_absen.head(10), use_container_width=True, hide_index=True)
            else:
                st.info(f"Belum ada data di tabel {ABSEN_TABLE}.")

    # ----------------------------------------------------------
    # TAB: ANALYTICS
    # ----------------------------------------------------------
    with active_tabs[tabs_list.index("📊 Analytics")]:
        st.subheader("📊 Presence History")
        try:
            df_absensi = load_absen_logs()
            if not df_absensi.empty:
                st.download_button("📥 Export CSV", data=df_absensi.to_csv(index=False), file_name="log_absensi.csv")
                st.dataframe(df_absensi, use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada data absensi.")
        except Exception as e:
            st.error(f"Gagal memuat data dari tabel {ABSEN_TABLE}: {e}")

    # ----------------------------------------------------------
    # TAB: KADER DATA
    # ----------------------------------------------------------
    if "📋 Kader Data" in tabs_list:
        with active_tabs[tabs_list.index("📋 Kader Data")]:
            t1, t2, t3 = st.tabs(["Add Single", "Bulk Import", "Delete Member"])
            with t1:
                with st.form("single_k"):
                    nk = st.text_input("Nama")
                    ni = st.text_input("NIM")
                    ak = st.text_input("Angkatan")
                    if st.form_submit_button("Save"):
                        # Validasi: field tidak boleh kosong
                        if nk.strip() and ni.strip() and ak.strip():
                            supabase.table("kader").insert({
                                "nama": escape_text(nk.strip()),
                                "nim":  escape_text(ni.strip()),
                                "angkatan": escape_text(ak.strip()),
                                "sp_level": 0
                            }).execute()
                            st.success("Kader berhasil ditambahkan!")
                            st.rerun()
                        else:
                            st.error("Semua field wajib diisi!")
            with t2:
                file_k = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
                if file_k and st.button("🚀 Import"):
                    df_bulk = pd.read_csv(file_k) if file_k.name.endswith('.csv') else pd.read_excel(file_k)
                    required_cols = {'nama', 'nim', 'angkatan'}
                    if required_cols.issubset(df_bulk.columns):
                        for _, row in df_bulk.iterrows():
                            supabase.table("kader").insert({
                                "nama":     escape_text(str(row['nama'])),
                                "nim":      escape_text(str(row['nim'])),
                                "angkatan": escape_text(str(row['angkatan'])),
                                "sp_level": 0
                            }).execute()
                        st.success(f"{len(df_bulk)} kader berhasil diimport!")
                        st.rerun()
                    else:
                        st.error(f"Kolom wajib: {required_cols}. Ditemukan: {set(df_bulk.columns)}")
            with t3:
                if not df_kader.empty:
                    k_to_del = st.selectbox("Hapus Member:", df_kader['nama'].tolist())
                    # Konfirmasi penghapusan
                    confirm_del = st.checkbox(f"Saya yakin ingin menghapus **{k_to_del}**")
                    if st.button("🚨 Delete", disabled=not confirm_del):
                        supabase.table("kader").delete().eq("nama", k_to_del).execute()
                        st.success(f"{k_to_del} berhasil dihapus.")
                        st.rerun()
            st.divider()
            st.dataframe(df_kader, use_container_width=True, hide_index=True)

    # ----------------------------------------------------------
    # TAB: SP CONTROL
    # ----------------------------------------------------------
    if "⚡ SP Control" in tabs_list:
        with active_tabs[tabs_list.index("⚡ SP Control")]:
            if not df_kader.empty:
                for _, r in df_kader.iterrows():
                    with st.expander(f"👤 {escape_text(r['nama'])} ({escape_text(str(r['angkatan']))}) — SP-{r['sp_level']}"):
                        c1, c2 = st.columns(2)
                        if c1.button("🔼 Naikkan SP", key=f"up_{r['id']}"):
                            supabase.table("kader").update({"sp_level": int(r['sp_level']) + 1}).eq("id", r['id']).execute()
                            st.rerun()
                        if c2.button("🔽 Turunkan SP", key=f"dw_{r['id']}"):
                            if r['sp_level'] > 0:
                                supabase.table("kader").update({"sp_level": int(r['sp_level']) - 1}).eq("id", r['id']).execute()
                                st.rerun()
            else:
                st.info("Belum ada data kader.")

    # ----------------------------------------------------------
    # TAB: FINANCE
    # ----------------------------------------------------------
    if "💰 Finance" in tabs_list:
        with active_tabs[tabs_list.index("💰 Finance")]:
            f1, f2, f3 = st.tabs(["Manual Input", "Bulk Import", "Delete Transaction"])
            with f1:
                c1, c2 = st.columns([1, 2])
                with c1:
                    with st.form("fin_m"):
                        ti = st.selectbox("Tipe", ["Pemasukan", "Pengeluaran"])
                        ke = st.text_input("Keterangan")
                        no = st.number_input("Nominal", min_value=0)
                        if st.form_submit_button("Record"):
                            if ke.strip() and no > 0:
                                v = no if ti == "Pemasukan" else -no
                                supabase.table("keuangan").insert({
                                    "tanggal":     str(datetime.now().date()),
                                    "keterangan":  escape_text(ke.strip()),
                                    "nominal":     v,
                                    "tipe":        ti
                                }).execute()
                                st.success("Transaksi dicatat!")
                                st.rerun()
                            else:
                                st.error("Keterangan dan nominal wajib diisi!")
                with c2:
                    if not df_fin.empty:
                        st.area_chart(df_fin, x="tanggal", y="nominal")
            with f2:
                file_f = st.file_uploader("Upload Finance CSV/Excel", type=["csv", "xlsx"])
                if file_f and st.button("🚀 Import Finance"):
                    df_bulk_f   = pd.read_csv(file_f) if file_f.name.endswith('.csv') else pd.read_excel(file_f)
                    required_f  = {'tanggal', 'keterangan', 'nominal', 'tipe'}
                    if required_f.issubset(df_bulk_f.columns):
                        for _, row in df_bulk_f.iterrows():
                            supabase.table("keuangan").insert({
                                "tanggal":    str(row['tanggal']),
                                "keterangan": escape_text(str(row['keterangan'])),
                                "nominal":    int(row['nominal']),
                                "tipe":       escape_text(str(row['tipe']))
                            }).execute()
                        st.success(f"{len(df_bulk_f)} transaksi diimport!")
                        st.rerun()
                    else:
                        st.error(f"Kolom wajib: {required_f}")
            with f3:
                if not df_fin.empty:
                    df_fin['display'] = df_fin['tanggal'] + " | " + df_fin['keterangan'] + " | " + df_fin['nominal'].astype(str)
                    fin_to_del = st.selectbox("Pilih Transaksi:", df_fin['display'].tolist())
                    confirm_f  = st.checkbox("Saya yakin ingin menghapus transaksi ini")
                    if st.button("❌ Hapus Transaksi", disabled=not confirm_f):
                        sel_id = df_fin[df_fin['display'] == fin_to_del].iloc[0]['id']
                        supabase.table("keuangan").delete().eq("id", sel_id).execute()
                        st.success("Transaksi dihapus.")
                        st.rerun()
            st.dataframe(df_fin, use_container_width=True, hide_index=True)

    # ----------------------------------------------------------
    # TAB: ARSIP SURAT
    # ----------------------------------------------------------
    if "📂 Arsip Surat" in tabs_list:
        with active_tabs[tabs_list.index("📂 Arsip Surat")]:
            st.subheader("📂 Manajemen Arsip Surat")
            with st.expander("➕ Tambah Arsip Surat Baru"):
                with st.form("form_surat"):
                    col1, col2  = st.columns(2)
                    no_s        = col1.text_input("Nomor Surat")
                    kat_s       = col2.selectbox("Kategori", ["Surat Masuk", "Surat Keluar", "SK", "Lainnya"])
                    perihal_s   = st.text_input("Perihal / Judul Surat")
                    link_s      = st.text_input("Link Document (GDrive/Dropbox)")
                    if st.form_submit_button("Simpan ke Database"):
                        # Validasi URL sederhana
                        if no_s.strip() and perihal_s.strip():
                            if link_s and not link_s.startswith(("https://", "http://")):
                                st.error("Link harus diawali https:// atau http://")
                            else:
                                supabase.table("arsip_surat").insert({
                                    "nomor":   escape_text(no_s.strip()),
                                    "kategori": kat_s,
                                    "perihal": escape_text(perihal_s.strip()),
                                    "link":    link_s.strip()
                                }).execute()
                                st.success("Arsip berhasil disimpan!")
                                st.rerun()
                        else:
                            st.error("Nomor dan Perihal wajib diisi!")
            try:
                res_s = supabase.table("arsip_surat").select("*").order("created_at", desc=True).execute()
                if res_s.data:
                    df_surat = pd.DataFrame(res_s.data)
                    st.dataframe(df_surat[['nomor', 'kategori', 'perihal', 'link']], use_container_width=True, hide_index=True)
                    confirm_s = st.checkbox("Saya yakin ingin menghapus arsip terakhir")
                    if st.button("🗑️ Hapus Arsip Terakhir", disabled=not confirm_s):
                        supabase.table("arsip_surat").delete().eq("id", df_surat.iloc[0]['id']).execute()
                        st.rerun()
                else:
                    st.info("Belum ada arsip surat.")
            except:
                st.warning("Gagal memuat tabel 'arsip_surat'.")

    # ----------------------------------------------------------
    # TAB: EXECUTIVE
    # ----------------------------------------------------------
    if "📜 Executive" in tabs_list:
        with active_tabs[tabs_list.index("📜 Executive")]:
            st.subheader("📜 Executive Summary & Strategic Notes")
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.info("📊 Status Kedisiplinan Kader")
                total_k = len(df_kader)
                sp_k    = len(df_kader[df_kader['sp_level'] > 0]) if not df_kader.empty else 0
                st.write(f"Total Kader: **{total_k}**")
                st.write(f"Kader dengan SP: **{sp_k}**")
                if total_k > 0: st.progress(sp_k / total_k)

                st.success("💸 Ringkasan Arus Kas")
                pemasukan   = df_fin[df_fin['nominal'] > 0]['nominal'].sum() if not df_fin.empty else 0
                pengeluaran = df_fin[df_fin['nominal'] < 0]['nominal'].sum() if not df_fin.empty else 0
                st.write(f"Pemasukan: **Rp {pemasukan:,.0f}**")
                st.write(f"Pengeluaran: **Rp {abs(pengeluaran):,.0f}**")
                st.write(f"Saldo: **Rp {saldo:,.0f}**")

            with c2:
                st.markdown("### 📝 Strategic Notes")
                with st.form("exec_note_form"):
                    new_note = st.text_area("Input Instruksi/Catatan:", placeholder="Contoh: Segera siapkan laporan proker.")
                    if st.form_submit_button("Posting Catatan"):
                        if new_note.strip():
                            # Sanitasi sebelum simpan ke DB
                            clean_note = sanitize_html(new_note.strip())
                            supabase.table("executive_notes").insert({
                                "author": escape_text(u_curr['username']),
                                "note":   clean_note
                            }).execute()
                            st.success("Catatan diposting!")
                            st.rerun()
                        else:
                            st.error("Catatan tidak boleh kosong!")
                st.divider()
                st.markdown("#### Catatan Terkini:")
                try:
                    res_notes = supabase.table("executive_notes").select("*").order("created_at", desc=True).limit(5).execute()
                    if res_notes.data:
                        for n in res_notes.data:
                            # AMAN: data sudah disanitasi saat input, escape lagi saat render
                            safe_author = escape_text(n['author'].upper())
                            safe_date   = escape_text(n['created_at'][:10])
                            safe_note   = sanitize_html(n['note'])  # double-check
                            st.markdown(f"""
                            <div class='note-card'>
                                <small><b>{safe_author}</b> • {safe_date}</small><br>
                                {safe_note}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Belum ada catatan strategis.")
                except:
                    st.warning("Tabel 'executive_notes' belum tersedia.")
            st.divider()
            st.warning("🚨 Dashboard ini hanya untuk pemantauan pimpinan.")

    # ----------------------------------------------------------
    # TAB: BROADCAST
    # ----------------------------------------------------------
    if "📢 Broadcast" in tabs_list:
        with active_tabs[tabs_list.index("📢 Broadcast")]:
            st.subheader("📢 Broadcast WhatsApp")
            msg = st.text_area("Pesan WA:", max_chars=1000)
            if st.button("🚀 BLAST"):
                if msg.strip():
                    # Hanya izinkan karakter aman untuk dikirim via URL
                    encoded = urllib.parse.quote(msg.strip())
                    st.markdown(f"### [🔗 Klik untuk Kirim via WA](https://wa.me/?text={encoded})")
                    st.info("Link di atas akan membuka WhatsApp dengan pesan yang sudah disiapkan.")
                else:
                    st.error("Pesan tidak boleh kosong!")

    # ----------------------------------------------------------
    # TAB: ADMIN
    # ----------------------------------------------------------
    if "⚙️ Admin" in tabs_list:
        with active_tabs[tabs_list.index("⚙️ Admin")]:
            if u_curr['username'] == SUPERADMIN_USER:
                st.subheader("🛠️ System Configuration")
                res_mt    = supabase.table("settings").select("value").eq("key", "maintenance_mode").execute()
                curr_mt   = res_mt.data[0]['value'] if res_mt.data else "false"
                new_status = st.toggle("Aktifkan Mode Maintenance", value=(curr_mt == "true"))
                if st.button("Simpan Konfigurasi"):
                    val_save = "true" if new_status else "false"
                    supabase.table("settings").update({"value": val_save}).eq("key", "maintenance_mode").execute()
                    get_maintenance_status.clear()  # Clear cache agar langsung update
                    st.success(f"Mode Maintenance: **{val_save}**")
                    st.rerun()
                st.divider()

            st.subheader("👥 User Management")
            res_u = supabase.table("users").select("id, username, role").execute()
            if res_u.data:
                df_u        = pd.DataFrame(res_u.data)
                st.dataframe(df_u[['username', 'role']], use_container_width=True, hide_index=True)
                other_users = [u for u in df_u['username'].tolist() if u != SUPERADMIN_USER]
                if other_users:
                    col_u, col_r, col_b = st.columns([2, 2, 1])
                    u_target = col_u.selectbox("Pilih User:", other_users)
                    new_r    = col_r.selectbox("Role Baru:", ["Anggota", "BPH", "Sekretaris", "Bendahara", "Ketua", "Wakil Ketua"])
                    col_b.write("")
                    if col_b.button("Update Role"):
                        supabase.table("users").update({"role": new_r}).eq("username", u_target).execute()
                        st.success(f"Role {escape_text(u_target)} diperbarui ke {new_r}!")
                        st.rerun()
                    confirm_del_u = st.checkbox(f"Saya yakin ingin menghapus akun **{u_target}**")
                    if st.button("🔥 Hapus Akun", disabled=not confirm_del_u):
                        supabase.table("users").delete().eq("username", u_target).execute()
                        st.success(f"Akun {escape_text(u_target)} dihapus.")
                        st.rerun()

# ============================================================
# 8. AUTH AREA (incl. PUBLIC QR ABSEN)
# ============================================================
else:
    # Mode publik untuk absen via QR: tidak butuh login.
    # Tetap divalidasi oleh `save_absen()` (harus ada di tabel kader & belum absen hari ini).
    st.title("📷 Absensi Kader (Tanpa Login)")
    st.caption(f"Scan QR untuk mencatat absensi langsung ke tabel {ABSEN_TABLE}.")

    c_public_scan, c_public_manual = st.columns([2, 1])

    with c_public_scan:
        qr_image = st.camera_input("Scan QR Kader")
        if qr_image:
            try:
                nim_from_qr = decode_qr_from_image(qr_image)
                if nim_from_qr:
                    ok, message = save_absen(nim_from_qr, metode="QR")
                    if ok:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("QR tidak terbaca. Pastikan QR berisi NIM dan gambar cukup jelas.")
            except Exception as e:
                st.error(f"Scanner QR bermasalah: {e}")

    with c_public_manual:
        with st.form("public_manual_absen_form"):
            nim_manual = st.text_input("Input NIM Manual")
            submitted_absen = st.form_submit_button("Catat")
            if submitted_absen:
                ok, message = save_absen(nim_manual, metode="Manual")
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    st.divider()

    # Area login tetap tersedia jika operator ingin akses dashboard.
    _, col_auth, _ = st.columns([1, 1.5, 1])
    with col_auth:

        if st.session_state.auth_page == "login":
            st.markdown("<h1 class='auth-heading'>🛡️ LOGIN HIMASTI</h1>", unsafe_allow_html=True)
            u_in_raw = st.text_input("Username", placeholder="huruf kecil/angka/_").lower().strip()
            # Larang simbol/karakter selain yang diizinkan
            u_in = u_in_raw if (u_in_raw == "" or is_valid_username(u_in_raw)) else ""
            p_in = st.text_input("Password", type="password")


            if st.button("LOG IN", use_container_width=True):
                if is_locked_out():
                    st.stop()

                login_ok = False

                # --- Superadmin: bcrypt ---
                if u_in == SUPERADMIN_USER:
                    try:
                        if bcrypt.checkpw(p_in.encode('utf-8'), SUPERADMIN_HASH.encode('utf-8')):
                            login_ok = True
                            st.session_state.user_data = {"username": SUPERADMIN_USER}
                    except Exception:
                        st.error("Terjadi kesalahan sistem saat verifikasi.")

                # --- User biasa: SHA-256 ---
                elif u_in:
                    try:
                        res = supabase.table("users").select("*").eq("username", u_in).execute()
                        if res.data and check_hashes(p_in, res.data[0]['password']):
                            login_ok = True
                            st.session_state.user_data = res.data[0]
                    except Exception:
                        st.error("Terjadi kesalahan saat menghubungi database.")

                if login_ok:
                    st.session_state.logged_in = True
                    reset_rate_limit()
                    st.rerun()
                else:
                    record_failed_attempt()

            if st.button("Belum punya akun? Daftar", use_container_width=True):
                st.session_state.auth_page = "register"
                st.rerun()

        elif st.session_state.auth_page == "register":
            st.markdown("<h1 class='auth-heading'>📝 REGISTER</h1>", unsafe_allow_html=True)
            u_reg = st.text_input("Username (3-30 karakter, huruf kecil/angka/_)").lower().strip()
            p_reg = st.text_input("Password (min 8 karakter, ada huruf & angka)", type="password")
            p_cfm = st.text_input("Confirm Password", type="password")

            if st.button("DAFTAR SEKARANG", use_container_width=True):
                # Validasi username
                if not is_valid_username(u_reg):
                    st.error("Username hanya boleh huruf kecil, angka, underscore (3-30 karakter).")
                # Validasi password strength
                elif not is_strong_password(p_reg):
                    st.error("Password minimal 8 karakter, harus ada huruf dan angka.")
                # Cek konfirmasi password
                elif p_reg != p_cfm:
                    st.error("Password dan konfirmasi tidak cocok.")
                # Cek username tidak boleh sama dengan superadmin
                elif u_reg == SUPERADMIN_USER:
                    st.error("Username tidak tersedia.")
                else:
                    try:
                        supabase.table("users").insert({
                            "username": u_reg,
                            "password": make_hashes(p_reg),
                            "role":     "Anggota"
                        }).execute()
                        st.success("✅ Registrasi berhasil! Silakan login.")
                        st.session_state.auth_page = "login"
                        st.rerun()
                    except Exception:
                        st.error("Username sudah digunakan atau terjadi kesalahan.")

            if st.button("Kembali ke Login", use_container_width=True):
                st.session_state.auth_page = "login"
                st.rerun()
