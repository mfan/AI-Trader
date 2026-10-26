"""
Email Reporter — sends trading reports via Gmail SMTP (SSL).

Credentials come from environment (.env):
    GMAIL_USER          sender Gmail address
    GMAIL_APP_PASSWORD  16-char Gmail App Password (NOT the account password)
    REPORT_EMAIL_TO     recipient address

Gmail app passwords: Google Account -> Security -> 2-Step Verification -> App passwords.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import pytz

logger = logging.getLogger('EmailReporter')


def email_configured() -> bool:
    return bool(os.getenv("GMAIL_USER") and os.getenv("GMAIL_APP_PASSWORD") and os.getenv("REPORT_EMAIL_TO"))


def send_email(subject: str, html_body: str) -> bool:
    """Send an HTML email via Gmail SMTP. Returns True on success."""
    # Re-read .env so credential rotation never needs a process restart
    from dotenv import load_dotenv
    load_dotenv(override=True)
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = os.getenv("REPORT_EMAIL_TO")
    if not (user and password and recipient):
        logger.warning("📧 Email not configured (GMAIL_USER/GMAIL_APP_PASSWORD/REPORT_EMAIL_TO) — skipping send.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
        logger.info(f"📧 Report emailed to {recipient}: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Email send failed: {e}")
        return False


def _positions_table(positions: dict, prices: dict) -> str:
    if not positions:
        return "<p><i>No open positions (flat).</i></p>"
    rows = []
    for sym, p in positions.items():
        cur = prices.get(sym)
        pnl = ""
        if cur:
            val = (cur - p["entry_price"]) * p["qty"]
            color = "#3fb950" if val >= 0 else "#ff7b72"
            pnl = f'<span style="color:{color}">${val:+,.0f}</span>'
        rows.append(
            f"<tr><td><b>{sym}</b></td><td>{p['qty']:,}</td><td>${p['entry_price']:.2f}</td>"
            f"<td>{f'${cur:.2f}' if cur else '—'}</td><td>${p.get('stop', 0):.2f}</td><td>{pnl}</td></tr>"
        )
    return ("<table border='0' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-size:14px'>"
            "<tr style='border-bottom:2px solid #4c9aff'><th align='left'>Symbol</th><th align='right'>Qty</th>"
            "<th align='right'>Entry</th><th align='right'>Last</th><th align='right'>Stop</th><th align='right'>Unrl. P&L</th></tr>"
            + "".join(rows) + "</table>")


def _page(title: str, sections: list) -> str:
    body = "".join(f"<h3 style='color:#4c9aff;margin:18px 0 6px'>{h}</h3>{c}" for h, c in sections)
    return (f"<div style='font-family:Segoe UI,Arial,sans-serif;max-width:640px;color:#222'>"
            f"<h2 style='margin-bottom:2px'>🤖 AI Trader — {title}</h2>{body}</div>")


def send_morning_report(signals_log: str, targets: dict, state: dict, equity: float, prices: dict):
    """Post-rebalance daily report (~9:40 AM ET)."""
    now = datetime.now(pytz.timezone('US/Eastern'))
    tgt = ("<table border='0' cellpadding='6' style='border-collapse:collapse;font-size:14px'>"
           + "".join(f"<tr><td><b>{s}</b></td><td align='right'>{w:.1%}</td>"
                     f"<td align='right'>${w * equity:,.0f}</td></tr>" for s, w in targets.items())
           + "</table>") if targets else "<p><i>Flat — no positive-momentum ETFs.</i></p>"

    hist = state.get("history", [])
    today = now.strftime("%Y-%m-%d")
    todays = [h for h in hist if h.get("exit_time", "").startswith(today)]
    fills = "".join(
        f"<li>{h['symbol']}: {h['qty']:,} sh — {h['exit_reason']}, P&L <b>${h.get('pnl') or 0:+,.0f}</b></li>"
        for h in todays
    ) or "<li>No exits today</li>"

    html = _page(f"Morning Report — {now.strftime('%a %b %d, %Y')}", [
        ("Account", f"<p>Equity: <b>${equity:,.2f}</b> (paper)</p>"),
        ("12-1 Momentum Signals", f"<pre style='background:#f4f6f8;padding:10px;border-radius:6px'>{signals_log}</pre>"),
        ("Target Portfolio", tgt),
        ("Current Positions", _positions_table(state.get("positions", {}), prices)),
        ("Today's Fills / Exits", f"<ul>{fills}</ul>"),
    ])
    return send_email(f"AI Trader Morning Report — {today}", html)


def send_daily_summary(state: dict, equity: float, day_start_equity: float,
                       month_start: float, prices: dict, signals_text: str,
                       targets: dict, broker_positions: dict,
                       spy_day_ret: float = None) -> bool:
    """
    Post-close daily summary (4:30 PM ET) with double-check analysis:
    reconciles state vs broker, measures target adherence, day P&L vs SPY,
    reviews exits, and checks risk limits.
    """
    now = datetime.now(pytz.timezone('US/Eastern'))
    today = now.strftime("%Y-%m-%d")
    positions = state.get("positions", {})
    hist = state.get("history", [])
    todays = [h for h in hist if h.get("exit_time", "").startswith(today)]

    # ── 1) Reconciliation double-check: state vs broker ──
    recon_rows = []
    recon_ok = True
    for sym in set(positions) | set(broker_positions):
        s_qty = positions.get(sym, {}).get("qty", 0)
        b_qty = int(abs(float(broker_positions.get(sym, {}).get("qty", 0))))
        match = "✅" if s_qty == b_qty else "❌"
        if s_qty != b_qty:
            recon_ok = False
        recon_rows.append(f"<tr><td>{sym}</td><td align='right'>{s_qty:,}</td>"
                          f"<td align='right'>{b_qty:,}</td><td align='center'>{match}</td></tr>")
    recon_html = ("<table border='0' cellpadding='6' style='border-collapse:collapse;font-size:14px'>"
                  "<tr style='border-bottom:2px solid #4c9aff'><th>Symbol</th><th align='right'>State qty</th>"
                  "<th align='right'>Broker qty</th><th>Match</th></tr>" + "".join(recon_rows) + "</table>"
                  if recon_rows else "<p><i>Flat on both sides.</i> ✅</p>")

    # ── 2) Day performance vs SPY ──
    day_pnl = equity - day_start_equity if day_start_equity else 0.0
    day_ret = (equity / day_start_equity - 1) * 100 if day_start_equity else 0.0
    spy_txt = f"{spy_day_ret:+.2f}%" if spy_day_ret is not None else "n/a"
    perf_color = "#3fb950" if day_ret >= 0 else "#ff7b72"
    bench_note = ""
    if spy_day_ret is not None:
        diff = day_ret - spy_day_ret
        bench_note = f"({'outperformed' if diff >= 0 else 'underperformed'} SPY by {abs(diff):.2f}%)"

    # ── 3) Realized exits review ──
    realized = sum(h.get("pnl") or 0 for h in todays)
    exits = "".join(
        f"<li><b>{h['symbol']}</b> {h['qty']:,} sh @ ${h.get('exit_price') or 0:.2f} — {h['exit_reason']}, "
        f"P&L <b>${h.get('pnl') or 0:+,.0f}</b></li>"
        for h in todays
    ) or "<li>No exits today</li>"

    # ── 4) Position risk check: distance from disaster stops ──
    risk_rows = []
    for sym, p in positions.items():
        cur = prices.get(sym)
        if cur and p.get("stop"):
            dist = (cur / p["stop"] - 1) * 100
            flag = "🟢" if dist > 5 else ("🟡" if dist > 2 else "🔴")
            risk_rows.append(f"<tr><td><b>{sym}</b></td><td align='right'>${cur:.2f}</td>"
                             f"<td align='right'>${p['stop']:.2f}</td><td align='right'>{dist:+.1f}%</td>"
                             f"<td align='center'>{flag}</td></tr>")
    risk_html = ("<table border='0' cellpadding='6' style='border-collapse:collapse;font-size:14px'>"
                 "<tr style='border-bottom:2px solid #4c9aff'><th>Symbol</th><th align='right'>Last</th>"
                 "<th align='right'>Stop</th><th align='right'>Buffer</th><th></th></tr>"
                 + "".join(risk_rows) + "</table>") if risk_rows else "<p><i>No open positions.</i></p>"

    # ── 5) Target adherence ──
    tgt_rows = []
    for sym, w in targets.items():
        cur_qty = positions.get(sym, {}).get("qty", 0)
        cur_px = prices.get(sym, 0)
        cur_w = (cur_qty * cur_px / equity) if equity else 0
        drift = (cur_w - w) * 100
        tgt_rows.append(f"<tr><td><b>{sym}</b></td><td align='right'>{w:.1%}</td>"
                        f"<td align='right'>{cur_w:.1%}</td><td align='right'>{drift:+.1f}pp</td></tr>")
    tgt_html = ("<table border='0' cellpadding='6' style='border-collapse:collapse;font-size:14px'>"
                "<tr style='border-bottom:2px solid #4c9aff'><th>Symbol</th><th align='right'>Target</th>"
                "<th align='right'>Actual</th><th align='right'>Drift</th></tr>"
                + "".join(tgt_rows) + "</table>") if tgt_rows else "<p><i>Target: flat.</i></p>"

    dd = (equity / month_start - 1) * 100 if month_start else 0.0
    unrealized = sum((prices.get(s, p["entry_price"]) - p["entry_price"]) * p["qty"]
                     for s, p in positions.items())

    html = _page(f"Daily Summary — {now.strftime('%a %b %d, %Y')}", [
        ("📊 Day Performance",
         f"<p>Equity: <b>${equity:,.2f}</b> | Day: <b style='color:{perf_color}'>${day_pnl:+,.0f} ({day_ret:+.2f}%)</b> "
         f"vs SPY {spy_txt} {bench_note}<br>"
         f"Realized today: <b>${realized:+,.0f}</b> | Unrealized open: <b>${unrealized:+,.0f}</b> | "
         f"Month-to-date: <b>{dd:+.2f}%</b> (breaker at −8%)</p>"),
        ("🔍 Signal Review", f"<pre style='background:#f4f6f8;padding:10px;border-radius:6px'>{signals_text or 'n/a'}</pre>"),
        ("🎯 Target Adherence", tgt_html),
        ("🔁 Reconciliation Check (state vs broker)", recon_html),
        ("🛡️ Risk Check (distance above disaster stops)", risk_html),
        ("📤 Today's Exits", f"<ul>{exits}</ul>"),
        ("📋 Open Positions (overnight)", _positions_table(positions, prices)),
    ])
    return send_email(f"AI Trader Daily Summary — {today}", html)


def send_eod_report(state: dict, equity: float, month_start: float, prices: dict):
    """End-of-day summary (~3:55 PM ET)."""
    now = datetime.now(pytz.timezone('US/Eastern'))
    today = now.strftime("%Y-%m-%d")
    hist = state.get("history", [])
    todays = [h for h in hist if h.get("exit_time", "").startswith(today)]
    realized = sum(h.get("pnl") or 0 for h in todays)
    unrealized = sum((prices.get(s, p["entry_price"]) - p["entry_price"]) * p["qty"]
                     for s, p in state.get("positions", {}).items())
    dd = (equity / month_start - 1) * 100 if month_start else 0.0

    exits = "".join(
        f"<li>{h['symbol']} {h['qty']:,} sh @ ${h.get('exit_price') or 0:.2f} — {h['exit_reason']}, "
        f"P&L <b>${h.get('pnl') or 0:+,.0f}</b></li>"
        for h in todays
    ) or "<li>None</li>"

    html = _page(f"End-of-Day Report — {now.strftime('%a %b %d, %Y')}", [
        ("Account", f"<p>Equity: <b>${equity:,.2f}</b> | Month-to-date: "
                    f"<b style='color:{'#3fb950' if dd >= 0 else '#ff7b72'}'>{dd:+.2f}%</b> "
                    f"(breaker at −8%)</p>"),
        ("Today's P&L", f"<p>Realized: <b>${realized:+,.2f}</b> | Unrealized: <b>${unrealized:+,.2f}</b></p>"),
        ("Today's Exits", f"<ul>{exits}</ul>"),
        ("Open Positions (held overnight)", _positions_table(state.get("positions", {}), prices)),
    ])
    return send_email(f"AI Trader EOD Report — {today}", html)
