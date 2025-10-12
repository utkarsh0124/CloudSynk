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
    
    Args:
        new_user_email: The recipient's email address
        subject: Email subject line
        body: Email body content
    """
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = new_user_email  # Use the actual recipient email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, new_user_email, msg.as_string())  # Send to actual recipient
        print(f"✅ Email sent successfully to {new_user_email}!")
    except Exception as e:
        print(f"❌ Error sending email to {new_user_email}:", e)
        raise  # Re-raise the exception so calling code can handle it
    finally:
        server.quit()

if __name__ == '__main__':
    # Example usage
    send_otp_email(os.environ.get("RECEIVER_EMAIL"), "Test Email from Python", "Hello! This is a test email.")
