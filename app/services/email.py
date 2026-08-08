import aiosmtplib
from email.message import EmailMessage
from typing import Optional
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _create_html_template(otp: str, purpose: str) -> str:
        if purpose == "registration":
            title = "Welcome to CareerShift!"
            message = "Thank you for starting your journey with us. Please use the verification code below to complete your registration."
        elif purpose == "password_reset":
            title = "Reset Your Password"
            message = "We received a request to reset your CareerShift password. Use the verification code below to set a new password."
        else:
            title = "Your Verification Code"
            message = "Please use the verification code below."

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                /* Email clients require inline or very simple CSS. These styles are fallbacks. */
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f3f4f6;
                    margin: 0;
                    padding: 0;
                    -webkit-font-smoothing: antialiased;
                }}
                .wrapper {{
                    width: 100%;
                    background-color: #f3f4f6;
                    padding: 40px 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
                }}
                .header {{
                    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    color: #ffffff;
                    margin: 0;
                    font-size: 28px;
                    font-weight: 700;
                    letter-spacing: -0.5px;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .content h2 {{
                    color: #1f2937;
                    font-size: 22px;
                    font-weight: 600;
                    margin-top: 0;
                    margin-bottom: 15px;
                }}
                .content p {{
                    color: #4b5563;
                    font-size: 16px;
                    line-height: 1.6;
                    margin: 0 0 25px 0;
                }}
                .otp-wrapper {{
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 25px;
                    margin: 30px auto;
                    max-width: 300px;
                }}
                .otp-code {{
                    font-family: monospace;
                    font-size: 36px;
                    font-weight: 700;
                    letter-spacing: 8px;
                    color: #2563eb;
                    margin: 0;
                    text-align: center;
                }}
                .warning {{
                    font-size: 14px !important;
                    color: #6b7280 !important;
                    margin-bottom: 0 !important;
                }}
                .footer {{
                    background-color: #f9fafb;
                    padding: 25px 30px;
                    text-align: center;
                    border-top: 1px solid #f3f4f6;
                }}
                .footer p {{
                    color: #9ca3af;
                    font-size: 13px;
                    margin: 0 0 10px 0;
                }}
                .footer a {{
                    color: #6b7280;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                    <td align="center">
                        <table class="container" cellpadding="0" cellspacing="0" role="presentation">
                            <tr>
                                <td class="header">
                                    <h1>CareerShift</h1>
                                </td>
                            </tr>
                            <tr>
                                <td class="content">
                                    <h2>{title}</h2>
                                    <p>{message}</p>
                                    
                                    <div class="otp-wrapper">
                                        <p class="otp-code">{otp}</p>
                                    </div>
                                    
                                    <p class="warning">This secure code will expire in <strong>10 minutes</strong>.<br>If you did not request this, please safely ignore this email.</p>
                                </td>
                            </tr>
                            <tr>
                                <td class="footer">
                                    <p>&copy; {datetime.now().year} CareerShift. All rights reserved.</p>
                                    <p>Automated message. Please do not reply.</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

    @staticmethod
    async def send_otp_email(to_email: str, otp: str, purpose: str) -> None:
        if not settings.email_configured:
            if settings.is_production:
                raise ValueError("Email service is not configured.")
            logger.warning("SMTP not configured — OTP logged for development only.")
            print(f"--- MOCK EMAIL --- To: {to_email} | OTP: {otp} | Purpose: {purpose}")
            return

        message = EmailMessage()
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = "Your CareerShift Verification Code"

        from datetime import datetime
        html_content = EmailService._create_html_template(otp, purpose).replace("{datetime.now().year}", str(datetime.now().year))
        
        message.set_content("Please enable HTML to view this email.")
        message.add_alternative(html_content, subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=False,
                start_tls=settings.SMTP_TLS,
            )
            logger.info(f"OTP email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise ValueError("Failed to send verification email. Please try again later.")

    @staticmethod
    async def send_report_ready_email(
        *,
        to_email: str,
        recipient_name: str,
        job_title: str,
        score: int,
        tier_label: str,
        report_url: str,
    ) -> None:
        if not settings.REPORT_READY_EMAIL_ENABLED:
            return

        subject = f"Your Career Intelligence Report is ready — {score}/100"
        html_content = f"""
        <!DOCTYPE html>
        <html><body style="font-family: Arial, sans-serif; color: #1a273d; line-height: 1.6;">
          <h1 style="color: #1a273d;">Your report is ready</h1>
          <p>Hi {recipient_name},</p>
          <p>Your CareerShift Career Intelligence Report for <strong>{job_title}</strong> has been generated.</p>
          <p><strong>AI Readiness:</strong> {score}/100 ({tier_label})</p>
          <p><a href="{report_url}" style="background:#1a273d;color:#fff;padding:12px 20px;text-decoration:none;border-radius:8px;display:inline-block;">View Your Report</a></p>
          <p style="color:#64748b;font-size:13px;">If the button does not work, copy this link:<br>{report_url}</p>
        </body></html>
        """

        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info(
                "Report ready email (mock) to=%s score=%s url=%s",
                to_email,
                score,
                report_url,
            )
            print(f"--- MOCK REPORT EMAIL --- To: {to_email} | Score: {score} | URL: {report_url}")
            return

        message = EmailMessage()
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(f"Your CareerShift report is ready. Score: {score}/100. View: {report_url}")
        message.add_alternative(html_content, subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=False,
                start_tls=settings.SMTP_TLS,
            )
            logger.info("Report ready email sent to %s", to_email)
        except Exception as e:
            logger.error("Failed to send report ready email to %s: %s", to_email, str(e))
