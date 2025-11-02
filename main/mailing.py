import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os 

# Gmail account credentials from env variables
sender_email = os.environ.get("SENDER_EMAIL", "your_email@gmail.com")
receiver_email = os.environ.get("RECEIVER_EMAIL", "receiver_email@example.com")
app_password = os.environ.get("APP_PASSWORD", "your_app_password")


def send_otp_email(new_user_email, subject, body):
    """
    Send an email via Gmail SMTP for OTP delivery.
    For SIGNUP: Sends to RECEIVER_EMAIL (admin/testing email)
    For LOGIN: Use send_login_otp_email() instead
    """
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email  # For signup, always send to RECEIVER_EMAIL

    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"✅ Signup OTP email sent successfully to {receiver_email}!")
    except Exception as e:
        print(f"❌ Error sending signup OTP: {e}")
        raise  # Re-raise to be caught by views.py logging
    finally:
        server.quit()


def send_login_otp_email(user_email, subject, body):
    """
    Send login OTP email via Gmail SMTP.
    For LOGIN: Sends to the actual user's registered email address
    """
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = user_email  # For login, send to actual user's email

    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, user_email, msg.as_string())
        print(f"✅ Login OTP email sent successfully to {user_email}!")
    except Exception as e:
        print(f"❌ Error sending login OTP: {e}")
        raise  # Re-raise to be caught by views.py logging
    finally:
        server.quit()

if __name__ == '__main__':
    # Example usage
    send_otp_email(os.environ.get("RECEIVER_EMAIL"), "Test Email from Python", "Hello! This is a test email.")
