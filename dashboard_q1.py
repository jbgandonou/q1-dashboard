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
    ("aguegues", "houedomey-ag"): ("AGUEGUES", "Houedomè", "Rural / Connectée", 8),
    ("aguegues", "zoungame"): ("AGUEGUES", "Zoungamè", "Rural / Connectée", 10),
    ("akpro-misserete", "akpro-misserete-centre"): ("AKPRO-MISSERETE", "Akpro-Missérété", "Urbain / Connectée", 24),
    ("akpro-misserete", "gome-sota"): ("AKPRO-MISSERETE", "Gomè-Sota", "Rural / Connectée", 9),
    ("akpro-misserete", "katagon"): ("AKPRO-MISSERETE", "Katagon", "Rural / Connectée", 10),
    ("akpro-misserete", "vakon"): ("AKPRO-MISSERETE", "Vakon", "Urbain / Connectée", 23),
    ("akpro-misserete", "zoungbome"): ("AKPRO-MISSERETE", "Zoungbomè", "Rural / Connectée", 8),
    ("avrankou", "atchoukpa"): ("AVRANKOU", "Atchoukpa", "Rural / Connectée", 20),
    ("avrankou", "avrankou-centre"): ("AVRANKOU", "Avrankou", "Urbain / Connectée", 12),
    ("avrankou", "djomon"): ("AVRANKOU", "Djomon", "Rural / Connectée", 13),
    ("avrankou", "gbozounme"): ("AVRANKOU", "Gbozounmè", "Rural / Connectée", 6),
    ("avrankou", "kouty"): ("AVRANKOU", "Kouty", "Rural / Connectée", 11),
    ("avrankou", "ouanho"): ("AVRANKOU", "Ouanho", "Rural / Connectée", 9),
    ("avrankou", "sado"): ("AVRANKOU", "Sado", "Rural / Connectée", 5),
    ("bonou", "affame"): ("BONOU", "Affamè", "Rural / Dégradée", 5),
    ("bonou", "atchonsa"): ("BONOU", "Atchonsa", "Rural / Dégradée", 5),
    ("bonou", "bonou-centre"): ("BONOU", "Bonou", "Urbain / Dégradée", 7),
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


def detect_duplicates(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Doublons consécutifs par enquêteur et arrondissement.

    Deux soumissions sont considérées comme doublons quand :
    - même enquêteur ET même arrondissement,
    - consécutives dans le temps (aucune autre soumission entre les deux
      pour ce couple enquêteur+arrondissement),
    - valeurs identiques sur toutes les colonnes SURVEY_COLS remplies,
    - au moins 8 colonnes non vides en commun.

    Seule la deuxième occurrence est marquée.

    Returns:
        is_dup: boolean Series — True pour la deuxième occurrence.
        dup_of: Series — _id de l'original pour chaque doublon, NaN sinon.
    """
    survey_vals = df[SURVEY_COLS].fillna("")
    enq = df["metadata_terrain/id_enqueteur"].fillna("")
    arr = df["metadata_terrain/arrondissement"].fillna("")
    ts = pd.to_datetime(df["start"], errors="coerce", utc=True)
    is_dup = pd.Series(False, index=df.index)
    dup_of = pd.Series(pd.NA, index=df.index)
    for key in (enq + "||" + arr).unique():
        mask = (enq + "||" + arr) == key
        idx = ts[mask].sort_values().index
        if len(idx) < 2:
            continue
        prev = idx[0]
        prev_filled = {c for c in SURVEY_COLS if survey_vals.loc[prev, c] != ""}
        for i in idx[1:]:
            filled = {c for c in SURVEY_COLS if survey_vals.loc[i, c] != ""}
            common = filled & prev_filled
            if len(common) >= 8 and all(survey_vals.loc[i, c] == survey_vals.loc[prev, c] for c in common):
                is_dup.loc[i] = True
                dup_of.loc[i] = df.loc[prev, "_id"]
            prev = i
            prev_filled = filled
    return is_dup, dup_of


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
    out["flag_consent"] = out.get("consentement", pd.Series("", index=out.index)).fillna("") != "yes"
    out["flag_doublon"], out["doublon_de"] = detect_duplicates(out)
    out["flagged"] = out["flag_court"] | out["flag_long"] | out["flag_a1"] | out["flag_consent"] | out["flag_doublon"]
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
        color, bg = "#16a34a", "#f0fdf4"
    elif value < lo:
        color, bg = "#dc2626", "#fef2f2"
    else:
        color, bg = "#dc2626", "#fef2f2"
    return (
        f'<div class="gauge" style="background:{bg};border:1px solid {color}22">'
        f'<div class="gauge-label">{label}</div>'
        f'<div class="gauge-value" style="color:{color}">{value:.0f}{unit}</div>'
        f'<div class="gauge-target">cible : {lo:.0f}–{hi:.0f}{unit}</div>'
        f'</div>'
    )


def wrap_table(html: str) -> str:
    """Wrap an HTML table in a scrollable container."""
    return f'<div class="table-scroll">{html}</div>'


# ── Styles ──────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
    /* ── Base ── */
    .block-container { padding-top: 1.5rem; }
    section.main > div.block-container { max-width: 100%; }

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
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-size: 12px !important;
    }

    /* ── Typography ── */
    h1 { font-weight: 800 !important; letter-spacing: -.5px; }
    h2 { font-weight: 700 !important; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }

    /* ── Scrollable table wrapper ── */
    .table-scroll {
        width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;
        border: 1px solid #e2e8f0; border-radius: 10px;
    }
    .table-scroll table { margin: 0; border: none; min-width: 600px; }

    /* ── Tables ── */
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    table th {
        background: #f8fafc; color: #475569; font-weight: 700;
        text-align: left; padding: 10px 12px; border-bottom: 2px solid #e2e8f0;
        font-size: 11px; text-transform: uppercase; letter-spacing: .4px;
        white-space: nowrap; position: sticky; top: 0; z-index: 1;
    }
    table td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
    table tr:hover td { background: #f8fafc; }

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

    /* ── Alert box ── */
    .alert-box { border-radius: 12px; padding: 16px 20px; margin: 16px 0; }
    .alert-box .alert-title { font-weight: 700; font-size: 15px; color: #1e293b; margin-bottom: 8px; }
    .alert-box .alert-item { margin-bottom: 5px; line-height: 1.5; }

    /* ── Gauge ── */
    .gauge { border-radius: 12px; padding: 14px 16px; text-align: center; }
    .gauge .gauge-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; font-weight: 600; }
    .gauge .gauge-value { font-size: 28px; font-weight: 800; margin: 2px 0; }
    .gauge .gauge-target { font-size: 10px; color: #94a3b8; }

    /* ── Tablet ── */
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem 0.5rem !important; }

        /* Columns → wrap 2-up */
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 8px !important; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: calc(50% - 8px) !important; flex: 1 1 calc(50% - 8px) !important;
        }

        div[data-testid="stMetric"] { padding: 10px 12px; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 20px !important; }
        div[data-testid="stMetric"] label { font-size: 10px !important; }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 11px !important; }

        table { font-size: 11px; }
        table th, table td { padding: 6px 8px; }
        .table-scroll table { min-width: 500px; }

        h1 { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }

        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto; flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch; scrollbar-width: none;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        .stTabs [data-baseweb="tab"] { font-size: 12px; padding: 6px 10px; white-space: nowrap; flex-shrink: 0; }

        .gauge .gauge-value { font-size: 24px; }
        .gauge .gauge-label { font-size: 9px; }

        .alert-box { padding: 14px 16px; }
        .alert-box .alert-title { font-size: 14px; }
        .alert-box .alert-item { font-size: 12px; }

        .enq-card { padding: 10px 14px; }
        .enq-card div:first-child div:first-child { font-size: 13px !important; }
        .enq-card div:last-child div:first-child { font-size: 18px !important; }
    }

    /* ── Phone ── */
    @media (max-width: 480px) {
        .block-container { padding: 0.5rem 0.3rem !important; }

        /* Columns → full width stack */
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 100% !important; flex: 1 1 100% !important;
        }

        div[data-testid="stMetric"] { padding: 8px 10px; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 18px !important; }

        table { font-size: 10px; }
        table th, table td { padding: 4px 6px; }
        .table-scroll table { min-width: 400px; }

        h1 { font-size: 1.1rem !important; }

        .gauge { padding: 10px 12px; }
        .gauge .gauge-value { font-size: 22px; }

        .alert-box .alert-item span { display: block; }
    }
</style>
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
CIBLE_TOTALE = 640
pct_global = round(len(df_ok) / CIBLE_TOTALE * 100)


# ── Danger KPIs (toujours visibles, avant les onglets) ────────────────

is_citizen_top = df_ok["role"] == "citizen"
is_interm_top = df_ok["role"] == "intermediary"
used_intermed_top = df_ok["section_b/B2"].isin(["intermediary", "relative"])

_b3_pop = df_ok[used_intermed_top & is_citizen_top]
_b3_yes = (_b3_pop["section_b/B3"] == "yes").sum()
_pct_pwd = _b3_yes / len(_b3_pop) * 100 if len(_b3_pop) else 0

_b4_pop = df_ok[used_intermed_top & is_citizen_top]
_b4_not_direct = _b4_pop["section_b/B4"].isin(["handed", "kept", "unknown"])
_pct_p3 = _b4_not_direct.sum() / len(_b4_pop) * 100 if len(_b4_pop) else 0

_c5_yes = (df_ok["section_c/C5q"] == "yes").sum()
_pct_inc = _c5_yes / len(df_ok) * 100 if len(df_ok) else 0

_pct_intermed = used_intermed_top.sum() / len(df_ok) * 100 if len(df_ok) else 0

_b7_pop_top = df_ok[used_intermed_top & is_citizen_top]
_b7_contrainte = _b7_pop_top["section_b/B7"].isin(["no_device", "no_skill"]).sum()
_pct_contrainte_top = _b7_contrainte / len(_b7_pop_top) * 100 if len(_b7_pop_top) else 0


_c1_cit = pd.to_numeric(df_ok.loc[is_citizen_top & used_intermed_top, "section_c/C1q"], errors="coerce").dropna()
_c1_int = pd.to_numeric(df_ok.loc[is_interm_top, "section_c/C1q_int"], errors="coerce").dropna()
_c2_cit = pd.to_numeric(df_ok.loc[is_citizen_top & used_intermed_top, "section_c/C2q"], errors="coerce").dropna()
_c2_int = pd.to_numeric(df_ok.loc[is_interm_top, "section_c/C2q_int"], errors="coerce").dropna()
_mean_conf = _c1_cit.mean() if len(_c1_cit) else 0
_mean_conf_int = _c1_int.mean() if len(_c1_int) else 0
_mean_sec = _c2_cit.mean() if len(_c2_cit) else 0
_mean_sec_int = _c2_int.mean() if len(_c2_int) else 0

_v1_verdict = f"Confiance déclarée, mais {_pct_pwd:.0f}% donnent leur mot de passe à un inconnu"
_v2_verdict = ("Inquiétude déclarée, mais les pratiques ne changent pas"
               if _mean_sec >= 3 else "Peu d'inquiétude — le risque n'est pas perçu")


def _kpi(value: str, label: str, detail: str, danger: bool = False) -> str:
    if danger:
        return (
            f'<div style="background:#991b1b;border-radius:10px;padding:22px 16px;text-align:center">'
            f'<div style="font-size:44px;font-weight:800;color:#fff;line-height:1">{value}</div>'
            f'<div style="font-size:11px;font-weight:700;color:#fecaca;margin-top:10px;text-transform:uppercase;letter-spacing:.8px">{label}</div>'
            f'<div style="font-size:11px;color:#fca5a5;margin-top:3px">{detail}</div>'
            f'</div>'
        )
    return (
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:22px 16px;text-align:center">'
        f'<div style="font-size:44px;font-weight:800;color:#0f172a;line-height:1">{value}</div>'
        f'<div style="font-size:11px;font-weight:700;color:#475569;margin-top:10px;text-transform:uppercase;letter-spacing:.8px">{label}</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:3px">{detail}</div>'
        f'</div>'
    )


def _score_card(question: str, v_cit: float, n_cit: int, v_int: float, n_int: int,
                verdict: str, accent: str) -> str:
    return (
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:20px 24px">'
        f'<div style="font-size:12px;font-weight:600;color:#475569;margin-bottom:16px">{question}</div>'
        f'<div style="display:flex;gap:28px;align-items:baseline">'
        f'<div>'
        f'<span style="font-size:38px;font-weight:800;color:#0f172a">{v_cit:.1f}</span>'
        f'<span style="font-size:15px;color:#94a3b8">/5</span>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:2px">citoyens (n={n_cit})</div>'
        f'</div>'
        f'<div>'
        f'<span style="font-size:38px;font-weight:800;color:#0f172a">{v_int:.1f}</span>'
        f'<span style="font-size:15px;color:#94a3b8">/5</span>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:2px">intermédiaires (n={n_int})</div>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top:14px;padding:8px 12px;background:{accent}10;border-left:3px solid {accent};'
        f'border-radius:0 6px 6px 0;font-size:12px;color:#334155">{verdict}</div>'
        f'</div>'
    )


st.markdown(
    '<div style="margin-bottom:4px">'
    '<span style="font-size:26px;font-weight:800;color:#0f172a;letter-spacing:-.5px">Intermédiation e-gouvernement</span>'
    f'<div style="font-size:13px;color:#64748b;margin-top:4px">Enquête terrain · Ouémé, Bénin · '
    f'{len(df_ok)} répondants · {is_citizen_top.sum()} citoyens · {is_interm_top.sum()} intermédiaires</div>'
    '</div>',
    unsafe_allow_html=True,
)

_n_intermed = used_intermed_top.sum()

def _kpi_large(val1: str, lbl1: str, val2: str, lbl2: str) -> str:
    return (
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:22px 20px;text-align:center">'
        f'<div style="font-size:44px;font-weight:800;color:#0f172a;line-height:1">{val1}</div>'
        f'<div style="font-size:11px;font-weight:700;color:#475569;margin-top:10px;text-transform:uppercase;letter-spacing:.8px">{lbl1}</div>'
        f'<div style="margin-top:14px;padding-top:14px;border-top:1px solid #e2e8f0">'
        f'<span style="font-size:28px;font-weight:800;color:#991b1b">{val2}</span>'
        f'<div style="font-size:11px;font-weight:700;color:#991b1b;margin-top:4px;text-transform:uppercase;letter-spacing:.8px">{lbl2}</div>'
        f'</div></div>'
    )


_k1, _k2, _k3, _k4 = st.columns([1.3, 1, 1, 1])
with _k1:
    st.markdown(_kpi_large(
        f"{_n_intermed}", f"citoyens passent par un intermédiaire ({_pct_intermed:.0f}%)",
        f"{_b7_contrainte}", f"n'ont pas le choix ({_pct_contrainte_top:.0f}%)",
    ), unsafe_allow_html=True)
with _k2:
    st.markdown(_kpi(f"{_pct_pwd:.0f}%", "donnent leur mot de passe",
                     f"{_b3_yes} sur {_n_intermed} via intermédiaire", danger=True), unsafe_allow_html=True)
with _k3:
    st.markdown(_kpi(f"{_pct_p3:.0f}%", "document non remis",
                     "transite par l'intermédiaire"), unsafe_allow_html=True)
with _k4:
    st.markdown(_kpi(f"{_pct_inc:.0f}%", "signalent des abus",
                     f"{_c5_yes} sur {len(df_ok)}"), unsafe_allow_html=True)

st.markdown(
    '<div style="font-size:16px;font-weight:800;color:#0f172a;margin-top:20px">'
    'Les citoyens font confiance — les faits disent le contraire</div>'
    '<div style="font-size:12px;color:#94a3b8;margin-bottom:4px">'
    'Score moyen de confiance sur 5</div>',
    unsafe_allow_html=True,
)

_cc1, _cc2 = st.columns(2)
with _cc1:
    st.markdown(_score_card(
        "« Faites-vous confiance à l'intermédiaire ? »",
        _mean_conf, len(_c1_cit), _mean_conf_int, len(_c1_int),
        _v1_verdict, "#dc2626",
    ), unsafe_allow_html=True)
with _cc2:
    st.markdown(_score_card(
        "« La sécurité de vos données vous inquiète ? »",
        _mean_sec, len(_c2_cit), _mean_sec_int, len(_c2_int),
        _v2_verdict, "#d97706",
    ), unsafe_allow_html=True)

st.markdown("---")


# ── Tabs ────────────────────────────────────────────────────────────────

tab_resultats, tab_quotas, tab_demo, tab_qualite, tab_timeline, tab_doublons, tab_consent, tab_detail = st.tabs([
    "Résultats clés",
    "Quotas",
    "Profil échantillon",
    "Qualité",
    "Timeline",
    "Doublons",
    "Consentement",
    "Exclusions",
])


# ── Tab Résultats clés ────────────────────────────────────────────────

with tab_resultats:
    used_intermed = used_intermed_top
    is_citizen = is_citizen_top
    is_interm = is_interm_top

    # Calculs complémentaires pour ce tab
    b3i_pop = df_ok[is_interm]
    b3i_yes = (b3i_pop["section_b/B3_int"] == "yes").sum()

    b9_pop = df_ok[used_intermed]
    b9_cols = ["section_b/B9", "section_b/B9_int"]
    b9_multi = sum(1 for _, r in b9_pop.iterrows() if any(r.get(c) == "multiple" for c in b9_cols))
    pct_multi = b9_multi / len(b9_pop) * 100 if len(b9_pop) else 0

    # --- Pourquoi l'intermédiation ? (B7) ---
    res_l, res_r = st.columns(2)

    with res_l:
        st.markdown("##### Les citoyens n'ont pas le choix")
        st.caption("Pourquoi confier sa démarche à un tiers ?")
        b7_pop = df_ok[used_intermed & is_citizen]
        b7_labels = {
            "no_device": "Pas de téléphone / ordinateur",
            "no_skill": "Ne sait pas utiliser Internet",
            "convenience": "Plus simple / plus rapide",
            "other": "Autre raison",
        }
        if len(b7_pop):
            b7_counts = b7_pop["section_b/B7"].value_counts()
            b7_df = b7_counts.reset_index()
            b7_df.columns = ["Raison", "Effectif"]
            b7_df["Raison"] = b7_df["Raison"].map(b7_labels).fillna("?")
            b7_df["%"] = (b7_df["Effectif"] / b7_df["Effectif"].sum() * 100).round(1)
            contrainte = b7_df[b7_df["Raison"].isin(["Pas de téléphone / ordinateur", "Ne sait pas utiliser Internet"])]["Effectif"].sum()
            pct_contrainte = contrainte / b7_df["Effectif"].sum() * 100
            st.dataframe(b7_df, hide_index=True, use_container_width=True)
            if pct_contrainte >= 50:
                msg_b7 = (
                    f'<strong style="color:#dc2626">{pct_contrainte:.0f}% subissent l\'intermédiation</strong> '
                    f'faute de terminal ou de compétence numérique. '
                    f'{100 - pct_contrainte:.0f}% choisissent par commodité.'
                )
                bg_b7, bd_b7 = "#fef2f2", "#dc2626"
            else:
                msg_b7 = (
                    f'<strong style="color:#ea580c">{100 - pct_contrainte:.0f}% choisissent l\'intermédiation par commodité</strong> — '
                    f'même quand ils pourraient faire la démarche eux-mêmes. '
                    f'{pct_contrainte:.0f}% y sont contraints faute de terminal ou de compétence.'
                )
                bg_b7, bd_b7 = "#fff7ed", "#ea580c"
            st.markdown(
                f'<div style="background:{bg_b7};border-left:3px solid {bd_b7};border-radius:8px;padding:12px 16px;margin-top:8px;font-size:13px">'
                f'{msg_b7}</div>',
                unsafe_allow_html=True,
            )

    # --- Services les plus exposés (B5) ---
    with res_r:
        st.markdown("##### Les services les plus sensibles sont les plus exposés")
        st.caption("Documents manipulés par des tiers non certifiés")
        b5_labels = {
            "ravip": "RAVIP — identité biométrique",
            "birth": "Acte de naissance",
            "criminal": "Casier judiciaire",
            "nationality": "Certificat de nationalité",
            "other": "Autre",
        }
        b5_pop = df_ok[df_ok["section_b/B5"].notna() & (df_ok["section_b/B5"] != "")]
        if len(b5_pop):
            b5_counts = b5_pop["section_b/B5"].value_counts()
            b5_df = b5_counts.reset_index()
            b5_df.columns = ["Service", "Effectif"]
            b5_df["Service"] = b5_df["Service"].map(b5_labels).fillna("Autre")
            b5_df["%"] = (b5_df["Effectif"] / b5_df["Effectif"].sum() * 100).round(1)
            st.dataframe(b5_df, hide_index=True, use_container_width=True)
            top_service = b5_df.iloc[0]
            st.markdown(
                f'<div style="background:#fff7ed;border-left:3px solid #ea580c;border-radius:8px;padding:12px 16px;margin-top:8px;font-size:13px">'
                f'<strong style="color:#ea580c">{top_service["Service"]}</strong> concentre '
                f'<strong>{top_service["%"]}%</strong> des démarches — '
                f'des données d\'identité critiques passent entre les mains de tiers.'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # --- Ce qui se passe concrètement avec les données ---
    st.markdown(
        '<div style="font-size:15px;font-weight:800;color:#1e293b;margin-bottom:4px">'
        'Ce qui se passe concrètement avec les données des citoyens</div>'
        '<div style="font-size:13px;color:#64748b;margin-bottom:12px">'
        'Parmi les répondants qui ont entendu parler d\'un abus, voici les types signalés</div>',
        unsafe_allow_html=True,
    )
    c6_pop = df_ok[df_ok["section_c/C6q"].notna() & (df_ok["section_c/C6q"] != "")]
    if len(c6_pop):
        c6_labels = {
            "password": "Quelqu'un a réutilisé le mot de passe",
            "copy": "Des documents personnels ont été copiés",
            "unauthorized": "Une démarche a été faite sans l'accord du citoyen",
        }
        all_types = []
        for val in c6_pop["section_c/C6q"]:
            for t in str(val).split():
                all_types.append(t)
        c6_series = pd.Series(all_types)
        c6_counts = c6_series.value_counts().reset_index()
        c6_counts.columns = ["Type d'abus", "Effectif"]
        c6_counts["Type d'abus"] = c6_counts["Type d'abus"].map(c6_labels).fillna("Autre")
        c6_counts = c6_counts.groupby("Type d'abus", as_index=False)["Effectif"].sum().sort_values("Effectif", ascending=False)
        c6_counts["% des signalements"] = (c6_counts["Effectif"] / c6_counts["Effectif"].sum() * 100).round(1)
        st.dataframe(c6_counts, hide_index=True, use_container_width=True)
    else:
        st.info("Aucun incident détaillé.")

    st.markdown("---")

    # --- Urbain vs Rural ---
    st.markdown(
        '<div style="font-size:15px;font-weight:800;color:#1e293b;margin-bottom:4px">'
        'Le monde rural est le plus exposé</div>'
        '<div style="font-size:13px;color:#64748b;margin-bottom:12px">'
        'Taux d\'intermédiation et de partage de mot de passe selon la zone</div>',
        unsafe_allow_html=True,
    )
    zone_l, zone_r = st.columns(2)

    with zone_l:
        zone_data = df_ok.copy()
        zone_data["zone"] = zone_data["metadata_terrain/zone"].fillna("?")
        zone_data["intermedie"] = used_intermed
        zone_grp = zone_data.groupby("zone").agg(
            n=("_id", "count"),
            intermedies=("intermedie", "sum"),
        ).reset_index()
        zone_grp["% qui passent par un tiers"] = (zone_grp["intermedies"] / zone_grp["n"] * 100).round(1)
        zone_labels = {"urbain": "Urbain", "rural": "Rural"}
        zone_grp["zone"] = zone_grp["zone"].map(zone_labels).fillna("?")
        zone_grp.columns = ["Zone", "Répondants", "Via intermédiaire", "% qui passent par un tiers"]
        st.dataframe(zone_grp[["Zone", "Répondants", "Via intermédiaire", "% qui passent par un tiers"]], hide_index=True, use_container_width=True)

    with zone_r:
        zone_data2 = df_ok[used_intermed & is_citizen].copy()
        zone_data2["zone"] = zone_data2["metadata_terrain/zone"].fillna("?")
        zone_data2["pwd_shared"] = zone_data2["section_b/B3"] == "yes"
        zone_pwd = zone_data2.groupby("zone").agg(
            n=("_id", "count"),
            partages=("pwd_shared", "sum"),
        ).reset_index()
        zone_pwd["% qui donnent leur MDP"] = (zone_pwd["partages"] / zone_pwd["n"] * 100).round(1)
        zone_pwd["zone"] = zone_pwd["zone"].map({"urbain": "Urbain", "rural": "Rural"}).fillna("?")
        zone_pwd.columns = ["Zone", "Via intermédiaire", "Partage MDP", "% qui donnent leur MDP"]
        st.dataframe(zone_pwd[["Zone", "Via intermédiaire", "Partage MDP", "% qui donnent leur MDP"]], hide_index=True, use_container_width=True)


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
        genre_df.columns = ["Genre", "Effectif"]
        genre_df["Genre"] = genre_df["Genre"].map({"M": "Homme", "F": "Femme"}).fillna("?")
        genre_df["%"] = (genre_df["Effectif"] / n * 100).round(1)
        st.dataframe(genre_df, hide_index=True, use_container_width=True)

    with d2:
        st.markdown("##### Tranche d'age")
        age_df = df_ok["age"].value_counts().reindex(["18-24", "25-34", "35-44", "45-54", "55+"]).reset_index()
        age_df.columns = ["Tranche", "Effectif"]
        age_df["%"] = (age_df["Effectif"] / n * 100).round(1)
        st.dataframe(age_df, hide_index=True, use_container_width=True)

    with d3:
        st.markdown("##### Education")
        edu_order = ["none", "primary", "secondary", "university"]
        edu_labels = {"none": "Aucun", "primary": "Primaire", "secondary": "Secondaire", "university": "Universitaire"}
        edu_df = df_ok["education"].value_counts().reindex(edu_order).reset_index()
        edu_df.columns = ["Niveau", "Effectif"]
        edu_df["Niveau"] = edu_df["Niveau"].map(edu_labels).fillna("?")
        edu_df["%"] = (edu_df["Effectif"] / n * 100).round(1)
        st.dataframe(edu_df, hide_index=True, use_container_width=True)

    with d4:
        st.markdown("##### Mode d'administration")
        mode_df = df_ok["mode"].value_counts().reset_index()
        mode_df.columns = ["Mode", "Effectif"]
        mode_df["Mode"] = mode_df["Mode"].map({"assiste": "Assisté", "auto": "Auto-administré"}).fillna("?")
        mode_df["%"] = (mode_df["Effectif"] / n * 100).round(1)
        st.dataframe(mode_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # Per-commune demographic breakdown
    st.markdown("##### Profil par commune")
    commune_demo = df_ok.groupby("commune").agg(
        Effectif=("_id", "count"),
        femmes=("genre", lambda x: (x == "F").sum()),
        intermediaires=("role", lambda x: (x == "intermediary").sum()),
        jeunes=("age", lambda x: (x == "18-24").sum()),
        sans_instr=("education", lambda x: (x == "none").sum()),
    ).reset_index()
    commune_demo.columns = ["Commune", "Effectif", "Femmes", "Interméd.", "18-24", "Sans instr."]
    for col in ["Femmes", "Interméd.", "18-24", "Sans instr."]:
        commune_demo[f"% {col}"] = (commune_demo[col] / commune_demo["Effectif"] * 100).round(0).astype(int)

    display_demo = commune_demo[["Commune", "Effectif", "Femmes", "% Femmes", "Interméd.", "% Interméd.", "18-24", "% 18-24", "Sans instr.", "% Sans instr."]].copy()
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
        wrap_table(disp[["Commune", "Arrondissement", "Strate", "Cible", "Collecté", "Restant", "Progression", "Statut"]]
        .to_html(escape=False, index=False)),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    c_comm, c_strate = st.columns(2)

    with c_comm:
        st.markdown("##### Par commune")
        ca = qt.groupby("Commune").agg(Cible=("Cible", "sum"), Collecté=("Collecté", "sum"), Restant=("Restant", "sum")).reset_index()
        ca["Taux"] = (ca["Collecté"] / ca["Cible"] * 100).round(0).astype(int)
        ca["Progression"] = ca["Taux"].apply(progress_html)
        ca = ca.sort_values("Taux", ascending=False)
        st.markdown(wrap_table(ca[["Commune", "Cible", "Collecté", "Restant", "Progression"]].to_html(escape=False, index=False)), unsafe_allow_html=True)

    with c_strate:
        st.markdown("##### Par strate")
        sa = qt.groupby("Strate").agg(Cible=("Cible", "sum"), Collecté=("Collecté", "sum"), Restant=("Restant", "sum")).reset_index()
        sa["Taux"] = (sa["Collecté"] / sa["Cible"] * 100).round(0).astype(int)
        sa["Progression"] = sa["Taux"].apply(progress_html)
        st.markdown(wrap_table(sa[["Strate", "Cible", "Collecté", "Restant", "Progression"]].to_html(escape=False, index=False)), unsafe_allow_html=True)


# ── Tab 2 : Qualité ────────────────────────────────────────────────────

with tab_qualite:
    col_flags, col_enq = st.columns([1, 1], gap="large")

    with col_flags:
        st.subheader("Nettoyage")

        f_court = int(df["flag_court"].sum())
        f_long = int(df["flag_long"].sum())
        f_a1 = int(df["flag_a1"].sum())
        f_consent = int(df["flag_consent"].sum())
        f_doublon = int(df["flag_doublon"].sum())

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
                "Consentement absent",
                "Doublon consécutif",
            ],
            "n": [f_court, f_long, f_a1, f_consent, f_doublon],
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
    st.caption(f"Cible : {CIBLE_TOTALE} exploitables")


# ── Tab 4 : Doublons ──────────────────────────────────────────────────

with tab_doublons:
    df_dups = df[df["flag_doublon"]]
    n_dups = len(df_dups)

    st.subheader(f"Doublons détectés : {n_dups}")

    st.markdown(
        '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
        'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
        '<strong>Méthode de détection</strong><br>'
        'Deux soumissions sont considérées comme doublons quand elles proviennent du '
        '<strong>même enquêteur</strong>, du <strong>même arrondissement</strong>, '
        'sont <strong>consécutives</strong> dans le temps, et ont des '
        '<strong>valeurs identiques</strong> sur au moins 8 colonnes substantives remplies. '
        'Seule la deuxième occurrence est exclue.'
        '</div>',
        unsafe_allow_html=True,
    )

    if n_dups == 0:
        st.success("Aucun doublon détecté.")
    else:
        pair_fields = ["_id", "date", "commune", "arrondissement", "enqueteur",
                       "role", "n_answered", "duration_min"]
        for idx, dup_row in df_dups.iterrows():
            orig_id = dup_row.get("doublon_de")
            orig_rows = df[df["_id"] == orig_id]
            orig_row = orig_rows.iloc[0] if len(orig_rows) else None

            st.markdown(f"##### Paire — {dup_row['enqueteur']} / {dup_row['arrondissement']}")

            rows = []
            if orig_row is not None:
                rows.append({"Statut": "Original (conservé)", "ID": orig_row["_id"],
                             "Date": orig_row["date"], "Commune": orig_row["commune"],
                             "Arrondissement": orig_row["arrondissement"],
                             "Enquêteur": orig_row["enqueteur"], "Rôle": orig_row["role"],
                             "Questions": orig_row["n_answered"],
                             "Durée (min)": round(orig_row["duration_min"], 1)})
            rows.append({"Statut": "Doublon (exclu)", "ID": dup_row["_id"],
                         "Date": dup_row["date"], "Commune": dup_row["commune"],
                         "Arrondissement": dup_row["arrondissement"],
                         "Enquêteur": dup_row["enqueteur"], "Rôle": dup_row["role"],
                         "Questions": dup_row["n_answered"],
                         "Durée (min)": round(dup_row["duration_min"], 1)})

            pair_df = pd.DataFrame(rows)
            st.dataframe(pair_df, hide_index=True, use_container_width=True)

            if orig_row is not None:
                common_cols = [c for c in SURVEY_COLS
                               if str(df.loc[idx, c]) not in ("", "nan", "None", "NaN")
                               and str(orig_rows.iloc[0].get(c, "")) not in ("", "nan", "None", "NaN")]
                st.caption(f"{len(common_cols)} colonnes identiques sur {len(SURVEY_COLS)}")

            st.markdown("---")


# ── Tab 5 : Consentement ─────────────────────────────────────────────

with tab_consent:
    df_no_consent = df[df["flag_consent"]]
    n_nc = len(df_no_consent)

    st.subheader(f"Consentement absent : {n_nc}")

    st.markdown(
        '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
        'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
        '<strong>Critère</strong><br>'
        'Toute soumission dont le champ <code>consentement</code> n\'est pas '
        '<code>yes</code> est exclue. Le skip logic du formulaire bloque la suite '
        'du questionnaire, ces réponses sont donc vides.'
        '</div>',
        unsafe_allow_html=True,
    )

    if n_nc == 0:
        st.success("Toutes les soumissions ont le consentement.")
    else:
        nc_cols = df_no_consent[["_id", "date", "commune", "arrondissement", "enqueteur",
                                  "n_answered", "duration_min"]].copy()
        nc_cols["duration_min"] = nc_cols["duration_min"].round(1)
        # Retrieve raw consent value
        nc_cols["consentement"] = df_no_consent.get("consentement", pd.Series("", index=df_no_consent.index)).fillna("(vide)")
        nc_cols.columns = ["ID", "Date", "Commune", "Arrondissement", "Enquêteur",
                           "Questions", "Durée (min)", "Valeur consentement"]
        st.dataframe(nc_cols.sort_values("Date"), hide_index=True, use_container_width=True)

        st.markdown("##### Par enquêteur")
        nc_enq = df_no_consent.groupby("enqueteur").size().reset_index(name="Refus")
        nc_enq.columns = ["Enquêteur", "Refus"]
        st.dataframe(nc_enq.sort_values("Refus", ascending=False), hide_index=True, use_container_width=True)


# ── Tab 6 : Détail exclusions ──────────────────────────────────────────

with tab_detail:
    st.subheader(f"{len(df_flag)} soumissions exclues")
    ff = st.selectbox("Filtrer", ["Tous", "Trop court", "Trop long", "A1 manquant", "Consentement", "Doublon"], key="ff")
    show = df_flag.copy()
    if ff == "Trop court":
        show = show[show["flag_court"]]
    elif ff == "Trop long":
        show = show[show["flag_long"]]
    elif ff == "A1 manquant":
        show = show[show["flag_a1"]]
    elif ff == "Consentement":
        show = show[show["flag_consent"]]
    elif ff == "Doublon":
        show = show[show["flag_doublon"]]

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
