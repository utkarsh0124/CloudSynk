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
    """
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Error:", e)
    finally:
        server.quit()

if __name__ == '__main__':
    # Example usage
    send_otp_email(os.environ.get("RECEIVER_EMAIL"), "Test Email from Python", "Hello! This is a test email.")
