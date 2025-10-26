# -*- coding: utf-8 -*-
"""
Created on Wed Oct 22 11:43:33 2025

@author: ericl
"""

import dash
from dash import dash_table  # Importera tabell-komponenten
from dash import html
import pandas as pd

# --- 1. DATALADDNING ---
# Nu anpassad för din .xlsx-fil

def load_data():
    # Sökväg till din .xlsx-fil
    excel_file_path = "Speltid tabell test.xlsx" 

    try:
        # Läs in .xlsx-filen
        # sheet_name=0 betyder "ta den första fliken, oavsett vad den heter"
        df = pd.read_excel(excel_file_path, sheet_name=0) 
        
    except FileNotFoundError:
        print(f"FEL: Hittade inte filen '{excel_file_path}'.")
        print("Se till att filen ligger i samma mapp som din app.py-fil.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Ett oväntat fel inträffade vid inläsning: {e}")
        return pd.DataFrame()

    # --- Lätt städning ---
    
    # 1. Fyll i saknade värden för 'Team' (om några finns)
    df['Team'] = df['Team'].fillna('Okänt')
    
    # 2. Ta bort rader där 'Name' saknas (om några finns)
    df = df.dropna(subset=['Name'])
    
    # 3. Avrunda siffran för snyggare presentation
    # (Antag att kolumnen fortfarande heter 'Förväntad speltid')
    if 'Förväntad speltid' in df.columns:
        df['Förväntad speltid'] = df['Förväntad speltid'].round(1)

    print("Datan har laddats framgångsrikt från Excel-filen.")
    return df

# --- Ladda all data vid start ---
df = load_data()

# --- 2. Initiera Dash-appen ---
app = dash.Dash(__name__)
server = app.server

# --- 3. Definiera appens Layout ---
app.layout = html.Div(children=[
    html.H1(children='Spelarstatistik - Totalt'),
    html.P("Interaktiv tabell över total speltid vs. förväntad speltid."),
    html.P("Klicka på kolumnrubrikerna för att sortera. Skriv i fälten under rubrikerna för att filtrera."),

    # --- DEN INTERAKTIVA TABELLEN ---
    dash_table.DataTable(
        id='spelar-tabell',
        
        # Kolumner och data hämtas direkt från vår rena DataFrame
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),

        # --- Interaktiva funktioner ---
        sort_action="native",   # Tillåt sortering
        filter_action="native", # Tillåt filtrering
        page_action="native",   # Aktivera sidnumrering
        page_current=0,
        page_size=20,           # Visa 20 spelare per sida

        # --- Styling ---
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '5px',
            'fontFamily': 'sans-serif'
        }
    )
])

# --- 4. Callbacks (Behövs fortfarande inte!) ---

# --- 5. Kör appen ---
if __name__ == '__main__':
    app.run(debug=True)
