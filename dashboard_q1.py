"""Dashboard de suivi des collectes Q1 — Ouémé.

Lancement local :
    streamlit run stat/dashboard_q1.py

Déploiement Streamlit Cloud :
    1. Push ce fichier + requirements-dashboard.txt sur GitHub
    2. streamlit.io → New app → pointer sur stat/dashboard_q1.py
    3. Ajouter le secret KOBO_TOKEN dans Settings > Secrets
"""

import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ── Config ──────────────────────────────────────────────────────────────

KOBO_SERVER = "https://kf.kobotoolbox.org"
ASSET_UID = "avzK5q3YLuXufY6j2haUNF"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

SEC_PER_QUESTION = 6  # plancher absolu par question répondue
DURATION_MAX_MIN = 180

SURVEY_COLS = [
    "section_a/A1", "section_a/A2", "section_a/A3", "section_a/A5",
    "section_a/A6", "section_a/A7",
    "section_b/B1", "section_b/B2", "section_b/B3", "section_b/B3_int",
    "section_b/B4", "section_b/B4_int", "section_b/B5", "section_b/B5bis",
    "section_b/B6", "section_b/B6_int", "section_b/B7", "section_b/B7bis",
    "section_b/B8", "section_b/B9", "section_b/B9_int",
    "section_c/C1q", "section_c/C1q_int", "section_c/C2q", "section_c/C2q_int",
    "section_c/C3q", "section_c/C4q", "section_c/C5q", "section_c/C6q",
    "section_c/C6bis",
]

# Cibles démographiques (basées sur RGPH-4 Ouémé + design)
TARGETS = {
    "genre_f_pct": (40, 60),  # % femmes acceptable
    "role_int_pct": (10, 25),  # % intermédiaires
    "age_18_24_pct": (15, 40),
    "edu_none_pct": (5, 30),  # % sans instruction
}

PLAN = {
    ("adjara", "aglogbe"): ("ADJARRA", "Aglogbe", "Rural / Connectée", 7),
    ("adjara", "honvie"): ("ADJARRA", "Honvie", "Rural / Connectée", 10),
    ("adjara", "malanhoui"): ("ADJARRA", "Malanhoui", "Rural / Connectée", 13),
    ("adjara", "mededjonou"): ("ADJARRA", "Mededjonou", "Rural / Connectée", 12),
    ("adjara", "adjarra-1"): ("ADJARRA", "Adjarra I", "Urbain / Connectée", 7),
    ("adjara", "adjarra-2"): ("ADJARRA", "Adjarra II", "Urbain / Connectée", 7),
    ("adjohoun", "adjohoun-centre"): ("ADJOHOUN", "Adjohoun", "Urbain / Dégradée", 6),
    ("adjohoun", "akpadanou"): ("ADJOHOUN", "Akpadanou", "Rural / Dégradée", 5),
    ("adjohoun", "awonou"): ("ADJOHOUN", "Awonou", "Rural / Dégradée", 5),
    ("adjohoun", "azowlisse"): ("ADJOHOUN", "Azowlissé", "Rural / Dégradée", 7),
    ("adjohoun", "deme"): ("ADJOHOUN", "Dèmè", "Rural / Dégradée", 5),
    ("adjohoun", "gangban"): ("ADJOHOUN", "Gangban", "Rural / Dégradée", 5),
    ("adjohoun", "kode"): ("ADJOHOUN", "Kodé", "Rural / Dégradée", 5),
    ("adjohoun", "togbota"): ("ADJOHOUN", "Togbota", "Rural / Dégradée", 5),
    ("aguegues", "avagbodji"): ("AGUEGUES", "Avagbodji", "Rural / Connectée", 7),
    ("aguegues", "houedome"): ("AGUEGUES", "Houedomè", "Rural / Connectée", 8),
    ("aguegues", "zoungame"): ("AGUEGUES", "Zoungamè", "Rural / Connectée", 10),
    ("akpro-misserete", "akpro-misserete-centre"): ("AKPRO-MISSERETE", "Akpro-Missérété", "Urbain / Connectée", 24),
    ("akpro-misserete", "gome-sota"): ("AKPRO-MISSERETE", "Gomè-Sota", "Rural / Connectée", 9),
    ("akpro-misserete", "katagon"): ("AKPRO-MISSERETE", "Katagon", "Rural / Connectée", 10),
    ("akpro-misserete", "vakon"): ("AKPRO-MISSERETE", "Vakon", "Urbain / Connectée", 23),
    ("akpro-misserete", "zoungbome"): ("AKPRO-MISSERETE", "Zoungbomè", "Rural / Connectée", 8),
    ("avrankou", "atchoukpa"): ("AVRANKOU", "Atchoukpa", "Rural / Connectée", 20),
    ("avrankou", "avrankou"): ("AVRANKOU", "Avrankou", "Urbain / Connectée", 12),
    ("avrankou", "djomon"): ("AVRANKOU", "Djomon", "Rural / Connectée", 13),
    ("avrankou", "gbozounme"): ("AVRANKOU", "Gbozounmè", "Rural / Connectée", 6),
    ("avrankou", "kouty"): ("AVRANKOU", "Kouty", "Rural / Connectée", 11),
    ("avrankou", "ouanho"): ("AVRANKOU", "Ouanho", "Rural / Connectée", 9),
    ("avrankou", "sado"): ("AVRANKOU", "Sado", "Rural / Connectée", 5),
    ("bonou", "affame"): ("BONOU", "Affamè", "Rural / Dégradée", 5),
    ("bonou", "atchonsa"): ("BONOU", "Atchonsa", "Rural / Dégradée", 5),
    ("bonou", "bonou"): ("BONOU", "Bonou", "Urbain / Dégradée", 7),
    ("bonou", "dame-wogon"): ("BONOU", "Dame-Wogon", "Rural / Dégradée", 5),
    ("bonou", "hounvigue"): ("BONOU", "Hounviguè", "Rural / Dégradée", 5),
    ("dangbo", "dangbo-centre"): ("DANGBO", "Dangbo", "Urbain / Connectée", 7),
    ("dangbo", "dekin"): ("DANGBO", "Dekin", "Rural / Connectée", 5),
    ("dangbo", "gbeko"): ("DANGBO", "Gbéko", "Rural / Connectée", 9),
    ("dangbo", "houedomey-da"): ("DANGBO", "Houedomèy", "Rural / Connectée", 10),
    ("dangbo", "hozin"): ("DANGBO", "Hozin", "Rural / Connectée", 9),
    ("dangbo", "kessounou"): ("DANGBO", "Kessounou", "Rural / Connectée", 8),
    ("dangbo", "zoungue"): ("DANGBO", "Zounguè", "Rural / Connectée", 7),
    ("porto-novo", "pn-1"): ("PORTO-NOVO", "1er Arrondissement", "Urbain / Connectée", 19),
    ("porto-novo", "pn-2"): ("PORTO-NOVO", "2e Arrondissement", "Urbain / Connectée", 31),
    ("porto-novo", "pn-3"): ("PORTO-NOVO", "3e Arrondissement", "Urbain / Connectée", 19),
    ("porto-novo", "pn-4"): ("PORTO-NOVO", "4e Arrondissement", "Urbain / Connectée", 37),
    ("porto-novo", "pn-5"): ("PORTO-NOVO", "5e Arrondissement", "Urbain / Connectée", 47),
    ("seme-podji", "agblangandan"): ("SEME-KPODJI", "Agblangandan", "Urbain / Connectée", 34),
    ("seme-podji", "aholouyeme"): ("SEME-KPODJI", "Aholouyèmè", "Rural / Connectée", 8),
    ("seme-podji", "djeregbe"): ("SEME-KPODJI", "Djèrègbé", "Rural / Connectée", 12),
    ("seme-podji", "ekpe"): ("SEME-KPODJI", "Ekpè", "Urbain / Connectée", 44),
    ("seme-podji", "seme-kpodji-centre"): ("SEME-KPODJI", "Sèmè-Kpodji", "Urbain / Connectée", 14),
    ("seme-podji", "tohoue"): ("SEME-KPODJI", "Tohouè", "Rural / Connectée", 19),
}


# ── Helpers ─────────────────────────────────────────────────────────────

def load_token() -> str:
    # 1. Streamlit Cloud secrets
    try:
        if "KOBO_TOKEN" in st.secrets:
            return st.secrets["KOBO_TOKEN"]
    except Exception:
        pass
    # 2. Env var
    token = os.environ.get("KOBO_TOKEN", "")
    # 3. .env file
    if not token and ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("KOBO_TOKEN="):
                token = line.split("=", 1)[1].strip()
    return token


@st.cache_data(ttl=120)
def fetch_kobo(token: str) -> pd.DataFrame:
    url = f"{KOBO_SERVER}/api/v2/assets/{ASSET_UID}/data.json?limit=5000"
    resp = requests.get(url, headers={"Authorization": f"Token {token}"}, timeout=30)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["results"])


def count_answered(row) -> int:
    n = 0
    for col in SURVEY_COLS:
        val = row.get(col)
        if val is not None and val != "" and not (isinstance(val, float) and pd.isna(val)):
            n += 1
    return n


def clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["start_dt"] = pd.to_datetime(out["start"], errors="coerce", utc=True)
    out["end_dt"] = pd.to_datetime(out["end"], errors="coerce", utc=True)
    out["duration_min"] = (out["end_dt"] - out["start_dt"]).dt.total_seconds() / 60
    out["n_answered"] = out.apply(count_answered, axis=1)
    out["seuil_min"] = (out["n_answered"] * SEC_PER_QUESTION / 60).clip(lower=1.0)
    out["flag_court"] = out["duration_min"] < out["seuil_min"]
    out["flag_long"] = out["duration_min"] > DURATION_MAX_MIN
    out["flag_a1"] = out["section_a/A1"].isna() | (out["section_a/A1"] == "")
    out["flagged"] = out["flag_court"] | out["flag_long"] | out["flag_a1"]
    out["commune"] = out["metadata_terrain/commune"].fillna("?")
    out["arrondissement"] = out["metadata_terrain/arrondissement"].fillna("?")
    out["enqueteur"] = out["metadata_terrain/id_enqueteur"].fillna("?")
    out["role"] = out["section_a/A1"].fillna("?")
    out["genre"] = out["section_a/A3"].fillna("?")
    out["age"] = out["section_a/A2"].fillna("?")
    out["education"] = out["section_a/A6"].fillna("?")
    out["mode"] = out["metadata_terrain/mode_administration"].fillna("?")
    out["date"] = out["_submission_time"].str[:10]
    return out


def build_quota_table(df_clean: pd.DataFrame) -> pd.DataFrame:
    counts = df_clean.groupby(["commune", "arrondissement"]).size().reset_index(name="collecte")
    rows = []
    for (ck, ak), (commune, arr, strate, cible) in PLAN.items():
        match = counts[(counts["commune"] == ck) & (counts["arrondissement"] == ak)]
        collecte = int(match["collecte"].sum()) if len(match) else 0
        restant = max(0, cible - collecte)
        taux = round(collecte / cible * 100) if cible else 0
        if collecte >= cible:
            statut = "Atteint"
        elif collecte > 0:
            statut = "En cours"
        else:
            statut = "Non démarré"
        rows.append({
            "Commune": commune, "Arrondissement": arr, "Strate": strate,
            "Cible": cible, "Collecté": collecte, "Restant": restant,
            "Taux": taux, "Statut": statut,
        })
    return pd.DataFrame(rows)


def progress_html(pct: int, width: str = "100%") -> str:
    pct_clamped = min(pct, 150)
    if pct >= 100:
        color, bg = "#22c55e", "#dcfce7"
    elif pct >= 50:
        color, bg = "#f59e0b", "#fef3c7"
    elif pct > 0:
        color, bg = "#ef4444", "#fee2e2"
    else:
        color, bg = "#d1d5db", "#f3f4f6"
    bar_w = min(pct_clamped * 100 // 150, 100)
    return (
        f'<div style="background:{bg};border-radius:8px;height:24px;width:{width};position:relative;overflow:hidden">'
        f'<div style="background:{color};height:100%;width:{bar_w}%;border-radius:8px;transition:width .3s"></div>'
        f'<span style="position:absolute;top:3px;left:10px;font-size:12px;font-weight:700;color:#1f2937">{pct}%</span>'
        f'</div>'
    )


def gauge_card(label: str, value: float, lo: float, hi: float, unit: str = "%") -> str:
    if lo <= value <= hi:
        color, icon, bg = "#16a34a", "check_circle", "#f0fdf4"
    elif value < lo:
        color, icon, bg = "#dc2626", "arrow_downward", "#fef2f2"
    else:
        color, icon, bg = "#dc2626", "arrow_upward", "#fef2f2"
    return f"""
    <div style="background:{bg};border-radius:12px;padding:16px 20px;text-align:center;border:1px solid {color}22">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600">{label}</div>
        <div style="font-size:32px;font-weight:800;color:{color};margin:4px 0">{value:.0f}{unit}</div>
        <div style="font-size:11px;color:#94a3b8">cible : {lo:.0f}–{hi:.0f}{unit}</div>
    </div>"""


# ── Styles ──────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
    /* ── Base ── */
    .block-container { padding-top: 1.5rem; }

    /* ── Metrics ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 14px 18px; box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    div[data-testid="stMetric"] label {
        font-size: 11px !important; color: #64748b !important;
        font-weight: 600 !important; text-transform: uppercase; letter-spacing: .6px;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 26px !important; font-weight: 800 !important; color: #0f172a !important;
    }

    /* ── Typography ── */
    h1 { font-weight: 800 !important; letter-spacing: -.5px; }
    h2 { font-weight: 700 !important; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }

    /* ── Tables responsive ── */
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    table th {
        background: #f8fafc; color: #475569; font-weight: 700;
        text-align: left; padding: 10px 12px; border-bottom: 2px solid #e2e8f0;
        font-size: 11px; text-transform: uppercase; letter-spacing: .4px;
        white-space: nowrap;
    }
    table td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
    table tr:hover td { background: #f8fafc; }

    /* Wrap HTML tables in scrollable container */
    .element-container:has(table) { overflow-x: auto; -webkit-overflow-scrolling: touch; }

    /* ── Cards ── */
    .enq-card {
        border-radius: 10px; padding: 14px 18px; margin-bottom: 6px;
        display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: 8px;
    }
    .section-label {
        font-size: 11px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: .6px; font-weight: 600; margin-bottom: 12px;
    }

    /* ── Mobile responsive ── */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }

        /* Stack metrics vertically */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 45% !important; flex: 1 1 45% !important;
        }

        /* Smaller metric text */
        div[data-testid="stMetric"] { padding: 10px 14px; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 20px !important;
        }

        /* Table font */
        table { font-size: 11px; }
        table th, table td { padding: 6px 8px; }

        /* Gauge cards */
        .gauge-row { flex-direction: column !important; }

        /* Header */
        h1 { font-size: 1.4rem !important; }

        /* Tabs scroll */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto; flex-wrap: nowrap;
            -webkit-overflow-scrolling: touch;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 13px; padding: 6px 12px; white-space: nowrap;
        }
    }

    @media (max-width: 480px) {
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 100% !important; flex: 1 1 100% !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 18px !important;
        }
        table { font-size: 10px; }
    }
</style>

<!-- Viewport meta for mobile -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">
"""


# ── App ─────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Q1 Ouémé — Suivi", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

token = load_token()
if not token:
    st.warning("Token API KoBoToolbox requis.")
    token = st.text_input("Token API", type="password")
if not token:
    st.stop()

# Header
hdr_l, hdr_r = st.columns([5, 1])
with hdr_l:
    st.markdown("# Suivi des collectes Q1")
    st.caption("Intermédiation dans l'e-gouvernement — Ouémé, Bénin")
with hdr_r:
    st.write("")
    if st.button("Rafraichir", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    raw = fetch_kobo(token)
except Exception as e:
    st.error(f"Erreur KoBoToolbox : {e}")
    st.stop()

df = clean(raw)
df_ok = df[~df["flagged"]]
df_flag = df[df["flagged"]]
qt = build_quota_table(df_ok)
n_atteints = (qt["Statut"] == "Atteint").sum()
jours = df["date"].nunique()
pct_global = round(len(df_ok) / 640 * 100)


# ── KPI strip ──────────────────────────────────────────────────────────

st.markdown("---")
k1, k2, k3 = st.columns(3)
k1.metric("Brutes", f"{len(df):,}")
k2.metric("Exploitables", f"{len(df_ok):,}", delta=f"{len(df_flag)} exclues", delta_color="inverse")
k3.metric("Progression", f"{pct_global}%", delta=f"{len(df_ok)} / 640")
k4, k5, k6 = st.columns(3)
k4.metric("Arrond. atteints", f"{n_atteints} / 52")
k5.metric("Jours", jours)
k6.metric("Rythme", f"{len(df_ok) // max(jours, 1)} / jour")

# ── Alertes collecte (toujours visible) ────────────────────────────────

_n = len(df_ok)
_n_f = (df_ok["genre"] == "F").sum()
_pct_f = _n_f / _n * 100 if _n else 0
_n_int = (df_ok["role"] == "intermediary").sum()
_pct_int = _n_int / _n * 100 if _n else 0
_n_none_edu = (df_ok["education"] == "none").sum()
_pct_none_edu = _n_none_edu / _n * 100 if _n else 0
_pct_45plus = ((df_ok["age"] == "45-54").sum() + (df_ok["age"] == "55+").sum()) / _n * 100 if _n else 0
_pct_none_primary = ((df_ok["education"] == "none").sum() + (df_ok["education"] == "primary").sum()) / _n * 100 if _n else 0

_alerts = []
if _pct_f < 40:
    _deficit_f = round((0.40 * 640 - _n_f) / max(640 - _n, 1) * 100)
    _alerts.append(("Femmes sous-représentées", f"Actuellement {_pct_f:.0f}% (cible 40–60%). Sur les {640-_n} restants, viser ~{min(_deficit_f,70)}% de femmes.", "#dc2626"))
elif _pct_f > 60:
    _alerts.append(("Trop de femmes", f"Actuellement {_pct_f:.0f}%. Prioriser les hommes.", "#dc2626"))
if _pct_none_edu < 10:
    _alerts.append(("Sans instruction sous-représentés", f"Actuellement {_pct_none_edu:.0f}% (RGPH-4 Ouémé ~30%). Cibler marchés, zones rurales, personnes âgées.", "#dc2626"))
if _pct_int < 10:
    _alerts.append(("Intermédiaires insuffisants", f"Actuellement {_pct_int:.0f}% (cible 10–25%). Recruter dans les cybercafés.", "#f59e0b"))
if _pct_45plus < 10:
    _alerts.append(("45+ ans sous-représentés", f"Actuellement {_pct_45plus:.0f}%. Cibler bureaux de quartier, chefs de ménage.", "#f59e0b"))
if _pct_none_primary < 25:
    _alerts.append(("Faible littératie sous-représentée", f"Sans instruction + primaire = {_pct_none_primary:.0f}% (RGPH-4 ~55%). Mode assisté en zone rurale.", "#f59e0b"))

if _alerts:
    if any(a[2] == "#dc2626" for a in _alerts):
        _bg, _bd = "#fef2f2", "#fecaca"
        _title = "Actions prioritaires pour la suite de la collecte"
        _icon = "🚨"
    else:
        _bg, _bd = "#fffbeb", "#fed7aa"
        _title = "Points d'attention"
        _icon = "⚠️"
    _html = f'<div style="background:{_bg};border:1px solid {_bd};border-radius:12px;padding:18px 22px;margin:16px 0">'
    _html += f'<div style="font-weight:700;font-size:15px;color:#1e293b;margin-bottom:10px">{_icon} {_title}</div>'
    for t, m, c in _alerts:
        _html += f'<div style="margin-bottom:6px"><span style="color:{c};font-weight:700;font-size:13px">{t}</span> <span style="color:#475569;font-size:13px">— {m}</span></div>'
    _html += '</div>'
    st.markdown(_html, unsafe_allow_html=True)
else:
    st.markdown(
        '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:18px 22px;margin:16px 0">'
        '<span style="font-weight:700;color:#166534">✅ Profil équilibré</span> — Tous les indicateurs sont dans les fourchettes cibles.'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")


# ── Tabs ────────────────────────────────────────────────────────────────

tab_quotas, tab_demo, tab_qualite, tab_timeline, tab_detail = st.tabs([
    "Quotas",
    "Profil échantillon",
    "Qualité",
    "Timeline",
    "Exclusions",
])


# ── Tab 0 : Profil démographique ───────────────────────────────────────

with tab_demo:
    n = len(df_ok)

    # Genre
    n_f = (df_ok["genre"] == "F").sum()
    pct_f = n_f / n * 100 if n else 0
    # Rôle
    n_int = (df_ok["role"] == "intermediary").sum()
    pct_int = n_int / n * 100 if n else 0
    # Age 18-24
    n_young = (df_ok["age"] == "18-24").sum()
    pct_young = n_young / n * 100 if n else 0
    # Education = none
    n_none_edu = (df_ok["education"] == "none").sum()
    pct_none_edu = n_none_edu / n * 100 if n else 0

    st.markdown('<div class="section-label">Indicateurs démographiques — échantillon exploitable</div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)
    with g1:
        st.markdown(gauge_card("Femmes", pct_f, *TARGETS["genre_f_pct"]), unsafe_allow_html=True)
    with g2:
        st.markdown(gauge_card("Intermédiaires", pct_int, *TARGETS["role_int_pct"]), unsafe_allow_html=True)
    g3, g4 = st.columns(2)
    with g3:
        st.markdown(gauge_card("18–24 ans", pct_young, *TARGETS["age_18_24_pct"]), unsafe_allow_html=True)
    with g4:
        st.markdown(gauge_card("Sans instruction", pct_none_edu, *TARGETS["edu_none_pct"]), unsafe_allow_html=True)

    st.markdown("---")

    # Detailed breakdowns
    d1, d2 = st.columns(2)
    d3, d4 = st.columns(2)

    with d1:
        st.markdown("##### Genre")
        genre_df = df_ok["genre"].value_counts().reset_index()
        genre_df.columns = ["Genre", "n"]
        genre_df["Genre"] = genre_df["Genre"].map({"M": "Homme", "F": "Femme"}).fillna("?")
        genre_df["%"] = (genre_df["n"] / n * 100).round(1)
        st.dataframe(genre_df, hide_index=True, use_container_width=True)

    with d2:
        st.markdown("##### Tranche d'age")
        age_df = df_ok["age"].value_counts().reindex(["18-24", "25-34", "35-44", "45-54", "55+"]).reset_index()
        age_df.columns = ["Tranche", "n"]
        age_df["%"] = (age_df["n"] / n * 100).round(1)
        st.dataframe(age_df, hide_index=True, use_container_width=True)

    with d3:
        st.markdown("##### Education")
        edu_order = ["none", "primary", "secondary", "university"]
        edu_labels = {"none": "Aucun", "primary": "Primaire", "secondary": "Secondaire", "university": "Universitaire"}
        edu_df = df_ok["education"].value_counts().reindex(edu_order).reset_index()
        edu_df.columns = ["Niveau", "n"]
        edu_df["Niveau"] = edu_df["Niveau"].map(edu_labels).fillna("?")
        edu_df["%"] = (edu_df["n"] / n * 100).round(1)
        st.dataframe(edu_df, hide_index=True, use_container_width=True)

    with d4:
        st.markdown("##### Mode d'administration")
        mode_df = df_ok["mode"].value_counts().reset_index()
        mode_df.columns = ["Mode", "n"]
        mode_df["Mode"] = mode_df["Mode"].map({"assiste": "Assisté", "auto": "Auto-administré"}).fillna("?")
        mode_df["%"] = (mode_df["n"] / n * 100).round(1)
        st.dataframe(mode_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # Per-commune demographic breakdown
    st.markdown("##### Profil par commune")
    commune_demo = df_ok.groupby("commune").agg(
        n=("_id", "count"),
        femmes=("genre", lambda x: (x == "F").sum()),
        intermediaires=("role", lambda x: (x == "intermediary").sum()),
        jeunes=("age", lambda x: (x == "18-24").sum()),
        sans_instr=("education", lambda x: (x == "none").sum()),
    ).reset_index()
    commune_demo.columns = ["Commune", "n", "Femmes", "Interméd.", "18-24", "Sans instr."]
    for col in ["Femmes", "Interméd.", "18-24", "Sans instr."]:
        commune_demo[f"% {col}"] = (commune_demo[col] / commune_demo["n"] * 100).round(0).astype(int)

    display_demo = commune_demo[["Commune", "n", "Femmes", "% Femmes", "Interméd.", "% Interméd.", "18-24", "% 18-24", "Sans instr.", "% Sans instr."]].copy()
    st.dataframe(display_demo, hide_index=True, use_container_width=True)


# ── Tab 1 : Quotas ─────────────────────────────────────────────────────

with tab_quotas:
    f1, f2, f3 = st.columns(3)
    with f1:
        communes = ["Toutes"] + sorted(qt["Commune"].unique().tolist())
        sel_commune = st.selectbox("Commune", communes, key="q_commune")
    with f2:
        strates = ["Toutes"] + sorted(qt["Strate"].unique().tolist())
        sel_strate = st.selectbox("Strate", strates, key="q_strate")
    with f3:
        statuts_opts = ["Tous", "Atteint", "En cours", "Non démarré"]
        sel_statut = st.selectbox("Statut", statuts_opts, key="q_statut")

    filtered = qt.copy()
    if sel_commune != "Toutes":
        filtered = filtered[filtered["Commune"] == sel_commune]
    if sel_strate != "Toutes":
        filtered = filtered[filtered["Strate"] == sel_strate]
    if sel_statut != "Tous":
        filtered = filtered[filtered["Statut"] == sel_statut]

    disp = filtered.copy()
    disp["Progression"] = disp["Taux"].apply(progress_html)
    status_icons = {"Atteint": "✅", "En cours": "🔶", "Non démarré": "❌"}
    disp["Statut"] = disp["Statut"].map(lambda s: f'{status_icons.get(s, "")} {s}')

    st.markdown(
        disp[["Commune", "Arrondissement", "Strate", "Cible", "Collecté", "Restant", "Progression", "Statut"]]
        .to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    c_comm, c_strate = st.columns(2)

    with c_comm:
        st.markdown("##### Par commune")
        ca = qt.groupby("Commune").agg(Cible=("Cible", "sum"), Collecté=("Collecté", "sum"), Restant=("Restant", "sum")).reset_index()
        ca["Taux"] = (ca["Collecté"] / ca["Cible"] * 100).round(0).astype(int)
        ca["Progression"] = ca["Taux"].apply(progress_html)
        st.markdown(ca[["Commune", "Cible", "Collecté", "Restant", "Progression"]].to_html(escape=False, index=False), unsafe_allow_html=True)

    with c_strate:
        st.markdown("##### Par strate")
        sa = qt.groupby("Strate").agg(Cible=("Cible", "sum"), Collecté=("Collecté", "sum"), Restant=("Restant", "sum")).reset_index()
        sa["Taux"] = (sa["Collecté"] / sa["Cible"] * 100).round(0).astype(int)
        sa["Progression"] = sa["Taux"].apply(progress_html)
        st.markdown(sa[["Strate", "Cible", "Collecté", "Restant", "Progression"]].to_html(escape=False, index=False), unsafe_allow_html=True)


# ── Tab 2 : Qualité ────────────────────────────────────────────────────

with tab_qualite:
    col_flags, col_enq = st.columns([1, 1], gap="large")

    with col_flags:
        st.subheader("Nettoyage")

        f_court = int(df["flag_court"].sum())
        f_long = int(df["flag_long"].sum())
        f_a1 = int(df["flag_a1"].sum())

        st.markdown(f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:20px;margin-bottom:16px">
            <div style="font-size:36px;font-weight:800;color:#991b1b">{len(df_flag)}</div>
            <div style="font-size:13px;color:#b91c1c;font-weight:500">exclues sur {len(df)} ({len(df_flag)*100//len(df)}%)</div>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(pd.DataFrame({
            "Motif": [
                f"Durée < seuil (n_questions x {SEC_PER_QUESTION}s)",
                f"Durée > {DURATION_MAX_MIN} min",
                "Role (A1) manquant",
            ],
            "n": [f_court, f_long, f_a1],
        }), hide_index=True, use_container_width=True)

        st.markdown(f"""
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;margin-top:12px;font-size:13px;color:#1e40af">
            <strong>Seuil adaptatif par skip logic</strong><br>
            Chaque soumission a un seuil = (questions répondues) x {SEC_PER_QUESTION}s.<br>
            Plage observée : {df['n_answered'].min()}–{df['n_answered'].max()} questions → seuils de {df['seuil_min'].min():.1f}–{df['seuil_min'].max():.1f} min.
        </div>
        """, unsafe_allow_html=True)

    with col_enq:
        st.subheader("Enquêteurs")
        enq = df.groupby("enqueteur").agg(
            total=("_id", "count"), flagged=("flagged", "sum"), dur=("duration_min", "median"),
        ).reset_index()
        enq["pct"] = (enq["flagged"] / enq["total"] * 100).round(0).astype(int)
        enq = enq.sort_values("pct", ascending=False)

        for _, r in enq.iterrows():
            if r["pct"] >= 40:
                bg, border = "#fef2f2", "#fecaca"
            elif r["pct"] >= 20:
                bg, border = "#fffbeb", "#fed7aa"
            else:
                bg, border = "#f0fdf4", "#bbf7d0"
            st.markdown(f"""
            <div class="enq-card" style="background:{bg};border:1px solid {border}">
                <div>
                    <div style="font-weight:700;font-size:14px;color:#1e293b">{r['enqueteur']}</div>
                    <div style="font-size:12px;color:#64748b">{int(r['total'])} soumissions · méd. {r['dur']:.1f} min</div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:22px;font-weight:800;color:#1e293b">{int(r['flagged'])}</div>
                    <div style="font-size:11px;color:#64748b">exclues ({r['pct']}%)</div>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Distribution des durées")

    dc1, dc2 = st.columns(2)
    with dc1:
        ch = df[df["duration_min"].between(0, 30)].copy()
        ch["Durée (min)"] = ch["duration_min"].round(0).astype(int)
        hist = ch.groupby("Durée (min)").size().reset_index(name="n")
        st.bar_chart(hist, x="Durée (min)", y="n", color="#6366f1")
        st.caption("0–30 min, toutes soumissions")

    with dc2:
        scatter_data = df[df["duration_min"].between(0, 30)][["n_answered", "duration_min"]].copy()
        scatter_data.columns = ["Questions répondues", "Durée (min)"]
        st.scatter_chart(scatter_data, x="Questions répondues", y="Durée (min)", color="#6366f1")
        st.caption("Durée vs nombre de questions (skip logic)")


# ── Tab 3 : Timeline ───────────────────────────────────────────────────

with tab_timeline:
    daily_all = df.groupby("date").size().reset_index(name="Brutes")
    daily_ok = df_ok.groupby("date").size().reset_index(name="Exploitables")
    daily = daily_all.merge(daily_ok, on="date", how="left").fillna(0)
    daily["Exploitables"] = daily["Exploitables"].astype(int)
    daily["date"] = pd.to_datetime(daily["date"])

    st.subheader("Par jour")
    st.bar_chart(daily, x="date", y=["Brutes", "Exploitables"], color=["#cbd5e1", "#6366f1"])

    st.markdown("---")
    st.subheader("Cumul")
    cumul = daily.sort_values("date").copy()
    cumul["Cumul brut"] = cumul["Brutes"].cumsum()
    cumul["Cumul exploitable"] = cumul["Exploitables"].cumsum()
    st.line_chart(cumul, x="date", y=["Cumul brut", "Cumul exploitable"], color=["#94a3b8", "#6366f1"])
    st.caption("Cible : 640 exploitables")


# ── Tab 4 : Détail exclusions ──────────────────────────────────────────

with tab_detail:
    st.subheader(f"{len(df_flag)} soumissions exclues")
    ff = st.selectbox("Filtrer", ["Tous", "Trop court", "Trop long", "A1 manquant"], key="ff")
    show = df_flag.copy()
    if ff == "Trop court":
        show = show[show["flag_court"]]
    elif ff == "Trop long":
        show = show[show["flag_long"]]
    elif ff == "A1 manquant":
        show = show[show["flag_a1"]]

    cols = show[["_id", "date", "commune", "arrondissement", "enqueteur", "role",
                  "n_answered", "seuil_min", "duration_min"]].copy()
    cols["seuil_min"] = cols["seuil_min"].round(1)
    cols["duration_min"] = cols["duration_min"].round(1)
    cols.columns = ["ID", "Date", "Commune", "Arrondissement", "Enquêteur", "Rôle",
                     "Questions", "Seuil (min)", "Durée (min)"]
    st.dataframe(cols.sort_values("Durée (min)"), hide_index=True, use_container_width=True, height=600)


# ── Footer ──────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#94a3b8;font-size:11px;padding:8px 0">'
    'Q1 Ouémé — Thèse J.-B. Gandonou · KoBoToolbox temps réel · Cache 2 min'
    '</div>',
    unsafe_allow_html=True,
)
