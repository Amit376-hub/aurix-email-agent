import smtplib
from email.mime.text import MIMEText

EMAIL = "kumaramitkumar6209@gmail.com"
PASSWORD = "uoumykmqcayjxoav"

def send_reply(to_email, subject, reply):

    msg = MIMEText(reply)

    msg["Subject"] = "Re: " + subject
    msg["From"] = EMAIL
    msg["To"] = to_email

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL, PASSWORD)

    server.sendmail(EMAIL, to_email, msg.as_string())

    server.quit()