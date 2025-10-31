# -*- coding: utf-8 -*-
"""
Created on Wed Oct 22 11:43:33 2025

@author: ericl
"""

import dash
from dash import html, dcc, Input, Output
import pandas as pd
from urllib.parse import parse_qs # <-- Importera för att läsa URL:en

# --- 1. DATALADDNING ---

def load_data():
    # --- UPPDATERAD GOOGLE SHEET CSV-LÄNK ---
    google_sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRtbObnJjSMSgEc7L5ZYBad_NscZPR2tQqrsecPSjCnGjyNoxWDQCGyxQyKVn9Vlw/pub?output=csv"
    
    try:
        df = pd.read_csv(google_sheet_url)
    except Exception as e:
        print(f"FEL: Kunde inte läsa datan från Google Sheets. Fel: {e}")
        return pd.DataFrame()

    df['Team'] = df['Team'].fillna('Okänt')
    df = df.dropna(subset=['Name'])
    if 'Förväntad speltid' in df.columns:
        df['Förväntad speltid'] = df['Förväntad speltid'].round(1)

    print("Datan har laddats framgångsrikt från Google Sheets.")
    return df

# --- Ladda all data vid start ---
df = load_data()

# --- 2. Initiera Dash-appen ---
app = dash.Dash(__name__)
server = app.server

# --- 3. Definiera appens Layout (HELT OMARBETAD) ---
# Vi lägger till dcc.Location för att läsa URL:en och en 'output-div'
# som kommer att fyllas med antingen spelardata eller tabellen.
def serve_layout():
    return html.Div(children=[
        # Denna komponent läser av webbläsarens URL
        dcc.Location(id='url', refresh=False),
        
        # Denna div kommer att innehålla vår data
        html.Div(id='page-content')
    ])

app.layout = serve_layout

# --- 4. NYTT: Callback för att uppdatera innehållet ---
# Denna funktion körs varje gång URL:en ändras
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'search')
)
def display_page(search_string):
    # 'search_string' är den del av URL:en som börjar med '?', t.ex. '?name=Alice%20Andersson'
    
    player_name = None
    if search_string:
        # Parsa söksträngen
        params = parse_qs(search_string.strip('?'))
        if 'name' in params:
            # Ta namnet från URL:en (t.ex. 'Alice Andersson')
            player_name = params['name'][0]

    # --- FALL 1: Ett spelarnamn finns i URL:en ---
    if player_name:
        if df.empty:
            return html.P("Data kunde inte laddas.")
            
        # Hitta spelaren i vår DataFrame
        player_data = df[df['Name'] == player_name]
        
        if player_data.empty:
            return html.P(f"Kunde inte hitta data för spelaren: {player_name}")
            
        # Plocka ut den första (och enda) raden
        player = player_data.iloc[0]
        
        # Skapa en anpassad layout för en enskild spelare
        return html.Div([
            html.H2(player['Name']),
            html.Hr(),
            html.P(f"Lag: {player['Team']}"),
            html.P(f"Position: {player['Position']}"),
            html.H3("Speltid"),
            html.P(f"Total speltid: {player['Total speltid']} min"),
            html.P(f"Förväntad speltid: {player['Förväntad speltid']} min"),
            # Lägg till fler fält här efter behov
        ], style={'padding': '20px', 'fontFamily': 'sans-serif'})

    # --- FALL 2: Ingen spelare finns i URL:en (visa hela tabellen) ---
    # Detta är vad som visas när du går till "Spelminuter"-sidan
    return html.Div(children=[
        html.H1(children='Spelarstatistik - Totalt'),
        html.P("Interaktiv tabell över total speltid vs. förväntad speltid."),
        html.P("Klicka på kolumnrubrikerna för att sortera. Skriv i fälten under rubrikerna för att filtrera."),

        dash_table.DataTable(
            id='spelar-tabell',
            columns=[{"name": i, "id": i} for i in df.columns],
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

