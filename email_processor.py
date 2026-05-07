from email_reader import read_unread_emails
from ai_reply import generate_reply
from email_sender import send_reply
from spam_detector import is_spam
from promptinjectionguard import secure_email_input


def process_emails():

    inbox_count = 0
    replies_generated = 0
    spam_blocked = 0

    emails = read_unread_emails()

    inbox_count = len(emails)

    for email in emails:

        body = email["body"]
        subject = email["subject"]
        sender = email["from"][0][1]

        # Spam detection
        if is_spam(body):
            spam_blocked += 1
            continue

        # Prompt injection protection
        security = secure_email_input(body)

        safe_body = security["sanitized_text"]

        try:
            reply = generate_reply(safe_body)

            replies_generated += 1

            send_reply(sender, subject, reply)

        except Exception as e:
            print("Error:", e)

    return inbox_count, replies_generated, spam_blocked