"""Export saved posting facts for the owning user as spreadsheet-safe CSV."""
import csv
import io
import json

FIRST_COLUMNS = (
    'job_title', 'company_name', 'job_url', 'description', 'source',
    'source_url', 'location', 'employment_type', 'posted_at', 'status',
    'match_score', 'fit_analysis',
)
INTERNAL_COLUMNS = {
    'user_id', 'selected_resume_id', 'selected_resume_label',
    'studio_state', 'studio_error', 'studio_kit_id', 'submission_logs',
    'extracted_form_fields', 'tailored_resume_path', 'tailored_cover_letter_path',
}
HEADERS = {
    'job_title': 'Job Title', 'company_name': 'Company', 'job_url': 'Job Link',
    'description': 'Job Description', 'source_url': 'Source Link',
    'match_score': 'Match Score (0–100)', 'fit_analysis': 'Fit Analysis (JSON)',
}

def cell(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    elif isinstance(value, bool):
        value = str(value).lower()
    else:
        value = str(value)
    # Spreadsheet applications can execute formulas in imported text cells.
    if value.lstrip().startswith(('=', '+', '-', '@')):
        value = "'" + value
    return value

def render(jobs):
    columns = list(FIRST_COLUMNS)
    columns += sorted({key for job in jobs for key in job if key not in columns and key not in INTERNAL_COLUMNS and not key.startswith('_')})
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow([HEADERS.get(key, key.replace('_', ' ').title()) for key in columns])
    for job in jobs:
        writer.writerow([cell(round(job.get(key, 0) * 100, 1) if key == 'match_score' and job.get(key) is not None else job.get(key)) for key in columns])
    return '\ufeff' + output.getvalue()
