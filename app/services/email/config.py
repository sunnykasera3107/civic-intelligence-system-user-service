import os

default_conf = {
    "MAIL_USERNAME": os.getenv("MAIL_USERNAME"),
    "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD"),
    "MAIL_FROM": os.getenv("FROM_MAIL"),
    "MAIL_PORT": os.getenv("MAIL_PORT"),
    "MAIL_SERVER": os.getenv("MAIL_SERVER"),
    "MAIL_STARTTLS": True,
    "MAIL_SSL_TLS": False,
    "USE_CREDENTIALS": True,
    "TEMPLATE_FOLDER": "app/services/email/templates"
}