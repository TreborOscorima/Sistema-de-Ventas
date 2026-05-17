"""Servicio de envío de emails via SMTP.

Configuración via variables de entorno:
    SMTP_HOST      Servidor SMTP (ej. smtp.gmail.com)
    SMTP_PORT      Puerto (587 para STARTTLS, 465 para SSL, 25 sin cifrado)
    SMTP_USER      Usuario SMTP
    SMTP_PASS      Contraseña / App Password
    SMTP_SENDER    Dirección del remitente (ej. "Sistema <noreply@empresa.com>")
    SMTP_TLS       "1" para STARTTLS (default), "0" para no cifrado, "ssl" para SSL directo

Raises:
    EmailConfigError si las variables requeridas no están configuradas.
    smtplib.SMTPException en errores de envío.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailConfigError(Exception):
    """SMTP no configurado en variables de entorno."""


def _get_config() -> dict:
    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    sender = os.getenv("SMTP_SENDER", user).strip()
    tls_mode = os.getenv("SMTP_TLS", "1").strip().lower()

    if not host or not user or not password:
        raise EmailConfigError(
            "Configura SMTP_HOST, SMTP_USER y SMTP_PASS en el archivo .env para habilitar el envío de correos."
        )

    return {
        "host": host,
        "port": int(port_str),
        "user": user,
        "password": password,
        "sender": sender or user,
        "tls_mode": tls_mode,  # "1" = STARTTLS | "ssl" = SSL | "0" = sin cifrado
    }


def send_email_with_pdf(
    to: str,
    subject: str,
    body_html: str,
    pdf_bytes: bytes,
    pdf_filename: str,
    reply_to: Optional[str] = None,
) -> None:
    """Envía un email con el PDF adjunto.

    Args:
        to: Dirección de destino.
        subject: Asunto del correo.
        body_html: Cuerpo en HTML.
        pdf_bytes: Contenido del PDF como bytes.
        pdf_filename: Nombre de archivo sugerido para el adjunto.
        reply_to: Dirección de respuesta opcional.

    Raises:
        EmailConfigError: Si SMTP no está configurado.
        smtplib.SMTPException: En errores de conexión o envío.
    """
    cfg = _get_config()

    msg = MIMEMultipart("mixed")
    msg["From"] = cfg["sender"]
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Parte HTML
    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(body_part)

    # Adjunto PDF
    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
    msg.attach(pdf_part)

    tls_mode = cfg["tls_mode"]

    try:
        if tls_mode == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["sender"], [to], msg.as_string())
        elif tls_mode == "1":
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["sender"], [to], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["sender"], [to], msg.as_string())

        logger.info("Email enviado a %s — asunto: %s", to, subject)

    except smtplib.SMTPException:
        logger.exception("Error al enviar email a %s", to)
        raise


def build_quotation_email_body(
    company_name: str,
    quotation_id: int,
    client_name: str,
    items_summary: list[str],
    total_str: str,
    currency: str,
    expires_at: str,
    notes: str = "",
) -> str:
    """Genera el HTML del cuerpo del email de un presupuesto."""
    items_html = "".join(f"<li>{line}</li>" for line in items_summary)
    notes_block = f"<p><b>Notas:</b> {notes}</p>" if notes else ""
    return f"""
    <html><body style="font-family: Arial, sans-serif; color: #1e293b; max-width: 600px; margin: auto;">
      <div style="background: #6366f1; padding: 20px 24px; border-radius: 8px 8px 0 0;">
        <h2 style="color: white; margin: 0;">Presupuesto #{quotation_id:05d}</h2>
        <p style="color: #c7d2fe; margin: 4px 0 0;">Enviado por {company_name}</p>
      </div>
      <div style="padding: 20px 24px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
        <p>Estimado(a) <b>{client_name}</b>,</p>
        <p>Adjunto encontrará el presupuesto <b>#{quotation_id:05d}</b> con los productos cotizados:</p>
        <ul style="line-height: 1.8;">{items_html}</ul>
        {notes_block}
        <div style="background: #eef2ff; border: 1px solid #6366f1; border-radius: 6px; padding: 12px 16px; margin-top: 16px;">
          <strong style="color: #6366f1;">Total: {currency} {total_str}</strong>
        </div>
        <p style="color: #f59e0b; font-size: 13px; margin-top: 8px;">
          <b>Válido hasta: {expires_at}</b>
        </p>
        <p style="margin-top: 20px; color: #64748b; font-size: 13px;">
          Para confirmar su pedido o realizar consultas, comuníquese con nosotros.<br/>
          Generado por <b>TUWAYKIAPP</b>
        </p>
      </div>
    </body></html>
    """


def build_po_email_body(
    company_name: str,
    po_id: int,
    supplier_name: str,
    items_summary: list[str],
    total_str: str,
    currency: str,
    notes: str = "",
) -> str:
    """Genera el HTML del cuerpo del email de una orden de compra."""
    items_html = "".join(f"<li>{line}</li>" for line in items_summary)
    notes_block = (
        f"<p><b>Notas:</b> {notes}</p>" if notes else ""
    )
    return f"""
    <html><body style="font-family: Arial, sans-serif; color: #1e293b; max-width: 600px; margin: auto;">
      <div style="background: #6366f1; padding: 20px 24px; border-radius: 8px 8px 0 0;">
        <h2 style="color: white; margin: 0;">Orden de Compra #{po_id}</h2>
        <p style="color: #c7d2fe; margin: 4px 0 0;">Enviada por {company_name}</p>
      </div>
      <div style="padding: 20px 24px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
        <p>Estimado(a) <b>{supplier_name}</b>,</p>
        <p>Adjunto encontrará la orden de compra <b>#{po_id}</b> con los productos solicitados:</p>
        <ul style="line-height: 1.8;">{items_html}</ul>
        {notes_block}
        <div style="background: #eef2ff; border: 1px solid #6366f1; border-radius: 6px; padding: 12px 16px; margin-top: 16px;">
          <strong style="color: #6366f1;">Total estimado: {currency} {total_str}</strong>
        </div>
        <p style="margin-top: 20px; color: #64748b; font-size: 13px;">
          Por favor confirme la recepción de este pedido y comuníquenos su disponibilidad.<br/>
          Generado por <b>TUWAYKIAPP</b>
        </p>
      </div>
    </body></html>
    """
