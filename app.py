# -*- coding: utf-8 -*-
"""
Created on Wed Oct 22 11:43:33 2025

@author: ericl
"""

import dash
from dash import dash_table
from dash import html
import pandas as pd

# --- 1. DATALADDNING ---

def load_data():
    # --- BYT UT DENNA LÄNK ---
    # Klistra in din publicerade Google Sheet CSV-länk här
    google_sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRtbObnJjSMSgEc7L5ZYBad_NscZPR2tQqrsecPSjCnGjyNoxWDQCGyxQyKVn9Vlw/pub?output=csv"
    
    try:
        # Läs in CSV-filen direkt från Google-länken
        df = pd.read_csv(google_sheet_url)
        
    except Exception as e:
        print(f"FEL: Kunde inte läsa datan från Google Sheets-länken.")
        print(f"Kontrollera att länken är korrekt och publicerad som CSV. Fel: {e}")
        return pd.DataFrame()

    # --- Lätt städning (samma som förut) ---
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
# Denna rad är KRITISK för publicering på Render
server = app.server 

# --- 3. Definiera appens Layout (Inga ändringar) ---
app.layout = html.Div(children=[
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
])

# --- 4. Kör appen (endast för lokal testning) ---
if __name__ == '__main__':
    app.run(debug=True)

