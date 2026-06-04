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
              <p><a href="https://careeros.ai/applications" style="background: #7c3aed; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">
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
    insights_html = "".join([
        f"<li><strong>{i.get('title')}</strong>: {i.get('summary')}</li>"
        for i in new_insights[:3]
    ])

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": to_email,
            "subject": f"Your CareerOS Weekly Intelligence Report",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
              <h1>Weekly Intelligence Report</h1>
              <p>Hi {user_name},</p>
              <h2>Career Health: {career_health_score}/100</h2>
              <p>You submitted {week_apps} applications this week.
              {follow_ups_due} follow-ups are due.</p>
              {"<h3>New Insights</h3><ul>" + insights_html + "</ul>" if new_insights else ""}
              <p><a href="https://careeros.ai/dashboard" style="background: #7c3aed; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">
                View Full Report
              </a></p>
            </div>
            """,
        })
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
              <p><a href="https://careeros.ai/resume" style="background: #7c3aed; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">
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
              <a href="https://careeros.ai/resume/{resume_id}/analysis"
                style="display:inline-block;background:#7c3aed;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:8px;">
                View Full Analysis & Fix Guide →
              </a>
              <p style="color:#6b7280;font-size:12px;margin-top:24px;">
                Once you update your resume, re-upload it to see your new score.
                <a href="https://careeros.ai/unsubscribe" style="color:#6b7280;">Unsubscribe</a>
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
