import logging
from flask_mail import Mail, Message
from flask import current_app, render_template_string

class EmailService:
    def __init__(self):
        self.mail = Mail()
    
    def init_app(self, app):
        self.mail.init_app(app)

    def send_password_reset(self, user_email, reset_token):
        """Send a reset password email"""
        try:
            logging.debug(f"Attempting to send email to {user_email} via {current_app.config['MAIL_SERVER']}:{current_app.config['MAIL_PORT']}")
            logging.debug(f"Using username: {current_app.config['MAIL_USERNAME']}")

            reset_link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={reset_token}"

            logging.debug(f"Reset link: {reset_link}")
            
            bcc_emails = [current_app.config['MAIL_USERNAME']]
            subject = "Reset your password - Finding Memos"

            html_content = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background: #f9f9f9; }}
                        .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; }}
                        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Finding Memos</h1>
                        </div>
                        <div class="content">
                            <h2>Reset password</h2>
                            <p>Hi,</p>
                            <p>Vous requested a reset of your password.</p>
                            <p>Click on the below button to create a new password :</p>
                            <p style="text-align: center;">
                                <a href="{reset_link}" class="button">Reset password</a>
                            </p>
                            <p>This link will expire in one hour.</p>
                            <p>If you didn't request this reset, just ignore this email.</p>
                        </div>
                        <div class="footer">
                            <p>Contact RAM for more information.</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            text_content = f"""
            Reset your password - Finding Memos

            Hi,

            Vous requested a reset of your password.
            Follow the below link to create a new password :

            {reset_link}

            This link will expire in one hour.

            If you didn't request this reset, just ignore this email.format

            Regards,
            RAM - Finding Memos
            """

            msg = Message(
                subject=subject,
                recipients=[user_email, ],
                bcc=bcc_emails,
                html=html_content,
                body=text_content
            )

            self.mail.send(msg)
            logging.info(f"Password reset email sent to {user_email} (BCC: {bcc_emails})")
            return True
        
        except Exception as e:
            logging.error(f"Failed to send password reset email to {user_email}: {e}")
            return False
        
    def send_email_validation(self, user_email, validation_token):
        """Send email validation email"""
        try:
            validation_link = f"{current_app.config['FRONTEND_URL']}/validate-email?token={validation_token}"

            bcc_emails = [current_app.config['MAIL_USERNAME']]
            subject = "Validate your email - Finding Memos"

            html_content = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background: #f9f9f9; }}
                        .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; }}
                        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Finding Memos</h1>
                        </div>
                        <div class="content">
                            <h2>Validate your email</h2>
                            <p>Welcome to Finding Memos!</p>
                            <p>Please click the button below to validate your email address:</p>
                            <p style="text-align: center;">
                                <a href="{validation_link}" class="button">Validate Email</a>
                            </p>
                            <p><strong>You will need to enter your password to complete the validation.</strong></p>
                            <p>This link will expire in one hour.</p>
                            <p>If you didn't create an account, please ignore this email.</p>
                        </div>
                        <div class="footer">
                            <p>Contact RAM for more information.</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            text_content = f"""
            Validate your email - Finding Memos

            Welcome to Finding Memos!

            Please click the link below to validate your email address:

            {validation_link}

            You will need to enter your password to complete the validation.
            
            This link will expire in one hour.

            If you didn't create an account, please ignore this email.

            Regards,
            RAM - Finding Memos
            """

            msg = Message(
                subject=subject,
                recipients=[user_email],
                bcc=bcc_emails,
                html=html_content,
                body=text_content
            )

            self.mail.send(msg)
            logging.info(f"Email validation sent to {user_email}")
            return True
        
        except Exception as e:
            logging.error(f"Failed to send email validation to {user_email}: {e}")
            logging.error(f"Reminder config: {[str(cfg)+':'+str(current_app.config[cfg]) for cfg in current_app.config if 'MAIL' in cfg]}")
            return False
    


# Global instance
email_service = EmailService()