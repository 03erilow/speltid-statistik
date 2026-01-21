# -*- coding: utf-8 -*-
"""
IFK Speltid – Dash (Option B, uppdaterad)
Genomför 6 steg:
1) Fixar datumparsning (år 0000/1899 -> korrekt säsongsår)
2) Vänder lag-topplistan så flest minuter ligger överst
3) Tar bort Datakvalitet-fliken
4) Stöd för Herr + Dam i en och samma app (dataset-switch)
5) Stöd för flera säsonger (t.ex. 2025 + 2026) (säsong-switch)
6) Fortsätter med samma Excel-mall och publicerade CSV-länkar (Option B)

OBS:
- Du måste fylla på DATASETS med rätt URLs för DAM och (senare) 2026.
- Dina nuvarande HERR 2025-URL:er är inlagda som default.
"""

import re
import numpy as np
import pandas as pd
from datetime import datetime
from urllib.parse import parse_qs

import dash
from dash import dcc, html, Input, Output
import plotly.express as px


# ============================================================
# 1) CONFIG: DATASETS (Herr/Dam) + Säsonger
# ============================================================

SASONG_DEFAULT = 2025
DATASET_DEFAULT = "HERR"

# Lägg in DAM och 2026 när ni har publicerat dem
DATASETS = {
    "HERR": {
        "label": "A-lag herr",
        "seasons": {
            2025: {
                "Januari": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRM7VMVvrdG4m2EC0TEd5K48Uu2QdmBlLvgP7SoPlth7kerxqqG4CRGp8woku3umlb92Z2Bl7BC5F1i/pub?output=csv",
                "Februari": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQltnyugu71GDNbHKb51w7HeTb4cREy1IYZY_TgW_uxoHT0_idnkEQJEMf2VYjNF_6K2IyMAHNG_be2/pub?output=csv",
                "Mars": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTYouUx8pTcHMJyco3KED4DpYnM07I5dIXrooPU-MXIzoChovOeWIpoF4H5akFu14J2qgjihlMeHCun/pub?output=csv",
                "April": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRUPOlhwdZDEtv_2EDdw4hgkleE1usfTq32xOx_ZnFgPvN9Ah-T1CjuhCL-alFAgGnAdpNmraAIvX8D/pub?output=csv",
                "Maj": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWG2f9_RMxu_GQRkb2amJy8twaPpYNzEYOmEnim--_6EF6fkowjWQ8hu8ybPCcwohKAxr68izmawtm/pub?output=csv",
                "Juni": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRqwUDyRB9H57kzaURL0GLzZChTQXIGz78HhjR79OKaOju0I1JtF-gAc_6vSb9a4JHwnlokAJOSRZsy/pub?output=csv",
                "Juli": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAQKTXSsYvkcRwrNvNkaJyAYqjQOxlXl9Y7HryzRKcOc-btUMwPtryUcEABrcEcQrr8W36mYG6UaYU/pub?output=csv",
                "Augusti": "https://docs.google.com/spreadsheets/d/e/2PACX-1vShBzn2GqH02590h19dUNJhIeU3Egg1jrAMg7Jy1AsvKcxBaeptps2DAFa2WGku_eIh0H1lw_ptcpqY/pub?output=csv",
                "September": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTjbpYxpx3mRIGyJAYKoaRpFvsHfU4DLfeTg0xJm4zKmybL5iUEoPOtTQ_mScsWo5-T6wgtOrrIPfN3/pub?output=csv",
                "Oktober": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS81r8mkN4dKbPVcnCsSoXaW38pjbagKQOrT4LM3qeDj5CSsKzBL09-y6zjH2Bz-eBiGDmTZJnI_fZC/pub?output=csv",
                "November": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRBZb4cfCdcMHfn-TFRUbETAY0vv38dwA3z2_QpTlek0x6FwkgG5TFx-k-6uQC0ErpvhdvbWuLaxCFI/pub?output=csv",
                "December": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS6svwKCVdfK8pgXMAVFpjgmcOae8ptEW8w5OdW8oO-t746JvCrW2cSSmXpljSLhaDkgChRF6pwEO4q/pub?output=csv"
            },
            # 2026: {...}  # Lägg till när ni publicerat 2026
        },
    },
    "DAM": {
        "label": "A-lag dam",
        "seasons": {
            # 2025: {...}  # Lägg in när ni publicerat dam 2025
            # 2026: {...}
        },
    }
}

# I din mall ligger metadata-etiketter i kolumn D:
# D1=Date, D2=Opponent, D3=Team, D4=Type of match
META_LABEL_COL = 3  # 0-index => A=0, B=1, C=2, D=3

META_KEYS = {
    "date": ["date", "datum"],
    "opponent": ["opponent", "motstånd"],
    "team": ["team", "lag"],
    "type": ["type of match", "matchtyp", "competition", "tävling"],
}

# Header-raden i din mall (rad 5 i Excel) innehåller:
# A5=Birth year, B5=Position, C5=No, D5=Name
HEADER_TOKENS = ["birth year", "position", "no", "name"]

# Totalkolumn brukar heta "Totalt månad" (ska ignoreras)
TOTAL_COL_MARKERS = ["totalt", "summa"]


# ============================================================
# 2) HJÄLPFUNKTIONER: PARSING + DATUM-FIX
# ============================================================

SWEDISH_MONTH_HINTS = {
    "Januari": 1, "Februari": 2, "Mars": 3, "April": 4, "Maj": 5, "Juni": 6,
    "Juli": 7, "Augusti": 8, "September": 9, "Oktober": 10, "November": 11, "December": 12
}

def s(x) -> str:
    return "" if pd.isna(x) else str(x).strip()

def lower(x) -> str:
    return s(x).lower()

def parse_date_cell(val, sheet_name=None, default_year=2025):
    """
    Klarar:
    - riktiga datumvärden (Timestamp)
    - strängar som '2025-03-30'
    - strängar som '19-ja' (vanligt i exporter)
    - enbart dag (t.ex. '19') om sheet_name anger månad
    """
    if pd.isna(val):
        return None

    if isinstance(val, (datetime, pd.Timestamp)):
        return pd.to_datetime(val).date()

    st = s(val)

    # Standard parse
    try:
        dt = pd.to_datetime(st, errors="raise")
        return dt.date()
    except Exception:
        pass

    # "19-ja" / "19-jan" / "19-03"
    m = re.match(r"^(\d{1,2})\s*[-/.]\s*([A-Za-z]{2,3}|\d{1,2})$", st)
    if m:
        day = int(m.group(1))
        mm = m.group(2).lower()

        if mm.isdigit():
            month = int(mm)
            try:
                return datetime(default_year, month, day).date()
            except Exception:
                return None

        month_map = {
            "ja": 1, "jan": 1,
            "fe": 2, "feb": 2,
            "ma": 3, "mar": 3,
            "ap": 4, "apr": 4,
            "maj": 5,
            "ju": 6, "jun": 6,
            "jul": 7,
            "au": 8, "aug": 8,
            "se": 9, "sep": 9,
            "ok": 10, "okt": 10,
            "no": 11, "nov": 11,
            "de": 12, "dec": 12,
        }
        month = month_map.get(mm) or (SWEDISH_MONTH_HINTS.get(sheet_name) if sheet_name else None)
        if month:
            try:
                return datetime(default_year, month, day).date()
            except Exception:
                return None

    # Enbart dag + månad via sheet_name
    if st.isdigit() and sheet_name in SWEDISH_MONTH_HINTS:
        day = int(st)
        month = SWEDISH_MONTH_HINTS[sheet_name]
        try:
            return datetime(default_year, month, day).date()
        except Exception:
            return None

    return None

def force_season_year(dt: pd.Timestamp, season_year: int) -> pd.Timestamp:
    """
    Steg 1: Fixar felparsat datum (år 0000/1899/etc).
    Om år < 2000 men månad/dag verkar rimliga -> tvinga år=season_year.
    """
    if pd.isna(dt):
        return dt
    try:
        if dt.year < 2000:
            return dt.replace(year=season_year)
    except Exception:
        return dt
    return dt

def find_header_row(df_wide: pd.DataFrame):
    for r in range(df_wide.shape[0]):
        row_vals = [lower(df_wide.iat[r, c]) for c in range(min(4, df_wide.shape[1]))]
        if row_vals == HEADER_TOKENS:
            return r, {"birth_year": 0, "position": 1, "no": 2, "name": 3}
    return None, None

def is_total_column(opponent_cell, date_cell) -> bool:
    txt = (lower(opponent_cell) + " " + lower(date_cell)).strip()
    return any(m in txt for m in TOTAL_COL_MARKERS)

def infer_match_possible_minutes(max_minutes: int) -> int:
    if max_minutes is None or np.isnan(max_minutes):
        return 90
    m = int(max_minutes)
    if m <= 0:
        return 90
    if m < 60:
        return 90
    if 60 <= m <= 100:
        return 90
    if 101 <= m <= 130:
        return 120
    return m


# ============================================================
# 3) WIDE -> LONG (per månad)
# ============================================================

def wide_month_to_long(df_wide: pd.DataFrame, sheet_name: str, dataset_key: str, season_year: int) -> pd.DataFrame:
    df_wide = df_wide.copy()

    header_row, cols = find_header_row(df_wide)
    if header_row is None:
        return pd.DataFrame()

    data_start = header_row + 1
    first_match_col = cols["name"] + 1

    meta_row = {}
    for r in range(min(15, df_wide.shape[0])):
        label = lower(df_wide.iat[r, META_LABEL_COL])
        for key, alts in META_KEYS.items():
            if any(label == a for a in alts):
                meta_row[key] = r

    date_r = meta_row.get("date", 0)
    opp_r = meta_row.get("opponent", 1)
    team_r = meta_row.get("team", 2)
    type_r = meta_row.get("type", 3)

    rows = []
    for c in range(first_match_col, df_wide.shape[1]):
        date_val = df_wide.iat[date_r, c] if date_r < df_wide.shape[0] else None
        opp_val = df_wide.iat[opp_r, c] if opp_r < df_wide.shape[0] else None
        team_val = df_wide.iat[team_r, c] if team_r < df_wide.shape[0] else None
        type_val = df_wide.iat[type_r, c] if type_r < df_wide.shape[0] else None

        if is_total_column(opp_val, date_val):
            continue

        match_date = parse_date_cell(date_val, sheet_name=sheet_name, default_year=season_year)
        opponent = s(opp_val)
        team = s(team_val)
        competition = s(type_val)

        if not match_date or not opponent or not team:
            continue

        for r in range(data_start, df_wide.shape[0]):
            name = s(df_wide.iat[r, cols["name"]])
            if not name:
                continue

            birth_year_raw = df_wide.iat[r, cols["birth_year"]]
            pos = s(df_wide.iat[r, cols["position"]]) or None
            player_no = s(df_wide.iat[r, cols["no"]]) or None

            minutes_raw = df_wide.iat[r, c]
            if pd.isna(minutes_raw):
                continue

            try:
                minutes = int(round(float(minutes_raw)))
            except Exception:
                continue

            birth_year = None
            age = None
            if not pd.isna(birth_year_raw) and s(birth_year_raw):
                try:
                    birth_year = int(float(birth_year_raw))
                    age = season_year - birth_year
                except Exception:
                    birth_year = None
                    age = None

            rows.append({
                "dataset": dataset_key,
                "season": season_year,
                "sheet_month": sheet_name,
                "match_date": pd.to_datetime(match_date),
                "opponent": opponent,
                "team": team,
                "competition": competition or "Okänd",
                "player_no": player_no,
                "name": name,
                "birth_year": birth_year,
                "age": age,
                "position": pos,
                "minutes": minutes,
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def load_and_convert_all_for(dataset_key: str, season_year: int) -> pd.DataFrame:
    """
    Steg 4/5: Läser rätt dataset + rätt säsong.
    """
    cfg = DATASETS.get(dataset_key, {})
    seasons = cfg.get("seasons", {})
    wide_urls = seasons.get(season_year, {})

    parts = []
    for sheet_name, url in wide_urls.items():
        try:
            df_wide = pd.read_csv(url, header=None)
        except Exception as e:
            print(f"[FEL] Kunde inte läsa '{dataset_key} {season_year} / {sheet_name}' från URL: {e}")
            continue

        part = wide_month_to_long(df_wide, sheet_name, dataset_key=dataset_key, season_year=season_year)
        if not part.empty:
            parts.append(part)

    if not parts:
        return pd.DataFrame(columns=[
            "dataset","season","sheet_month","match_date","opponent","team","competition",
            "player_no","name","birth_year","age","position","minutes"
        ])

    df = pd.concat(parts, ignore_index=True)

    # Städning + Steg 1: Datum-fix
    df["name"] = df["name"].astype(str).str.strip()
    df["team"] = df["team"].astype(str).str.strip()
    df["opponent"] = df["opponent"].astype(str).str.strip()
    df["competition"] = df["competition"].fillna("Okänd").astype(str).str.strip()

    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df["match_date"] = df["match_date"].apply(lambda d: force_season_year(d, season_year))

    df = df.dropna(subset=["match_date"])

    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)

    return df


# ============================================================
# 4) KPI: MÖJLIGA MINUTER
# ============================================================

def add_possible_minutes(df_long: pd.DataFrame) -> pd.DataFrame:
    if df_long.empty:
        df_long["possible_minutes"] = 90
        return df_long

    g = (df_long.groupby(["team", "match_date"], as_index=False)
         .agg(max_minutes=("minutes", "max")))

    g["possible_minutes"] = g["max_minutes"].apply(infer_match_possible_minutes)
    g = g.drop(columns=["max_minutes"])

    out = df_long.merge(g, on=["team", "match_date"], how="left")
    out["possible_minutes"] = out["possible_minutes"].fillna(90).astype(int)
    return out


# ============================================================
# 5) DASH UI (modernare “cards” + svenska texter) + Steg 3/4/5
# ============================================================

app = dash.Dash(__name__)
server = app.server

COLORS = {
    "bg": "#f6f7fb",
    "card": "#ffffff",
    "text": "#111827",
    "muted": "#6b7280",
    "border": "#e5e7eb",
}

CARD_STYLE = {
    "background": COLORS["card"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "14px",
    "boxShadow": "0 8px 22px rgba(17,24,39,0.06)",
    "padding": "14px 14px",
}

H2_STYLE = {"margin": 0, "fontSize": "20px", "color": COLORS["text"]}
MUTED_STYLE = {"margin": 0, "color": COLORS["muted"], "fontSize": "13px"}

def available_seasons_for(dataset_key: str):
    cfg = DATASETS.get(dataset_key, {})
    seasons = sorted(list(cfg.get("seasons", {}).keys()))
    return seasons

def serve_layout():
    dataset_opts = [{"label": v["label"], "value": k} for k, v in DATASETS.items()]

    seasons_default = available_seasons_for(DATASET_DEFAULT) or [SASONG_DEFAULT]
    season_default = SASONG_DEFAULT if SASONG_DEFAULT in seasons_default else seasons_default[0]

    # laddar initial data för default-val (Steg 4/5)
    df0 = add_possible_minutes(load_and_convert_all_for(DATASET_DEFAULT, season_default))
    valid_dates = df0["match_date"].dropna()
    start_date = valid_dates.min().date() if not valid_dates.empty else None
    end_date = valid_dates.max().date() if not valid_dates.empty else None

    teams = sorted(df0["team"].unique()) if not df0.empty else []
    comps = sorted(df0["competition"].unique()) if not df0.empty else []

    return html.Div(
        style={"background": COLORS["bg"], "minHeight": "100vh", "padding": "18px",
               "fontFamily": "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial"},
        children=[
            dcc.Location(id="url", refresh=False),

            # Dataset + Säsong (Steg 4/5)
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "marginBottom": "12px"},
                children=[
                    html.Div(style=CARD_STYLE, children=[
                        html.Div("Dataset", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Dropdown(id="dataset-select", options=dataset_opts, value=DATASET_DEFAULT, clearable=False),
                    ]),
                    html.Div(style=CARD_STYLE, children=[
                        html.Div("Säsong", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Dropdown(
                            id="season-select",
                            options=[{"label": str(y), "value": y} for y in seasons_default],
                            value=season_default,
                            clearable=False,
                        ),
                    ]),
                ],
            ),

            html.Div(
                style={**CARD_STYLE, "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div([
                        html.H2("Speltid – Dashboard", style=H2_STYLE),
                        html.P("Översikt, spelarkort och belastning", style=MUTED_STYLE),
                    ]),
                    html.Div(id="stats-box", style={"color": COLORS["muted"], "fontSize": "13px", "textAlign": "right"})
                ]
            ),

            html.Div(style={"height": "12px"}),

            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1.2fr 1fr 1fr 1fr", "gap": "12px"},
                children=[
                    html.Div(style=CARD_STYLE, children=[
                        html.Div("Lag", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Dropdown(id="team-filter", options=[{"label": t, "value": t} for t in teams],
                                     multi=True, placeholder="Alla lag"),
                    ]),
                    html.Div(style=CARD_STYLE, children=[
                        html.Div("Matchtyp / tävling", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Dropdown(id="comp-filter", options=[{"label": c, "value": c} for c in comps],
                                     multi=True, placeholder="Alla"),
                    ]),
                    html.Div(style=CARD_STYLE, children=[
                        html.Div("Datumintervall", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.DatePickerRange(
                            id="date-filter",
                            start_date=start_date,
                            end_date=end_date,
                            display_format="YYYY-MM-DD",
                        ),
                    ]),
                    html.Div(style=CARD_STYLE, children=[
                        html.Div("Topplista – antal spelare", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Slider(id="topn-slider", min=10, max=60, step=5, value=30,
                                   marks={10:"10",20:"20",30:"30",40:"40",50:"50",60:"60"}),
                    ]),
                ],
            ),

            html.Div(style={"height": "12px"}),

            html.Div(style=CARD_STYLE, children=[
                dcc.Tabs(
                    id="tabs",
                    value="oversikt",
                    children=[
                        dcc.Tab(label="Översikt", value="oversikt"),
                        dcc.Tab(label="Spelare", value="spelare"),
                        # Steg 3: Datakvalitet borttagen
                    ],
                ),
                html.Div(id="tab-content", style={"marginTop": "12px"}),
            ]),

            # Lagra aktiv DF i browser memory (så vi slipper globala DF och kan byta dataset/säsong)
            dcc.Store(id="df-store", data=df0.to_json(date_format="iso", orient="split")),
        ],
    )

app.layout = serve_layout


# ============================================================
# 6) FILTER + METRIKER
# ============================================================

def apply_filters(df, teams, comps, start_date, end_date):
    if df.empty:
        return df
    out = df.copy()
    if teams:
        out = out[out["team"].isin(teams)]
    if comps:
        out = out[out["competition"].isin(comps)]
    if start_date:
        out = out[out["match_date"] >= pd.to_datetime(start_date)]
    if end_date:
        out = out[out["match_date"] <= pd.to_datetime(end_date)]
    return out

def player_share(df_player: pd.DataFrame) -> float:
    if df_player.empty:
        return 0.0
    num = df_player["minutes"].sum()
    den = df_player.drop_duplicates(["team","match_date"])["possible_minutes"].sum()
    return float(num) / float(den) if den > 0 else 0.0


# ============================================================
# 7) CALLBACKS
# ============================================================

@app.callback(
    Output("season-select", "options"),
    Output("season-select", "value"),
    Input("dataset-select", "value"),
    Input("season-select", "value"),
)
def update_season_options(dataset_key, current_season):
    seasons = available_seasons_for(dataset_key)
    opts = [{"label": str(y), "value": y} for y in seasons]
    if not seasons:
        # dataset saknar config -> håll kvar befintlig men låt det synas
        return [], None
    if current_season in seasons:
        return opts, current_season
    return opts, seasons[0]


@app.callback(
    Output("df-store", "data"),
    Output("team-filter", "options"),
    Output("comp-filter", "options"),
    Output("date-filter", "start_date"),
    Output("date-filter", "end_date"),
    Output("stats-box", "children"),
    Input("dataset-select", "value"),
    Input("season-select", "value"),
)
def reload_data(dataset_key, season_year):
    if not dataset_key or not season_year:
        empty = pd.DataFrame()
        return empty.to_json(date_format="iso", orient="split"), [], [], None, None, ""

    df = add_possible_minutes(load_and_convert_all_for(dataset_key, int(season_year)))

    teams = sorted(df["team"].unique()) if not df.empty else []
    comps = sorted(df["competition"].unique()) if not df.empty else []

    valid_dates = df["match_date"].dropna()
    start_date = valid_dates.min().date() if not valid_dates.empty else None
    end_date = valid_dates.max().date() if not valid_dates.empty else None

    stats = []
    stats.append(html.Div(f"Rader: {len(df)}"))
    stats.append(html.Div(f"Spelare: {df['name'].nunique() if not df.empty else 0}"))
    stats.append(html.Div(f"Matcher: {df[['team','match_date']].drop_duplicates().shape[0] if not df.empty else 0}"))
    stats.append(html.Div(f"Dataset: {DATASETS.get(dataset_key, {}).get('label', dataset_key)}"))
    stats.append(html.Div(f"Säsong: {season_year}"))

    return (
        df.to_json(date_format="iso", orient="split"),
        [{"label": t, "value": t} for t in teams],
        [{"label": c, "value": c} for c in comps],
        start_date,
        end_date,
        stats
    )


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("url", "search"),
    Input("team-filter", "value"),
    Input("comp-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("topn-slider", "value"),
    Input("df-store", "data"),
)
def render_tabs(tab, search, teams, comps, start_date, end_date, topn, df_json):
    df = pd.read_json(df_json, orient="split") if df_json else pd.DataFrame()
    if df.empty:
        return html.Div("Ingen data laddad för valt dataset/säsong.", style={"color": COLORS["muted"]})

    player_name = None
    if search and search.strip("?"):
        params = parse_qs(search.strip("?"))
        if "name" in params and params["name"]:
            player_name = params["name"][0].strip()

    dff = apply_filters(df, teams, comps, start_date, end_date)

    if tab == "oversikt":
        if dff.empty:
            return html.Div("Inga rader matchar valda filter.", style={"color": COLORS["muted"]})

        totals = (dff.groupby("name", as_index=False)
                  .agg(total_minutes=("minutes","sum")))
        totals = totals.sort_values("total_minutes", ascending=False)

        form_list = []
        for p in totals["name"].tolist():
            dp = dff[dff["name"] == p].sort_values("match_date")
            last5 = dp.tail(5)
            form5 = last5["minutes"].mean() if len(last5) else 0
            if len(dp):
                end = dp["match_date"].max()
                w1 = dp[(dp["match_date"] > end - pd.Timedelta(days=30)) & (dp["match_date"] <= end)]["minutes"].sum()
                w0 = dp[(dp["match_date"] > end - pd.Timedelta(days=60)) & (dp["match_date"] <= end - pd.Timedelta(days=30))]["minutes"].sum()
                growth30 = w1 - w0
            else:
                growth30 = 0
            form_list.append((p, form5, growth30))

        form_df = pd.DataFrame(form_list, columns=["name","form5_avg","growth30"])
        totals = totals.merge(form_df, on="name", how="left").fillna({"form5_avg":0,"growth30":0})

        median_minutes = float(totals["total_minutes"].median()) if len(totals) else 0.0

        fig_team = px.bar(
            totals.head(int(topn)),
            x="total_minutes",
            y="name",
            orientation="h",
            hover_data={"form5_avg":":.1f", "growth30": True},
            title="Lagöversikt: total speltid per spelare (Topplista)",
        )
        fig_team.add_vline(x=median_minutes, line_width=2, line_dash="dash",
                           annotation_text="Median", annotation_position="top")

        # Steg 2: vänd så mest minuter ligger överst
        fig_team.update_yaxes(autorange="reversed")

        fig_team.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=700)

        per_match = (dff.groupby("match_date", as_index=False)
                     .agg(total_minutes=("minutes","sum"))
                     .sort_values("match_date"))
        per_match["kumulativ"] = per_match["total_minutes"].cumsum()

        fig_cdf_team = px.line(
            per_match, x="match_date", y="kumulativ", markers=True,
            title="Kumulativ speltid över säsongen (lag – totalminuter)",
        )
        fig_cdf_team.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=350)

        return html.Div([
            dcc.Graph(figure=fig_team),
            dcc.Graph(figure=fig_cdf_team),
            html.Div(style={"color": COLORS["muted"], "fontSize": "12px"},
                     children="Tips: Använd spelartabben för djupdykning per spelare.")
        ])

    if tab == "spelare":
        players = sorted(df["name"].unique())
        default_player = player_name if (player_name in players) else (players[0] if players else None)

        return html.Div([
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "2fr 1fr", "gap": "12px"},
                children=[
                    html.Div(children=[
                        html.Div("Välj spelare", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Dropdown(
                            id="player-select",
                            options=[{"label": p, "value": p} for p in players],
                            value=default_player,
                            clearable=False
                        ),
                    ]),
                    html.Div(children=[
                        html.Div("Rullande fönster (matcher)", style={"fontSize": "13px", "color": COLORS["muted"], "marginBottom": "6px"}),
                        dcc.Slider(id="rolling-window", min=3, max=10, step=1, value=5,
                                   marks={3:"3",5:"5",7:"7",10:"10"}),
                    ]),
                ],
            ),
            html.Div(style={"height": "10px"}),
            html.Div(id="player-content"),
        ])

    return html.Div("Okänd flik.", style={"color": COLORS["muted"]})


@app.callback(
    Output("player-content", "children"),
    Input("player-select", "value"),
    Input("rolling-window", "value"),
    Input("team-filter", "value"),
    Input("comp-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("df-store", "data"),
)
def render_player(player, window, teams, comps, start_date, end_date, df_json):
    df = pd.read_json(df_json, orient="split") if df_json else pd.DataFrame()
    if df.empty:
        return html.Div("Ingen data laddad.", style={"color": COLORS["muted"]})

    if not player:
        return html.Div("Välj en spelare.", style={"color": COLORS["muted"]})

    dff = apply_filters(df, teams, comps, start_date, end_date)
    dp = dff[dff["name"] == player].sort_values("match_date")
    if dp.empty:
        return html.Div("Ingen data för vald spelare med aktuella filter.", style={"color": COLORS["muted"]})

    birth_year = dp["birth_year"].dropna().iloc[0] if dp["birth_year"].dropna().shape[0] else None
    age = int(dp["age"].dropna().iloc[0]) if dp["age"].dropna().shape[0] else None
    pos = dp["position"].dropna().iloc[0] if dp["position"].dropna().shape[0] else None
    team_guess = dp["team"].mode().iloc[0] if dp["team"].nunique() else None

    # CDF-stil
    cdf = dp.groupby("match_date", as_index=False).agg(minuter=("minutes","sum"), possible=("possible_minutes","max"))
    cdf = cdf.sort_values("match_date")
    cdf["kumulativ"] = cdf["minuter"].cumsum()

    fig_cdf = px.line(cdf, x="match_date", y="kumulativ", markers=True,
                      title="Speltid över tid (kumulativ / CDF-stil)")
    fig_cdf.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=320)

    # Månadssummering – formatera månad så det inte blir "timestamp-etiketter"
    dp2 = dp.copy()
    dp2["månad"] = dp2["match_date"].dt.strftime("%Y-%m")
    per_month = dp2.groupby("månad", as_index=False)["minutes"].sum().sort_values("månad")
    fig_month = px.bar(per_month, x="månad", y="minutes", title="Månadssummering: totalt spelade minuter")
    fig_month.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=320)

    # Andel av möjlig speltid
    share_season = player_share(dp)
    dp_last5 = dp.tail(5)
    share_last5 = player_share(dp_last5) if len(dp_last5) else 0.0
    end = dp["match_date"].max()
    dp_30 = dp[(dp["match_date"] > end - pd.Timedelta(days=30)) & (dp["match_date"] <= end)]
    dp_90 = dp[(dp["match_date"] > end - pd.Timedelta(days=90)) & (dp["match_date"] <= end)]
    share_30 = player_share(dp_30) if len(dp_30) else 0.0
    share_90 = player_share(dp_90) if len(dp_90) else 0.0

    share_df = pd.DataFrame([
        ["Säsong", share_season],
        ["Senaste 5 matcher", share_last5],
        ["Senaste 30 dagar", share_30],
        ["Senaste 90 dagar", share_90],
    ], columns=["Period", "Andel"])

    fig_share = px.bar(share_df, x="Period", y="Andel", title="Andel av möjlig speltid")
    fig_share.update_yaxes(tickformat=".0%")
    fig_share.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=320)

    # Rullande belastning (matchfönster)
    roll = dp.groupby("match_date", as_index=False)["minutes"].sum().sort_values("match_date")
    roll["rullande"] = roll["minutes"].rolling(int(window), min_periods=1).sum()
    fig_roll = px.line(roll, x="match_date", y="rullande", markers=True,
                       title=f"Rullande belastning: senaste {int(window)} matcher (minuter)")
    fig_roll.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=320)

    # Timeline
    fig_timeline = px.bar(dp, x="match_date", y="minutes",
                          hover_data=["team","competition","opponent","possible_minutes"],
                          title="Minuter per match")
    fig_timeline.update_layout(margin=dict(l=10,r=10,t=55,b=10), height=320)

    header = html.Div(
        style={"display": "grid", "gridTemplateColumns": "2fr 1fr 1fr 1fr", "gap": "10px", "marginBottom": "10px"},
        children=[
            html.Div(style={**CARD_STYLE}, children=[
                html.Div("Spelare", style={"fontSize":"12px","color":COLORS["muted"]}),
                html.Div(player, style={"fontSize":"18px","fontWeight":"700","color":COLORS["text"]}),
                html.Div(f"Lag: {team_guess or '—'}", style={"fontSize":"13px","color":COLORS["muted"]}),
            ]),
            html.Div(style={**CARD_STYLE}, children=[
                html.Div("Position", style={"fontSize":"12px","color":COLORS["muted"]}),
                html.Div(pos or "—", style={"fontSize":"18px","fontWeight":"700","color":COLORS["text"]}),
            ]),
            html.Div(style={**CARD_STYLE}, children=[
                html.Div("Födelseår", style={"fontSize":"12px","color":COLORS["muted"]}),
                html.Div(str(int(birth_year)) if birth_year is not None else "—",
                         style={"fontSize":"18px","fontWeight":"700","color":COLORS["text"]}),
            ]),
            html.Div(style={**CARD_STYLE}, children=[
                html.Div("Ålder (säsong)", style={"fontSize":"12px","color":COLORS["muted"]}),
                html.Div(str(age) if age is not None else "—", style={"fontSize":"18px","fontWeight":"700","color":COLORS["text"]}),
            ]),
        ]
    )

    grid = html.Div(
        style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"12px"},
        children=[
            html.Div(style=CARD_STYLE, children=[dcc.Graph(figure=fig_cdf, config={"displayModeBar": False})]),
            html.Div(style=CARD_STYLE, children=[dcc.Graph(figure=fig_month, config={"displayModeBar": False})]),
            html.Div(style=CARD_STYLE, children=[dcc.Graph(figure=fig_share, config={"displayModeBar": False})]),
            html.Div(style=CARD_STYLE, children=[dcc.Graph(figure=fig_roll, config={"displayModeBar": False})]),
            html.Div(style={**CARD_STYLE, "gridColumn":"1 / span 2"}, children=[dcc.Graph(figure=fig_timeline, config={"displayModeBar": False})]),
        ],
    )

    return html.Div([header, grid])


if __name__ == "__main__":
    app.run(debug=True)
