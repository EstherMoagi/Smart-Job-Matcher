from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import io
from datetime import datetime
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

# For CV parsing
import fitz  # PyMuPDF for PDFs
from docx import Document  # python-docx for DOCX

# Database models
from models import db, User, UserSkill, Job, JobMatch

# Enhanced matching algorithm
from matching_algorithm import EnhancedMatcher

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///jobmatcher.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize the enhanced matcher
matcher = EnhancedMatcher()
print("Available methods in matcher:", [method for method in dir(matcher) if not method.startswith('_')])
import json
import os
import os
import json

def load_jobs():
    jobs_path = os.path.join(os.path.dirname(__file__), "jobs.json")

    if not os.path.exists(jobs_path):
        return []

    with open(jobs_path, "r") as f:
        return json.load(f)

def smart_match(job, user_keywords, user_location):
    score = 0
  # Skill match

    job_skills = job["required_skills"].lower().split(",")

    for skill in user_keywords:
        if skill.lower() in job_skills:
            score += 30

    return min(score, 100)


    # Location match
    if user_location.lower() in job["location"].lower():
        score += 20

    # Title relevance
    if any(word.lower() in job["title"].lower() for word in user_keywords):
        score += 50

    return score

# -------------------- ROUTES --------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("User already exists with that email.", "danger")
            return render_template("register.html")
        
        # Create new user
        new_user = User(email=email)
        new_user.set_password(password)
        
        # Try to extract name from email
        name_part = email.split('@')[0]
        if '.' in name_part:
            new_user.name = ' '.join([part.capitalize() for part in name_part.split('.')])
        else:
            new_user.name = name_part.capitalize()
            
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["email"] = user.email
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        
        flash("Invalid email or password.", "danger")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    
    # Check if user exists
    if user is None:
        session.clear()
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for("login"))
    
    matched_jobs = []
    skills_gap_image = None
    
    # Get user stats
    total_matches = JobMatch.query.filter_by(user_id=user.id).count()
    recent_matches = JobMatch.query.filter_by(user_id=user.id).order_by(JobMatch.matched_on.desc()).limit(5).all()
    
    if request.method == "POST":
        keyword = request.form.get("keyword", "").lower()
        location = request.form.get("location", "").lower()
        cv_file = request.files.get("cv")
        
        if cv_file and cv_file.filename:
            print(f"Processing CV file: {cv_file.filename}")
            cv_text = extract_cv_text(cv_file)
            print(f"Extracted text length: {len(cv_text)} characters")
            
            # Check what jobs are available
            all_jobs = Job.query.all()
            print(f"Available jobs in database: {len(all_jobs)}")
            for job in all_jobs:
                print(f"Job: {job.title}, Skills: {job.required_skills}")
            
            if not cv_text.strip():
                flash("Could not extract text from the CV file. Please try a different file format.", "warning")
            else:
                matched_jobs = match_jobs(cv_text, keyword, location, user)
                print(f"Found {len(matched_jobs)} matching jobs")
                
                if matched_jobs:
                    skills_gap_image = generate_skills_gap_chart(cv_text, matched_jobs)
                    session["matched_results"] = [{
                        "title": job["title"],
                        "location": job["location"],
                        "company": job.get("company", ""),
                        "match_score": job["match_score"],
                        "skills_matched": job["skills_matched"],
                        "skills_missing": job["skills_missing"]
                    } for job in matched_jobs]
                    flash(f"Found {len(matched_jobs)} matching jobs!", "success")
                else:
                    flash("No matching jobs found. Try different keywords or upload a different CV.", "info")
    
    return render_template("index.html", 
                         matched_jobs=matched_jobs, 
                         skills_gap_image=skills_gap_image,
                         user=user,
                         total_matches=total_matches,
                         recent_matches=recent_matches)
@app.route('/match', methods=['POST'])
def match():
    keywords = request.form.get("keywords").lower().split(",")
    location = request.form.get("location").lower().split(",")

    jobs = load_jobs()  # your job list

    matched_jobs = []

    for job in jobs:
        score = smart_match(job, keywords, location)

        if score > 30:
            job["match_score"] = score
            matched_jobs.append(job)

    # Sort by best match
    matched_jobs = sorted(matched_jobs, key=lambda x: x["match_score"], reverse=True)

    return render_template("results.html", jobs=matched_jobs)


@app.route("/send_report")
def send_report():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    matched_results = session.get("matched_results", [])
    
    if not matched_results:
        flash("No matched results to report.", "warning")
        return redirect(url_for("index"))
    
    report = generate_email_report(user.email, matched_results)
    send_email(user.email, "Your Job Match Report", report)
    flash("Email report sent successfully!", "success")
    return redirect(url_for("index"))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    
    if request.method == "POST":
        user.name = request.form.get("name", user.name)
        user.phone = request.form.get("phone", user.phone)
        user.location = request.form.get("location", user.location)
        
        # Update skills
        skills = request.form.get("skills", "")
        if skills:
            # Clear existing skills
            UserSkill.query.filter_by(user_id=user.id).delete()
            
            # Add new skills
            for skill in skills.split(','):
                skill = skill.strip()
                if skill:
                    user_skill = UserSkill(user_id=user.id, skill_name=skill)
                    db.session.add(user_skill)
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    
    # Get user skills
    user_skills = [skill.skill_name for skill in user.skills]
    
    return render_template("profile.html", user=user, skills=", ".join(user_skills))

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    matches = JobMatch.query.filter_by(user_id=user.id).order_by(JobMatch.matched_on.desc()).all()
    
    # Format history for template
    history = []
    for match in matches:
        history.append({
            "date": match.matched_on.strftime("%Y-%m-%d"),
            "cv_filename": match.cv_filename or "Uploaded CV",
            "matches": [{
                "title": match.job.title,
                "score": match.match_score
            }]
        })
    
    return render_template("history.html", history=history)

# -------------------- HELPERS --------------------

def extract_cv_text(file):
    """Extracts text from uploaded CV based on file type."""
    filename = file.filename.lower()
    file.stream.seek(0) 

    try:
        if filename.endswith(".pdf"):
            try:
                doc = fitz.open(stream=file.read(), filetype="pdf")
                text = " ".join(page.get_text() for page in doc)
                print(f"PDF extracted: {len(text)} characters")
                return text
            except Exception as e:
                print(f"PDF read error: {e}")
                return ""
        
        elif filename.endswith(".docx"):
            try:
                document = Document(file)
                text = " ".join([para.text for para in document.paragraphs])
                print(f"DOCX extracted: {len(text)} characters")
                return text
            except Exception as e:
                print(f"DOCX read error: {e}")
                return ""
        
        elif filename.endswith(".txt"):
            try:
                text = file.read().decode("utf-8", errors="ignore")
                print(f"TXT extracted: {len(text)} characters")
                return text
            except Exception as e:
                print(f"TXT read error: {e}")
                return ""
        
        else:
            print(f"Unsupported file type: {filename}")
            return ""
            
    except Exception as e:
        print(f"General file reading error: {e}")
        return ""

def match_jobs(cv_text, keyword, location, user):
    """Match jobs using enhanced algorithm"""
    # Get all jobs from database
    jobs = Job.query.all()
    
    # Use enhanced matching algorithm
    matched_results = matcher.match_jobs(cv_text, jobs, keyword, location)
    
    results = []
    for match in matched_results:
        job = match["job"]
        results.append({
            "id": job.id,
            "title": job.title,
            "location": job.location,
            "company": job.company,
            "match_score": match["match_score"],
            "skills_matched": match["skills_matched"],
            "skills_missing": match["skills_missing"]
        })
        
        # Save match to database
        job_match = JobMatch(
            user_id=user.id,
            job_id=job.id,
            match_score=match["match_score"],
            cv_filename=request.files.get("cv").filename if request.files.get("cv") else "Unknown",
            skills_matched=",".join(match["skills_matched"]),
            skills_missing=",".join(match["skills_missing"])
        )
        db.session.add(job_match)
    
    db.session.commit()
    return results

def generate_skills_gap_chart(cv_text, matched_jobs):
    cv_words = cv_text.lower().split()
    all_skills = []
    
    for job in matched_jobs:
        all_skills.extend(job["skills_matched"])
        all_skills.extend(job["skills_missing"])
    
    skill_counts = {}
    for skill in set(all_skills):
        skill_counts[skill] = (skill.lower() in cv_words)
    
    labels = list(skill_counts.keys())
    values = [1 if present else 0 for present in skill_counts.values()]
    
    plt.figure(figsize=(10, 4))
    bars = plt.bar(labels, values, color=["green" if v else "red" for v in values])
    plt.xticks(rotation=45)
    plt.ylim(0, 1.2)
    plt.title("Skills Gap Analysis (Green = Present, Red = Missing)")
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f"{'✓' if yval else '✗'}", ha='center', fontsize=12)
    
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close()
    return f"data:image/png;base64,{encoded}"

SKILLS_DB = [
    "python", "sql", "excel", "power bi", "html", "css", "javascript",
    "react", "flask", "django", "machine learning", "data analysis",
    "statistics", "communication", "problem solving"
]

def extract_skills_from_cv(text):
    found = []
    text = text.lower()

    for skill in SKILLS_DB:
        if skill in text:
            found.append(skill.title())

    return list(set(found))
def calculate_skill_gap(required_skills, user_skills):
    missing = [s for s in required_skills if s.lower() not in [u.lower() for u in user_skills]]
    score = (len(required_skills) - len(missing)) / len(required_skills) * 100
    return missing, round(score)


def create_skill_chart(score):
    plt.figure(figsize=(5,4))
    plt.bar(["Skill Match"], [score])
    plt.ylim(0, 100)

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode()

    plt.close()
    return base64_img

def generate_email_report(user_email, matched_jobs):
    if not matched_jobs:
        return "No matches found."
    
    report = f"Hi {user_email},\n\nHere are your job match results:\n\n"
    for job in matched_jobs:
        report += f"- {job['title']} at {job.get('company', 'Unknown')} in {job['location']} (Match Score: {job['match_score']}%)\n"
    
    report += "\nBest regards,\nSmart Job Matcher Team"
    return report

def send_email(to_email, subject, body):
   
    print(f"Sending email to {to_email}...\nSubject: {subject}\n\n{body}")
    
@app.route("/skills-gap", methods=["GET", "POST"])
def skills_gap():
    jobs = load_jobs()

    if request.method == "POST":
        selected_title = request.form.get("job_title")
        cv_text = request.form.get("cv_text")

        # find selected job
        job = next((j for j in jobs if j["title"] == selected_title), None)

        if not job:
            return "Job not found"

        required_skills = job["required_skills"].split(",")

        user_skills = extract_skills_from_cv(cv_text)
        missing_skills, score = calculate_skill_gap(required_skills, user_skills)
        chart = create_skill_chart(score)

        return render_template(
            "skills_gap.html",
            jobs=jobs,
            selected_job=selected_title,
            required_skills=required_skills,
            user_skills=user_skills,
            missing_skills=missing_skills,
            score=score,
            chart=chart
        )

    return render_template("skills_gap.html", jobs=jobs)


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

## User dashboard


@app.route("/dashboard")
def dashboard():
    
    user_email = "student@example.com"

    stats = {
        "jobs_matched": 3,
        "last_login": "2026-01-14"
    }

    is_admin = True  

    return render_template(
        "dashboard.html",
        user_email=user_email,
        stats=stats,
        is_admin=is_admin
    )

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    is_admin = True 

    if not is_admin:
        return "Access denied", 403

    jobs = load_jobs()

    if request.method == "POST":
        title = request.form.get("title")
        skills = request.form.get("skills")

        jobs.append({
            "title": title,
            "required_skills": skills
        })

        # Save back to JSON
        with open("jobs.json", "w") as f:
            
            json.dump(jobs, f, indent=2)

    return render_template("admin.html", jobs=jobs)

# Health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}


def test_matcher():
    """Test the enhanced matcher with actual database jobs"""
    test_cv = """
    Esther Moagi
    IT Student with experience in Python, Microsoft Office, Excel, and communication skills.
    Worked as Computer Literacy Assistant helping students with computer systems.
    Proficient in troubleshooting, teamwork, and networking.
    """
    
    # Get real jobs from database
    with app.app_context():
        jobs = Job.query.all()
        
        if not jobs:
            print("No jobs in database. Please run init_db.py first.")
            return
        
        print(f"Testing with {len(jobs)} real jobs from database:")
        for job in jobs:
            print(f"  - {job.title}: {job.required_skills}")
        
        try:
            
            if hasattr(matcher, 'match_jobs'):
                results = matcher.match_jobs(test_cv, jobs, None, None)
                print(f"\nTest results: {len(results)} matches")
                for result in results:
                    job = result['job']
                    print(f"Job: {job.title} at {job.company}")
                    print(f"  Score: {result['match_score']}%")
                    print(f"  Skills matched: {', '.join(result['skills_matched'])}")
                    print(f"  Skills missing: {', '.join(result['skills_missing'])}")
                    print()
            else:
                print("Error: matcher doesn't have match_jobs method")
                print("Available methods:", [method for method in dir(matcher) if not method.startswith('_')])
                
        except Exception as e:
            print(f"Matcher test failed: {e}")
            import traceback
            traceback.print_exc()
if __name__ == "__main__":
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Test the matcher
    print("Testing matcher...")
    test_matcher()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')