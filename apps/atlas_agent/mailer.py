import smtplib
from email.mime.text import MIMEText
import os
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import time
from .models import Lead


def _mailer_enabled_from_env() -> bool:
    value = (os.getenv("ATLAS_ENABLE_MAILER") or "").strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


class ColdMailer:
    """
    Controlador de envio de E-mails Frios para a plataforma Google Workspace.
    Integra sistema de Opt-Out (LGPD) e templates dinâmicos.
    """
    def __init__(self, smtp_user: Optional[str] = None, smtp_pass: Optional[str] = None, dry_run: Optional[bool] = None):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_user = smtp_user or os.getenv("ATLAS_SMTP_USER") or os.getenv("SMTP_USER", "")
        self.smtp_pass = smtp_pass or os.getenv("ATLAS_SMTP_PASS") or os.getenv("SMTP_PASSWORD", "")
        if dry_run is None:
            # Opt-in explícito: só envia e-mail real com ATLAS_ENABLE_MAILER=true.
            self.dry_run = not _mailer_enabled_from_env()
        else:
            self.dry_run = dry_run

    def generate_email_body(self, lead: Lead) -> str:
        """
        Gera o corpo do e-mail com variáveis dinâmicas alinhadas aos produtos 
        LIRO/LittleBot e à BNCC.
        """
        nome_decisor = lead.decider_name.split()[0] if lead.decider_name else "Diretoria"
        
        template = f"""Olá {nome_decisor}, tudo bem?

Acompanhamos o trabalho de excelência do {lead.institution_name} em {lead.city} e notamos o compromisso de vocês com a inovação pedagógica.

Sabemos que alinhar o ensino de tecnologia às diretrizes da BNCC é um dos grandes desafios atuais das escolas. É por isso que desenvolvemos os robôs educacionais LIRO e LittleBot — plataformas 100% aplicadas que transformam laboratórios makers em centros de excelência, sem depender de professores especialistas em programação.

Gostaria de lhe apresentar, em uma rápida reunião de 15 minutos, como podemos estruturar essa matriz curricular tecnológica no {lead.institution_name}.

Qual o melhor horário na sua agenda na próxima semana?

Um abraço,
Marcelo | Smart Control Brasil
https://smartcontrolbrasil.com.br/

---
*Caso não deseje receber mais comunicações, responda com "Descadastrar".*
"""
        return template

    def send_email(self, lead: Lead):
        """
        Envia e-mail único. Se dry_run=True, apenas loga no terminal.
        """
        if not lead.contact_email:
            print(f"[Atlas Mailer] Pulando {lead.institution_name} - Sem E-mail.")
            return False

        subject = f"Inovação e Robótica no {lead.institution_name}"
        body = self.generate_email_body(lead)

        if self.dry_run:
            print(f"\n[Atlas Mailer DRY RUN] Enviando para: {lead.contact_email}")
            print(f"Subject: {subject}\n{'-'*40}\n{body}\n{'-'*40}")
            lead.approach_status = "E-mail Enviado (Mock)"
            return True

        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = lead.contact_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
            server.quit()
            lead.approach_status = "E-mail Enviado"
            print(f"[Atlas Mailer] E-mail enviado com sucesso para {lead.contact_email}")
            return True
        except Exception as e:
            print(f"[Atlas Mailer] Erro ao enviar para {lead.contact_email}: {str(e)}")
            return False

    def run_campaign(self, leads: List[Lead]):
        """
        Roda a campanha de disparo em lote respeitando delay.
        """
        print(f"[Atlas Mailer] Iniciando campanha para {len(leads)} leads.")
        for lead in leads:
            self.send_email(lead)
            if not self.dry_run:
                # Simula comportamento humano (Warm-up / Anti-spam)
                time.sleep(5)
