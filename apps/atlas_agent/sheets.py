import json
import os
from typing import List
from .models import Lead

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_INSTALLED = True
except ImportError:
    GSPREAD_INSTALLED = False

class GoogleSheetsIntegration:
    """
    Controlador para salvar leads processados diretamente em uma Matriz Google Sheets.
    Requer: 
    - Biblioteca gspread
    - credentials.json da Conta de Serviço Google
    """
    def __init__(self, spreadsheet_title: str, credentials_path: str = "credentials.json"):
        self.spreadsheet_title = spreadsheet_title
        self.credentials_path = credentials_path
        self.client = None
        self.sheet = None
        self._authenticate()

    def _authenticate(self):
        if not GSPREAD_INSTALLED:
            print("[Atlas Sheets] Warning: gspread is not installed. Use 'pip install gspread google-auth'")
            return
            
        if not os.path.exists(self.credentials_path):
            print(f"[Atlas Sheets] Warning: Credentials file {self.credentials_path} not found. Running in offline/mock mode.")
            return

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
            credentials = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            self.client = gspread.authorize(credentials)
            # Open by Exact Title as configured in Drive
            self.sheet = self.client.open(self.spreadsheet_title).sheet1
            print(f"[Atlas Sheets] Connected to '{self.spreadsheet_title}' successfully.")
        except Exception as e:
            print(f"[Atlas Sheets] Error authenticating: {str(e)}")

    def push_lead(self, lead: Lead):
        """
        Injeta o lead na planilha no formato esperado.
        """
        if not self.sheet:
            print(f"[Atlas Sheets Offline] Would push lead to Sheets: {lead.institution_name}")
            return
            
        try:
            row_data = lead.to_csv_row()
            self.sheet.append_row(row_data)
            print(f"[Atlas Sheets] Lead {lead.institution_name} salvo na nuvem.")
        except Exception as e:
            print(f"[Atlas Sheets] Error appending row: {str(e)}")

    def push_leads_batch(self, leads: List[Lead]):
        """
        Injeta leads em lote.
        """
        if not self.sheet:
            print(f"[Atlas Sheets Offline] Would push {len(leads)} leads to Sheets.")
            return
            
        try:
            rows = [lead.to_csv_row() for lead in leads]
            self.sheet.append_rows(rows)
            print(f"[Atlas Sheets] {len(leads)} leads salvos na nuvem com sucesso.")
        except Exception as e:
            print(f"[Atlas Sheets] Error appending batch rows: {str(e)}")
