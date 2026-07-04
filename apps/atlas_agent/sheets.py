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
    def __init__(
        self,
        spreadsheet_title: str,
        spreadsheet_id: str = "",
        credentials_path: str = "",
    ):
        self.spreadsheet_title = spreadsheet_title
        self.spreadsheet_id = (spreadsheet_id or "").strip()
        self.credentials_path = (credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
        self.client = None
        self.sheet = None
        self._authenticate()

    def _authenticate(self):
        if not GSPREAD_INSTALLED:
            print("[Atlas Sheets] desabilitado: gspread/google-auth nao instalado.")
            return

        if not self.credentials_path:
            print("[Atlas Sheets] credencial ausente: defina GOOGLE_APPLICATION_CREDENTIALS.")
            return

        if not os.path.exists(self.credentials_path):
            print("[Atlas Sheets] credencial ausente no filesystem (caminho nao exibido).")
            return

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
            credentials = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            self.client = gspread.authorize(credentials)
            if self.spreadsheet_id:
                self.sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
            else:
                # Mantem fallback por titulo para compatibilidade local.
                self.sheet = self.client.open(self.spreadsheet_title).sheet1
            print(
                "[Atlas Sheets] autenticado com sucesso; spreadsheet_id={sheet_id}.".format(
                    sheet_id="presente" if self.spreadsheet_id else "ausente",
                )
            )
        except Exception as e:
            print(f"[Atlas Sheets] falha na autenticacao/conexao: {str(e)}")

    def push_lead(self, lead: Lead):
        """
        Injeta o lead na planilha no formato esperado.
        """
        if not self.sheet:
            print("[Atlas Sheets] sem sessao ativa; gravacao ignorada (offline/mock).")
            return
            
        try:
            row_data = lead.to_csv_row()
            self.sheet.append_row(row_data)
            print("[Atlas Sheets] 1 lead salvo na planilha.")
        except Exception as e:
            print(f"[Atlas Sheets] falha ao salvar lead: {str(e)}")

    def push_leads_batch(self, leads: List[Lead]):
        """
        Injeta leads em lote.
        """
        if not self.sheet:
            print(f"[Atlas Sheets] sem sessao ativa; lote de {len(leads)} leads nao enviado.")
            return

        try:
            if not leads:
                print("[Atlas Sheets] lote vazio; nenhuma linha enviada.")
                return
            rows = [lead.to_csv_row() for lead in leads]
            self.sheet.append_rows(rows)
            print(f"[Atlas Sheets] {len(leads)} leads salvos com sucesso.")
        except Exception as e:
            print(f"[Atlas Sheets] falha no envio em lote: {str(e)}")
