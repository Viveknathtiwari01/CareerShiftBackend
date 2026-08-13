import aiosmtplib
from email.message import EmailMessage
from typing import Optional
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _otp_copy(purpose: str) -> tuple[str, str, str]:
        if purpose == "registration":
            return (
                "Welcome to CareerShift!",
                "Verify your email address",
                "Thank you for starting your career readiness journey. Enter the verification code below to complete your registration and access your personalized AI Career Readiness assessment.",
            )
        if purpose == "password_reset":
            return (
                "Reset your password",
                "Password reset verification",
                "We received a request to reset your CareerShift password. Enter the verification code below to continue. If you did not request this, you can safely ignore this email.",
            )
        return (
            "Your verification code",
            "Account verification",
            "Please use the verification code below to continue.",
        )

    @staticmethod
    def _create_plain_text(otp: str, purpose: str) -> str:
        title, _, message = EmailService._otp_copy(purpose)
        year = datetime.now().year
        return (
            f"CareerShift\n"
            f"{'=' * 40}\n\n"
            f"{title}\n\n"
            f"{message}\n\n"
            f"Verification code: {otp}\n\n"
            f"This code expires in 10 minutes.\n"
            f"If you did not request this email, please ignore it.\n\n"
            f"© {year} CareerShift. All rights reserved.\n"
            f"Automated message — please do not reply."
        )

    @staticmethod
    def _create_html_template(otp: str, purpose: str) -> str:
        title, eyebrow, message = EmailService._otp_copy(purpose)
        year = datetime.now().year

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{title} · CareerShift</title>
</head>
<body style="margin:0;padding:0;background-color:#f6f5ec;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f6f5ec;margin:0;padding:0;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background-color:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 12px 32px rgba(10,18,31,0.08);">
          <tr>
            <td style="background-color:#0a121f;padding:28px 32px;text-align:center;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding-bottom:12px;">
                    <span style="display:inline-block;width:40px;height:40px;line-height:40px;border-radius:10px;background-color:#c9a84c;color:#0a121f;font-size:18px;font-weight:700;text-align:center;">C</span>
                  </td>
                </tr>
                <tr>
                  <td align="center">
                    <p style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.2px;font-family:Georgia,'Times New Roman',serif;">CareerShift</p>
                    <p style="margin:8px 0 0;color:rgba(255,255,255,0.72);font-size:12px;font-weight:600;letter-spacing:1.4px;text-transform:uppercase;">{eyebrow}</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:36px 32px 28px;text-align:center;">
              <h1 style="margin:0 0 12px;color:#0a121f;font-size:24px;line-height:1.3;font-weight:700;font-family:Georgia,'Times New Roman',serif;">{title}</h1>
              <p style="margin:0 0 28px;color:#5c6b7e;font-size:15px;line-height:1.65;">{message}</p>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto 24px;max-width:360px;">
                <tr>
                  <td style="background-color:#faf8f0;border:1px solid #eadfb8;border-radius:12px;padding:22px 18px;text-align:center;">
                    <p style="margin:0 0 10px;color:#8a6d1f;font-size:11px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;">Your verification code</p>
                    <p style="margin:0;color:#0a121f;font-size:34px;line-height:1;font-weight:700;letter-spacing:10px;font-family:'Courier New',Courier,monospace;">{otp}</p>
                  </td>
                </tr>
              </table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;max-width:420px;">
                <tr>
                  <td style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;text-align:left;">
                    <p style="margin:0;color:#5c6b7e;font-size:13px;line-height:1.6;">
                      <strong style="color:#0a121f;">Expires in 10 minutes.</strong>
                      For your security, never share this code with anyone. CareerShift will never ask for it by phone or message.
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:20px 0 0;color:#94a3b8;font-size:13px;line-height:1.6;">
                Didn't request this? You can safely ignore this email — no changes will be made to your account.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background-color:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;text-align:center;">
              <p style="margin:0 0 6px;color:#64748b;font-size:12px;line-height:1.5;">© {year} CareerShift. All rights reserved.</p>
              <p style="margin:0;color:#94a3b8;font-size:11px;line-height:1.5;">Automated message · Please do not reply</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @staticmethod
    def _otp_subject(purpose: str) -> str:
        if purpose == "registration":
            return "Verify your CareerShift account"
        if purpose == "password_reset":
            return "Reset your CareerShift password"
        return "Your CareerShift verification code"

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
        message["Subject"] = EmailService._otp_subject(purpose)

        html_content = EmailService._create_html_template(otp, purpose)
        plain_content = EmailService._create_plain_text(otp, purpose)

        message.set_content(plain_content)
        message.add_alternative(html_content, subtype="html")

        try:
            if settings.RESEND_API_KEY:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
                            "to": [to_email],
                            "subject": "Your CareerShift Verification Code",
                            "html": html_content,
                        }
                    )
                    response.raise_for_status()
            else:
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
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'DM Sans', Arial, Helvetica, sans-serif; background-color: #f6f5ec; margin: 0; padding: 0; -webkit-font-smoothing: antialiased;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f6f5ec; padding: 40px 0;">
                <tr>
                    <td align="center">
                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; max-width: 600px; box-shadow: 0 10px 25px rgba(10, 18, 31, 0.05); overflow: hidden; border-top: 4px solid #c9a84c;">
                            <tr>
                                <td style="background-color: #141f32; padding: 40px 30px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-family: 'Cormorant Garamond', Georgia, serif; font-size: 32px; font-weight: 700; letter-spacing: 0.5px;">CareerShift</h1>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px; text-align: center;">
                                    <h2 style="color: #141f32; margin-top: 0; margin-bottom: 15px; font-size: 24px; font-weight: 700; font-family: 'Cormorant Garamond', Georgia, serif;">Your report is ready!</h2>
                                    <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">Hi {recipient_name},</p>
                                    <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">Your CareerShift Career Intelligence Report for <strong>{job_title}</strong> has been generated.</p>
                                    
                                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 25px; margin: 0 auto 30px auto; max-width: 300px;">
                                        <p style="font-size: 14px; color: #5c6b7e; margin: 0 0 5px 0; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;">AI Readiness Score</p>
                                        <p style="font-size: 42px; font-weight: 700; font-family: 'Cormorant Garamond', Georgia, serif; color: #c9a84c; margin: 0;">{score}<span style="font-size: 20px; color: #9ca3af;">/100</span></p>
                                        <p style="font-size: 16px; font-weight: 700; color: #141f32; margin: 10px 0 0 0;">{tier_label}</p>
                                    </div>
                                    
                                    <a href="{report_url}" style="background-color: #141f32; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; display: inline-block; margin-bottom: 25px; border: 1px solid #141f32;">View Your Report</a>
                                    
                                    <p style="font-size: 13px; color: #6b7280; line-height: 1.5; margin: 0; word-break: break-all;">If the button does not work, copy this link:<br><a href="{report_url}" style="color: #c9a84c; text-decoration: underline;">{report_url}</a></p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: #f4f6f8; padding: 25px 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                                    <p style="color: #5c6b7e; font-size: 13px; margin: 0 0 10px 0;">&copy; {datetime.now().year} CareerShift. All rights reserved.</p>
                                    <p style="color: #5c6b7e; font-size: 13px; margin: 0;">Automated message. Please do not reply.</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        if not settings.email_configured:
            if settings.is_production:
                raise ValueError("Email service is not configured.")
            logger.warning(
                "SMTP not configured — report ready email logged for development only."
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
            if settings.RESEND_API_KEY:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
                            "to": [to_email],
                            "subject": subject,
                            "html": html_content,
                        }
                    )
                    response.raise_for_status()
            else:
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
