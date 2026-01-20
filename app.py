import re
import numpy as np
import pandas as pd
from datetime import datetime
from urllib.parse import parse_qs

import dash
from dash import dcc, html, Input, Output
import plotly.express as px


# ============================================================
# 1) CONFIG
# ============================================================

# Put ONE published CSV URL per monthly sheet tab (Google Sheets "Publish to web").
# These should be the "wide" manual documentation tabs (Januari, Februari, ...).
# Example format often looks like:
# https://docs.google.com/spreadsheets/d/e/<PUB_ID>/pub?gid=<GID>&single=true&output=csv
WIDE_SHEET_URLS = {
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
}

# Set this per deployment (e.g. MEN / WOMEN) if you run two apps.
DATASET_LABEL = "MEN"  # or "WOMEN"

# Rows in the wide sheet (0-indexed) that contain metadata
ROW_DATE = 0          # row with "Date" and date values
ROW_OPPONENT = 1      # row with "Opponent" and opponent values
ROW_TEAM = 2          # row with "Team" and team values (First Team / U19 / U17 ...)
ROW_COMPETITION = 3   # row with "Type of match" or competition

# Player header row: contains "No" and "Name"
# Data starts the row AFTER this.
PLAYER_HEADER_TOKENS = ("No", "Name")

# Columns (0-indexed) used for player identity in your workbook layout:
COL_NO = 1
COL_NAME = 2

# Optional: if you add Position as a dedicated column in the wide sheet,
# set COL_POSITION = 3 (and shift match columns accordingly in your template).
COL_POSITION = None  # e.g. 3 if you add it as its own column


# ============================================================
# 2) WIDE -> LONG PARSER
# ============================================================

SWEDISH_MONTH_HINTS = {
    "Januari": 1, "Februari": 2, "Mars": 3, "April": 4, "Maj": 5, "Juni": 6,
    "Juli": 7, "Augusti": 8, "September": 9, "Oktober": 10, "November": 11, "December": 12
}

def _safe_str(x):
    return "" if pd.isna(x) else str(x).strip()

def _parse_date_cell(val, sheet_name=None, default_year=2025):
    """
    Handles:
    - real Excel/Sheets dates (already datetime-like)
    - strings like '19-ja' (common in exported sheets)
    """
    if pd.isna(val):
        return None

    # If already datetime-like
    if isinstance(val, (datetime, pd.Timestamp)):
        return pd.to_datetime(val).date()

    s = str(val).strip()

    # Try ISO / standard parsing first
    try:
        dt = pd.to_datetime(s, errors="raise")
        return dt.date()
    except Exception:
        pass

    # Handle patterns like "19-ja" or "19-jan" or "19-01"
    m = re.match(r"^(\d{1,2})\s*[-/.]\s*([A-Za-z]{2,3}|\d{1,2})$", s)
    if m:
        day = int(m.group(1))
        mm = m.group(2).lower()

        # numeric month
        if mm.isdigit():
            month = int(mm)
            try:
                return datetime(default_year, month, day).date()
            except Exception:
                return None

        # Swedish-ish abbreviations; "ja" frequently means januari in these exports
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
        month = month_map.get(mm)
        if not month and sheet_name in SWEDISH_MONTH_HINTS:
            month = SWEDISH_MONTH_HINTS[sheet_name]
        if month:
            try:
                return datetime(default_year, month, day).date()
            except Exception:
                return None

    # Last resort: if sheet_name implies month and s is just a day
    if s.isdigit() and sheet_name in SWEDISH_MONTH_HINTS:
        day = int(s)
        month = SWEDISH_MONTH_HINTS[sheet_name]
        try:
            return datetime(default_year, month, day).date()
        except Exception:
            return None

    return None

def _find_player_header_row(df_wide):
    """
    Finds the row where columns [COL_NO, COL_NAME] equal ("No","Name") (case-insensitive).
    Returns index or None.
    """
    for r in range(df_wide.shape[0]):
        v_no = _safe_str(df_wide.iat[r, COL_NO]).lower()
        v_name = _safe_str(df_wide.iat[r, COL_NAME]).lower()
        if v_no == PLAYER_HEADER_TOKENS[0].lower() and v_name == PLAYER_HEADER_TOKENS[1].lower():
            return r
    return None

def wide_month_to_long(df_wide, sheet_name):
    """
    Expects wide sheet layout:
    - ROW_DATE: date values across match columns
    - ROW_OPPONENT: opponent across match columns
    - ROW_TEAM: team across match columns
    - ROW_COMPETITION: competition/type across match columns
    - player header row contains "No" and "Name"
    - player data rows below; minutes are under each match column
    """
    # Ensure rectangular
    df_wide = df_wide.copy()

    header_row = _find_player_header_row(df_wide)
    if header_row is None:
        return pd.DataFrame()

    data_start = header_row + 1

    # Identify match columns:
    # We assume identity columns end at COL_NAME (and optionally position column).
    first_match_col = (COL_POSITION + 1) if COL_POSITION is not None else (COL_NAME + 1)

    rows = []
    for c in range(first_match_col, df_wide.shape[1]):
        date_val = df_wide.iat[ROW_DATE, c]
        opp_val = df_wide.iat[ROW_OPPONENT, c]
        team_val = df_wide.iat[ROW_TEAM, c]
        comp_val = df_wide.iat[ROW_COMPETITION, c]

        # Skip totals columns / blank columns
        if "totalt" in _safe_str(opp_val).lower() or "totalt" in _safe_str(date_val).lower():
            continue

        match_date = _parse_date_cell(date_val, sheet_name=sheet_name, default_year=2025)
        opponent = _safe_str(opp_val)
        team = _safe_str(team_val)
        competition = _safe_str(comp_val)

        # If there's no meaningful match identity, skip column
        if not match_date or not opponent or not team:
            continue

        # For each player row, read minutes
        for r in range(data_start, df_wide.shape[0]):
            name = _safe_str(df_wide.iat[r, COL_NAME])
            if not name:
                continue

            player_no = _safe_str(df_wide.iat[r, COL_NO])
            minutes_raw = df_wide.iat[r, c]

            # Only keep numeric minutes (including 0). Blank means not recorded / not in squad.
            if pd.isna(minutes_raw):
                continue

            try:
                minutes = float(minutes_raw)
            except Exception:
                continue

            # Normalize minutes to int when close
            minutes_i = int(round(minutes))
            position = None
            if COL_POSITION is not None:
                position = _safe_str(df_wide.iat[r, COL_POSITION]) or None

            rows.append({
                "dataset": DATASET_LABEL,
                "sheet_month": sheet_name,
                "player_no": player_no or None,
                "name": name,
                "team": team,
                "competition": competition or None,
                "opponent": opponent,
                "match_date": pd.to_datetime(match_date),
                "minutes": minutes_i,
                "position": position,
                "start": 1 if minutes_i >= 45 else 0,  # heuristic; replace if you later track starts explicitly
            })

    if not rows:
        return pd.DataFrame()

    df_long = pd.DataFrame(rows)
    return df_long


def load_and_convert_all():
    """
    Loads all wide monthly tabs (CSV) and returns long-format dataframe.
    """
    all_parts = []
    for sheet_name, url in WIDE_SHEET_URLS.items():
        try:
            df_wide = pd.read_csv(url, header=None)
        except Exception as e:
            print(f"[ERROR] Could not read {sheet_name} from URL: {e}")
            continue

        part = wide_month_to_long(df_wide, sheet_name=sheet_name)
        if not part.empty:
            all_parts.append(part)

    if not all_parts:
        return pd.DataFrame(columns=[
            "dataset","sheet_month","player_no","name","team","competition","opponent","match_date",
            "minutes","position","start"
        ])

    df = pd.concat(all_parts, ignore_index=True)

    # Clean / normalize
    df["name"] = df["name"].str.strip()
    df["team"] = df["team"].str.strip()
    df["opponent"] = df["opponent"].str.strip()
    df["competition"] = df["competition"].fillna("").astype(str).str.strip().replace({"": "Unknown"})
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
    df["start"] = pd.to_numeric(df["start"], errors="coerce").fillna(0).astype(int)

    return df


# ============================================================
# 3) DASH APP
# ============================================================

app = dash.Dash(__name__)
server = app.server

# Load and convert once at startup (simple + robust for Render).
# If you want auto-refresh, you can reload in a callback or via Interval.
DF_LONG = load_and_convert_all()

def serve_layout():
    return html.Div(
        style={"padding": "16px", "fontFamily": "sans-serif"},
        children=[
            dcc.Location(id="url", refresh=False),

            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "baseline"},
                children=[
                    html.H2(f"Playing Time Dashboard ({DATASET_LABEL})", style={"margin": 0}),
                    html.Div(
                        [
                            html.Span("Data rows: "),
                            html.Strong(str(len(DF_LONG))),
                        ]
                    ),
                ],
            ),
            html.Hr(),

            # Global filters (apply to Overview)
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "12px"},
                children=[
                    html.Div([
                        html.Label("Team"),
                        dcc.Dropdown(
                            id="team-filter",
                            options=[{"label": t, "value": t} for t in sorted(DF_LONG["team"].unique())] if not DF_LONG.empty else [],
                            multi=True,
                            placeholder="All teams",
                        )
                    ]),
                    html.Div([
                        html.Label("Competition"),
                        dcc.Dropdown(
                            id="comp-filter",
                            options=[{"label": c, "value": c} for c in sorted(DF_LONG["competition"].unique())] if not DF_LONG.empty else [],
                            multi=True,
                            placeholder="All competitions",
                        )
                    ]),
                    html.Div([
                        html.Label("Date range"),
                        dcc.DatePickerRange(
                            id="date-filter",
                            start_date=DF_LONG["match_date"].min().date() if not DF_LONG.empty else None,
                            end_date=DF_LONG["match_date"].max().date() if not DF_LONG.empty else None,
                            display_format="YYYY-MM-DD",
                        )
                    ]),
                    html.Div([
                        html.Label("Top N players (heatmap)"),
                        dcc.Slider(
                            id="topn-slider", min=10, max=60, step=5, value=30,
                            marks={10:"10",20:"20",30:"30",40:"40",50:"50",60:"60"},
                        )
                    ]),
                ],
            ),

            html.Br(),

            dcc.Tabs(
                id="tabs",
                value="overview",
                children=[
                    dcc.Tab(label="Overview", value="overview"),
                    dcc.Tab(label="Player", value="player"),
                    dcc.Tab(label="Data quality", value="quality"),
                ],
            ),

            html.Div(id="tab-content", style={"marginTop": "12px"}),
        ],
    )

app.layout = serve_layout


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


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("url", "search"),
    Input("team-filter", "value"),
    Input("comp-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("topn-slider", "value"),
)
def render_tabs(tab, search, teams, comps, start_date, end_date, topn):
    # Handle URL param ?name=...
    player_name = None
    if search and search.strip("?"):
        params = parse_qs(search.strip("?"))
        if "name" in params and params["name"]:
            player_name = params["name"][0].strip()

    df = apply_filters(DF_LONG, teams, comps, start_date, end_date)

    if DF_LONG.empty:
        return html.Div([
            html.P("No data loaded. Check WIDE_SHEET_URLS configuration and published CSV links.")
        ])

    if tab == "overview":
        if df.empty:
            return html.Div([html.P("No rows match the selected filters.")])

        # A) Minutes distribution (total minutes per player)
        totals = (
            df.groupby(["name"], as_index=False)["minutes"]
            .sum()
            .sort_values("minutes", ascending=False)
        )

        fig_dist = px.bar(
            totals.head(40),
            x="minutes",
            y="name",
            orientation="h",
            title="Total minutes per player (Top 40)",
        )
        fig_dist.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=700)

        # B) Squad utilization matrix (heatmap) for top N by total minutes
        top_players = totals.head(int(topn))["name"].tolist()
        df_hm = df[df["name"].isin(top_players)].copy()

        # pivot: rows players, cols match dates (sorted)
        df_hm["match_day"] = df_hm["match_date"].dt.date.astype(str)

        pivot = (
            df_hm.pivot_table(
                index="name",
                columns="match_day",
                values="minutes",
                aggfunc="sum",
                fill_value=0,
            )
        )
        pivot = pivot.loc[top_players]  # preserve order

        # plotly express imshow expects array
        fig_hm = px.imshow(
            pivot.values,
            x=pivot.columns,
            y=pivot.index,
            aspect="auto",
            title=f"Squad utilization heatmap (Top {int(topn)} players by minutes)",
        )
        fig_hm.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=700)

        # C) Match rhythm: players used + total minutes (sanity / rotation)
        per_match = (
            df.groupby("match_date", as_index=False)
            .agg(total_minutes=("minutes", "sum"), players_used=("name", "nunique"))
            .sort_values("match_date")
        )
        fig_rhythm = px.line(
            per_match, x="match_date", y="players_used", markers=True,
            title="Players used per match (rotation signal)",
        )
        fig_rhythm.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=350)

        return html.Div([
            html.Div([
                dcc.Graph(figure=fig_hm),
            ]),
            html.Div([
                dcc.Graph(figure=fig_dist),
            ]),
            html.Div([
                dcc.Graph(figure=fig_rhythm),
            ]),
        ])

    if tab == "player":
        # Player selection: from URL if present, else dropdown default
        all_players = sorted(DF_LONG["name"].unique())
        default_player = player_name if (player_name in all_players) else (all_players[0] if all_players else None)

        # Build dropdown + charts area; charts depend on selected player via another callback-like pattern:
        return html.Div([
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "2fr 1fr", "gap": "12px", "alignItems": "end"},
                children=[
                    html.Div([
                        html.Label("Player"),
                        dcc.Dropdown(
                            id="player-select",
                            options=[{"label": p, "value": p} for p in all_players],
                            value=default_player,
                            clearable=False
                        )
                    ]),
                    html.Div([
                        html.Label("Rolling window (matches)"),
                        dcc.Slider(
                            id="rolling-window", min=3, max=10, step=1, value=5,
                            marks={3:"3",5:"5",7:"7",10:"10"},
                        )
                    ]),
                ]
            ),
            html.Hr(),
            html.Div(id="player-content"),
        ])

    if tab == "quality":
        # Basic checks: duplicates, impossible minutes, missing metadata
        dfq = DF_LONG.copy()
        dfq["bad_minutes"] = (dfq["minutes"] < 0) | (dfq["minutes"] > 130)

        summary = {
            "rows_total": len(dfq),
            "players": dfq["name"].nunique(),
            "matches": dfq["match_date"].nunique(),
            "bad_minutes_rows": int(dfq["bad_minutes"].sum()),
            "unknown_comp_rows": int((dfq["competition"] == "Unknown").sum()),
        }

        by_team = (
            dfq.groupby("team", as_index=False)
            .agg(rows=("minutes", "size"), players=("name", "nunique"), matches=("match_date", "nunique"), minutes=("minutes","sum"))
            .sort_values("minutes", ascending=False)
        )

        fig_team = px.bar(by_team, x="team", y="minutes", title="Total minutes by team")
        fig_team.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=350)

        return html.Div([
            html.H3("Quality summary"),
            html.Ul([
                html.Li(f"Rows: {summary['rows_total']}"),
                html.Li(f"Players: {summary['players']}"),
                html.Li(f"Matches: {summary['matches']}"),
                html.Li(f"Rows with minutes outside 0–130: {summary['bad_minutes_rows']}"),
                html.Li(f"Rows with Unknown competition: {summary['unknown_comp_rows']}"),
            ]),
            dcc.Graph(figure=fig_team),
        ])

    return html.Div([html.P("Unknown tab")])


@app.callback(
    Output("player-content", "children"),
    Input("player-select", "value"),
    Input("rolling-window", "value"),
    Input("team-filter", "value"),
    Input("comp-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
)
def render_player(player, window, teams, comps, start_date, end_date):
    if not player:
        return html.P("Select a player.")

    df = apply_filters(DF_LONG, teams, comps, start_date, end_date)
    d = df[df["name"] == player].sort_values("match_date")
    if d.empty:
        return html.P("No rows for this player with the current filters.")

    # Timeline bar
    fig_timeline = px.bar(
        d,
        x="match_date",
        y="minutes",
        hover_data=["team", "competition", "opponent"],
        title=f"{player}: Minutes per match",
    )
    fig_timeline.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=350)

    # Rolling minutes over last N matches
    d2 = d.copy()
    d2["rolling_minutes"] = d2["minutes"].rolling(int(window), min_periods=1).sum()

    fig_roll = px.line(
        d2,
        x="match_date",
        y="rolling_minutes",
        markers=True,
        title=f"{player}: Rolling minutes (last {int(window)} matches)",
    )
    fig_roll.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=350)

    # Split: competition
    comp_split = (
        d.groupby("competition", as_index=False)["minutes"]
        .sum()
        .sort_values("minutes", ascending=False)
    )
    fig_comp = px.bar(
        comp_split, x="minutes", y="competition", orientation="h",
        title=f"{player}: Minutes by competition",
    )
    fig_comp.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=350)

    return html.Div([
        dcc.Graph(figure=fig_timeline),
        dcc.Graph(figure=fig_roll),
        dcc.Graph(figure=fig_comp),
    ])


if __name__ == "__main__":
    app.run(debug=True)





