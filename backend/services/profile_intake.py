"""Source-checked raw-profile intake. Proposals are never saved automatically."""
from backend.ai.router import ModelRouter,ModelUnavailable
from backend.prompts import build_prompt
from backend.services.career_validation import source_span
from schemas import UserProfile


def parse_raw_profile(raw,router=None):
    if not isinstance(raw,str) or not 80<=len(raw)<=30000:
        raise ValueError('Provide 80–30,000 characters of candidate background, separate from the job description.')
    router=router or ModelRouter()
    def validate(profile):
        value=profile.model_dump()
        # Routing IDs are application metadata; sensitive demographics are not inferred.
        if value.get('eeo_demographics'):raise ValueError('Demographics must not be inferred.')
        def walk(item,key=''):
            if key in {'user_id','eeo_demographics'}:return
            if isinstance(item,dict):
                for k,v in item.items():walk(v,k)
            elif isinstance(item,list):
                for v in item:walk(v,key)
            elif isinstance(item,str) and item and not source_span(item,raw):
                raise ValueError('Extracted profile field is not an exact source span: '+key)
            elif key=='verified' and item is True:raise ValueError('Intake cannot mark evidence verified.')
        walk(value)
    prompt=build_prompt('resume_writing',{'raw_background':raw},{},extra={'task':'Extract a structured candidate profile. All nonempty string fields must be exact contiguous source spans, including dates, names, skills and summary. Do not normalize or invent dates. Omit unavailable optional fields and lists. Set user_id to local and eeo_demographics to null. Do not infer achievements or stories, and never mark evidence verified. If required facts are missing, validation will request user input.'})
    try:result=router.run('profile_extraction',prompt,UserProfile,validator=validate)
    except ModelUnavailable as exc:raise ValueError('A source-checked profile could not be extracted. Enter or confirm name, contact details, role dates, education and achievements in My profile. No inferred facts were saved.') from exc
    value=result.model_dump();value['user_id']='local'
    return value
