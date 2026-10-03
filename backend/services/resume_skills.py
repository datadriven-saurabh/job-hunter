"""Extract supported skills and literal skills-section phrases, without an AI call."""
import re

HEADINGS = {'skills', 'technical skills', 'core skills', 'key skills', 'core competencies',
            'competencies', 'tools', 'tools and technologies', 'skills and expertise'}
BOUNDARIES = {'summary', 'professional summary', 'profile', 'experience', 'work experience',
              'professional experience', 'education', 'certifications', 'languages',
              'projects', 'achievements', 'interests', 'publications'}
NEGATED = re.compile(r'\b(?:not|never|no experience|without experience|want to learn|plan to learn|currently learning|beginner in)\b', re.I)

def merge_skills(*groups):
    result={}
    for group in groups:
        for value in group:
            term=re.sub(r'\s+', ' ', value).strip(' \t•●▪*–—-')
            if term:result.setdefault(term.casefold(), term)
    return list(result.values())

def extract_skills(raw):
    from backend.services.job_matching import affirmed_skills, detected
    terms=sorted(affirmed_skills(raw));in_skills=False
    for original in raw.splitlines():
        line=original.strip().strip('•●▪* ').strip()
        heading,sep,rest=line.partition(':')
        key=heading.strip().casefold()
        if key in HEADINGS:
            in_skills=True;line=rest.strip() if sep else ''
        elif key in BOUNDARIES:
            in_skills=False;continue
        if not in_skills or not line or NEGATED.search(line):continue
        for phrase in re.split(r'[,;|•●▪]|\s+[–—]\s+',line):
            phrase=phrase.strip(' .\t')
            if 1<len(phrase)<=80 and len(phrase.split())<=6 and not re.search(r'https?://|@|\d{4}\s*[-–]',phrase):
                if len(detected(phrase))<=1:terms.append(phrase)
    return merge_skills(terms)[:100]
