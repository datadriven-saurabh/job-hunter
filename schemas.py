from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator

# ==========================================
# ENUMS
# ==========================================

class ApplicationClassification(str, Enum):
    HEADLESS_AUTO = "HEADLESS_AUTO"
    HUMAN_IN_THE_LOOP_LINK = "HUMAN_IN_THE_LOOP_LINK"

class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    MATCHED = "MATCHED"
    QUEUED = "QUEUED"
    TAILORED = "TAILORED"
    APPLIED = "APPLIED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    OFFER = "OFFER"

class ExecutionResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_HUMAN = "NEEDS_HUMAN"

# ==========================================
# USER PROFILE & STATIC INPUTS
# ==========================================

class PersonalDetails(BaseModel):
    @field_validator("full_name", "phone", "location", "work_authorization")
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError("This field is required")
        return value.strip()

    full_name: str = Field(..., description="Full legal name")
    email: EmailStr = Field(..., description="Primary contact email")
    phone: str = Field(..., description="Phone number with country code")
    location: str = Field(..., description="City, State, Country")
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    work_authorization: str = Field(..., description="e.g., US Citizen, EU Visa, H1B")

class ExperienceItem(BaseModel):
    @field_validator('start_date','end_date')
    @classmethod
    def valid_month(cls,value,info):
        if info.field_name=='end_date' and value=='Present': return value
        import re
        if not re.fullmatch(r'(19[5-9][0-9]|20[0-9]{2}|2100)-(0[1-9]|1[0-2])',value): raise ValueError('Choose a valid month and year.')
        return value

    @model_validator(mode='after')
    def chronological(self):
        if self.end_date!='Present' and self.end_date<self.start_date: raise ValueError('End date must be on or after start date.')
        return self

    company: str
    role: str
    start_date: str  # Format: YYYY-MM
    end_date: str    # Format: YYYY-MM or Present
    bullet_points: List[str]

class EducationItem(BaseModel):
    @field_validator('graduation_year')
    @classmethod
    def valid_year(cls,value):
        if not value.isdigit() or not 1950<=int(value)<=datetime.now().year+10: raise ValueError('Choose a valid graduation year.')
        return value

    institution: str
    degree: str
    field_of_study: str
    graduation_year: str

class EEODemographics(BaseModel):
    gender: Optional[str] = "Prefer not to say"
    race_ethnicity: Optional[str] = "Prefer not to say"
    veteran_status: Optional[str] = "Prefer not to say"
    disability_status: Optional[str] = "Prefer not to say"

class BaseResume(BaseModel):
    @field_validator("structured_skills")
    @classmethod
    def clean_skills(cls, values):
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))

    raw_text: str
    structured_skills: List[str]
    experience_history: List[ExperienceItem]
    education: List[EducationItem]

class UserProfile(BaseModel):
    user_id: str
    personal_details: PersonalDetails
    base_resume: BaseResume
    eeo_demographics: Optional[EEODemographics] = None

# ==========================================
# SYSTEM STRATEGY CONFIGURATION
# ==========================================

class JobSearchCriteria(BaseModel):
    @field_validator("target_roles", "target_locations", "employment_types", "dealbreaker_keywords", "required_stack_keywords")
    @classmethod
    def clean_terms(cls, values):
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))

    target_roles: List[str]
    target_locations: List[str]
    employment_types: List[str] = ["Full-time"]
    min_salary_threshold: Optional[int] = None
    dealbreaker_keywords: List[str] = []
    required_stack_keywords: List[str] = []

class ExecutionPreferences(BaseModel):
    auto_apply_threshold_score: float = Field(default=0.85, ge=0.0, le=1.0)
    max_daily_applications: int = Field(default=20, ge=1, le=200)
    enable_headless_auto_apply: bool = False
    human_in_the_loop_fallback: bool = True

class LLMProviderConfig(BaseModel):
    @field_validator("local_ollama_base_url")
    @classmethod
    def loopback_only(cls, value):
        from urllib.parse import urlparse
        parsed=urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("The local model URL must use a loopback address.")
        return value

    primary_model: str = "gemini-2.5-flash"
    reasoning_model: str = "qwen3:4b"
    local_ollama_base_url: str = "http://localhost:11434"

class SystemVariables(BaseModel):
    job_search_criteria: JobSearchCriteria
    execution_preferences: ExecutionPreferences
    llm_provider_config: LLMProviderConfig

# ==========================================
# DYNAMIC APPLICATION & RUNTIME STATE
# ==========================================

class SubmissionLog(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    result: ExecutionResult
    error_message: Optional[str] = None

class ApplicationRecord(BaseModel):
    job_id: str
    company_name: str
    job_title: str
    job_url: str
    match_score: float
    classification: ApplicationClassification
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    tailored_resume_path: Optional[str] = None
    tailored_cover_letter_path: Optional[str] = None
    extracted_form_fields: Optional[Dict[str, Any]] = None
    submission_logs: List[SubmissionLog] = []

# ==========================================
# INTERVIEW COACHING SCHEMAS
# ==========================================

class InterviewQuestion(BaseModel):
    id: str
    category: str  # Behavioral, Technical, System Design
    question: str
    evaluation_criteria: List[str]

class UserAnswerFeedback(BaseModel):
    question_id: str
    score: float = Field(..., ge=0.0, le=10.0)
    strengths: List[str]
    missing_elements: List[str]
    improved_answer_suggestion: str

