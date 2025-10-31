# -*- coding: utf-8 -*-
"""
Created on Wed Oct 22 11:43:33 2025
@author: ericl
"""

import dash
# Importera alla nödvändiga Dash-komponenter
from dash import html, dcc, Input, Output, dash_table
import pandas as pd
from urllib.parse import parse_qs

# --- Lista över förväntade kolumner BASERAT PÅ DIN BILD ---
# Vi lägger till 'Position' som valfri, ifall du lägger till den senare.
EXPECTED_COLUMNS = [
    'Name', 'Team', 'Total (IFK)', 'Position'
]

# --- 1. DATALADDNING ---
def load_data():
    # --- UPPDATERA DENNA LÄNK MED DIN RIKTIGA CSV-LÄNK ---
    google_sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRHlsWWf5ixMe6JaAhqRiZRBFTTNUI1Ait-7wZhh2FriUPfj6_ikF7BRmHJPXXUnZYy0P5bAf-EpXiR/pub?output=csv"
    
    try:
        # Läs in CSV, hoppa över de två första raderna (No, Name, Team...)
        df = pd.read_csv(google_sheet_url, header=1) 
    except Exception as e:
        print(f"FEL: Kunde inte läsa datan från Google Sheets. Fel: {e}")
        return pd.DataFrame()

    # --- Kontrollera efter saknade kolumner ---
    missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing_cols:
        print(f"VARNING: Följande kolumner saknas i din CSV: {', '.join(missing_cols)}")
        # Fyll i saknade kolumner med 'N/A' så att appen inte kraschar
        for col in missing_cols:
            df[col] = 'N/A'

    # --- Lätt städning ---
    df['Team'] = df['Team'].fillna('Okänt')
    df = df.dropna(subset=['Name'])
    df['Name'] = df['Name'].str.strip()

    print("Datan har laddats framgångsrikt från Google Sheets.")
    return df

# --- Ladda all data vid start ---
df = load_data()

# --- 2. Initiera Dash-appen ---
app = dash.Dash(__name__)
server = app.server

# --- 3. Definiera appens Layout ---
def serve_layout():
    return html.Div(children=[
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ])

app.layout = serve_layout()

# --- 4. Callback för att uppdatera innehållet ---
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'search')
)
def display_page(search_string):
    player_name = None
    
    if search_string and search_string.strip('?'):
        params = parse_qs(search_string.strip('?'))
        if 'name' in params:
            player_name = params['name'][0]

    # --- FALL 1: Ett spelarnamn finns i URL:en ---
    if player_name:
        if df.empty:
            return html.P("Data kunde inte laddas.")
            
        player_name_clean = player_name.strip()
        player_data = df[df['Name'].str.lower() == player_name_clean.lower()]
        
        if player_data.empty:
            return html.P(f"Kunde inte hitta data för spelaren: {player_name_clean}")
            
        player = player_data.iloc[0]
        
        # --- FIX: Använder kolumnerna som finns: 'Name', 'Team', 'Total (IFK)' ---
        return html.Div([
            html.H2(player.get('Name', 'Okänt Namn')),
            html.Hr(),
            html.P(f"Lag: {player.get('Team', 'N/A')}"),
            html.P(f"Position: {player.get('Position', 'N/A')}"), # Visar 'N/A' eftersom den saknas
            html.H3("Speltid"),
            html.P(f"Total speltid: {player.get('Total (IFK)', 'N/A')} min"),
            # Vi har inte 'Förväntad speltid', så vi visar den inte.
        ], style={'padding': '20px', 'fontFamily': 'sans-serif'})

    # --- FALL 2: Ingen spelare finns i URL:en (visa hela tabellen) ---
    # Vi visar bara de kolumner som faktiskt finns
    display_columns = [col for col in EXPECTED_COLUMNS if col in df.columns]
    
    return html.Div(children=[
        html.H1(children='Spelarstatistik - Totalt'),
        html.P("Interaktiv tabell över total speltid."),
        html.P("Klicka på kolumnrubrikerna för att sortera. Skriv i fälten under rubrikerna för att filtrera."),

        dash_table.DataTable(
            id='spelar-tabell',
            # --- FIX: Använder bara de kolumner som finns ---
            columns=[{"name": i, "id": i} for i in display_columns],
            data=df.to_dict('records'),
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=20,
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)','fontWeight': 'bold'},
            style_cell={'textAlign': 'left','padding': '5px','fontFamily': 'sans-serif'}
        )
    ], style={'padding': '20px'})


# --- 5. Kör appen (endast för lokal testning) ---
if __name__ == '__main__':
    app.run(debug=True)

