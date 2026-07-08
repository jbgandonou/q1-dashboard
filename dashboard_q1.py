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
from scipy.stats import chi2_contingency, fisher_exact, mannwhitneyu, kruskal, spearmanr

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

n_cit = (df_ok["section_a/A1"] == "citizen").sum()
n_int = (df_ok["section_a/A1"] == "intermediary").sum()

st.markdown(
    '<div style="margin-bottom:4px">'
    '<span style="font-size:26px;font-weight:800;color:#0f172a;letter-spacing:-.5px">Intermédiation e-gouvernement</span>'
    f'<div style="font-size:13px;color:#64748b;margin-top:4px">Enquête terrain · Ouémé, Bénin · '
    f'{len(df_ok)} répondants exploitables · {n_cit} citoyens · {n_int} intermédiaires</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── Tabs ────────────────────────────────────────────────────────────────

tab_lemmes, tab_bdd = st.tabs([
    "Lemmes",
    "Base de données",
])


# ── Tab Lemmes ────────────────────────────────────────────────────────

def _contingency_html(ct: pd.DataFrame, title: str) -> None:
    """Affiche un tableau de contingence avec totaux."""
    ct_display = ct.copy()
    ct_display["Total"] = ct_display.sum(axis=1)
    ct_display.loc["Total"] = ct_display.sum(axis=0)
    st.markdown(f"**{title}**")
    st.dataframe(ct_display, use_container_width=True)


def _chi2_result(ct: pd.DataFrame) -> str:
    """Calcule chi2 et retourne un résumé texte."""
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return "Tableau insuffisant pour le test"
    chi2, p, dof, _ = chi2_contingency(ct)
    sig = "significatif" if p < 0.05 else "non significatif"
    return f"Chi2 = {chi2:.2f}, ddl = {dof}, p = {p:.4f} ({sig})"


def _fisher_result(ct: pd.DataFrame) -> str:
    """Test exact de Fisher pour tableau 2x2."""
    if ct.shape != (2, 2):
        return "Fisher requiert un tableau 2x2"
    odds, p = fisher_exact(ct)
    sig = "significatif" if p < 0.05 else "non significatif"
    return f"OR = {odds:.2f}, p = {p:.4f} ({sig})"


def _stat_box(text: str, significant: bool) -> None:
    if significant:
        bg, border, color = "#fef2f2", "#dc2626", "#991b1b"
    else:
        bg, border, color = "#f0fdf4", "#22c55e", "#166534"
    st.markdown(
        f'<div style="background:{bg};border-left:3px solid {border};border-radius:8px;'
        f'padding:12px 16px;margin:8px 0;font-size:13px;color:{color};font-weight:600">'
        f'{text}</div>',
        unsafe_allow_html=True,
    )


def _method_box(text: str) -> None:
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
        f'padding:14px 18px;margin:12px 0;font-size:12px;color:#475569;line-height:1.6">'
        f'{text}</div>',
        unsafe_allow_html=True,
    )


def _bias_box(text: str) -> None:
    st.markdown(
        f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;'
        f'padding:14px 18px;margin:12px 0;font-size:12px;color:#92400e;line-height:1.6">'
        f'<strong>Biais et limites</strong><br>{text}</div>',
        unsafe_allow_html=True,
    )


with tab_lemmes:
    lemme_choice = st.selectbox("Sélectionner un lemme", [
        "L1 — Observabilité du terminal (C1∧C3 → I contrôle T)",
        "L2 — Indistinguabilité du consentement (P1)",
        "L3 — Accessibilité du secret (P2, catégories A-H sauf F)",
        "L4 — Résistance cryptographique (P2 satisfaite, FIDO2)",
        "L5 — Impossibilité de la livraison exclusive (P3)",
    ], key="lemme_sel")

    # Populations réutilisées
    _cit = df_ok[df_ok["section_a/A1"] == "citizen"]
    _int = df_ok[df_ok["section_a/A1"] == "intermediary"]
    _intermedies = _cit[_cit["section_b/B2"].isin(["intermediary", "relative"])]

    # Rappel des items du questionnaire utilisés dans les lemmes
    ITEMS_REF = {
        "A5": ("Quel type de téléphone possédez-vous ?", "Smartphone / Téléphone basique / Aucun"),
        "A7": ("Utilisez-vous internet ?", "Oui, facilement / Oui, avec difficulté / Non"),
        "B2": ("Qui a effectué la démarche sur le terminal ?", "Moi-même / Un intermédiaire / Un proche"),
        "B3": ("Avez-vous communiqué votre mot de passe à cette personne ?", "Oui / Non / Pas de mot de passe"),
        "B3_int": ("Le citoyen vous a-t-il communiqué son mot de passe ?", "Oui / Non / Pas de mot de passe"),
        "B4": ("Qui a reçu le document final ?", "Moi directement / Remis par l'intermédiaire / Gardé par l'intermédiaire / Ne sait pas"),
        "B6": ("Étiez-vous physiquement présent pendant la démarche ?", "Oui, tout le temps / Oui, partiellement / Non"),
        "B7": ("Pourquoi avez-vous confié cette démarche à quelqu'un d'autre ?", "Commodité / Pas de terminal / Manque de compétence / Autre"),
        "B9": ("L'intermédiaire a-t-il accédé à plusieurs services dans la même session ?", "Un seul service / Plusieurs services / Ne sait pas"),
        "B9_int": ("Avez-vous accédé à plusieurs services pour ce citoyen ?", "Un seul service / Plusieurs services / Ne sait pas"),
        "C4q": ("Les documents devraient être remis directement à l'usager (1-5)", "1 = pas du tout d'accord → 5 = tout à fait d'accord"),
        "C5q": ("Avez-vous entendu parler d'un cas où les informations d'une personne ont été utilisées sans son accord ?", "Oui / Non"),
        "C6q": ("Si oui, quel type d'incident ? (multi-réponses)", "Copie de documents / Réutilisation MDP / Démarche non autorisée / Autre"),
    }

    def _show_items(item_keys: list) -> None:
        rows = []
        for k in item_keys:
            if k in ITEMS_REF:
                q, r = ITEMS_REF[k]
                rows.append({"Item": k, "Question posée": q, "Réponses proposées": r})
        if rows:
            with st.expander("Rappel des questions du questionnaire utilisées", expanded=False):
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── LEMME 1 ──────────────────────────────────────────────────────
    if "L1" in lemme_choice:
        st.markdown("### Lemme 1 — Observabilité du terminal")
        st.markdown(
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
            'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
            '<strong>Énoncé :</strong> Sous C1∧C3, l\'intermédiaire I observe l\'intégralité '
            'des interactions sur le terminal de session.<br>'
            '<strong>Ce qu\'on cherche :</strong> montrer que C1 (absence de terminal / compétence) '
            'et C3 (intermédiation) existent massivement et sont corrélés.<br>'
            '<strong>Statut épistémologique :</strong> le lemme est un résultat déductif (si C1∧C3 alors observabilité). '
            'L\'enquête ne le prouve pas : elle vérifie que ses prémisses (C1 et C3) existent sur le terrain.'
            '</div>', unsafe_allow_html=True,
        )

        _show_items(["A5", "A7", "B2", "B7"])

        _method_box(
            '<strong>Méthode</strong><br>'
            'Deux tableaux de contingence croisent la variable dépendante B2 (qui a opéré le terminal : '
            'soi-même / intermédiaire / proche) avec deux opérationnalisations de C1 : '
            'A7 (littératie numérique, 3 niveaux) et A5 (type de téléphone, 3 niveaux).<br><br>'
            '<strong>Test appliqué :</strong> chi-deux de Pearson. Approprié car les deux variables sont '
            'catégorielles nominales avec effectifs attendus suffisants (> 5 par cellule dans la majorité des cas). '
            'Le chi-deux mesure l\'association, pas la causalité.<br><br>'
            '<strong>Population :</strong> citoyens uniquement (n ci-dessous). Les intermédiaires sont exclus '
            'car B2 n\'a de sens que pour quelqu\'un qui effectue une démarche en tant que bénéficiaire.<br><br>'
            '<strong>Hypothèse H0 :</strong> A7 (resp. A5) et B2 sont indépendants. '
            'Un p < 0.05 rejette H0 : la littératie (resp. le type de terminal) est associée au mode d\'opération.'
        )

        l1_a, l1_b = st.columns(2)

        with l1_a:
            st.markdown("##### A7 (littératie) × B2 (qui opère)")
            ct1 = pd.crosstab(
                _cit["section_a/A7"].map({"yes_easy": "Facile", "yes_hard": "Difficile", "no": "Non"}).fillna("?"),
                _cit["section_b/B2"].map({"self": "Soi-même", "intermediary": "Intermédiaire", "relative": "Proche"}).fillna("?"),
            )
            _contingency_html(ct1, "Littératie numérique × Opérateur du terminal")
            res1 = _chi2_result(ct1)
            _stat_box(res1, "significatif" in res1 and "non" not in res1)

        with l1_b:
            st.markdown("##### A5 (téléphone) × B2 (qui opère)")
            ct2 = pd.crosstab(
                _cit["section_a/A5"].map({"smartphone": "Smartphone", "basic": "Basique", "none": "Aucun"}).fillna("?"),
                _cit["section_b/B2"].map({"self": "Soi-même", "intermediary": "Intermédiaire", "relative": "Proche"}).fillna("?"),
            )
            _contingency_html(ct2, "Type de téléphone × Opérateur du terminal")
            res2 = _chi2_result(ct2)
            _stat_box(res2, "significatif" in res2 and "non" not in res2)

        st.markdown("---")
        st.markdown("##### Comparaison des deux facettes de C1")
        st.markdown(
            "La comparaison des deux chi-deux indique laquelle des deux facettes de C1 "
            "(possession matérielle vs compétence d'usage) est la plus associée au recours à l'intermédiation. "
            "Un chi-deux plus élevé signifie une association plus forte, pas une causalité plus forte."
        )

        # Motif de recours B7
        st.markdown("##### B7 — Motif du recours (citoyens intermédiés)")
        b7_map = {"convenience": "Commodité", "no_device": "Pas de terminal", "no_skill": "Manque de compétence", "other": "Autre"}
        if len(_intermedies):
            b7_df = _intermedies["section_b/B7"].map(b7_map).fillna("?").value_counts().reset_index()
            b7_df.columns = ["Motif", "Effectif"]
            b7_df["%"] = (b7_df["Effectif"] / b7_df["Effectif"].sum() * 100).round(1)
            st.dataframe(b7_df, hide_index=True, use_container_width=True)

        _bias_box(
            '<strong>Échantillonnage par convenance stratifiée</strong> : les résultats ne sont pas '
            'généralisables au-delà du département de l\'Ouémé. La représentativité nationale '
            'nécessiterait les départements du nord (Borgou, Atacora, Alibori).<br>'
            '<strong>Biais de désirabilité sociale</strong> : B7 (motif du recours) est auto-déclaré. '
            'Les répondants peuvent surestimer la « commodité » et sous-déclarer le manque de compétence '
            'par fierté. Le taux réel de contrainte pourrait être supérieur au taux déclaré.<br>'
            '<strong>Confondeur potentiel</strong> : A5 et A7 sont corrélés (ceux sans smartphone ont souvent '
            'une faible littératie). Les chi-deux mesurent des associations marginales, pas des effets nets. '
            'Une régression logistique multivariée serait nécessaire pour isoler les effets.'
        )

    # ── LEMME 2 ──────────────────────────────────────────────────────
    elif "L2" in lemme_choice:
        st.markdown("### Lemme 2 — Indistinguabilité du consentement (P1)")
        st.markdown(
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
            'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
            '<strong>Énoncé :</strong> Sous C1∧C3, le serveur S ne peut distinguer le consentement '
            'actif de C d\'une action provoquée par I (Adv(S) = 0).<br>'
            '<strong>Ce qu\'on cherche :</strong> montrer que les credentials sont délégués d\'emblée, '
            'rendant la question du consentement caduque.<br>'
            '<strong>Statut épistémologique :</strong> le lemme est mathématique (indistinguabilité des transcripts). '
            'L\'enquête montre que le scénario réel est pire que le lemme : les credentials sont '
            'partagés volontairement, la question de la simulation ne se pose même pas.'
            '</div>', unsafe_allow_html=True,
        )

        _show_items(["B3", "B3_int", "B6", "A7"])

        _method_box(
            '<strong>Méthode — Croisement B3 × B6</strong><br>'
            'B3 (« avez-vous partagé votre mot de passe ? ») est croisé avec B6 (« étiez-vous '
            'physiquement présent ? ») par un chi-deux de Pearson. Les deux sont catégorielles nominales.<br>'
            '<strong>Population :</strong> citoyens intermédiés uniquement (B2 = intermédiaire ou proche). '
            'Les citoyens autonomes (B2 = soi-même) et les intermédiaires sont exclus car B3 ne s\'applique '
            'qu\'à ceux qui ont délégué.<br>'
            '<strong>Hypothèse testée :</strong> si la présence physique protège le consentement, le taux '
            'de partage devrait être significativement plus bas quand le citoyen est présent (B6 = oui). '
            'H0 : B3 et B6 sont indépendants.<br><br>'
            '<strong>Méthode — Convergence citoyens / intermédiaires</strong><br>'
            'Comparaison descriptive (pas de test) des taux de partage déclarés par les citoyens (B3) '
            'et par les intermédiaires (B3_int). La convergence des deux taux indépendants renforce la '
            'crédibilité de la mesure par triangulation des sources.<br><br>'
            '<strong>Méthode — B3 × A7</strong><br>'
            'Chi-deux entre littératie numérique et partage de MDP. Teste si la compétence réduit le partage.'
        )

        l2_a, l2_b = st.columns(2)

        with l2_a:
            st.markdown("##### B3 (partage MDP) × B6 (présence physique)")
            st.caption("La présence du citoyen protège-t-elle le consentement ?")
            if len(_intermedies):
                b3_map = {"yes": "Partage MDP", "no": "Ne partage pas", "no_password": "Pas de MDP"}
                b6_map = {"yes_all": "Présent tout le temps", "yes_partial": "Présent partiellement", "no": "Absent"}
                ct3 = pd.crosstab(
                    _intermedies["section_b/B6"].map(b6_map).fillna("?"),
                    _intermedies["section_b/B3"].map(b3_map).fillna("?"),
                )
                _contingency_html(ct3, "Présence physique × Partage de mot de passe")
                res3 = _chi2_result(ct3)
                _stat_box(res3, "significatif" in res3 and "non" not in res3)

                st.markdown("**Taux de partage MDP par niveau de présence**")
                for pres, label in b6_map.items():
                    sub = _intermedies[_intermedies["section_b/B6"] == pres]
                    if len(sub):
                        pct = (sub["section_b/B3"] == "yes").sum() / len(sub) * 100
                        st.markdown(f"- {label} : **{pct:.0f}%** (n={len(sub)})")

        with l2_b:
            st.markdown("##### Convergence citoyens / intermédiaires")
            st.caption("Les deux parties déclarent-elles les mêmes taux ?")
            cit_pwd = (_intermedies["section_b/B3"] == "yes").sum()
            cit_total = len(_intermedies[_intermedies["section_b/B3"].isin(["yes", "no"])])
            int_pwd = (_int["section_b/B3_int"] == "yes").sum()
            int_total = len(_int[_int["section_b/B3_int"].isin(["yes", "no"])])

            conv_df = pd.DataFrame({
                "Source": ["Citoyens intermédiés", "Intermédiaires"],
                "Partage MDP": [cit_pwd, int_pwd],
                "Total (avec MDP)": [cit_total, int_total],
                "%": [cit_pwd / cit_total * 100 if cit_total else 0, int_pwd / int_total * 100 if int_total else 0],
            })
            conv_df["%"] = conv_df["%"].round(1)
            st.dataframe(conv_df, hide_index=True, use_container_width=True)

            st.markdown("##### B3 (partage MDP) × A7 (littératie)")
            st.caption("Les plus compétents partagent-ils moins ?")
            if len(_intermedies):
                a7_map = {"yes_easy": "Facile", "yes_hard": "Difficile", "no": "Non"}
                ct4 = pd.crosstab(
                    _intermedies["section_a/A7"].map(a7_map).fillna("?"),
                    _intermedies["section_b/B3"].map(b3_map).fillna("?"),
                )
                _contingency_html(ct4, "Littératie × Partage MDP")
                res4 = _chi2_result(ct4)
                _stat_box(res4, "significatif" in res4 and "non" not in res4)

        _bias_box(
            '<strong>Désirabilité sociale</strong> : le partage de MDP pourrait être sous-déclaré si '
            'les répondants le perçoivent comme risqué. Cependant, la convergence des taux citoyens/intermédiaires '
            'et le taux élevé (> 60%) suggèrent une normalisation de la pratique qui atténue ce biais.<br>'
            '<strong>Biais de mémoire</strong> : B3 et B6 portent sur « la dernière démarche ». Le rappel '
            'est fiable pour des événements récents mais se dégrade au-delà de quelques semaines. '
            'Aucun contrôle de la date de la dernière démarche n\'est disponible.<br>'
            '<strong>Catégorie « Pas de MDP »</strong> : les répondants déclarant « pas de mot de passe » '
            '(services sans compte) sont inclus dans le tableau mais ne sont ni dans le numérateur ni '
            'dans le dénominateur du taux de partage. Cette catégorie n\'invalide pas le test mais réduit '
            'la puissance en ajoutant une modalité non pertinente pour l\'hypothèse.'
        )

    # ── LEMME 3 ──────────────────────────────────────────────────────
    elif "L3" in lemme_choice:
        st.markdown("### Lemme 3 — Accessibilité du secret (P2)")
        st.markdown(
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
            'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
            '<strong>Énoncé :</strong> Sous C1∧C3, I accède au secret et peut produire des '
            'preuves valides pour des sessions futures sans l\'intervention de C.<br>'
            '<strong>Ce qu\'on cherche :</strong> documenter la chaîne partage → réutilisation → incidents.<br>'
            '<strong>Statut épistémologique :</strong> le lemme prédit une capacité technique (I peut forger). '
            'L\'enquête documente le cas 2 (secret communiqué) et les conséquences observées (incidents). '
            'Le cas 1 (secret stocké sur le terminal de I) est une propriété des plateformes, non mesurable par questionnaire.'
            '</div>', unsafe_allow_html=True,
        )

        _show_items(["B3", "B9", "B9_int", "C5q", "C6q"])

        _method_box(
            '<strong>Méthode — B3 × C5q</strong><br>'
            'Chi-deux entre le partage de MDP (B3, 3 modalités) et la connaissance d\'incidents (C5q, oui/non). '
            'Teste si le partage est associé à un taux d\'incidents plus élevé.<br>'
            '<strong>Population :</strong> citoyens intermédiés. C5q est posé à tous les répondants, '
            'mais le croisement n\'est pertinent que pour ceux qui ont délégué.<br>'
            '<strong>Hypothèse H0 :</strong> B3 et C5q sont indépendants.<br><br>'
            '<strong>Méthode — B9 × B3</strong><br>'
            'Chi-deux entre le partage de MDP et l\'accès multi-services (B9). '
            'Teste l\'amplification once-only : ceux qui partagent le MDP sont-ils plus exposés à un accès multi-services ?<br><br>'
            '<strong>Méthode — C6q (types d\'incidents)</strong><br>'
            'Statistique descriptive. C6q est un champ multi-réponses (les valeurs sont séparées par des espaces). '
            'Chaque type est compté indépendamment. Le mapping vers les propriétés formelles '
            '(password → P1, copy → P3, unauthorized → P2) est notre interprétation, pas une donnée brute.<br><br>'
            '<strong>Méthode — Asymétrie citoyens/intermédiaires sur B9</strong><br>'
            'Comparaison descriptive des taux de multi-services déclarés par les citoyens (B9) '
            'et par les intermédiaires (B9_int). L\'écart suggère une sous-estimation par les citoyens.'
        )

        l3_a, l3_b = st.columns(2)

        with l3_a:
            st.markdown("##### B3 (partage MDP) × C5q (connaissance d'incidents)")
            st.caption("Ceux qui partagent signalent-ils plus d'incidents ?")
            if len(_intermedies):
                b3_bin = _intermedies["section_b/B3"].map({"yes": "Partage MDP", "no": "Ne partage pas", "no_password": "Pas de MDP"}).fillna("?")
                c5_bin = _intermedies["section_c/C5q"].map({"yes": "Incidents connus", "no": "Aucun incident"}).fillna("?")
                ct5 = pd.crosstab(b3_bin, c5_bin)
                _contingency_html(ct5, "Partage MDP × Connaissance d'incidents")
                res5 = _chi2_result(ct5)
                _stat_box(res5, "significatif" in res5 and "non" not in res5)

            st.markdown("##### B9 (multi-services) × B3 (partage MDP)")
            st.caption("Amplification once-only : le secret ouvre plusieurs services ?")
            if len(_intermedies):
                b9_map = {"one": "Un seul", "multiple": "Plusieurs", "unknown": "Ne sait pas"}
                ct6 = pd.crosstab(
                    _intermedies["section_b/B3"].map({"yes": "Partage MDP", "no": "Ne partage pas", "no_password": "Pas de MDP"}).fillna("?"),
                    _intermedies["section_b/B9"].map(b9_map).fillna("?"),
                )
                _contingency_html(ct6, "Partage MDP × Accès multi-services")
                res6 = _chi2_result(ct6)
                _stat_box(res6, "significatif" in res6 and "non" not in res6)

        with l3_b:
            st.markdown("##### Types d'incidents rapportés (C6q)")
            st.caption("Correspondance avec les violations prédites par le lemme")
            c6_pop = df_ok[df_ok["section_c/C6q"].notna() & (df_ok["section_c/C6q"] != "")]
            if len(c6_pop):
                c6_labels = {
                    "password": "Réutilisation MDP (→ P1)",
                    "copy": "Copie de documents (→ P3)",
                    "unauthorized": "Démarche non autorisée (→ P2)",
                    "other": "Autre",
                }
                all_types = []
                for val in c6_pop["section_c/C6q"]:
                    for t in str(val).split():
                        all_types.append(t)
                c6_s = pd.Series(all_types).map(c6_labels).fillna("Autre")
                c6_df = c6_s.value_counts().reset_index()
                c6_df.columns = ["Type d'incident", "Effectif"]
                c6_df["%"] = (c6_df["Effectif"] / c6_df["Effectif"].sum() * 100).round(1)
                st.dataframe(c6_df, hide_index=True, use_container_width=True)

            st.markdown("##### Amplification côté intermédiaires")
            st.caption("B9_int : accès multi-services déclaré par les intermédiaires")
            if len(_int):
                b9i = _int["section_b/B9_int"].map(b9_map).fillna("?").value_counts().reset_index()
                b9i.columns = ["Accès multi-services", "Effectif"]
                b9i["%"] = (b9i["Effectif"] / b9i["Effectif"].sum() * 100).round(1)
                st.dataframe(b9i, hide_index=True, use_container_width=True)

                pct_cit = (_intermedies["section_b/B9"] == "multiple").sum() / len(_intermedies) * 100 if len(_intermedies) else 0
                pct_int = (_int["section_b/B9_int"] == "multiple").sum() / len(_int) * 100 if len(_int) else 0
                if pct_int > pct_cit:
                    _stat_box(
                        f"Asymétrie : {pct_int:.0f}% côté intermédiaires vs {pct_cit:.0f}% côté citoyens. "
                        f"Les citoyens sous-estiment l'ampleur de l'accès effectué en leur nom.",
                        True,
                    )

        _bias_box(
            '<strong>Causalité non établie</strong> : le croisement B3 × C5q montre une association, '
            'pas une causalité. C5q mesure « avez-vous entendu parler d\'un incident » (ouï-dire), '
            'pas « avez-vous subi un incident suite au partage ». La chaîne causale '
            'partage → réutilisation → incident n\'est pas prouvée par ces données.<br>'
            '<strong>Biais de rappel sur C5q/C6q</strong> : les incidents rapportés sont déclaratifs '
            'et souvent de seconde main. Aucune vérification factuelle. Les taux d\'incidents '
            'sont probablement sous-estimés (victimes non conscientes) ou sur-estimés (rumeurs).<br>'
            '<strong>Multi-réponses C6q</strong> : un même répondant peut cocher plusieurs types. '
            'Les effectifs ne sont pas des individus mais des mentions. Le total des mentions '
            'dépasse le nombre de répondants ayant répondu « oui » à C5q.<br>'
            '<strong>Rejeu effectif non mesuré</strong> : le lemme prédit que I peut réutiliser les '
            'credentials post-session. L\'enquête ne mesure pas cette réutilisation directement. '
            'Seuls les incidents déclarés (C6q = unauthorized, n faible) s\'en approchent.'
        )

    # ── LEMME 4 ──────────────────────────────────────────────────────
    elif "L4" in lemme_choice:
        st.markdown("### Lemme 4 — Résistance cryptographique (P2 satisfaite, FIDO2)")
        st.markdown(
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
            'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
            '<strong>Énoncé :</strong> Le confinement matériel de la clé (FIDO2) empêche I de '
            'forger des preuves, même sous C1∧C3. P2 est satisfaite.<br>'
            '<strong>Ce qu\'on cherche :</strong> ce lemme est purement cryptographique. L\'enquête '
            'ne peut ni le confirmer ni l\'infirmer. Elle documente la faisabilité du déploiement.<br>'
            '<strong>Statut épistémologique :</strong> seul lemme sans ancrage empirique direct, '
            'et seul qui n\'en a pas besoin. Il pose une condition suffisante (confinement matériel → P2), '
            'pas une assertion sur le terrain. Les données ci-dessous évaluent la faisabilité, pas la validité.'
            '</div>', unsafe_allow_html=True,
        )

        _show_items(["A5", "A7"])

        _method_box(
            '<strong>Méthode</strong><br>'
            'Statistiques descriptives uniquement (fréquences, pourcentages). Aucun test d\'hypothèse : '
            'il n\'y a rien à tester puisque FIDO2 n\'est pas déployé dans les plateformes étudiées.<br>'
            '<strong>Population :</strong> tous les répondants exploitables (citoyens + intermédiaires). '
            'A5 (type de téléphone) et A7 (littératie) sont des proxys de la capacité à utiliser un '
            'authentificateur matériel.'
        )

        st.markdown("##### Parc de terminaux (A5) — faisabilité FIDO2")
        a5_map = {"smartphone": "Smartphone", "basic": "Téléphone basique", "none": "Aucun téléphone"}
        a5_df = df_ok["section_a/A5"].map(a5_map).fillna("?").value_counts().reset_index()
        a5_df.columns = ["Type de terminal", "Effectif"]
        a5_df["%"] = (a5_df["Effectif"] / a5_df["Effectif"].sum() * 100).round(1)
        st.dataframe(a5_df, hide_index=True, use_container_width=True)

        st.markdown("##### Littératie numérique (A7) — capacité d'usage")
        a7_map = {"yes_easy": "Utilise internet facilement", "yes_hard": "Utilise avec difficulté", "no": "N'utilise pas internet"}
        a7_df = df_ok["section_a/A7"].map(a7_map).fillna("?").value_counts().reset_index()
        a7_df.columns = ["Littératie", "Effectif"]
        a7_df["%"] = (a7_df["Effectif"] / a7_df["Effectif"].sum() * 100).round(1)
        st.dataframe(a7_df, hide_index=True, use_container_width=True)

        pct_no_smart = df_ok[df_ok["section_a/A5"].isin(["basic", "none"])].shape[0] / len(df_ok) * 100
        pct_no_skill = df_ok[df_ok["section_a/A7"].isin(["yes_hard", "no"])].shape[0] / len(df_ok) * 100
        _stat_box(
            f"{pct_no_smart:.0f}% n'ont pas de smartphone, {pct_no_skill:.0f}% ne maîtrisent pas internet. "
            f"FIDO2 satisfait P2 mais son déploiement suppose un terminal et une compétence "
            f"que {max(pct_no_smart, pct_no_skill):.0f}% des répondants n'ont pas.",
            False,
        )

        _bias_box(
            '<strong>Proxy indirect</strong> : posséder un smartphone ≠ pouvoir utiliser FIDO2. '
            'Le WebAuthn nécessite un navigateur compatible, un OS à jour, et un geste d\'activation '
            '(empreinte, PIN). Ces prérequis ne sont pas mesurés par A5.<br>'
            '<strong>Aucune donnée sur les authentificateurs physiques</strong> : l\'enquête ne demande '
            'pas si le répondant possède une clé USB de sécurité (YubiKey, Titan). Ce scénario est '
            'jugé irréaliste dans le contexte étudié mais l\'absence de donnée reste une limite.<br>'
            '<strong>Extrapolation du lemme</strong> : les chiffres de faisabilité ne disent rien sur P2. '
            'Le lemme tient par construction cryptographique (confinement matériel). Ces données '
            'informent la discussion (section X), pas la preuve.'
        )

    # ── LEMME 5 ──────────────────────────────────────────────────────
    elif "L5" in lemme_choice:
        st.markdown("### Lemme 5 — Impossibilité de la livraison exclusive (P3)")
        st.markdown(
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
            'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1e40af">'
            '<strong>Énoncé :</strong> Sous C1∧C3, aucun mécanisme numérique ne peut garantir '
            'Receive(D(s)) = {C}. Le document passe par I.<br>'
            '<strong>Ce qu\'on cherche :</strong> documenter que la livraison via I est massive '
            'et que la présence physique ne la corrige pas.<br>'
            '<strong>Statut épistémologique :</strong> le lemme est déductif (3 cas exhaustifs). '
            'L\'enquête documente que le cas 1 (livraison via T) domine massivement et que '
            'les mécanismes correctifs (présence, littératie) ne restaurent pas l\'exclusivité.'
            '</div>', unsafe_allow_html=True,
        )

        _show_items(["B4", "B6", "A7", "C4q"])

        _method_box(
            '<strong>Méthode — B4 × B6</strong><br>'
            'Chi-deux entre le destinataire du document (B4, 4 modalités : moi / remis par I / gardé / ne sait pas) '
            'et la présence physique (B6, 3 niveaux). Teste si la présence du citoyen modifie la voie de livraison.<br>'
            '<strong>Population :</strong> citoyens intermédiés (B2 ≠ soi-même).<br>'
            '<strong>Hypothèse H0 :</strong> B4 et B6 sont indépendants.<br><br>'
            '<strong>Méthode — B4 × A7</strong><br>'
            'Chi-deux entre le destinataire et la littératie numérique. Teste si les citoyens plus compétents '
            'récupèrent davantage le document directement.<br><br>'
            '<strong>Méthode — C4q citoyens vs intermédiaires</strong><br>'
            'Test de Mann-Whitney U (bilatéral). C4q est une échelle de Likert (1-5, variable ordinale), '
            'ce qui exclut le t-test (hypothèse de normalité non vérifiable). Mann-Whitney compare les rangs '
            'moyens des deux groupes indépendants.<br>'
            '<strong>H0 :</strong> les distributions de C4q sont identiques entre citoyens intermédiés et intermédiaires.<br><br>'
            '<strong>Méthode — B4 par commune</strong><br>'
            'Statistique descriptive. Le taux de livraison via I par commune permet de visualiser '
            'le gradient territorial. Aucun test : les effectifs par commune sont trop hétérogènes '
            'pour un chi-deux inter-communes fiable.'
        )

        l5_a, l5_b = st.columns(2)

        with l5_a:
            st.markdown("##### B4 (destinataire) × B6 (présence physique)")
            st.caption("La présence corrige-t-elle la livraison ?")
            if len(_intermedies):
                b4_map = {"me": "Citoyen directement", "handed": "Via intermédiaire", "kept": "Gardé par I", "unknown": "Ne sait pas"}
                b6_map = {"yes_all": "Présent tout le temps", "yes_partial": "Partiellement", "no": "Absent"}
                ct7 = pd.crosstab(
                    _intermedies["section_b/B6"].map(b6_map).fillna("?"),
                    _intermedies["section_b/B4"].map(b4_map).fillna("?"),
                )
                _contingency_html(ct7, "Présence × Destinataire du document")
                res7 = _chi2_result(ct7)
                _stat_box(res7, "significatif" in res7 and "non" not in res7)

                st.markdown("**Taux de livraison via I par niveau de présence**")
                for pres, label in b6_map.items():
                    sub = _intermedies[_intermedies["section_b/B6"] == pres]
                    if len(sub):
                        pct = sub["section_b/B4"].isin(["handed", "kept", "unknown"]).sum() / len(sub) * 100
                        st.markdown(f"- {label} : **{pct:.0f}%** via I (n={len(sub)})")

        with l5_b:
            st.markdown("##### B4 (destinataire) × A7 (littératie)")
            st.caption("Les plus compétents reçoivent-ils directement ?")
            if len(_intermedies):
                a7_map = {"yes_easy": "Facile", "yes_hard": "Difficile", "no": "Non"}
                ct8 = pd.crosstab(
                    _intermedies["section_a/A7"].map(a7_map).fillna("?"),
                    _intermedies["section_b/B4"].map(b4_map).fillna("?"),
                )
                _contingency_html(ct8, "Littératie × Destinataire du document")
                res8 = _chi2_result(ct8)
                _stat_box(res8, "significatif" in res8 and "non" not in res8)

            st.markdown("##### C4q (attente livraison exclusive) × rôle")
            st.caption("Mann-Whitney : citoyens vs intermédiaires")
            c4_cit = pd.to_numeric(_intermedies["section_c/C4q"], errors="coerce").dropna()
            c4_int = pd.to_numeric(_int["section_c/C4q"], errors="coerce").dropna()
            if len(c4_cit) > 1 and len(c4_int) > 1:
                u_stat, p_val = mannwhitneyu(c4_cit, c4_int, alternative="two-sided")
                _stat_box(
                    f"C4q citoyens intermédiés : M = {c4_cit.mean():.2f} (n={len(c4_cit)}) · "
                    f"Intermédiaires : M = {c4_int.mean():.2f} (n={len(c4_int)}) · "
                    f"U = {u_stat:.0f}, p = {p_val:.4f}",
                    p_val < 0.05,
                )

        st.markdown("---")
        st.markdown("##### B4 par commune — le gradient territorial")
        if len(_intermedies):
            commune_b4 = _intermedies.groupby("metadata_terrain/commune").apply(
                lambda g: pd.Series({
                    "n": len(g),
                    "Via I (%)": g["section_b/B4"].isin(["handed", "kept", "unknown"]).sum() / len(g) * 100 if len(g) else 0,
                })
            ).reset_index()
            commune_b4.columns = ["Commune", "n intermédiés", "Via I (%)"]
            commune_b4["Via I (%)"] = commune_b4["Via I (%)"].round(1)
            commune_b4 = commune_b4.sort_values("Via I (%)", ascending=False)
            st.dataframe(commune_b4, hide_index=True, use_container_width=True)

        _bias_box(
            '<strong>Ambiguïté B4 « remis par l\'intermédiaire »</strong> : B4 = « handed » signifie que '
            'l\'intermédiaire a remis le document au citoyen. Cela ne signifie pas que l\'intermédiaire a conservé '
            'une copie, seulement que le canal de livraison passe par I. Le lemme prédit I ∈ Receive(D), '
            'pas Receive(D) = {I}. La distinction est correcte mais subtile.<br>'
            '<strong>Biais de non-réponse B4</strong> : « ne sait pas » (2-3%) peut masquer des cas où '
            'le document n\'a jamais été remis ou a été perdu. Ces cas renforcent plutôt la violation de P3.<br>'
            '<strong>Mann-Whitney et Likert</strong> : l\'utilisation de Mann-Whitney sur des échelles '
            'à 5 points est standard en sciences sociales (Jamieson 2004 vs Norman 2010, débat non tranché). '
            'Nous traitons les Likert comme ordinales (position conservative). Les moyennes sont rapportées '
            'à titre indicatif mais le test porte sur les rangs, pas les moyennes.<br>'
            '<strong>Effectifs par commune</strong> : certaines communes ont peu de citoyens intermédiés '
            '(Aguégués, Bonou). Les pourcentages par commune sont instables pour n < 30. '
            'Le gradient territorial est illustratif, pas confirmatoire.'
        )


# ── Tab Base de données ──────────────────────────────────────────────

BDD_INTERNAL_COLS = {
    "__version__", "_attachments", "_geolocation", "_xform_id_string",
    "_submitted_by", "_uuid", "_validation_status", "_status",
    "formhub/uuid", "meta/instanceID", "meta/rootUuid",
    "start_dt", "end_dt", "seuil_min", "n_answered",
    "flag_court", "flag_long", "flag_a1", "flag_consent", "flag_doublon",
    "doublon_de",
}

BDD_LABELS = {
    "_id": "ID",
    "_submission_time": "Date soumission",
    "start": "Début",
    "end": "Fin",
    "consentement": "Consentement",
    "gps_location": "GPS",
    "metadata_terrain/commune": "Commune",
    "metadata_terrain/arrondissement": "Arrondissement",
    "metadata_terrain/zone": "Zone (urbain/rural)",
    "metadata_terrain/strate": "Strate",
    "metadata_terrain/connectivite": "Connectivité",
    "metadata_terrain/id_enqueteur": "Enquêteur",
    "metadata_terrain/mode_administration": "Mode administration",
    "section_a/A1": "A1 — Rôle (citoyen/intermédiaire)",
    "section_a/A2": "A2 — Tranche d'âge",
    "section_a/A3": "A3 — Genre",
    "section_a/A5": "A5 — Type de téléphone",
    "section_a/A6": "A6 — Niveau d'éducation",
    "section_a/A7": "A7 — Littératie numérique",
    "section_b/B1": "B1 — Démarche effectuée",
    "section_b/B2": "B2 — Qui a opéré le terminal",
    "section_b/B3": "B3 — A partagé son mot de passe",
    "section_b/B3_int": "B3 int — Reçoit le mot de passe",
    "section_b/B4": "B4 — Qui a reçu le document",
    "section_b/B4_int": "B4 int — Remet le document au citoyen",
    "section_b/B5": "B5 — Type de service",
    "section_b/B5bis": "B5bis — Autre service (texte)",
    "section_b/B6": "B6 — Présence physique du citoyen",
    "section_b/B6_int": "B6 int — Citoyen présent",
    "section_b/B7": "B7 — Motif du recours",
    "section_b/B7bis": "B7bis — Autre motif (texte)",
    "section_b/B8": "B8 — Problèmes de connexion",
    "section_b/B9": "B9 — Multi-services dans la session",
    "section_b/B9_int": "B9 int — Multi-services",
    "section_c/C1q": "C1q — Confiance envers l'intermédiaire (1-5)",
    "section_c/C1q_int": "C1q int — Confiance perçue du citoyen (1-5)",
    "section_c/C2q": "C2q — Inquiétude sécurité données (1-5)",
    "section_c/C2q_int": "C2q int — Inquiétude sécurité (1-5)",
    "section_c/C3q": "C3q — Perception de forgeabilité (1-5)",
    "section_c/C4q": "C4q — Attente livraison exclusive (1-5)",
    "section_c/C5q": "C5q — Connaissance d'incidents",
    "section_c/C6q": "C6q — Type d'incidents rapportés",
    "section_c/C6bis": "C6bis — Détail incidents (texte)",
    "duration_min": "Durée (min)",
    "flagged": "Statut",
}

BDD_VALUES = {
    "consentement": {"yes": "Oui", "no": "Non"},
    "metadata_terrain/zone": {"urbain": "Urbain", "rural": "Rural"},
    "metadata_terrain/strate": {
        "urbain_connectee": "Urbain connecté", "urbain_degradee": "Urbain dégradé",
        "rural_connectee": "Rural connecté", "rural_degradee": "Rural dégradé",
    },
    "metadata_terrain/connectivite": {"connectee": "Connectée", "degradee": "Dégradée"},
    "metadata_terrain/mode_administration": {"assiste": "Assisté", "auto": "Auto-administré"},
    "section_a/A1": {"citizen": "Citoyen", "intermediary": "Intermédiaire"},
    "section_a/A3": {"M": "Homme", "F": "Femme"},
    "section_a/A5": {"smartphone": "Smartphone", "basic": "Téléphone basique", "none": "Aucun téléphone"},
    "section_a/A6": {"none": "Sans instruction", "primary": "Primaire", "secondary": "Secondaire", "university": "Universitaire"},
    "section_a/A7": {"yes_easy": "Oui, facilement", "yes_hard": "Oui, avec difficulté", "no": "Non"},
    "section_b/B1": {"never": "Jamais", "1-2": "1 à 2 fois", "3-5": "3 à 5 fois", "5+": "Plus de 5 fois"},
    "section_b/B2": {"self": "Moi-même", "intermediary": "Un intermédiaire", "relative": "Un proche"},
    "section_b/B3": {"yes": "Oui", "no": "Non", "no_password": "Pas de mot de passe"},
    "section_b/B3_int": {"yes": "Oui", "no": "Non", "no_password": "Pas de mot de passe"},
    "section_b/B4": {"me": "Moi directement", "handed": "Remis par l'intermédiaire", "kept": "Gardé par l'intermédiaire", "unknown": "Ne sait pas"},
    "section_b/B4_int": {"me": "Directement au citoyen", "handed": "Remis au citoyen", "kept": "Conservé"},
    "section_b/B5": {"ravip": "RAVIP", "birth": "Acte de naissance", "criminal": "Casier judiciaire", "nationality": "Certificat de nationalité", "other": "Autre"},
    "section_b/B6": {"yes_all": "Oui, tout le temps", "yes_partial": "Oui, partiellement", "no": "Non"},
    "section_b/B6_int": {"yes_all": "Oui, tout le temps", "yes_partial": "Oui, partiellement", "no": "Non"},
    "section_b/B7": {"convenience": "Commodité", "no_device": "Pas de terminal", "no_skill": "Manque de compétence", "other": "Autre"},
    "section_b/B8": {"no": "Non", "yes_completed": "Oui, démarche terminée", "yes_interrupted": "Oui, démarche interrompue"},
    "section_b/B9": {"one": "Un seul service", "multiple": "Plusieurs services", "unknown": "Ne sait pas"},
    "section_b/B9_int": {"one": "Un seul service", "multiple": "Plusieurs services", "unknown": "Ne sait pas"},
    "section_c/C5q": {"yes": "Oui", "no": "Non"},
    "section_c/C6q": {"copy": "Copie de documents", "password": "Réutilisation mot de passe", "unauthorized": "Démarche non autorisée", "other": "Autre"},
}

# Colonnes calculées par clean() qui dupliquent les colonnes brutes
BDD_INTERNAL_COLS.update({
    "commune", "arrondissement", "enqueteur", "role", "genre",
    "age", "education", "mode", "date",
})

with tab_bdd:
    st.subheader(f"Base de données complète — {len(df)} soumissions, {len(df.columns)} colonnes")

    bdd_f1, bdd_f2, bdd_f3 = st.columns(3)
    with bdd_f1:
        bdd_communes = ["Toutes"] + sorted(df["commune"].unique().tolist())
        bdd_sel_commune = st.selectbox("Commune", bdd_communes, key="bdd_commune")
    with bdd_f2:
        bdd_enqueteurs = ["Tous"] + sorted(df["enqueteur"].unique().tolist())
        bdd_sel_enq = st.selectbox("Enquêteur", bdd_enqueteurs, key="bdd_enq")
    with bdd_f3:
        bdd_sel_statut = st.selectbox("Statut", ["Toutes", "Exploitables", "Exclues"], key="bdd_statut")

    bdd_view = df.copy()
    if bdd_sel_commune != "Toutes":
        bdd_view = bdd_view[bdd_view["commune"] == bdd_sel_commune]
    if bdd_sel_enq != "Tous":
        bdd_view = bdd_view[bdd_view["enqueteur"] == bdd_sel_enq]
    if bdd_sel_statut == "Exploitables":
        bdd_view = bdd_view[~bdd_view["flagged"]]
    elif bdd_sel_statut == "Exclues":
        bdd_view = bdd_view[bdd_view["flagged"]]

    all_cols = [c for c in bdd_view.columns if c not in BDD_INTERNAL_COLS]
    bdd_export = bdd_view[all_cols].copy()
    if "duration_min" in bdd_export.columns:
        bdd_export["duration_min"] = bdd_export["duration_min"].round(1)
    if "flagged" in bdd_export.columns:
        bdd_export["flagged"] = bdd_export["flagged"].map({True: "Exclue", False: "OK"})

    for col, mapping in BDD_VALUES.items():
        if col not in bdd_export.columns:
            continue
        if col == "section_c/C6q":
            bdd_export[col] = bdd_export[col].apply(
                lambda v: ", ".join(mapping.get(t, t) for t in str(v).split()) if pd.notna(v) and v != "" else v
            )
        else:
            bdd_export[col] = bdd_export[col].map(mapping).fillna(bdd_export[col])

    rename_map = {c: BDD_LABELS.get(c, c) for c in bdd_export.columns}
    bdd_display = bdd_export.rename(columns=rename_map)

    sort_col = "Date" if "Date" in bdd_display.columns else bdd_display.columns[0]
    st.dataframe(bdd_display.sort_values(sort_col, ascending=False),
                 hide_index=True, use_container_width=True, height=700)

    st.caption(f"{len(bdd_view)} lignes x {len(all_cols)} colonnes")

    csv = bdd_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Télécharger CSV ({len(bdd_view)} lignes x {len(all_cols)} colonnes)",
        data=csv,
        file_name=f"q1_oueme_{bdd_sel_statut.lower()}_{len(bdd_view)}.csv",
        mime="text/csv",
    )


# ── Footer ──────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#94a3b8;font-size:11px;padding:8px 0">'
    'Q1 Ouémé — Thèse J.-B. Gandonou · KoBoToolbox temps réel · Cache 2 min'
    '</div>',
    unsafe_allow_html=True,
)
