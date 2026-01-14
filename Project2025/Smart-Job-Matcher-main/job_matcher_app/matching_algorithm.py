# matching_algorithm.py
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download NLTK data with more error handling
try:
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    print("Downloading NLTK data...")
    try:
        nltk.download('stopwords')
        nltk.download('wordnet')
        print("NLTK data downloaded successfully.")
    except Exception as e:
        print(f"Failed to download NLTK data: {e}")

class EnhancedMatcher:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )
        
    def preprocess_text(self, text):
        """Clean and preprocess text"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Remove numbers
        text = re.sub(r'\d+', '', text)
        
        # Tokenize and remove stopwords
        tokens = text.split()
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens 
                 if token not in self.stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def extract_skills(self, cv_text):
        """Extract skills from CV text using keyword matching"""
        # Common tech skills dictionary
        tech_skills = {
            'python', 'java', 'javascript', 'html', 'css', 'react', 'angular', 
            'vue', 'node', 'express', 'django', 'flask', 'sql', 'mysql', 
            'postgresql', 'mongodb', 'aws', 'azure', 'docker', 'kubernetes',
            'git', 'linux', 'windows', 'excel', 'word', 'powerpoint', 'access',
            'troubleshooting', 'networking', 'communication', 'leadership',
            'teamwork', 'problem solving', 'data analysis', 'machine learning',
            'ai', 'cybersecurity', 'cloud', 'devops', 'agile', 'scrum'
        }
        
        cv_text_lower = cv_text.lower()
        found_skills = []
        
        for skill in tech_skills:
            if skill in cv_text_lower:
                found_skills.append(skill)
                
        return found_skills
    
    def calculate_match_score(self, cv_text, job_description):
        """Calculate match score using TF-IDF and cosine similarity"""
        # Preprocess texts
        processed_cv = self.preprocess_text(cv_text)
        processed_job = self.preprocess_text(job_description)
        
        if not processed_cv or not processed_job:
            return 0.0
        
        # Creates TF-IDF vectors
        tfidf_matrix = self.vectorizer.fit_transform([processed_cv, processed_job])
        
        # Calculates cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        
        return similarity[0][0] * 100  # Convert to percentage
    
    def match_jobs(self, cv_text, jobs, keyword=None, location=None):
        """Match CV against multiple jobs"""
        results = []
        cv_skills = self.extract_skills(cv_text)
        
        for job in jobs:
            # Apply filters
            if keyword and keyword.lower() not in job.title.lower():
                continue
                
            if location and location.lower() not in job.location.lower():
                continue
            
            # Create job description from title and required skills
            job_description = f"{job.title} {job.required_skills}"
            
            # Add description if it exists
            if hasattr(job, 'description') and job.description:
                job_description += f" {job.description}"
            
            # Calculate match score
            match_score = self.calculate_match_score(cv_text, job_description)
            
            # Extract job skills
            job_skills = [skill.strip().lower() for skill in job.required_skills.split(',')]
            
            # Find matching and missing skills
            skills_matched = [skill for skill in job_skills if skill in cv_skills]
            skills_missing = [skill for skill in job_skills if skill not in cv_skills]
            
            # Boost score based on skill matches
            skill_boost = len(skills_matched) / len(job_skills) * 30 if job_skills else 0
            final_score = min(match_score + skill_boost, 100)
            
            results.append({
                "job": job,
                "match_score": round(final_score, 1),
                "skills_matched": skills_matched,
                "skills_missing": skills_missing,
                "tfidf_score": round(match_score, 1),
                "skill_boost": round(skill_boost, 1)
            })
        
        return sorted(results, key=lambda x: x["match_score"], reverse=True)