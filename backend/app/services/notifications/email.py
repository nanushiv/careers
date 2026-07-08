"""
Email service — transactional emails via Resend.
"""
import logging
from typing import Optional
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


async def send_follow_up_reminder(
    to_email: str,
    user_name: str,
    company_name: str,
    role_title: str,
    draft_message: Optional[str] = None,
):
    """Send a follow-up reminder email."""
    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": f"Follow-up reminder: {role_title} at {company_name}",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
              <h2>Time to follow up, {user_name}!</h2>
              <p>You applied to <strong>{role_title}</strong> at <strong>{company_name}</strong>
              and it's time to check in.</p>
              {"<h3>Suggested Message</h3><blockquote>" + draft_message + "</blockquote>" if draft_message else ""}
              <p><a href="{settings.FRONTEND_URL}/applications" style="background: #7c3aed; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">
                View Application
              </a></p>
            </div>
            """,
        })
        logger.info(f"Follow-up reminder sent to {to_email}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")


async def send_weekly_digest(
    to_email: str,
    user_name: str,
    career_health_score: float,
    new_insights: list,
    follow_ups_due: int,
    week_apps: int,
):
    """Send weekly career intelligence digest."""
    first = user_name.split()[0] if user_name else "there"
    score_color = "#4ade80" if career_health_score >= 65 else "#fbbf24" if career_health_score >= 50 else "#f87171"
    next_action = (
        "Log your applications this week to keep your pipeline active."
        if week_apps == 0 else
        f"Great — {week_apps} application{'s' if week_apps != 1 else ''} this week. Keep the momentum going."
    )
    followup_line = (
        f'<p style="color:#fbbf24;">⚠️ You have <strong>{follow_ups_due} follow-up{"s" if follow_ups_due != 1 else ""}</strong> due — don\'t let those go cold.</p>'
        if follow_ups_due > 0 else ""
    )
    insights_html = "".join([
        f'<li style="margin-bottom:8px;"><strong style="color:#a78bfa;">{i.get("title")}</strong><br><span style="color:#9ca3af;">{i.get("summary","")}</span></li>'
        for i in new_insights[:3]
    ])

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": f"Your career health this week: {int(career_health_score)}/100",
            "html": f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0d1117;color:#e5e7eb;padding:32px;border-radius:12px;">
              <div style="text-align:center;margin-bottom:24px;">
                <span style="font-size:20px;font-weight:700;color:#fff;">CareerOS</span>
                <span style="font-size:12px;color:#6b7280;display:block;margin-top:2px;">Weekly Intelligence Report</span>
              </div>
              <p style="color:#d1d5db;">Hi {first},</p>
              <div style="text-align:center;margin:24px 0;padding:20px;background:#111827;border-radius:10px;border:1px solid #1f2937;">
                <p style="color:#9ca3af;font-size:12px;margin:0 0 8px 0;">CAREER HEALTH SCORE</p>
                <p style="font-size:56px;font-weight:700;color:{score_color};margin:0;line-height:1;">{int(career_health_score)}</p>
                <p style="color:#6b7280;font-size:14px;margin:4px 0 0 0;">/100</p>
              </div>
              <p style="color:#d1d5db;">{next_action}</p>
              {followup_line}
              {"<h3 style='color:#fff;margin-top:24px;'>This Week's Insights</h3><ul style='padding-left:20px;color:#d1d5db;'>" + insights_html + "</ul>" if new_insights else ""}
              <div style="text-align:center;margin-top:28px;">
                <a href="{settings.FRONTEND_URL}/dashboard"
                  style="background:#7c3aed;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;">
                  View Dashboard →
                </a>
              </div>
              <p style="color:#4b5563;font-size:11px;text-align:center;margin-top:24px;">
                CareerOS · <a href="{settings.FRONTEND_URL}/settings" style="color:#4b5563;">Manage email preferences</a>
              </p>
            </div>
            """,
        })
        logger.info(f"Weekly digest sent to {to_email}")
    except Exception as e:
        logger.error(f"Weekly digest send failed: {e}")


async def send_analysis_complete(
    to_email: str,
    user_name: str,
    resume_name: str,
    ats_score: float,
    top_gap: Optional[str] = None,
):
    """Notify user when analysis is complete."""
    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": f"Analysis complete: Your resume scored {ats_score}/100",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
              <h2>Your Resume Analysis Is Ready</h2>
              <p>Hi {user_name}, we've finished analyzing <strong>{resume_name}</strong>.</p>
              <p style="font-size: 48px; text-align: center; color: #7c3aed;">{ats_score}<span style="font-size:20px">/100</span></p>
              {"<p><strong>Top gap found:</strong> " + top_gap + "</p>" if top_gap else ""}
              <p><a href="{settings.FRONTEND_URL}/resume" style="background: #7c3aed; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">
                View Full Analysis
              </a></p>
            </div>
            """,
        })
    except Exception as e:
        logger.error(f"Analysis complete email failed: {e}")


async def send_resume_fix_reminder(
    to_email: str,
    user_name: str,
    ats_score: float,
    top_gaps: list,
    resume_id: str,
):
    """3-day post-analysis reminder if resume not yet updated."""
    gaps_html = "".join([f"<li>{g}</li>" for g in top_gaps[:3]])
    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": f"Your resume scored {ats_score}/100 — 3 quick fixes inside",
            "html": f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0d1117;color:#e5e7eb;padding:32px;border-radius:12px;">
              <h2 style="color:#fff;">Hey {user_name.split()[0]} — your resume still needs work 👀</h2>
              <p>3 days ago your resume scored <strong style="color:#a78bfa;">{ats_score}/100</strong> on ATS analysis.</p>
              <p>Here are the top 3 gaps recruiters are seeing:</p>
              <ul style="color:#d1d5db;">{gaps_html}</ul>
              <p>These are quick fixes — most take under 20 minutes.</p>
              <a href="{settings.FRONTEND_URL}/resume/{resume_id}/analysis"
                style="display:inline-block;background:#7c3aed;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:8px;">
                View Full Analysis & Fix Guide →
              </a>
              <p style="color:#6b7280;font-size:12px;margin-top:24px;">
                Once you update your resume, re-upload it to see your new score.
                <a href="{settings.FRONTEND_URL}/unsubscribe" style="color:#6b7280;">Unsubscribe</a>
              </p>
            </div>
            """,
        })
        logger.info(f"Resume fix reminder sent to {to_email}")
    except Exception as e:
        logger.error(f"Resume fix reminder failed: {e}")


async def _notify_team_feedback(email: str, name: str, would_pay: str):
    """Notify founder when new feedback comes in."""
    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": settings.NOTIFY_EMAIL,
            "subject": f"New CareerOS feedback: {name or email} — {would_pay}",
            "html": f"<p>New feedback from <b>{name}</b> ({email})</p><p>Would pay: <b>{would_pay}</b></p>",
        })
    except Exception:
        pass


async def send_pro_welcome(to_email: str, user_name: str):
    """Welcome email when a user upgrades to Pro."""
    first = user_name.split()[0] if user_name else "there"
    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": "Welcome to CareerOS Pro 🎉",
            "html": f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0d1117;color:#e5e7eb;padding:32px;border-radius:12px;">
              <div style="text-align:center;margin-bottom:24px;">
                <div style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#2563eb);padding:12px 20px;border-radius:10px;">
                  <span style="font-size:24px;font-weight:700;color:#fff;">CareerOS Pro</span>
                </div>
              </div>
              <h2 style="color:#fff;margin-top:0;">Welcome to Pro, {first}!</h2>
              <p style="color:#d1d5db;">Your subscription is now active. Here's everything unlocked for you:</p>
              <ul style="color:#a78bfa;line-height:2;">
                <li>Unlimited AI resume analyses</li>
                <li>Unlimited application tracking</li>
                <li>AI Job Matches ranked by your resume fit</li>
                <li>Outreach Drafter — personalised cold emails</li>
                <li>AI contact suggestions for networking</li>
                <li>Interview question generator</li>
                <li>Weekly AI strategy insights</li>
                <li>Full analytics &amp; score trends</li>
              </ul>
              <div style="text-align:center;margin-top:28px;">
                <a href="{settings.FRONTEND_URL}/dashboard"
                  style="background:linear-gradient(135deg,#7c3aed,#2563eb);color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">
                  Go to Dashboard →
                </a>
              </div>
              <p style="color:#6b7280;font-size:12px;margin-top:28px;text-align:center;">
                Questions? Reply to this email or chat with us on CareerOS.
              </p>
            </div>
            """,
        })
        logger.info(f"Pro welcome email sent to {to_email}")
    except Exception as e:
        logger.error(f"Pro welcome email failed: {e}")


async def _notify_team_new_subscriber(user_name: str, user_email: str):
    """Notify founder when a new Pro subscriber signs up."""
    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": settings.NOTIFY_EMAIL,
            "subject": f"💰 New Pro subscriber: {user_name or user_email}",
            "html": f"<p><strong>{user_name}</strong> ({user_email}) just subscribed to CareerOS Pro!</p>",
        })
    except Exception:
        pass
