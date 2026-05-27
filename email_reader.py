from imapclient import IMAPClient
import email
from email.header import decode_header


def decode_mime_words(s):

    decoded_words = decode_header(s)

    return ''.join(
        str(word, encoding or 'utf-8') if isinstance(word, bytes) else word
        for word, encoding in decoded_words
    )


def read_unread_emails(user_email, user_password):

    client = None

    try:

        print(f"Connecting to Gmail for {user_email}...")

        # Gmail IMAP server
        client = IMAPClient("imap.gmail.com", ssl=True)

        print("Logging in...")
        client.login(user_email, user_password)

        print("Selecting Inbox...")
        client.select_folder("INBOX", readonly=True)

        print("Fetching latest emails...")

        # Fetch emails after this date
        messages = client.search(['SINCE', '01-Jan-2024'])

        if not messages:
            print("No emails found.")
            return []

        # Get latest 20 emails
        latest_messages = sorted(messages, reverse=True)[:20]

        emails = []

        for uid in latest_messages:

            # Fetch raw email
            raw_message = client.fetch([uid], ['BODY[]'])

            raw_email = raw_message[uid][b'BODY[]']

            # Convert raw email into message object
            message = email.message_from_bytes(raw_email)

            # Decode subject safely
            subject = decode_mime_words(
                message.get("Subject", "(No Subject)")
            )

            from_email = message.get("From", "Unknown Sender")

            body = ""

            try:

                if message.is_multipart():

                    for part in message.walk():

                        content_type = part.get_content_type()
                        content_disposition = str(
                            part.get("Content-Disposition")
                        )

                        if (
                            content_type == "text/plain"
                            and "attachment" not in content_disposition
                        ):

                            charset = (
                                part.get_content_charset() or "utf-8"
                            )

                            body = part.get_payload(
                                decode=True
                            ).decode(
                                charset,
                                errors="ignore"
                            )

                            break

                else:

                    charset = message.get_content_charset() or "utf-8"

                    body = message.get_payload(
                        decode=True
                    ).decode(
                        charset,
                        errors="ignore"
                    )

            except Exception:

                body = "Could not decode email body."

            emails.append({
                "subject": subject,
                "from": from_email,
                "body": body
            })

        print(f"Fetched {len(emails)} emails successfully ✅")

        return emails

    except Exception as e:

        error_msg = str(e)

        if "AUTHENTICATIONFAILED" in error_msg:

            print("❌ Gmail login failed.")
            print("👉 Use Gmail APP PASSWORD only.")

        elif "timed out" in error_msg.lower():

            print("❌ Connection timed out.")

        else:

            print("❌ Error reading emails:", e)

        return []

    finally:

        if client:
            try:
                client.logout()
            except:
                pass