from imapclient import IMAPClient
import pyzmail36 as pyzmail


def read_unread_emails(user_email, user_password):

    client = None

    try:
        print(f"Connecting to Gmail for {user_email}...")

        # ✅ Use correct Gmail IMAP host
        client = IMAPClient("imap.gmail.com", ssl=True)

        print("Logging in...")
        client.login(user_email, user_password)

        print("Selecting Inbox...")
        client.select_folder("INBOX", readonly=True)

        print("Fetching latest emails...")

        # ✅ Get only recent emails (faster & safer)
        messages = client.search(['SINCE', '01-Jan-2024'])

        if not messages:
            print("No emails found.")
            return []

        # Latest 20 emails (reduce load)
        latest_messages = sorted(messages, reverse=True)[:20]

        emails = []

        for uid in latest_messages:

            raw_message = client.fetch(uid, ['BODY.PEEK[]'])

            message = pyzmail.PyzMessage.factory(
                raw_message[uid][b'BODY[]']
            )

            subject = message.get_subject() or "(No Subject)"
            from_email = message.get_addresses('from')

            body = ""

            try:
                if message.text_part:
                    body = message.text_part.get_payload().decode(errors="ignore")

                elif message.html_part:
                    body = message.html_part.get_payload().decode(errors="ignore")

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

        # 🔴 Better error visibility
        error_msg = str(e)

        if "AUTHENTICATIONFAILED" in error_msg:
            print("❌ Gmail login failed.")
            print("👉 Check email & APP PASSWORD (not normal password).")

        elif "timed out" in error_msg.lower():
            print("❌ Connection timed out. Check internet.")

        else:
            print("❌ Error reading emails:", e)

        return []

    finally:
        # ✅ Always close connection safely
        if client:
            try:
                client.logout()
            except:
                pass