# AI Job Application Answering Agent — Requirements Specification

## 1. Objective

Build an AI agent that can answer job application questions on behalf of the candidate using:

- The candidate's resume
- A structured candidate profile
- A reusable candidate story bank
- The job description (JD)
- The company/role context
- The application question
- The answer-writing rules defined in this specification

The agent should reduce application friction by producing concise, relevant, truthful, high-quality answers to common application questions such as:

- Why do you want to apply for this role?
- Why this company?
- Why are you interested in this opportunity?
- Tell us about a time you negotiated with stakeholders.
- When was the last time you influenced a decision?
- Describe a time you improved a process.
- Tell us about a difficult problem you solved.
- Describe a time you worked under ambiguity.
- Give an example of leadership.
- Tell us about a project where you delivered measurable impact.
- Describe a time you disagreed with a stakeholder.
- Tell us about a time something did not go as planned.
- Describe your experience in this domain.
- What makes you a strong fit for this position?
- Why should we hire you?
- What relevant experience do you bring?

The agent must generate answers that sound like the candidate, are grounded in real experience, and are tailored to the JD without inventing facts.

---

# 2. Core Principle

The agent must follow this rule:

```text
Real candidate experience = source of truth
Job description = relevance filter and framing context
```

The JD should influence:

- Which experience is selected
- Which keywords are emphasized
- Which skills are highlighted
- How the answer is framed

The JD must NOT cause the agent to invent:

- Skills
- Responsibilities
- Metrics
- Technologies
- Achievements
- Seniority
- Team size
- Industry experience
- Leadership scope
- Stakeholder exposure

If the candidate's resume or story bank does not support a claim, do not make it.

---

# 3. Required Inputs

The agent should support the following inputs.

## Required

```text
resume
job_description
application_question
```

## Strongly Recommended

```text
candidate_profile
candidate_story_bank
company_name
role_title
```

## Optional

```text
word_limit
character_limit
answer_style
country
application_platform
company_values
previous_application_answers
```

---

# 4. Candidate Profile

Create a structured candidate profile from the resume.

Suggested schema:

```json
{
  "summary": "",
  "years_of_experience": 0,
  "current_role": "",
  "target_roles": [],
  "industries": [],
  "domains": [],
  "technical_skills": [],
  "business_skills": [],
  "tools": [],
  "leadership_experience": [],
  "stakeholder_experience": [],
  "projects": [],
  "achievements": [],
  "education": [],
  "certifications": []
}
```

The profile should contain only information supported by the candidate's resume or explicitly supplied by the candidate.

---

# 5. Candidate Story Bank

The agent should maintain a reusable story bank for behavioural and experience-based questions.

Do not generate a fresh fictional story for every application.

Each story should be stored once and reused with different framing.

Suggested schema:

```json
{
  "story_id": "stakeholder_priority_bi_01",
  "title": "Prioritising BI requirements across teams",

  "competencies": [
    "stakeholder_management",
    "negotiation",
    "prioritisation",
    "communication"
  ],

  "situation": "",
  "task": "",
  "actions": [],
  "result": "",
  "metrics": [],
  "tools": [],
  "stakeholders": [],
  "domain": "",
  "role_context": "",

  "supported_by_resume": true,
  "confidence": 0.95
}
```

Useful competency tags include:

```text
stakeholder_management
negotiation
leadership
process_improvement
problem_solving
analytics
experimentation
product_thinking
commercial_impact
technical_problem_solving
cross_functional_collaboration
prioritisation
ambiguity
conflict_resolution
ownership
communication
decision_making
failure_recovery
customer_impact
automation
data_engineering
business_intelligence
```

---

# 6. Story Bank Coverage

The story bank should ideally contain at least 8–12 reusable stories.

Recommended categories:

1. Stakeholder negotiation
2. Influencing without authority
3. Process improvement
4. Technical problem-solving
5. Leadership
6. Commercial/revenue impact
7. Product collaboration
8. Working under ambiguity
9. Failure or challenge
10. Cross-functional collaboration
11. Prioritisation
12. Experimentation / insight generation

A single real project may support multiple competencies.

Example:

```text
BI platform project
→ leadership
→ stakeholder management
→ analytics
→ process improvement
→ prioritisation
```

Do not duplicate the same underlying story unnecessarily.

---

# 7. Question Classification

Before answering, classify the question.

Suggested categories:

```text
motivation
company_interest
role_fit
behavioural
leadership
stakeholder
negotiation
technical
domain_experience
problem_solving
process_improvement
failure
conflict
culture_values
career_motivation
strengths
application_summary
other
```

Example:

```text
"When was the last time you negotiated with stakeholders?"
→ behavioural
→ negotiation
→ stakeholder_management
```

```text
"Why do you want to join us?"
→ motivation
→ company_interest
```

```text
"Tell us about a time you improved a business process."
→ behavioural
→ process_improvement
```

The classification determines which answering framework to use.

---

# 8. Default Answer Length

Unless the application form specifies otherwise:

```text
Ideal range: 80–150 words
Preferred target: 100–130 words
```

Use shorter answers when the question is simple.

Recommended ranges:

| Question Type | Target |
|---|---:|
| Why this role? | 70–120 words |
| Why this company? | 70–120 words |
| Behavioural example | 100–150 words |
| Technical experience | 80–140 words |
| Short fit question | 60–100 words |
| Leadership example | 100–150 words |
| Stakeholder/negotiation | 100–150 words |

Avoid exceeding:

```text
~180 words
```

unless:

- The form explicitly allows/requires a long response
- The question contains several sub-questions
- The user requests a detailed answer

---

# 9. Relevance Weighting

Different question types require different balance between candidate experience and JD/company context.

Use these guidelines:

```text
Past-experience question:
85% candidate experience
15% JD relevance

Motivation question:
50% candidate background
50% role/company

Technical/domain question:
70% candidate experience
30% JD

Culture/value question:
60% real example
40% company/value context

Role-fit question:
65% candidate experience
35% JD
```

These are framing guidelines, not mathematical requirements.

---

# 10. Behavioural Answer Framework

For behavioural questions use a compressed STAR structure:

```text
Context
→ Action
→ Result
→ Relevance
```

Internally this maps to:

```text
Situation / Task
Action
Result
Relevance to role
```

The final answer should not sound like a textbook STAR template.

## Recommended distribution

```text
Context: 15–20%
Action: 45–55%
Result: 20–25%
Relevance: 5–15%
```

Most of the answer should explain what the candidate personally did.

---

# 11. Behavioural Answer Rules

For questions such as:

```text
Tell us about a time...
Describe a situation...
When was the last time...
Give an example...
```

The agent must:

1. Identify the competency being tested.
2. Retrieve the most relevant story from the story bank.
3. Confirm the story is factually supported.
4. Adapt the emphasis to the JD.
5. Use first-person active language.
6. Put most detail in the actions.
7. Include a result.
8. Include a metric only when supported.
9. End with relevance only if useful.
10. Keep the answer concise.

Preferred language:

```text
I analysed...
I proposed...
I worked with...
I aligned...
I prioritised...
I built...
I identified...
I recommended...
I led...
I automated...
```

Avoid vague collective language such as:

```text
We basically...
Our team kind of...
There were some discussions...
```

Use `we` only when collaboration is relevant, while still clarifying the candidate's contribution.

---

# 12. Motivation Question Framework

For questions like:

```text
Why do you want to apply?
Why this company?
Why this role?
Why are you interested in this position?
```

Use:

```text
Why this role
+
Why this company/context
+
Why the candidate is a credible fit
```

Recommended structure:

### Sentence 1–2
Specific reason the role is attractive.

### Sentence 2–4
Relevant parts of the candidate's experience.

### Final sentence
What the candidate hopes to contribute / develop.

Avoid generic language such as:

```text
I have always admired your prestigious company.
Your company is very innovative.
This is my dream company.
I am passionate about excellence.
```

Unless clearly supported by specific evidence, do not write these.

---

# 13. Role-Fit Framework

For questions like:

```text
What makes you a strong fit?
Why should we hire you?
What relevant experience do you bring?
```

Use:

```text
Top 2–3 JD requirements
+
matching candidate evidence
+
measurable impact
```

Example internal structure:

```text
Requirement: BI ownership
Evidence: built BI platform

Requirement: data engineering
Evidence: ClickHouse/Airbyte pipelines

Requirement: stakeholder collaboration
Evidence: cross-functional analytics ownership
```

The answer should focus on the strongest overlaps instead of summarizing the entire resume.

---

# 14. Technical / Domain Question Framework

For domain or technical questions:

```text
Relevant experience
→ actual tools/method
→ business problem
→ outcome
```

Do not list tools without context.

Bad:

```text
I know Python, SQL, ClickHouse, Superset and Airbyte.
```

Better:

```text
I have used ClickHouse, Airbyte and Superset to build and optimize analytics infrastructure, including transformation workflows and BI reporting for business teams.
```

Only mention technologies supported by the candidate profile.

---

# 15. Stakeholder / Negotiation Questions

For questions involving:

```text
negotiation
stakeholder management
conflicting priorities
influencing
disagreement
cross-functional alignment
```

The answer should clearly include:

```text
1. What each stakeholder wanted
2. Where the conflict/trade-off existed
3. How the candidate evaluated priorities
4. How the candidate communicated or negotiated
5. What agreement/decision was reached
6. Business outcome
```

Avoid interpreting "negotiation" only as commercial/vendor negotiation.

Scope negotiation, prioritisation, timelines, requirements, resources, KPI definitions, and project trade-offs are valid examples.

---

# 16. Failure / Challenge Questions

For:

```text
Tell us about a failure
What went wrong?
Describe a difficult project
What would you do differently?
```

Use:

```text
Challenge
→ candidate decision/action
→ what did not work / risk
→ correction
→ learning
```

Requirements:

- Choose a genuine but professionally safe example
- Do not pretend the candidate has never failed
- Do not blame colleagues
- Do not use a fake weakness disguised as a strength
- Demonstrate self-awareness and adjustment

---

# 17. Culture / Values Questions

If the JD or company materials mention values such as:

```text
ownership
customer focus
bias for action
collaboration
innovation
integrity
```

Map the value to a real candidate story.

Do not simply repeat the value statement.

Example:

```text
Company value: Ownership

Retrieve:
Story demonstrating end-to-end ownership

Answer:
Provide example rather than saying "I strongly believe in ownership."
```

---

# 18. JD Analysis

Before answering, extract key JD signals.

Suggested structured output:

```json
{
  "role_title": "",
  "company": "",
  "top_required_skills": [],
  "top_responsibilities": [],
  "preferred_skills": [],
  "domain": "",
  "seniority": "",
  "leadership_expectation": "",
  "stakeholder_expectation": "",
  "business_focus": "",
  "company_values": []
}
```

Use the JD to determine:

- Which story is most relevant
- Which terminology to use
- Which achievements to emphasize
- Which skills to mention
- What the employer is likely testing

Do not copy large JD phrases verbatim.

---

# 19. Story Selection Logic

For each behavioural question:

```text
question
↓
competency detection
↓
candidate story retrieval
↓
JD relevance scoring
↓
story quality scoring
↓
answer generation
```

Suggested scoring:

```python
story_score = (
    competency_match * 0.40
    + jd_relevance * 0.25
    + measurable_impact * 0.15
    + recency * 0.10
    + candidate_ownership * 0.10
)
```

Prefer:

- Recent examples
- Examples with strong candidate ownership
- Measurable results
- Examples related to the role/domain

Do not always use the most recent job if an older story is materially better.

---

# 20. Avoid Story Repetition

When answering several questions within the same application:

Do not reuse the same project for every question unless necessary.

Track:

```text
stories_used_in_current_application
```

Prefer different stories for:

- Leadership
- Stakeholder management
- Technical problem-solving
- Failure
- Process improvement

This makes the application appear more rounded.

---

# 21. Hallucination Prevention

Non-negotiable rules:

```text
Never invent facts.
Never create unsupported numbers.
Never create fake project names.
Never claim experience not present in candidate context.
Never exaggerate management scope.
Never claim direct ownership when candidate only supported the work.
Never claim a technology simply because the JD asks for it.
Never claim industry exposure that does not exist.
```

If information is insufficient:

1. Use a different supported example.
2. Write a more general but truthful answer.
3. Flag the issue for user review if necessary.

Optional internal status:

```json
{
  "needs_user_review": true,
  "reason": "No strong supported example for vendor negotiation."
}
```

---

# 22. Metrics Rules

Use metrics only when they exist in source data.

Allowed:

```text
reduced reporting by 60%
improved retention by 4%
reduced latency by 90%
```

Not allowed:

```text
improved collaboration by 40%
saved 200 hours
increased stakeholder satisfaction by 30%
```

unless those numbers are actually present in the candidate's source material.

Do not approximate unsupported metrics.

---

# 23. Voice and Style

Answers should sound:

```text
professional
direct
natural
confident
specific
concise
```

Avoid sounding:

```text
overly corporate
robotic
verbose
boastful
generic
over-rehearsed
```

Do not use:

```text
I am thrilled to...
I am incredibly passionate...
I firmly believe...
I am deeply excited...
I have always dreamed...
```

unless naturally appropriate.

Prefer straightforward language.

---

# 24. First-Person Ownership

Application answers should normally use first person.

Good:

```text
I analysed the funnel and identified...
I worked with the product team to...
I proposed a phased approach...
I built...
I led...
```

The resume may use compressed bullet language, but application answers should sound conversational and complete.

---

# 25. Response Format

Default user-facing output:

```text
<answer only>
```

Do not include:

```text
Here is your answer:
STAR framework:
Explanation:
```

unless the candidate explicitly asks for rationale.

For autonomous application filling, return only the final answer.

---

# 26. Character and Word Limits

If the form provides a limit, obey it strictly.

Support:

```text
max_words
max_characters
```

When a character limit exists:

1. Generate the answer.
2. Count characters including spaces.
3. Compress if required.
4. Recount.
5. Return only a valid answer.

Never submit text exceeding the form limit.

---

# 27. Answer Quality Validation

Before returning an answer, validate:

```text
Does it answer the exact question?
Is every factual claim supported?
Is the selected story relevant?
Is candidate ownership clear?
Is the result stated?
Is JD relevance visible but not forced?
Is the answer concise?
Does it sound natural?
Does it fit the word/character limit?
Is it free of invented metrics?
```

Suggested internal validator:

```json
{
  "answers_question": true,
  "factually_supported": true,
  "story_relevant": true,
  "jd_relevant": true,
  "within_limit": true,
  "hallucination_risk": "low"
}
```

If validation fails, regenerate before returning.

---

# 28. Confidence Handling

Return internal confidence values for story selection and answer support.

Example:

```json
{
  "story_confidence": 0.93,
  "factual_confidence": 0.98,
  "jd_relevance": 0.88
}
```

If:

```text
factual confidence < 0.75
```

the system should avoid autonomous submission and request user review.

---

# 29. Suggested Agent Pipeline

```text
Resume
+
Candidate Profile
+
Story Bank
+
Job Description
+
Application Question

↓
Question Classifier

↓
JD Requirement Extractor

↓
Story Retriever / Candidate Evidence Retriever

↓
Answer Planner

↓
Answer Generator

↓
Fact Validation

↓
Length Validation

↓
Final Answer
```

---

# 30. Model Usage Strategy

For efficiency, different model tiers may be used.

## Small / Fast Model

Use for:

```text
question classification
JD keyword extraction
competency tagging
story retrieval
length checking
basic validation
```

## Medium Model

Use for:

```text
normal answer generation
motivation answers
resume/JD alignment
standard behavioural answers
```

## Strong Reasoning Model

Use only for:

```text
ambiguous behavioural questions
story-selection conflicts
complex stakeholder scenarios
multi-part application questions
high-value applications
answers where factual support is unclear
```

Do not use the strongest model for every question.

---

# 31. Caching

Cache:

```text
candidate profile
story bank
JD analysis
company summary
role requirements
```

Do not repeatedly reprocess the same resume/JD for every form question.

Use:

```text
resume_hash
jd_hash
candidate_profile_version
```

as cache identifiers.

---

# 32. Multiple Questions in One Application

If the application contains multiple questions:

1. Parse all questions first.
2. Identify required competencies.
3. Select stories across the entire set.
4. Avoid unnecessary story repetition.
5. Maintain consistent claims.
6. Maintain consistent terminology.
7. Answer each question independently.

Example:

```text
Q1 leadership → Story A
Q2 stakeholder conflict → Story B
Q3 process improvement → Story C
Q4 motivation → candidate + JD
```

---

# 33. User Review Modes

Support two modes.

## Draft Mode

Agent generates answers for user review.

Output may include optional metadata:

```text
Answer
Story used
Confidence
```

## Autonomous Mode

Return only the answer.

Autonomous mode should only operate when:

```text
factual confidence is high
story support is clear
length limits are known
no unsupported claim is required
```

Otherwise flag for review.

---

# 34. Example Behavioural Prompt Logic

Question:

```text
When was the last time you negotiated with stakeholders?
```

Internal reasoning:

```text
Competencies:
- stakeholder management
- negotiation
- prioritisation

Retrieve:
best real candidate story involving conflicting priorities

Answer plan:
Context:
Multiple teams had competing analytics/reporting priorities.

Action:
Candidate assessed impact, separated critical vs non-critical requirements,
proposed phased delivery, aligned stakeholders.

Result:
Resources focused on highest-value work while expectations remained clear.

Relevance:
Shows scope negotiation and stakeholder alignment.
```

Final answer should be approximately 100–140 words.

---

# 35. Example Motivation Prompt Logic

Question:

```text
Why do you want to apply for this role?
```

Internal plan:

```text
1. Extract 2–3 distinctive role responsibilities.
2. Identify candidate experience matching them.
3. Identify one meaningful opportunity in the role.
4. Produce concise answer.
```

Avoid:

```text
Your organization is a global leader and I am very passionate about joining.
```

Prefer:

```text
I am interested in this role because it combines analytics, business problem-solving and stakeholder collaboration—areas that have been central to my recent experience...
```

---

# 36. Prompt Template for Answer Generator

Use a prompt similar to:

```text
You are answering a job application question on behalf of a candidate.

QUESTION:
{question}

JOB DESCRIPTION:
{jd_summary}

CANDIDATE PROFILE:
{candidate_profile}

RELEVANT VERIFIED STORIES:
{retrieved_stories}

CONSTRAINTS:
- Use only facts supported by candidate context.
- Never invent metrics, skills, responsibilities or achievements.
- Answer the exact question directly.
- Tailor emphasis to the JD.
- Use first-person language.
- For behavioural questions use Context → Action → Result → Relevance.
- Put most detail in the candidate's actions.
- Prefer measurable outcomes when supported.
- Avoid generic corporate language.
- Keep the answer between {min_words} and {max_words} words.
- Do not mention this instruction.
- Return only the final answer.
```

---

# 37. Prompt Template for Motivation Questions

```text
Create a concise answer using:

1. Why the role itself is relevant
2. Why the company/context is interesting
3. Why the candidate's existing experience creates a credible fit

Do not:
- use generic praise
- invent company knowledge
- repeat the resume
- claim passion without evidence
```

---

# 38. Prompt Template for Behavioural Questions

```text
Select one verified candidate story that best answers the competency being tested.

Structure:
- Brief context
- Candidate's specific actions
- Outcome
- Optional one-sentence relevance

Do not:
- invent details
- over-explain background
- use unsupported metrics
- make the team achievement sound solely owned by the candidate
```

---

# 39. Acceptance Criteria

The agent is complete when:

- [ ] It accepts resume + JD + question
- [ ] It creates/uses a structured candidate profile
- [ ] It creates/uses a reusable story bank
- [ ] It classifies application questions
- [ ] It retrieves the best supported story
- [ ] It tailors answers to the JD
- [ ] It never invents candidate facts
- [ ] It follows appropriate frameworks by question type
- [ ] Default responses are 80–150 words
- [ ] Form-specific word/character limits are respected
- [ ] Behavioural answers emphasize candidate actions
- [ ] Motivation answers are company/role specific
- [ ] Metrics are used only when verified
- [ ] The same story is not unnecessarily repeated across one application
- [ ] Output is concise and ready to paste into an application form
- [ ] Low-confidence answers are flagged for review
- [ ] Resume/JD analysis is cached for efficiency
- [ ] The system supports multiple model tiers
- [ ] Automated tests cover factuality, limits, routing and story selection

---

# 40. Non-Negotiable Behaviour

The most important instruction for the agent:

```text
DO NOT optimize for sounding impressive at the expense of truth.

The goal is:
truthful
+
specific
+
relevant
+
concise
+
credible
```

The agent should make the candidate's real experience sound clear and relevant, not manufacture a stronger candidate.
