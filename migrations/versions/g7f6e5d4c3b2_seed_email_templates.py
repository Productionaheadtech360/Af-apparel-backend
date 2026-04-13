"""seed email templates

Revision ID: g7f6e5d4c3b2
Revises: f6e5d4c3b2a1
Create Date: 2026-04-13
"""
from alembic import op

revision = 'g7f6e5d4c3b2'
down_revision = 'f6e5d4c3b2a1'
branch_labels = None
depends_on = None

# All valid trigger_event enum values that have corresponding Celery tasks
_EVENTS = [
    'order_confirmation',
    'password_reset',
    'wholesale_approved',
    'wholesale_rejected',
    'email_verification',
    'user_invitation',
    'rma_approved',
    'rma_rejected',
    'payment_failed',
    'welcome',
]


def upgrade() -> None:
    # Cast text literals to the email_trigger_event enum so PostgreSQL accepts them.
    # WHERE NOT EXISTS makes this idempotent on re-runs.
    op.execute("""
        INSERT INTO email_templates
        (id, trigger_event, name, subject, body_html, body_text, is_active, available_variables, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            t.trigger_event::email_trigger_event,
            t.name,
            t.subject,
            t.body_html,
            t.body_text,
            true,
            t.available_variables,
            NOW(),
            NOW()
        FROM (VALUES
            (
                'order_confirmation',
                'Order Confirmation',
                'Order Confirmed — {{ order_number }}',
                '<h2 style="color:#2A2830;font-family:sans-serif">Thanks {{ first_name }}!</h2><p>Order <strong>{{ order_number }}</strong> has been received.</p><p>Total: <strong>{{ order_total }}</strong></p><p><a href="{{ order_url }}" style="background:#1A5CFF;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block">View Order</a></p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Order {{ order_number }} confirmed. Total: {{ order_total }}. View: {{ order_url }}',
                '["first_name","order_number","order_total","order_url","items"]'
            ),
            (
                'password_reset',
                'Password Reset',
                'Reset Your AF Apparels Password',
                '<h2 style="color:#2A2830;font-family:sans-serif">Password Reset</h2><p>Hi {{ first_name or name }},</p><p>Click below to reset your password. This link expires in {{ expiry_hours or 1 }} hour(s).</p><p><a href="{{ reset_url }}" style="background:#E8242A;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block">Reset Password</a></p><p>If you did not request a reset, ignore this email.</p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Hi {{ first_name or name }}, reset your password here: {{ reset_url }} (expires {{ expiry_hours or 1 }}hr)',
                '["first_name","name","reset_url","expiry_hours"]'
            ),
            (
                'wholesale_approved',
                'Wholesale Application Approved',
                'Your Wholesale Account is Approved — {{ company_name }}',
                '<h2 style="color:#2A2830;font-family:sans-serif">Welcome to AF Apparels!</h2><p>Hi {{ contact_name }},</p><p>Great news — <strong>{{ company_name }}</strong>''s wholesale account has been approved.</p><p>You can now log in to browse our full catalogue and place orders.</p><p><a href="https://afapparels.com/login" style="background:#1A5CFF;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block">Log In to Your Account</a></p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Hi {{ contact_name }}, your wholesale account for {{ company_name }} has been approved. Log in to start ordering.',
                '["contact_name","company_name","login_url"]'
            ),
            (
                'wholesale_rejected',
                'Wholesale Application — Update',
                'Update on Your AF Apparels Application',
                '<h2 style="color:#2A2830;font-family:sans-serif">Application Update</h2><p>Hi {{ contact_name }},</p><p>Thank you for applying to AF Apparels Wholesale. After reviewing your application for <strong>{{ company_name }}</strong>, we''re unable to approve it at this time.</p>{% if reason %}<p><strong>Reason:</strong> {{ reason }}</p>{% endif %}<p>If you have questions, please contact us at info@afapparels.com.</p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Hi {{ contact_name }}, we were unable to approve the application for {{ company_name }} at this time.{% if reason %} Reason: {{ reason }}{% endif %}',
                '["contact_name","company_name","reason"]'
            ),
            (
                'email_verification',
                'Verify Your Email Address',
                'Verify Your AF Apparels Email',
                '<h2 style="color:#2A2830;font-family:sans-serif">Verify Your Email</h2><p>Hi {{ name }},</p><p>Please verify your email address to complete your AF Apparels account setup.</p><p><a href="{{ verify_url }}" style="background:#1A5CFF;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block">Verify Email</a></p><p>If you did not create an account, ignore this email.</p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Hi {{ name }}, verify your email here: {{ verify_url }}',
                '["name","verify_url"]'
            ),
            (
                'user_invitation',
                'You Have Been Invited',
                'You''ve Been Invited to {{ company_name }}''s AF Apparels Account',
                '<h2 style="color:#2A2830;font-family:sans-serif">You''re Invited!</h2><p>Hi {{ name }},</p><p>You have been invited to join <strong>{{ company_name }}</strong>''s wholesale account on AF Apparels.</p><p><a href="{{ invite_url }}" style="background:#1A5CFF;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block">Accept Invitation</a></p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Hi {{ name }}, you have been invited to {{ company_name }}''s AF Apparels account. Accept here: {{ invite_url }}',
                '["name","company_name","invite_url"]'
            ),
            (
                'rma_approved',
                'RMA Approved',
                'Your Return Request {{ rma_number }} Has Been Approved',
                '<h2 style="color:#2A2830;font-family:sans-serif">RMA Approved</h2><p>Your return request <strong>{{ rma_number }}</strong> has been approved.</p>{% if resolution_notes %}<p><strong>Notes:</strong> {{ resolution_notes }}</p>{% endif %}<p>Our team will follow up with return shipping instructions.</p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Your return request {{ rma_number }} has been approved.{% if resolution_notes %} Notes: {{ resolution_notes }}{% endif %}',
                '["rma_number","status","resolution_notes"]'
            ),
            (
                'rma_rejected',
                'RMA Update',
                'Update on Your Return Request {{ rma_number }}',
                '<h2 style="color:#2A2830;font-family:sans-serif">RMA Update</h2><p>We were unable to approve your return request <strong>{{ rma_number }}</strong>.</p>{% if resolution_notes %}<p><strong>Notes:</strong> {{ resolution_notes }}</p>{% endif %}<p>Please contact us at info@afapparels.com if you have questions.</p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Update on return request {{ rma_number }}: unable to approve.{% if resolution_notes %} Notes: {{ resolution_notes }}{% endif %}',
                '["rma_number","status","resolution_notes"]'
            ),
            (
                'payment_failed',
                'Payment Failed',
                'Action Required: Payment Failed for Order {{ order_number }}',
                '<h2 style="color:#2A2830;font-family:sans-serif">Payment Failed</h2><p>We were unable to process the payment for order <strong>{{ order_number }}</strong> ({{ total }}).</p><p>Please update your payment details to avoid delays.</p><p><a href="{{ retry_url }}" style="background:#E8242A;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block">Retry Payment</a></p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Payment failed for order {{ order_number }} ({{ total }}). Retry here: {{ retry_url }}',
                '["order_number","total","retry_url"]'
            ),
            (
                'welcome',
                'Welcome to AF Apparels',
                'Welcome to AF Apparels Wholesale',
                '<h2 style="color:#2A2830;font-family:sans-serif">Welcome, {{ name }}!</h2><p>Your AF Apparels wholesale account is ready. Log in to browse our full catalogue.</p><p><a href="https://afapparels.com/login" style="background:#1A5CFF;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block">Go to Your Account</a></p><p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>',
                'Welcome {{ name }}! Your AF Apparels wholesale account is ready.',
                '["name","login_url"]'
            )
        ) AS t(trigger_event, name, subject, body_html, body_text, available_variables)
        WHERE NOT EXISTS (
            SELECT 1 FROM email_templates
            WHERE email_templates.trigger_event = t.trigger_event::email_trigger_event
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM email_templates
        WHERE trigger_event IN (
            'order_confirmation',
            'password_reset',
            'wholesale_approved',
            'wholesale_rejected',
            'email_verification',
            'user_invitation',
            'rma_approved',
            'rma_rejected',
            'payment_failed',
            'welcome'
        )
    """)
