import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("z9pay_vtu_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()