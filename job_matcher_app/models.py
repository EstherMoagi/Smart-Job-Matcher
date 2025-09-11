# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    skills = db.relationship('UserSkill', backref='user', lazy=True)
    matches = db.relationship('JobMatch', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    
    def update_login_time(self):
        self.last_login = datetime.utcnow()
        # Don't commit here, let the calling code handle the commit
class UserSkill(db.Model):
    __tablename__ = 'user_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.Integer, default=1)  # 1-5 scale

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    required_skills = db.Column(db.Text)  # Comma-separated skills
    
    # Relationships
    matches = db.relationship('JobMatch', backref='job', lazy=True)

class JobMatch(db.Model):
    __tablename__ = 'job_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    match_score = db.Column(db.Float, nullable=False)
    matched_on = db.Column(db.DateTime, default=datetime.utcnow)
    cv_filename = db.Column(db.String(200))
    
    # Additional match details
    skills_matched = db.Column(db.Text)  # Comma-separated list
    skills_missing = db.Column(db.Text)  # Comma-separated list