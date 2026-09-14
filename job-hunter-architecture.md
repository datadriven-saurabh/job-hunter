Here is the complete, unified **`ARCHITECTURE.md`** file formatted as a single, contiguous Markdown document. You can save this directly into your project root as `ARCHITECTURE.md` to provide full, un-truncated context for your coding agent (Cursor, Claude Code, Windsurf, etc.).

```markdown
# Job Hunter: Complete System Architecture & Code Specification

> **Instructions for Autonomous Coding Agent:**  
> This file is the single source of truth for `Job Hunter`.
> Build the platform modularly according to the directory structure in Section 7. Implement all Pydantic schemas, database tables, FastAPI API endpoints, Chrome extension scripts, and agent orchestrators exactly as specified below.

---

## 1. System Overview & Architecture

`Job Hunter` is a localized, privacy-first career automation platform. It uses an **Orchestrator-Worker Pattern** implemented via **LangGraph** in Python. Tasks are isolated across specialized agents to manage state, evaluate job descriptions, tailor resumes, handle applications, and run interactive interview prep.


```

```
                            +-----------------------------+
                            |      Orchestrator Agent     |
                            |   (LangGraph State Machine) |
                            +--------------+--------------+
                                           |
     +------------------+------------------+------------------+------------------+
     |                  |                  |                  |                  |

```

+------v-------+   +------v-------+   +------v-------+   +------v-------+   +------v-------+
|  Scout Agent |   | Classifier   |   | Tailor Agent |   | Apply Agent  |   | Coach Agent  |
|  (Job Discovery) |   | Agent (Triage)|   | (Resume/CL)  |   | (Headless &  |   | (Interview)  |
+--------------+   +--------------+   +--------------+   | Extension)   |   +--------------+
+--------------+
| (On 3+ Failures)
+------v-------+
| [Optional]   |
| Meta-Agent   |
| (Self-Patch) |
+--------------+

```

---

## 2. Agent Roles & Specifications

### 2.1 Scout Agent (Job Discovery & Matching)
* **Objective:** Searches and ingests job postings from public feeds, company portals, and target job board APIs.
* **Logic:** Calculates vector similarity between candidate skills and job requirements. Automatically filters out postings that match user-defined dealbreaker keywords or location constraints.

### 2.2 Classifier Agent (Application Triage)
* **Objective:** Segregates incoming job opportunities into **Headless Auto-Apply** vs. **Human-in-the-Loop (HITL)**.
* **Triage Rules:**
  * **Headless Auto-Apply:** Standard Lever, Greenhouse, or single-page static forms with no CAPTCHA or multi-factor authentication walls.
  * **Human-in-the-Loop (HITL):** Portals requiring candidate user accounts (e.g., Workday, Taleo, SuccessFactors) or forms protected by Cloudflare / reCAPTCHA.

### 2.3 Tailor Agent (Document Optimization & Compilation)
* **Objective:** Rewrites base resume bullets and generates targeted cover letters.
* **Constraints:** Enforces Google’s **XYZ Formula** (*"Accomplished [X] as measured by [Y], by doing [Z]"*). Strictly prohibited from hallucinating skills or experiences not present in the user profile. Compiles templates into ATS-compliant PDFs using Typst or LaTeX.

### 2.4 Apply Agent (Execution Engine)
* **Objective:** Populates and submits job application forms.
* **Dual Execution:**
  * **Headless Mode:** Runs Python `Playwright` / `browser-use` background tasks for auto-apply queues.
  * **HITL Extension Mode:** Passes extracted field data to the Manifest V3 Chrome Extension, opening the active browser tab so the candidate can complete CAPTCHAs and click submit.

### 2.5 Coach Agent (Interview Simulation)
* **Objective:** Generates job-description-specific mock interview scenarios across behavioral (STAR method), technical, and system design categories. Evaluates user input in real-time.

### 2.6 [Optional Module] Meta-Agent (Self-Patching Selector Maintenance)
* **Objective:** Monitors headless execution logs. When form submission fails 3 consecutive times on a domain, inspects page screenshots and DOM trees, updates field selector mappings, and validates fixes via unit tests. *(Optional for initial MVP).*

---

## 3. Data Schemas (`schemas.py`)

```python
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

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
    full_name: str = Field(..., description="Full legal name")
    email: EmailStr = Field(..., description="Primary contact email")
    phone: str = Field(..., description="Phone number with country code")
    location: str = Field(..., description="City, State, Country")
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    work_authorization: str = Field(..., description="e.g., US Citizen, EU Visa, H1B")

class ExperienceItem(BaseModel):
    company: str
    role: str
    start_date: str  # Format: YYYY-MM
    end_date: str    # Format: YYYY-MM or Present
    bullet_points: List[str]

class EducationItem(BaseModel):
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
    target_roles: List[str]
    target_locations: List[str]
    employment_types: List[str] = ["Full-time"]
    min_salary_threshold: Optional[int] = None
    dealbreaker_keywords: List[str] = []
    required_stack_keywords: List[str] = []

class ExecutionPreferences(BaseModel):
    auto_apply_threshold_score: float = Field(default=0.85, ge=0.0, le=1.0)
    max_daily_applications: int = Field(default=20)
    enable_headless_auto_apply: bool = True
    human_in_the_loop_fallback: bool = True

class LLMProviderConfig(BaseModel):
    primary_model: str = "gemini-2.5-flash"
    reasoning_model: str = "deepseek-r1:8b"
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

```

---

## 4. Database Schema SQL (`schema.sql`)

```sql
-- PostgreSQL / SQLite Compatible Database Schema

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    location VARCHAR(255) NOT NULL,
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    work_authorization VARCHAR(100) NOT NULL,
    base_resume_json JSONB NOT NULL,
    eeo_demographics_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_config (
    config_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    search_criteria_json JSONB NOT NULL,
    execution_preferences_json JSONB NOT NULL,
    llm_config_json JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_records (
    job_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    job_url TEXT NOT NULL,
    match_score FLOAT NOT NULL,
    classification VARCHAR(50) NOT NULL, -- HEADLESS_AUTO | HUMAN_IN_THE_LOOP_LINK
    status VARCHAR(50) NOT NULL,        -- DISCOVERED | MATCHED | QUEUED | TAILORED | APPLIED | INTERVIEWING | REJECTED | OFFER
    tailored_resume_path TEXT,
    tailored_cover_letter_path TEXT,
    extracted_form_fields JSONB,
    submission_logs_json JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional Table for Meta-Agent Selectors
CREATE TABLE IF NOT EXISTS dom_patches (
    patch_id VARCHAR(255) PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    selector_mappings JSONB NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_apps_status ON application_records(status);
CREATE INDEX IF NOT EXISTS idx_apps_classification ON application_records(classification);

```

---

## 5. Backend REST API Controller (`main.py`)

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from schemas import (
    UserProfile, 
    SystemVariables, 
    ApplicationRecord, 
    ApplicationStatus, 
    ApplicationClassification,
    InterviewQuestion,
    UserAnswerFeedback
)

app = FastAPI(
    title="Job Hunter Orchestrator API",
    version="1.0.0",
    description="Backend API powering the multi-agent career platform."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# ROUTE HANDLERS
# ==========================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "LangGraph Orchestrator Active"}

@app.post("/api/v1/profile")
async def save_user_profile(profile: UserProfile):
    return {"status": "success", "user_id": profile.user_id}

@app.post("/api/v1/jobs/search")
async def trigger_job_search(background_tasks: BackgroundTasks, user_id: str):
    """Triggers the Scout and Classifier Agents in background."""
    return {"message": "Job discovery agent started in background."}

@app.get("/api/v1/applications", response_model=List[ApplicationRecord])
async def get_applications(status: Optional[ApplicationStatus] = None):
    return []

@app.post("/api/v1/applications/batch-apply")
async def trigger_batch_apply(job_ids: List[str], background_tasks: BackgroundTasks):
    """Executes Headless Apply Agent for selected auto-apply jobs."""
    return {"message": f"Queued {len(job_ids)} applications for headless execution."}

@app.get("/api/v1/extension/fill-context/{job_id}")
async def get_extension_fill_context(job_id: str):
    """Endpoint consumed by Chrome Extension to autofill forms in HITL mode."""
    return {
        "job_id": job_id,
        "fields": {
            "first_name": "Sample",
            "last_name": "User",
            "email": "user@example.com",
            "resume_path": "/path/to/tailored_resume.pdf"
        }
    }

@app.post("/api/v1/interview/generate-questions")
async def generate_mock_interview(job_id: str) -> List[InterviewQuestion]:
    """Coach Agent generates JD-specific interview questions."""
    return []

```

---

## 6. Manifest V3 Chrome Extension Bridge

### 6.1 `manifest.json`

```json
{
  "manifest_version": 3,
  "name": "Job Hunter Extension Bridge",
  "version": "1.0.0",
  "description": "Fills complex job application forms locally in HITL mode.",
  "permissions": ["activeTab", "scripting", "storage"],
  "host_permissions": ["http://localhost:8000/*", "https://*/*"],
  "action": {
    "default_popup": "popup.html"
  },
  "content_scripts": [
    {
      "matches": ["https://*/*"],
      "js": ["content.js"]
    }
  ]
}

```

### 6.2 `content.js` (DOM Form Auto-Fill Script)

```javascript
// Listens for message from extension popup script to autofill current form tab
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "AUTOFILL_FORM") {
    const data = request.formData;
    let filledCount = 0;

    const fieldMappings = {
      email: ['input[type="email"]', 'input[name*="email"]'],
      first_name: ['input[name*="first"]', 'input[id*="first"]'],
      last_name: ['input[name*="last"]', 'input[id*="last"]'],
      phone: ['input[type="tel"]', 'input[name*="phone"]']
    };

    for (const [key, selectors] of Object.entries(fieldMappings)) {
      if (data[key]) {
        for (const selector of selectors) {
          const input = document.querySelector(selector);
          if (input) {
            input.value = data[key];
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            filledCount++;
            break;
          }
        }
      }
    }

    sendResponse({ status: "SUCCESS", fieldsFilled: filledCount });
  }
});

```

---

## 7. Project File Directory Structure

```
job-hunter/
├── README.md
├── ARCHITECTURE.md            # This single master context file
├── docker-compose.yml
├── requirements.txt
├── schemas.py                 # Pydantic Schemas (Section 3)
├── schema.sql                 # SQL Table definitions (Section 4)
├── backend/
│   ├── main.py                # FastAPI Application (Section 5)
│   ├── database.py            # SQLAlchemy Connection Engine
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py    # LangGraph State Graph Workflow
│   │   ├── scout_agent.py     # Job Fetching and Scoring
│   │   ├── classifier.py      # Form & Triage Classifier
│   │   ├── tailor_agent.py    # PDF Generator & Resume Bullet Rewriter
│   │   ├── apply_agent.py     # Headless Playwright Script Execution
│   │   ├── coach_agent.py      # Interview Simulator Engine
│   │   └── meta_agent.py       # [Optional] Self-Patching Selector Engine
│   └── templates/
│       └── resume_template.typ # Typst / LaTeX PDF Generation Engine
├── frontend/
│   ├── package.json
│   └── src/
│       ├── app/               # Next.js App Router (Dashboard)
│       ├── components/        # Kanban Board, Apply Queue Table
│       └── lib/api.ts         # Axios/Fetch client for Backend API
└── extension/                 # Chrome Extension Code (Section 6)
    ├── manifest.json
    ├── popup.html
    ├── popup.js
    └── content.js

```

---

## 8. Step-by-Step Build Sequence for Coding Agent

Follow this exact build order:

1. **Phase 1: Schemas & Database Layer:** Create `schemas.py` and run `schema.sql` against SQLite/PostgreSQL. Set up SQLAlchemy connections in `backend/database.py`.
2. **Phase 2: Agent Orchestration Engine:** Implement `scout_agent.py`, `classifier.py`, and `tailor_agent.py`. Wire them into `backend/agents/orchestrator.py` using LangGraph.
3. **Phase 3: Execution Services:** Build `apply_agent.py` using Playwright for headless automation. Set up the `extension/` directory for browser-assisted HITL submissions.
4. **Phase 4: Dashboard & API:** Complete `backend/main.py` endpoints and connect them to the Next.js frontend UI for application tracking and mock interview practice.

```

```