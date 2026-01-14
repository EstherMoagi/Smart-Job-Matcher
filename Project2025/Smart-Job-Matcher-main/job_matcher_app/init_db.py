# init_db.py
from app import app, db
from models import User, Job, UserSkill
from datetime import datetime

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Add sample jobs if none exists
    if Job.query.count() == 0:
        sample_jobs = [
            Job(
                title="Software Engineer", 
                company="Tech Solutions Inc.", 
                location="Cape Town", 
                required_skills="Python,Flask,SQL,Git"
            ),
            Job(
                title="Data Analyst", 
                company="Data Insights Ltd.", 
                location="Johannesburg", 
                required_skills="Excel,SQL,PowerBI,Python"
            ),
            Job(
                title="Web Developer", 
                company="WebCraft Studios", 
                location="Cape Town", 
                required_skills="HTML,CSS,JavaScript,React"
            ),
            Job(
                title="Cybersecurity Intern", 
                company="SecureNet Systems", 
                location="Durban", 
                required_skills="Networking,Python,Linux,Security"
            ),
            Job(
                title="IT Support Technician", 
                company="IT Helpdesk Solutions", 
                location="Pretoria", 
                required_skills="Troubleshooting,Windows,Networking,Communication"
            ),
        ]
        db.session.bulk_save_objects(sample_jobs)
        db.session.commit()
        print("Sample jobs added!")

    #  sample user 
    if User.query.count() == 0:
        user = User(
            email="2021390741@ufs4life.ac.za",
            name="Esther Moagi",
            phone="078 730 8904",
            location="Tshepisong West, Roodepoort, 1754"
        )
        user.set_password("password123")  
        
        # First commit the user to get an ID
        db.session.add(user)
        db.session.commit()
        print(f"User created with ID: {user.id}")
        
        #  adds user skills with the proper user_id
        skills = [
            "Python", "Microsoft Office", "Communication", 
            "Leadership", "Teamwork", "Problem Solving"
        ]
        
        for skill in skills:
            user_skill = UserSkill(user_id=user.id, skill_name=skill)
            db.session.add(user_skill)
        
        db.session.commit()
        print("User skills added!")
    
    print("Database initialized successfully!")