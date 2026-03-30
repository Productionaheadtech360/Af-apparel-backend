"""Celery application instance."""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "afapparel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.quickbooks_tasks",
        "app.tasks.pricelist_tasks",
        "app.tasks.inventory_tasks",
        "app.tasks.cart_tasks",
    ],
)

celery_app.config_from_object("celeryconfig")

if __name__ == "__main__":
    celery_app.start()
