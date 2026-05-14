import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime


def _today_weekday_id():
    """Return weekday id 0=Senin ... 6=Minggu using pandas (requested: pakai pd)."""
    now = pd.Timestamp(datetime.now().date())
    day_name = now.day_name()  # English day name
    id_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    return id_map.get(day_name, -1)


import bcrypt
import urllib.parse
import html
import time
import os
import base64

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="HIMASTI PORTAL",
    page_icon="🛡️",
    layout="wide"
)

# =========================================================
# LOAD SECRETS
# =========================================================
try:
    def get_secret(name, default=""):
        return st.secrets.get(name, os.getenv(name, default))

    URL = get_secret("SUPABASE_URL")
    KEY = get_secret("SUPABASE_KEY")

    SUPERADMIN_CONFIG = st.secrets.get("superadmin", {})
    SUPERADMIN_ID = (
        SUPERADMIN_CONFIG.get("username", "") or
        get_secret("SUPERADMIN_USERNAME") or
        get_secret("SUPERADMIN_ID")
    ).strip().lower()
    SUPERADMIN_HASH = (
        SUPERADMIN_CONFIG.get("password_hash", "") or
        get_secret("SUPERADMIN_PASSWORD_HASH") or
        get_secret("SUPERADMIN_HASH")
    ).strip()

    missing_secrets = []

    if not URL:
        missing_secrets.append("SUPABASE_URL")

    if not KEY:
        missing_secrets.append("SUPABASE_KEY")

    if not SUPERADMIN_ID:
        missing_secrets.append(
            "[superadmin].username atau SUPERADMIN_USERNAME"
        )

    if not SUPERADMIN_HASH:
        missing_secrets.append(
            "[superadmin].password_hash atau SUPERADMIN_PASSWORD_HASH"
        )

    if missing_secrets:
        detected_keys = ", ".join(st.secrets.keys())

        st.error(
            "Secrets belum lengkap: " +
            ", ".join(missing_secrets)
        )
        st.caption(
            "Key secrets yang terbaca: " +
            (detected_keys if detected_keys else "tidak ada")
        )
        st.stop()

except Exception as e:
    st.error(f"Secrets Error: {e}")
    st.stop()

supabase = create_client(URL, KEY)

# =========================================================
# SESSION
# =========================================================
DEFAULT_SESSION = {
    "logged_in": False,
    "user_data": None,
    "auth_page": "login"
}

ORGANIZATION_ROLES = [
    "Ketua Himpunan",
    "Wakil Ketua Himpunan",
    "Sekretaris",
    "Bendahara",
    "Kabid Organisasi",
    "Kabid Riset dan Pengembangan",
    "Kabid Advokasi",
    "Kabid Kemuhammadiyahan",
    "Kabid Humas",
    "Kabid Minat Bakat",
    "Kabid Pengkaderan",
    "Kabid Kewirausahaan",
    "Kabid Media Komunikasi",
    "Korlap",
    "Dewan Penasehat",
    "Dewan Pengawas",
    "BPH",
    "Anggota"
]

SINGLE_OCCUPANCY_ROLES = [
    "Ketua Himpunan",
    "Wakil Ketua Himpunan",
    "Sekretaris",
    "Bendahara",
    "Kabid Organisasi",
    "Kabid Riset dan Pengembangan",
    "Kabid Advokasi",
    "Kabid Kemuhammadiyahan",
    "Kabid Humas",
    "Kabid Minat Bakat",
    "Kabid Pengkaderan",
    "Kabid Kewirausahaan",
    "Kabid Media Komunikasi"
]

for k, v in DEFAULT_SESSION.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================================================
# CSS global (Streamlit 1.57+: stElementContainer / stMarkdown / stMarkdownContainer)
# =========================================================
_GLOBAL_CSS = """
<style>

/* =========================================================
   ROOT & CORE RESET
========================================================= */
:root {
  --bg-main: #050505;
  --bg-secondary: #0A0A0A;
  --card-bg: #111111;
  --card-border: #262626;
  --primary: #00d1b2;
  --primary-hover: #00b89c;
  --primary-soft: rgba(0, 209, 178, 0.05);
  --text-main: #F9FAFB;
  --text-soft: #A3A3A3;
  --text-muted: #525252;

  --danger: #ef4444;
  --success: #10b981;

  --radius: 8px;
  --radius-sm: 4px;

  --shadow-sm: 0 1px 2px rgba(0,0,0,0.5);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.6);

  --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
/* =========================================================
APP BACKGROUND
========================================================= */
.stApp {
  background-color: var(--bg-main);
  color: var(--text-main);
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-main); }
::-webkit-scrollbar-thumb { background: #262626; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #333333; }

/* =========================================================
   LOGO BULAT DENGAN BACKGROUND PUTIH
========================================================= */
.auth-logo, .sidebar-logo, .hero-watermark {
    background-color: white !important; /* Memberikan latar putih */
    border-radius: 50% !important;      /* Membuat bentuk menjadi bulat */
    padding: 5px;                       /* Memberi jarak antara logo dan tepi lingkaran */
    object-fit: contain;
    /* Hapus filter atau mix-blend-mode yang membuat warna berubah */
    display: inline-block;
}

/* Ukuran & posisi masing-masing logo */
.auth-logo {
    width: 120px;
    height: 120px;
    margin: 0 auto 20px;
    display: block;
}

.sidebar-logo {
    width: 38px;
    height: 38px;
    padding: 3px;
}

.hero-watermark {
    width: 92px;
    height: 92px;
    padding: 6px;
    display: block;
    margin: 0 auto 18px;
}
/* =========================================================
   SIDEBAR & BRANDING
   ========================================================= */
section[data-testid="stSidebar"] {
    background-color: #0A0A0A !important;
    border-right: 1px solid #262626;
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    margin-bottom: 20px;
}

.sidebar-brand h2 {
    font-size: 0.9rem;
    font-weight: 700;
    color: #F9FAFB;
    margin: 0;
    letter-spacing: -0.01em;
}

/* =========================================================
   REFINED COMPONENTS (Clean Enterprise Look)
   ========================================================= */
.auth-brand {
    max-width: 400px;
    padding: 40px;
    background: #111111;
    border: 1px solid #262626;
    border-radius: 8px;
    text-align: center;
}

div[data-testid="stMetric"] {
    background: #111111;
    border: 1px solid #262626;
    border-radius: 8px;
}

.stButton > button {
    background: #00d1b2 !important;
    color: #000 !important;
    border-radius: 4px !important;
    font-weight: 700 !important;
    border: none !important;
}

.stTextInput input {
    background-color: #1A1A1A !important;
    border: 1px solid #262626 !important;
    border-radius: 4px !important;
}

/* Tab Active State */
.stTabs [aria-selected="true"] {
    color: #00d1b2 !important;
    border-bottom: 2px solid #00d1b2 !important;
}

</style>
"""

# =========================================================
# FUNCTIONS
# =========================================================
def hash_password(password):
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()


def verify_password(password, hashed):
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(
            password.encode(),
            hashed.encode()
        )

    except ValueError:
        return False


def sanitize(text):
    return html.escape(str(text))


def format_rupiah(value):
    return f"Rp {value:,.0f}"


@st.cache_data
def get_logo_data_uri():
    """Prioritaskan PNG/WebP (transparan). JPEG tetap didukung."""
    candidates = [
        ("assets/logo-himasti.png", "image/png"),
        ("assets/logo-himasti.webp", "image/webp"),
    ]
    for path, mime in candidates:
        if os.path.exists(path):
            with open(path, "rb") as logo_file:
                encoded = base64.b64encode(logo_file.read()).decode()
            return f"data:{mime};base64,{encoded}"
    return ""


def build_finance_pie_chart(df_chart):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df_chart["tipe"],
                values=df_chart["nominal"],
                hole=0.52,
                marker=dict(colors=["#00d1b2", "#ff6b6b"]),
                textinfo="label+percent",
                hovertemplate="%{label}<br>Rp %{value:,.0f}<extra></extra>"
    )
                            ]
                                    )

    fig.update_layout(
        height=360,
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f1f1f1"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
    )
                )

    return fig


def save_executive_note(topik, hasil, pembuat):
    return supabase.table("agenda_eksekutif").insert({
        "topik": sanitize(topik),
        "hasil": sanitize(hasil),
        "pembuat": sanitize(pembuat)
    }).execute()


def logout():
    st.session_state.clear()
    st.rerun()


def has_role(roles):
    if not st.session_state.logged_in:
        return False

    role = st.session_state.user_data.get("role")

    return role in roles or role == "Super Admin"


@st.cache_data(ttl=1)
def get_maintenance():
    try:
        res = supabase.table("settings")\
            .select("value")\
                            .eq("key", "maintenance_mode")\
                            .execute()

        if res.data:
            return res.data[0]["value"].lower() == "true"
        return False
    except:
        return False

# =========================================================
# DATABASE LOADERS (lazy + cache-friendly)
# =========================================================

@st.cache_data(ttl=60)
def load_kader():
    try:
        res = supabase.table("kader")\
            .select("*")\
            .order("nama")\
            .execute()

        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Kader Error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_keuangan():
    try:
        res = supabase.table("keuangan")\
            .select("*")\
            .order("tanggal", desc=True)\
            .execute()

        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Finance Error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_absensi():
    try:
        res = supabase.table("absensi")\
            .select("*")\
            .order("waktu", desc=True)\
            .execute()

        return pd.DataFrame(res.data)

    except Exception as e:
        st.error(f"Absensi Error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_arsip():
    try:
        res = supabase.table("arsip_surat")\
            .select("*")\
            .order("tanggal", desc=True)\
            .execute()

        return pd.DataFrame(res.data)

    except Exception as e:
        st.error(f"Arsip Error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_users():
    try:
        res = supabase.table("users")\
            .select("id, username, role")\
            .order("username")\
            .execute()

        return pd.DataFrame(res.data)

    except Exception as e:
        st.error(f"Users Error: {e}")
        return pd.DataFrame()

# =========================================================
# SURAT GENERATOR
# =========================================================
def generate_surat(nomor: str, perihal: str, tanggal: str, jenis: str) -> str:
    nomor_s = sanitize(nomor)
    perihal_s = sanitize(perihal)
    tanggal_s = sanitize(tanggal)
    jenis_s = sanitize(jenis)

    return f"""
    <div class="surat-doc">
    <div class="surat-header">
        <h2>HIMPUNAN MAHASISWA TEKNOLOGI INFORMASI</h2>
        <h3>UNIVERSITAS MUHAMMADIYAH MATARAM</h3>
        <p>Gedung FIK UMMAT</p>
    </div>

    <div class="surat-meta">Mataram, {tanggal_s}</div>

    <p>Nomor : {nomor_s}<br>
    Jenis : {jenis_s}<br>
    Perihal : <b>{perihal_s}</b></p>

    <p>Dengan hormat,</p>

    <p>Sehubungan dengan agenda <b>{perihal_s}</b>,
    maka surat ini dibuat untuk dipergunakan sebagaimana mestinya.</p>

    <div class="surat-sign">
        Ketua HIMASTI
        <br><br><br><br>
        (........................)
    </div>

    </div>
    """

# =========================================================
# MAIN APP
# =========================================================
maintenance = get_maintenance()
logo_data_uri = get_logo_data_uri()
auth_logo_html = (
    f'<img class="auth-logo" src="{logo_data_uri}" alt="Logo HIMASTI">'
    if logo_data_uri
    else ""
)
sidebar_logo_html = (
    f'<img class="sidebar-logo" src="{logo_data_uri}" alt="Logo HIMASTI">'
    if logo_data_uri
    else ""
)
hero_watermark_html = (
    f'<img class="hero-watermark" src="{logo_data_uri}" alt="">'
    if logo_data_uri
    else ""
)

# =========================================================
# AUTH
# =========================================================
# Login dan register sekarang dibuat lebih sejajar dan modern.
# =========================================================
if not st.session_state.logged_in:

    _, col, _ = st.columns([1,1.05,1])

    with col:

        st.markdown(f"""
        <div class="himasti-embed auth-shell">
            <div class="auth-brand">
                {auth_logo_html}
                <h1>HIMASTI PORTAL</h1>
                <p>Command Center Himpunan Mahasiswa Teknologi Informasi</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register"])

        with login_tab:
            if maintenance:
                st.warning("⚠️ SYSTEM MAINTENANCE")

            username = st.text_input("Username", key="login_username").strip().lower()
            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            if st.button("LOGIN"):

                time.sleep(1)

                if (
                    username == SUPERADMIN_ID and
                    verify_password(password, SUPERADMIN_HASH)
                ):

                    st.session_state.logged_in = True
                    st.session_state.user_data = {
                        "username": username,
                        "role": "Super Admin"
                    }

                    st.rerun()

                try:

                    res = supabase.table("users")\
                        .select("*")\
                        .eq("username", username)\
                        .execute()

                    if res.data:

                        user = res.data[0]
                        stored_password = user.get("password", "")

                        if verify_password(password, stored_password):

                            st.session_state.logged_in = True
                            st.session_state.user_data = user

                            st.rerun()

                        if password == stored_password:
                            new_hash = hash_password(password)

                            supabase.table("users")\
                                .update({"password": new_hash})\
                                .eq("id", user["id"])\
                                .execute()

                            user["password"] = new_hash
                            st.session_state.logged_in = True
                            st.session_state.user_data = user

                            st.rerun()

                    st.error("Username / Password Salah")

                except Exception as e:
                    st.error(e)

        with register_tab:

            st.title("📝 REGISTER")

            username = st.text_input("Username", key="register_username")
            password = st.text_input(
                "Password",
                type="password",
                key="register_password"
            )

            if st.button("DAFTAR"):

                username = username.strip().lower()

                if len(username) < 3:
                    st.error("Username terlalu pendek")

                elif " " in username:
                    st.error("Username tidak boleh pakai spasi")

                elif len(password) < 6:
                    st.error("Password minimal 6 karakter")

                else:

                    try:

                        cek = supabase.table("users")\
                            .select("id")\
                            .eq("username", username)\
                            .execute()

                        if cek.data:
                            st.error("Username sudah digunakan")

                        else:

                            supabase.table("users").insert({
                                "username": username,
                                "password": hash_password(password),
                                "role": "Anggota"
                            }).execute()

                            st.success("Akun berhasil dibuat")

                            st.session_state.auth_page = "login"
                            st.rerun()

                    except Exception as e:
                        st.error(e)



# =========================================================
# DASHBOARD
# =========================================================
else:

    user = st.session_state.user_data
    role = user.get("role", "Anggota")
    username = user.get("username", "").upper()

    if maintenance and role != "Super Admin":
        st.warning("System Maintenance")

        if st.button("Logout"):
            logout()

        st.stop()

    with st.sidebar:

        st.markdown(f"""
        <div class="himasti-embed">
        <div class="sidebar-brand">
            {sidebar_logo_html}
            <div>
                <h2>HIMASTI</h2>
                <div class="sidebar-tagline">Integrated Organization System</div>
            </div>
        </div>
        <div class="sidebar-profile">
            <div class="sidebar-label">SIGNED IN AS</div>
            <div class="name">👤 {sanitize(username)}</div>
            <span class="role">{sanitize(role)}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        if st.button("🚪 Logout"):
            logout()

    # =====================================================
    # LOAD DATA (lazy)
    # =====================================================
    df_kader = pd.DataFrame()
    df_fin = pd.DataFrame()
    df_absen = pd.DataFrame()
    df_arsip = pd.DataFrame()

    # Finance needed for saldo metric
    if has_role(["Bendahara"]):


        df_fin = load_keuangan()

    # Kader needed for kader metrics & SP Control/ Kader Data
    df_kader = load_kader()


    saldo = 0

    if not df_fin.empty:
        saldo = df_fin["nominal"].sum()




    # =====================================================
    # METRIC
    # =====================================================
    status_text = "Maintenance" if maintenance else "Active"

    # =====================================================
    # FEATURE: KHUSUS RABU & KAMIS
    # (gunakan pandas / pd sesuai permintaan)
    # =====================================================
    weekday_id = _today_weekday_id()  # 0=Senin ... 6=Minggu
    is_rabu_kamis = weekday_id in (2, 3)  # 2=Rabu, 3=Kamis

    # Catatan: jangan tampilkan debug weekday agar tidak bocor ke tampilan panel.


    if is_rabu_kamis:
        st.markdown("""
        <div class="note-card">
            <h4>Pengingat Khusus</h4>
            <p>Hari Ini Jangan Lupa Menggunakan Pakaian Dinas Harian <b>Rabu</b> atau <b>Kamis</b></p>
        </div>
        """, unsafe_allow_html=True)


        # Aksi contoh (opsional): buat catatan otomatis agar ada jejak aktivitas pimpinan/anggota
        # Tidak ada paksaan insert DB supaya tidak merusak struktur tabel yang mungkin belum ada.
        with st.expander("Lihat Agenda Singkat Hari Ini"):
            hint_text = "Rabu" if weekday_id == 2 else "Kamis"
            st.info(f"Agenda khusus hari ini: {hint_text}.")
            st.write("- Jangan lupa Memakai Pakaian Dinas Harian")




    st.markdown(f"""
    <div class="himasti-embed app-hero">
        {hero_watermark_html}
        <div class="hero-row">
            <div>
                <h1>🏛️ HIMASTI Command Center</h1>
                <p>Sistem kendali data kader, keuangan, arsip, agenda, dan administrasi organisasi.</p>
            </div>
            <div class="hero-pills">
                <span class="role-pill">Role: {sanitize(role)}</span>
                <span class="status-pill">Status: {status_text}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)

    m1.metric("TOTAL KADER", len(df_kader))

    m2.metric(
        "SALDO",
        f"Rp {saldo:,.0f}"
        if has_role(["Bendahara"])
        else "HIDDEN"
    )

    m3.metric(
        "STATUS",
        "⚠️ Maintenance"
        if maintenance
        else "✅ Active"
    )

    # =====================================================
    # TABS
    # =====================================================
    role_tabs_map = {
        "Super Admin": [
            "📊 Analytics",
            "📋 Kader Data",
            "⚡ SP Control",
            "💰 Finance",
            "📂 Arsip Surat",
            "📜 Executive",
            "📢 Broadcast",
            "⚙️ Admin"
        ],

        "Ketua Himpunan": [
            "📊 Analytics",
            "⚡ SP Control",
            "📜 Executive",
            "📢 Broadcast"
        ],

        "Ketua": [
            "📊 Analytics",
            "⚡ SP Control",
            "📜 Executive",
            "📢 Broadcast"
        ],

        "Wakil Ketua Himpunan": [
            "📊 Analytics",
            "⚡ SP Control",
            "📜 Executive",
            "📢 Broadcast"
        ],

        "Wakil Ketua": [
            "📊 Analytics",
            "⚡ SP Control",
            "📜 Executive",
            "📢 Broadcast"
        ],

        "Sekretaris": [
            "📊 Analytics",
            "📋 Kader Data",
            "📂 Arsip Surat"
        ],

        "Bendahara": [
            "📊 Analytics",
            "💰 Finance"
        ],

        "BPH": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Organisasi": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Riset dan Pengembangan": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Advokasi": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Kemuhammadiyahan": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Humas": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Minat Bakat": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Pengkaderan": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Kewirausahaan": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Kabid Media Komunikasi": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Korlap": [
            "📊 Analytics",
            "📋 Kader Data"
        ],

        "Dewan Penasehat": [
            "📊 Analytics",
            "📋 Kader Data",
            "📜 Executive"
        ],

        "Dewan Pengawas": [
            "📊 Analytics",
            "📋 Kader Data",
            "📜 Executive"
        ],

        "Anggota": [
            "📊 Analytics"
        ]
    }

    tabs_list = role_tabs_map.get(role, ["📊 Analytics"])

    active_tabs = st.tabs(tabs_list)
    tab_map = dict(zip(tabs_list, active_tabs))

    # =====================================================
    # ANALYTICS
    # =====================================================
    with tab_map["📊 Analytics"]:

        # Lazy-load absensi supaya tab lain tidak membebani query
        if df_absen.empty:
            df_absen = load_absensi()

        st.subheader("📌 Log Absensi")


        if role == "Anggota":

            if not df_absen.empty:
                df_show = df_absen[
                    df_absen["nama"].str.lower() ==
                    username.lower()
                ]
            else:
                df_show = pd.DataFrame()

        else:
            df_show = df_absen

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True
        )

        if not df_show.empty:

            st.download_button(
                "📥 Download CSV",
                df_show.to_csv(index=False).encode("utf-8"),
                "absensi.csv"
            )

            if has_role(["Sekretaris", "Super Admin"]):

                if st.button("🗑️ Bersihkan Semua Log Absensi"):

                    try:

                        supabase.table("absensi")\
                            .delete()\
                            .neq("id", 0)\
                            .execute()

                        st.success("Log absensi dibersihkan")
                        st.rerun()

                    except Exception as e:
                        st.error(e)

    # =====================================================
    # KADER
    # =====================================================
    if "📋 Kader Data" in tab_map:

        with tab_map["📋 Kader Data"]:

            st.subheader("📋 Manajemen Kader")

            sub1, sub2 = st.tabs([
                "Manajemen Kader",
                "Bulk Import"
            ])

            # =================================================
            # CRUD KADER
            # =================================================
            with sub1:

                col1, col2 = st.columns(2)

                with col1:

                    with st.form("add_kader"):

                        nama = st.text_input("Nama")
                        nim = st.text_input("NIM")
                        hp = st.text_input("No HP")
                        angkatan = st.text_input("Angkatan")

                        if st.form_submit_button("Tambah"):

                            if not nama or not nim:
                                st.error("Lengkapi data")

                            elif not nim.isdigit():
                                st.error("NIM harus angka")

                            else:

                                try:

                                    supabase.table("kader").insert({
                                        "nama": sanitize(nama),
                                        "nim": nim,
                                        "no_hp": hp,
                                        "angkatan": sanitize(angkatan),
                                        "sp_level": 0
                                    }).execute()

                                    st.success("Kader ditambahkan")
                                    st.rerun()

                                except Exception as e:
                                    st.error(e)

                with col2:

                    if not df_kader.empty:

                        pilihan = {
                            f"{x['nama']} ({x['nim']})": x["id"]
                            for _, x in df_kader.iterrows()
                        }

                        target = st.selectbox(
                            "Hapus Kader",
                            pilihan.keys()
                        )

                        if st.button("🗑️ Hapus"):

                            try:

                                supabase.table("kader")\
                                    .delete()\
                                    .eq("id", pilihan[target])\
                                    .execute()

                                st.success("Berhasil dihapus")
                                st.rerun()

                            except Exception as e:
                                st.error(e)

                st.divider()

                st.dataframe(
                    df_kader,
                    use_container_width=True,
                    hide_index=True
                )

            # =================================================
            # BULK IMPORT
            # =================================================
            with sub2:

                if has_role(["BPH"]):

                    file_csv = st.file_uploader(
                        "Upload CSV",
                        type="csv"
                    )

                    if file_csv:

                        try:

                            df_import = pd.read_csv(file_csv)

                            required = [
                                "nama",
                                "nim",
                                "angkatan"
                            ]

                            if all(
                                col in df_import.columns
                                for col in required
                            ):

                                supabase.table("kader").insert(
                                    df_import.to_dict(
                                        orient="records"
                                    )
                                ).execute()

                                st.success("Bulk Import Berhasil")

                            else:
                                st.error("Format CSV Salah")

                        except Exception as e:
                            st.error(e)

    # =====================================================
    # SP CONTROL
    # =====================================================
    if "⚡ SP Control" in tab_map:

        with tab_map["⚡ SP Control"]:

            st.subheader("⚡ SP CONTROL")

            if df_kader.empty:
                st.info("Tidak ada data")

            else:

                for _, row in df_kader.iterrows():

                    c1, c2, c3 = st.columns([4,1,1])

                    c1.write(
                        f"**{row['nama']}** | SP-{row['sp_level']}"
                    )

                    if c2.button(
                        "⬆️",
                        key=f"up_{row['id']}"
                    ):

                        supabase.table("kader")\
                            .update({
                                "sp_level": row["sp_level"] + 1
                            })\
                            .eq("id", row["id"])\
                            .execute()

                        st.rerun()

                    if c3.button(
                        "⬇️",
                        key=f"down_{row['id']}"
                    ):

                        if row["sp_level"] > 0:

                            supabase.table("kader")\
                                .update({
                                    "sp_level": row["sp_level"] - 1
                                })\
                                .eq("id", row["id"])\
                                .execute()

                            st.rerun()

    # =====================================================
    # FINANCE
    # =====================================================
    if "💰 Finance" in tab_map:

        with tab_map["💰 Finance"]:

            st.subheader("💰 Finance")

            if not df_fin.empty:

                chart = df_fin.groupby("tipe")["nominal"]\
                    .sum()\
                    .abs()\
                    .reset_index()

                st.plotly_chart(
                    build_finance_pie_chart(chart),
                    width="stretch"
                )

            with st.form("finance_form"):

                tipe = st.selectbox(
                    "Tipe",
                    ["Pemasukan", "Pengeluaran"]
                )

                tanggal = st.date_input("Tanggal")

                ket = st.text_input("Keterangan")

                nominal = st.number_input(
                    "Nominal",
                    min_value=0
                )

                if st.form_submit_button("Simpan"):

                    try:

                        value = nominal

                        if tipe == "Pengeluaran":
                            value = -nominal

                        supabase.table("keuangan").insert({
                            "tanggal": str(tanggal),
                            "keterangan": sanitize(ket),
                            "nominal": value,
                            "tipe": tipe
                        }).execute()

                        st.success("Transaksi disimpan")
                        st.rerun()

                    except Exception as e:
                        st.error(e)

            st.divider()

            st.dataframe(
                df_fin,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            if st.button("🗑️ Bersihkan Riwayat Keuangan"):

                try:

                    supabase.table("keuangan")\
                        .delete()\
                        .neq("id", 0)\
                        .execute()

                    st.success("Riwayat keuangan dibersihkan")
                    st.rerun()

                except Exception as e:
                    st.error(e)

    # =====================================================
    # ARSIP SURAT
    # =====================================================
    if "📂 Arsip Surat" in tab_map:

        with tab_map["📂 Arsip Surat"]:

            # Lazy-load arsip supaya tab lain tidak membebani query
            if df_arsip.empty:
                df_arsip = load_arsip()

            st.subheader("📂 Sekretaris Center")


            st.info("Panel sekretaris digunakan untuk manajemen surat, dokumentasi administrasi, arsip organisasi, dan draft surat resmi.")

            col1, col2 = st.columns([1,2])

            with col1:

                with st.form("arsip_form"):

                    jenis = st.selectbox(
                        "Jenis",
                        [
                            "Surat Keluar",
                            "Surat Masuk",
                            "SK",
                            "Surat Tugas"
                        ]
                    )

                    nomor = st.text_input("Nomor Surat")
                    kategori = st.text_input("Kategori")
                    perihal = st.text_area("Perihal")
                    link = st.text_input("Link File")
                    status = st.selectbox(
                        "Status",
                        ["Draft", "Approved"]
                    )

                    if st.form_submit_button("Simpan"):

                        try:

                            supabase.table("arsip_surat").insert({
                                "no_surat": sanitize(nomor),
                                "kategori": sanitize(kategori),
                                "perihal": sanitize(perihal),
                                "link": link,
                                "status": status,
                                "jenis": jenis
                            }).execute()

                            st.success("Arsip berhasil disimpan")
                            st.rerun()

                        except Exception as e:
                            st.error(e)

                st.divider()

                if st.checkbox("✨ Preview Surat"):

                    st.markdown(
                        generate_surat(
                            nomor,
                            perihal,
                            datetime.now().strftime("%d %B %Y"),
                            jenis
                        ),
                        unsafe_allow_html=True
                    )

            with col2:

                st.subheader("📁 Data Arsip")

                st.dataframe(
                    df_arsip,
                    use_container_width=True,
                    hide_index=True
                )

    # =====================================================
    # EXECUTIVE
    # =====================================================
    if "📜 Executive" in tab_map:

        with tab_map["📜 Executive"]:

            st.subheader("📜 Executive Center")

            st.info("Panel ini digunakan untuk notulensi rapat, keputusan inti organisasi, reminder penting, serta agenda pimpinan.")

            exec_note_tab, strategic_tab, history_tab = st.tabs([
                "Notulensi",
                "Fitur Strategis",
                "Riwayat"
            ])

            with exec_note_tab:

                with st.form("exec_form"):

                    topik = st.text_input("Topik")
                    hasil = st.text_area("Hasil")

                    if st.form_submit_button("Simpan"):

                        if not topik or not hasil:
                            st.error("Topik dan hasil wajib diisi")

                        else:
                            try:

                                save_executive_note(topik, hasil, username)

                                st.success("Disimpan")
                                st.rerun()

                            except Exception as e:
                                st.error(e)

                st.divider()

            with strategic_tab:

                st.subheader("📌 Fitur Strategis")

                with st.form("strategic_form"):

                    jenis_strategis = st.selectbox(
                        "Jenis Strategis",
                        [
                            "Reminder Agenda Organisasi",
                            "Keputusan Rapat",
                            "Evaluasi Divisi",
                            "Target Kerja",
                            "Pelanggaran Kader",
                            "Kebijakan Internal"
                        ],
                        key="strategic_type"
                    )

                    judul = st.text_input("Judul", key="strategic_title")
                    penanggung_jawab = st.text_input(
                        "Penanggung Jawab",
                        value=username,
                        key="strategic_pic"
                    )

                    col_s1, col_s2, col_s3 = st.columns(3)

                    with col_s1:
                        target_tanggal = st.date_input(
                            "Target Tanggal",
                            key="strategic_target_date"
                        )

                    with col_s2:
                        prioritas = st.selectbox(
                            "Prioritas",
                            ["Tinggi", "Sedang", "Rendah"],
                            key="strategic_priority"
                        )

                    with col_s3:
                        status = st.selectbox(
                            "Status",
                            ["Rencana", "Berjalan", "Selesai", "Tertunda"],
                            key="strategic_status"
                        )

                    detail = st.text_area(
                        "Detail Strategis",
                        key="strategic_detail"
                    )

                    if st.form_submit_button("Simpan Strategis"):

                        if not judul or not detail:
                            st.error("Judul dan detail strategis wajib diisi")

                        else:
                            try:

                                hasil_strategis = f"""
Jenis: {jenis_strategis}
Penanggung Jawab: {penanggung_jawab}
Target Tanggal: {target_tanggal}
Prioritas: {prioritas}
Status: {status}

Detail:
{detail}
                                """.strip()

                                save_executive_note(
                                    f"[{jenis_strategis}] {judul}",
                                    hasil_strategis,
                                    username
                                )

                                st.success("Fitur strategis disimpan")
                                st.rerun()

                            except Exception as e:
                                st.error(e)

            with history_tab:

                try:

                    res_exec = supabase.table(
                        "agenda_eksekutif"
                    ).select("*")\
                    .order("created_at", desc=True)\
                    .execute()

                    for row in res_exec.data:

                        st.markdown(f"""
                        <div class="note-card">
                            <h4>{sanitize(row.get('topik', ''))}</h4>
                            <p>{sanitize(row.get('hasil', ''))}</p>
                            <small>{sanitize(row.get('pembuat', ''))}</small>
                        </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(e)

    # =====================================================
    # BROADCAST
    # =====================================================
    if "📢 Broadcast" in tab_map:

        with tab_map["📢 Broadcast"]:

            st.subheader("📢 WhatsApp Broadcast")

            pesan = st.text_area("Pesan")

            if st.button("Generate Link"):

                if pesan:

                    link = (
                        "https://wa.me/?text=" +
                        urllib.parse.quote(pesan)
                    )

                    st.markdown(
                        f"[📲 Open WhatsApp]({link})"
                    )

    # =====================================================
    # ADMIN
    # =====================================================
    if "⚙️ Admin" in tab_map:

        with tab_map["⚙️ Admin"]:

            st.subheader("⚙️ System Admin")

            admin_setting_tab, admin_role_tab = st.tabs([
                "Pengaturan Sistem",
                "Manajemen Role BPH"
            ])

            with admin_setting_tab:

                maintenance_toggle = st.toggle(
                    "Maintenance Mode",
                    value=maintenance
                )

                if st.button("Apply Setting"):

                    try:

                        supabase.table("settings")\
                            .update({
                                "value":
                                "true"
                                if maintenance_toggle
                                else "false"
                            })\
                            .eq("key", "maintenance_mode")\
                            .execute()

                        st.cache_data.clear()

                        st.success("Status diperbarui")
                        st.rerun()

                    except Exception as e:
                        st.error(e)

            with admin_role_tab:

                st.subheader("👥 Akun Terdaftar")

                df_users = load_users()

                if df_users.empty:
                    st.info("Belum ada akun yang terdaftar")

                else:
                    st.dataframe(
                        df_users,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.divider()

                    with st.form("role_management_form"):

                        user_options = {
                            f"{row['username']} — {row.get('role', 'Anggota')}": row["id"]
                            for _, row in df_users.iterrows()
                        }

                        selected_user_label = st.selectbox(
                            "Pilih Akun",
                            list(user_options.keys()),
                            key="admin_selected_user"
                        )

                        selected_user_id = user_options[selected_user_label]
                        selected_user = df_users[
                            df_users["id"] == selected_user_id
                        ].iloc[0]
                        current_role = selected_user.get("role", "Anggota")

                        role_index = (
                            ORGANIZATION_ROLES.index(current_role)
                            if current_role in ORGANIZATION_ROLES
                            else ORGANIZATION_ROLES.index("Anggota")
                        )

                        selected_role = st.selectbox(
                            "Role Baru",
                            ORGANIZATION_ROLES,
                            index=role_index,
                            key="admin_selected_role"
                        )

                        st.caption(
                            "Ketua, Wakil Ketua, Sekretaris, Bendahara, dan semua Kabid hanya bisa diisi oleh satu akun."
                        )

                        confirm_delete = st.checkbox(
                            "Saya yakin ingin menghapus akun ini",
                            key="admin_confirm_delete"
                        )

                        col_update, col_delete = st.columns(2)

                        with col_update:
                            update_role = st.form_submit_button("Update Role")

                        with col_delete:
                            delete_user = st.form_submit_button("Hapus Akun")

                        if update_role:

                            conflict = pd.DataFrame()

                            if selected_role in SINGLE_OCCUPANCY_ROLES:
                                conflict = df_users[
                                    (df_users["role"] == selected_role) &
                                    (df_users["id"] != selected_user_id)
                                ]

                            if not conflict.empty:
                                taken_by = conflict.iloc[0]["username"]
                                st.error(
                                    f"Role {selected_role} sudah dipakai oleh {taken_by}"
                                )

                            else:
                                try:

                                    supabase.table("users")\
                                        .update({"role": selected_role})\
                                        .eq("id", selected_user_id)\
                                        .execute()

                                    st.success("Role berhasil diperbarui")
                                    st.rerun()

                                except Exception as e:
                                    st.error(e)

                        if delete_user:

                            if not confirm_delete:
                                st.error("Centang konfirmasi sebelum menghapus akun")

                            else:
                                try:

                                    supabase.table("users")\
                                        .delete()\
                                        .eq("id", selected_user_id)\
                                        .execute()

                                    st.success("Akun berhasil dihapus")
                                    st.rerun()

                                except Exception as e:
                                    st.error(e)

