import os
import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from .config import default_conf

logger = logging.getLogger(__name__)

async def send_email(subject: str, recipients: list, body_arg: dict, template: str) -> bool:
    """
    Send email asynchronously.
    
    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        body_arg: Template variables dictionary
        template: Template filename
        
    Returns:
        bool: True if email sent successfully
        
    Raises:
        HTTPException: If email sending fails
    """
    try:
        print(template)
        # Build config
        from_email = {"MAIL_FROM": f"Civic Intelligence System <{os.getenv("FROM_MAIL")}>"}
        updated_conf = default_conf | from_email
        
        # Validate required config
        if not os.getenv("FROM_MAIL"):
            logger.warning("FROM_MAIL environment variable not set")
        
        # Create message
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=body_arg,
            subtype="html"
        )
        
        # Send email
        conf = ConnectionConfig(**updated_conf)
        fm = FastMail(conf)
        await fm.send_message(message, template_name=template)
        
        logger.info(f"Email sent successfully to {recipients}")
        return True
        
    except ConnectionError as e:
        logger.error(f"Email service connection error: {str(e)}")
        return False
    except ValueError as e:
        logger.error(f"Email configuration error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected email error: {str(e)}", exc_info=True)
        return False