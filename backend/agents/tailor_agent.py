"""Application preparation uses the same validated assets as Application Studio."""
from backend.database import DATA
from backend.services import resumes
from backend.services.career_generator import generateATSResume, generateCoverLetter
from backend.services.career_render import render_resume, render_cover


def tailor(job, profile):
    selection = resumes.selected(job['job_id'])
    if selection and selection != 'profile':
        raise ValueError('Uploaded resumes remain available for matching and download. Confirm their achievements in My profile and select Profile resume to generate the required reference format; unreviewed uploads cannot bypass validation.')
    directory = DATA / 'documents' / job['job_id']
    resume = generateATSResume(profile, job)
    cover = generateCoverLetter(profile, job)
    for asset in (resume, cover):
        if asset['status'] != 'valid':
            messages = asset['missing_inputs'] + [e['message'] for e in asset['validation']['errors']]
            raise ValueError(asset['asset_type'] + ': ' + ' '.join(messages))
    path = render_resume(resume, directory)
    render_cover(cover, directory)
    (directory / 'cover-letter.txt').write_text(cover['text'])
    return path, str(directory / 'cover-letter.txt')
