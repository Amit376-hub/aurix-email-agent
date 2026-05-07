import streamlit as st

from auth import login, signup, logout, is_authenticated
from email_reader import read_unread_emails
from ai_reply import generate_reply
from email_sender import send_reply
from spam_detector import is_spam
from report_logger import log_scan_event, clear_logs, get_all_logs
from report_generator import (
    generate_spam_report,
    generate_user_report,
    generate_date_report,
    generate_combined_report,
)

# ---------- Page Config ----------
st.set_page_config(
    page_title="AURIX Mail Agent",
    page_icon="🤖",
    layout="wide"
)

# ================================================================
#  AUTH SECTION
# ================================================================
if not is_authenticated():

    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Rajdhani:wght@300;400;600&display=swap');
[data-testid="stAppViewContainer"]{
    background:
        radial-gradient(ellipse at 10% 10%, rgba(14,165,233,0.15) 0%, transparent 40%),
        radial-gradient(ellipse at 90% 80%, rgba(30,58,138,0.25) 0%, transparent 40%),
        #020617;
    color:#e2e8f0; font-family:'Rajdhani',sans-serif;
}
[data-testid="stHeader"]{background:transparent !important;}
[data-testid="stToolbar"]{display:none;}
#MainMenu,footer{visibility:hidden;}
.aurix-logo{text-align:center;padding:2.5rem 0 0.25rem;}
.aurix-logo h1{font-family:'Orbitron',monospace;font-size:2.8rem;font-weight:800;
    color:#38bdf8;text-shadow:0 0 24px rgba(56,189,248,0.6),0 0 48px rgba(14,165,233,0.3);
    letter-spacing:4px;margin:0;}
.aurix-logo p{font-size:0.85rem;color:#64748b;letter-spacing:3px;text-transform:uppercase;margin:0.2rem 0 0;}
.stTextInput>label{font-family:'Orbitron',monospace !important;font-size:0.62rem !important;
    letter-spacing:2px !important;color:#64748b !important;text-transform:uppercase !important;}
.stTextInput>div>div>input{background:rgba(2,6,23,0.7) !important;
    border:1px solid rgba(56,189,248,0.2) !important;border-radius:10px !important;
    color:#e2e8f0 !important;font-family:'Rajdhani',sans-serif !important;font-size:1rem !important;padding:0.6rem 1rem !important;}
.stTextInput>div>div>input:focus{border-color:rgba(56,189,248,0.55) !important;
    box-shadow:0 0 12px rgba(56,189,248,0.15) !important;}
.stButton>button{width:100%;
    background:linear-gradient(135deg,#0ea5e9 0%,#1e40af 100%) !important;
    color:#fff !important;border:none !important;border-radius:10px !important;
    padding:0.72rem 1.5rem !important;font-family:'Orbitron',monospace !important;
    font-size:0.68rem !important;letter-spacing:3px !important;text-transform:uppercase !important;
    font-weight:600 !important;box-shadow:0 0 20px rgba(14,165,233,0.25) !important;
    transition:all 0.2s ease !important;margin-top:0.4rem;}
.stButton>button:hover{box-shadow:0 0 32px rgba(14,165,233,0.5) !important;transform:translateY(-1px) !important;}
.hint{text-align:center;color:#334155;font-size:0.78rem;letter-spacing:1px;margin:1.2rem 0 0.5rem;}
.aurix-footer{text-align:center;color:#1e293b;font-size:0.6rem;
    font-family:'Orbitron',monospace;letter-spacing:2px;padding:2.5rem 0 1rem;}
</style>
""", unsafe_allow_html=True)

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    st.markdown("<div class='aurix-logo'><h1>AURIX</h1><p>Mail Intelligence Agent</p></div><br>",
                unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.session_state.auth_mode == "login":
            with st.form("aurix_login"):
                email    = st.text_input("Email Address", placeholder="agent@aurix.ai")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Access System", use_container_width=True)

            if submitted:
                ok, result = login(email, password)
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.user_name     = result
                    st.session_state.user_email    = email.strip().lower()
                    st.session_state.user_password = password
                    st.rerun()
                else:
                    st.error(result)

            st.markdown('<p class="hint">— No account yet? —</p>', unsafe_allow_html=True)
            if st.button("Create an Account →", key="go_signup", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()

        else:
            with st.form("aurix_signup"):
                name     = st.text_input("Full Name", placeholder="Ada Lovelace")
                email    = st.text_input("Email Address", placeholder="agent@aurix.ai")
                password = st.text_input("Password", type="password", placeholder="Min. 8 characters")
                confirm  = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Initialize Agent", use_container_width=True)

            if submitted:
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = signup(name, email, password)
                    if ok:
                        st.success(msg + "  Please log in.")
                        st.session_state.auth_mode = "login"
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown('<p class="hint">— Already registered? —</p>', unsafe_allow_html=True)
            if st.button("← Back to Login", key="go_login", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()

    st.markdown("<div class='aurix-footer'>AURIX © 2025 · SECURE AUTH · v1.0</div>",
                unsafe_allow_html=True)
    st.stop()

# ================================================================
#  MAIN APP
# ================================================================

if "inbox_count" not in st.session_state:
    st.session_state.inbox_count = 0
if "replies_generated" not in st.session_state:
    st.session_state.replies_generated = 0
if "spam_blocked" not in st.session_state:
    st.session_state.spam_blocked = 0
if "emails" not in st.session_state:
    st.session_state.emails = []

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 20% 20%, #0ea5e9 0%, transparent 30%),
        radial-gradient(circle at 80% 70%, #1e3a8a 0%, transparent 35%),
        #020617;
    color:#e2e8f0; font-family:"Orbitron",monospace;
}
h1{text-align:center;font-size:54px;color:#38bdf8;text-shadow:0 0 20px #38bdf8,0 0 40px #0ea5e9;}
p{text-align:center;color:#94a3b8;font-size:18px;}
.panel{background:rgba(15,23,42,0.75);border:1px solid rgba(56,189,248,0.4);
    border-radius:16px;padding:20px;backdrop-filter:blur(20px);box-shadow:0 0 20px rgba(56,189,248,0.25);}
.email-card{background:rgba(15,23,42,0.85);border:1px solid rgba(56,189,248,0.35);
    padding:25px;border-radius:16px;margin-bottom:25px;
    backdrop-filter:blur(10px);box-shadow:0 0 20px rgba(56,189,248,0.25);}
.metric{font-size:32px;color:#38bdf8;text-align:center;text-shadow:0 0 15px #38bdf8;}
.spam-reason{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.4);
    border-radius:10px;padding:10px 16px;margin-top:10px;
    color:#fca5a5;font-size:0.85rem;font-family:'Rajdhani',sans-serif;line-height:1.5;}
.spam-reason-label{font-weight:700;color:#ef4444;font-size:0.8rem;
    letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;}
.stButton>button{background:linear-gradient(90deg,#06b6d4,#3b82f6);color:white;border:none;
    border-radius:12px;padding:12px 28px;font-weight:bold;box-shadow:0 0 15px rgba(59,130,246,0.6);}
textarea{background:#020617 !important;color:#38bdf8 !important;
    border:1px solid #38bdf8 !important;border-radius:10px !important;}
[data-testid="stSidebar"]{background:#020617;border-right:1px solid rgba(56,189,248,0.3);}
</style>
""", unsafe_allow_html=True)

st.title("🤖 AURIX - Mail Agent")
st.write(f"Welcome, **{st.session_state.get('user_name', '')}** · Autonomous AI system that reads your emails and generates smart replies.")

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🤖 AURIX System Monitor")
    st.success("Email Scanner: ACTIVE")
    st.info("Spam Filter: RUNNING")
    st.warning("AI Reply Engine: READY")
    st.write("---")
    st.write("System Load")
    st.progress(70)
    st.write("---")
    if st.button("Sign Out"):
        logout()
        st.rerun()

# ---------- Metrics ----------
col1, col2, col3, col4 = st.columns(4)
inbox_metric  = col1.empty()
reply_metric  = col2.empty()
spam_metric   = col3.empty()
status_metric = col4.empty()

def update_metrics():
    inbox_metric.markdown(f'<div class="panel"><center>📬 Inbox<div class="metric">{st.session_state.inbox_count}</div></center></div>', unsafe_allow_html=True)
    reply_metric.markdown(f'<div class="panel"><center>🤖 Replies Generated<div class="metric">{st.session_state.replies_generated}</div></center></div>', unsafe_allow_html=True)
    spam_metric.markdown(f'<div class="panel"><center>🚫 Spam Blocked<div class="metric">{st.session_state.spam_blocked}</div></center></div>', unsafe_allow_html=True)
    status_metric.markdown('<div class="panel"><center>⚡ AI Status<div class="metric">ONLINE</div></center></div>', unsafe_allow_html=True)

update_metrics()
st.write("")

# ---------- Tabs ----------
tab_inbox, tab_report = st.tabs(["📬 Inbox", "📊 Reports"])

# ================================================================
#  TAB 1 — INBOX
# ================================================================
with tab_inbox:

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        check_emails = st.button("📬 Scan Inbox")

    if check_emails:
        st.session_state.replies_generated = 0
        st.session_state.spam_blocked      = 0

        # ✅ Wipe old logs so reports only reflect this scan
        clear_logs()

        with st.spinner("🤖 AURIX scanning inbox..."):
            st.session_state.emails = read_unread_emails(
                st.session_state.user_email,
                st.session_state.user_password
            )

        st.session_state.inbox_count = len(st.session_state.emails)
        update_metrics()

    for idx, email in enumerate(st.session_state.emails):
        body    = email["body"][:2000]
        subject = email["subject"]
        sender  = email["from"][0][1]

        with st.container():
            st.markdown('<div class="email-card">', unsafe_allow_html=True)

            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"📧 {subject}")
                st.write(f"**From:** {sender}")

            # ✅ Unpack verdict AND reason
            spam_result, spam_reason = is_spam(body)

            if spam_result:
                st.session_state.spam_blocked += 1
                update_metrics()
                st.error("🚫 Spam Email Detected")

                # ✅ Show reason on screen
                if spam_reason:
                    st.markdown(
                        f"""<div class="spam-reason">
                            <div class="spam-reason-label">⚠ Detection Reason</div>
                            {spam_reason}
                        </div>""",
                        unsafe_allow_html=True
                    )

                log_scan_event(
                    username     = st.session_state.get("user_name", "Unknown"),
                    user_email   = st.session_state.user_email,
                    subject      = subject,
                    sender       = sender,
                    is_spam      = True,
                    spam_reasons = [spam_reason] if spam_reason else [],
                )

                st.markdown('</div>', unsafe_allow_html=True)
                continue

            log_scan_event(
                username   = st.session_state.get("user_name", "Unknown"),
                user_email = st.session_state.user_email,
                subject    = subject,
                sender     = sender,
                is_spam    = False,
            )

            with st.spinner("🤖 Generating AI reply..."):
                reply = generate_reply(body)

            st.session_state.replies_generated += 1
            update_metrics()

            st.markdown("### 🤖 AI Draft Reply")
            edited_reply = st.text_area(
                "Edit reply before sending",
                value=reply, height=180, key=f"reply_{idx}"
            )

            if st.button(f"Send Reply to {sender}", key=f"send_{idx}"):
                send_reply(sender, subject, edited_reply)
                st.success("Reply sent successfully!")

            st.markdown('</div>', unsafe_allow_html=True)

# ================================================================
#  TAB 2 — REPORTS
# ================================================================
with tab_report:
    st.markdown("### 📊 Reports")
    st.write("All reports reflect the **latest scan** only.")

    logs      = get_all_logs()
    spam_logs = [e for e in logs if e.get("is_spam")]
    safe_logs = [e for e in logs if not e.get("is_spam")]

    if not logs:
        st.info("No scan data yet. Run a scan first from the Inbox tab.")
    else:
        # ── Summary metrics ──
        m1, m2, m3 = st.columns(3)
        m1.metric("📧 Total Emails Scanned", len(logs))
        m2.metric("🚫 Spam Detected",        len(spam_logs))
        m3.metric("✅ Safe Emails",           len(safe_logs))

        st.write("")
        st.markdown("---")

        # ── Inline spam preview table ──
        if spam_logs:
            st.markdown("#### 🚫 Spam Emails Detected")
            from collections import defaultdict
            by_user = defaultdict(list)
            for e in spam_logs:
                by_user[e.get("username", "Unknown")].append(e)

            for user, entries in sorted(by_user.items()):
                st.markdown(f"**👤 {user}** — {len(entries)} spam mail(s) detected")
                st.table({
                    "Subject": [e.get("subject", "—") for e in entries],
                    "Sender":  [e.get("sender",  "—") for e in entries],
                    "Reason":  [(e.get("spam_reasons") or ["—"])[0] for e in entries],
                })
        else:
            st.success("✅ No spam detected in the latest scan.")

        st.write("")
        st.markdown("---")

        # ── PDF Download buttons ──
        st.markdown("#### 📄 Download PDF Reports")
        st.write("Choose which report you want to download:")

        user_name = st.session_state.get("user_name", "user")

        dl1, dl2, dl3, dl4 = st.columns(4)

        with dl1:
            st.markdown("**🚫 Spam Report**")
            st.caption("User · Spam count · Subjects")
            if st.button("Generate", key="btn_spam"):
                pdf = generate_spam_report(logs)
                st.download_button(
                    label     = "⬇️ Download",
                    data      = pdf,
                    file_name = f"aurix_spam_report_{user_name}.pdf",
                    mime      = "application/pdf",
                    key       = "dl_spam",
                )

        with dl2:
            st.markdown("**👤 Username-wise**")
            st.caption("Full per-user breakdown")
            if st.button("Generate", key="btn_user"):
                pdf = generate_user_report(logs)
                st.download_button(
                    label     = "⬇️ Download",
                    data      = pdf,
                    file_name = f"aurix_user_report_{user_name}.pdf",
                    mime      = "application/pdf",
                    key       = "dl_user",
                )

        with dl3:
            st.markdown("**📅 Date-wise**")
            st.caption("Daily activity breakdown")
            if st.button("Generate", key="btn_date"):
                pdf = generate_date_report(logs)
                st.download_button(
                    label     = "⬇️ Download",
                    data      = pdf,
                    file_name = f"aurix_date_report_{user_name}.pdf",
                    mime      = "application/pdf",
                    key       = "dl_date",
                )

        with dl4:
            st.markdown("**📋 Combined**")
            st.caption("Full summary + spam detail")
            if st.button("Generate", key="btn_combined"):
                pdf = generate_combined_report(logs)
                st.download_button(
                    label     = "⬇️ Download",
                    data      = pdf,
                    file_name = f"aurix_combined_report_{user_name}.pdf",
                    mime      = "application/pdf",
                    key       = "dl_combined",
                )