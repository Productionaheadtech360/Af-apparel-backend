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


def upgrade() -> None:
    op.execute("""
        INSERT INTO email_templates 
        (id, trigger_event, name, subject, body_html, body_text, is_active, available_variables, created_at, updated_at)
        SELECT 
            gen_random_uuid(),
            t.trigger_event, t.name, t.subject, t.body_html, t.body_text, true, t.available_variables, NOW(), NOW()
        FROM (VALUES
            (
                'order_confirmation',
                'Order Confirmation', 
                'Order Confirmed — {{ order_number }}',
                '<h1>Thanks {{ first_name }}!</h1><p>Order <b>{{ order_number }}</b> received.</p><p>Total: {{ order_total }}</p><p><a href="{{ order_url }}">View Order</a></p><p>— AF Apparels</p>',
                'Order {{ order_number }} confirmed. Total: {{ order_total }}.',
                '["first_name","order_number","order_total","order_url","items"]'
            ),
            (
                'password_reset',
                'Password Reset',
                'Reset Your AF Apparels Password',
                '<h1>Password Reset</h1><p>Hi {{ first_name }},</p><p><a href="{{ reset_url }}" style="background:#E8242A;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;">Reset Password</a></p><p>Expires in {{ expiry_hours }} hour(s).</p><p>— AF Apparels</p>',
                'Hi {{ first_name }}, reset here: {{ reset_url }} (expires {{ expiry_hours }}hr)',
                '["first_name","reset_url","expiry_hours"]'
            ),
            (
                'wholesale_application_received',
                'Wholesale Application Received',
                'Application Received — {{ company_name }}',
                '<h1>Application Received!</h1><p>Hi {{ first_name }},</p><p>We received your application for <b>{{ company_name }}</b>. Our team will review within 1-2 business days.</p><p>— AF Apparels</p>',
                'Hi {{ first_name }}, application for {{ company_name }} received.',
                '["first_name","company_name"]'
            )
        ) AS t(trigger_event, name, subject, body_html, body_text, available_variables)
        WHERE NOT EXISTS (
            SELECT 1 FROM email_templates WHERE email_templates.trigger_event = t.trigger_event
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM email_templates 
        WHERE trigger_event IN ('order_confirmation', 'password_reset', 'wholesale_application_received')
    """)