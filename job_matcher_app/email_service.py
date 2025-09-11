# email_service.py
from flask_mail import Mail, Message
from flask import current_app
import os

mail = Mail()

def init_email_service(app):
    """Initialize email service with configuration"""
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', '')
    
    mail.init_app(app)

def send_email(to_email, subject, body, html_body=None):
    """Send email with both plain text and HTML versions"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body,
            html=html_body
        )
        
        mail.send(msg)
        current_app.logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def generate_job_report_email(user, matched_jobs):
    """Generate HTML email content for job matches"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #4e73df 0%, #6f42c1 100%); 
                     color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .job-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; }}
            .match-score {{ font-weight: bold; color: #1cc88a; }}
            .skills {{ margin: 10px 0; }}
            .skill-match {{ color: #1cc88a; }}
            .skill-missing {{ color: #e74a3b; }}
            .footer {{ background: #f8f9fc; padding: 15px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Your Job Match Report</h2>
            <p>Hello {user.name}, here are your personalized job matches</p>
        </div>
        
        <div class="content">
            <h3>Found {len(matched_jobs)} Matching Jobs</h3>
    """
    
    for job in matched_jobs:
        html_content += f"""
            <div class="job-card">
                <h4>{job['title']} at {job.get('company', 'Unknown Company')}</h4>
                <p><strong>Location:</strong> {job['location']}</p>
                <p><strong>Match Score:</strong> <span class="match-score">{job['match_score']}%</span></p>
                
                <div class="skills">
                    <strong>Skills Matched:</strong>
                    <span class="skill-match">{', '.join(job['skills_matched'])}</span>
                </div>
                
                <div class="skills">
                    <strong>Skills to Improve:</strong>
                    <span class="skill-missing">{', '.join(job['skills_missing'])}</span>
                </div>
            </div>
        """
    
    html_content += """
        </div>
        
        <div class="footer">
            <p>Best regards,<br>Smart Job Matcher Team</p>
            <p><small>This is an automated message. Please do not reply.</small></p>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_content = f"Hello {user.name},\n\nHere are your job match results:\n\n"
    for job in matched_jobs:
        text_content += f"- {job['title']} at {job.get('company', 'Unknown')} in {job['location']} "
        text_content += f"(Match Score: {job['match_score']}%)\n"
        text_content += f"  Skills you have: {', '.join(job['skills_matched'])}\n"
        text_content += f"  Skills to learn: {', '.join(job['skills_missing'])}\n\n"
    
    text_content += "\nBest regards,\nSmart Job Matcher Team"
    
    return text_content, html_content