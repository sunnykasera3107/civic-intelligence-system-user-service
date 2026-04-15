import os

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import HTTPException

from .config import default_conf


async def send_email(subject, recipients, body_arg, template):

    from_email = {
        "MAIL_FROM": os.getenv("FROM_MAIL") # If you want to send email from different account everytime.
    }

    updated_conf = default_conf | from_email 

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        template_body=body_arg,
        subtype="html"
    )

    try:
        conf = ConnectionConfig(**updated_conf)
        fm = FastMail(conf)
        await fm.send_message(message,  template_name=template)
    except ConnectionRefusedError as e:
        raise HTTPException(
            status_code=400, 
            detail="Email server connection refused"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=str(e)
        )