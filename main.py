from email_reader import read_unread_emails
from ai_reply import generate_reply
from email_sender import send_reply
from spam_detector import is_spam
from promptinjectionguard import secure_email_input


def run_mail_agent(user_email, user_password):

    # ✅ Fetch emails for THIS user
    emails = read_unread_emails(user_email, user_password)

    if not emails:
        print("No emails found.")
        return

    for email_data in emails:

        print("\n📩 New Email Found")

        body = email_data["body"]
        subject = email_data["subject"]
        sender = email_data["from"][0][1]

        print("From:", sender)
        print("Subject:", subject)

        # 🔴 Spam detection
        if is_spam(body):
            print("⚠️ Spam detected. Skipping...")
            continue

        # 🔐 Prompt Injection Protection
        security = secure_email_input(body)

        if not security["safe"]:
            print("⚠️ Prompt injection detected.")
            print("Sanitizing content...")

        safe_body = security["sanitized_text"]

        try:
            # 🤖 Generate AI reply
            reply = generate_reply(safe_body)

            print("\n🤖 Generated Reply:\n")
            print(reply)

            # 👤 User decision
            decision = input("\nSend reply? (yes / no / edit): ").lower()

            if decision == "yes":
                send_reply(
                    user_email,
                    user_password,
                    sender,
                    subject,
                    reply
                )
                print("✅ Reply Sent")

            elif decision == "edit":
                print("\n✏️ Enter your edited reply:\n")
                edited_reply = input()

                send_reply(
                    user_email,
                    user_password,
                    sender,
                    subject,
                    edited_reply
                )
                print("✅ Edited Reply Sent")

            else:
                print("❌ Skipped")

        except Exception as e:
            print("❌ Error:", e)


# ---------- RUN ----------
if __name__ == "__main__":

    print("🤖 AURIX CLI Mail Agent")

    user_email = input("Enter your email: ")
    user_password = input("Enter your app password: ")

    run_mail_agent(user_email, user_password)