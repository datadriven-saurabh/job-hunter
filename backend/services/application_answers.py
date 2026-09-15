"""Reusable verified stories and source-bound application answers."""
import json
import re
from backend import database as db
from backend.ai.router import digest,ModelRouter
from backend.prompts import PROMPT_VERSIONS
from backend.services.career_generator import context,output,_ranked_evidence
from backend.services.career_validation import Validation,words,clean_text
from backend.services.job_matching import detected

CATEGORIES=[('negotiation',['negotiat','competing priorit'],['negotiation','stakeholder_management','prioritisation']),('conflict',['disagree','conflict'],['conflict_resolution','stakeholder_management']),('failure',['fail','wrong','differently'],['failure_recovery']),('leadership',['leadership','led a','lead a'],['leadership','ownership']),('process_improvement',['improv','automat'],['process_improvement','automation']),('problem_solving',['problem','difficult','challenge'],['problem_solving','technical_problem_solving']),('stakeholder',['stakeholder','influenc'],['stakeholder_management','communication']),('company_interest',['why this company','join us','why do you want','why are you interested'],[]),('role_fit',['fit','hire you','relevant experience'],[]),('technical',['technical','experience with','used '],[])]


def classify_question(question):
    low=question.lower();category,tags=next(((c,t) for c,terms,t in CATEGORIES if any(term in low for term in terms)),('behavioural',['ownership']) if re.search(r'tell us about|describe a time|give an example|when was',low) else ('application_summary',[]))
    return {'category':category,'competencies':tags,'behavioural':bool(tags)}


def retrieve_stories(profile,question,job,used=None):
    kind=classify_question(question);used=used or set();stories=[]
    for s in profile['base_resume'].get('story_bank',[]):
        if not s.get('verified') or not s['situation'] or not s['actions'] or not s['result']:continue
        overlap=set(kind['competencies'])&set(s['competencies'])
        if kind['behavioural'] and not overlap:continue
        text=' '.join([s['situation'],s['task'],s['result']]+s['actions'])
        score=len(overlap)*40+len(detected(text)&detected(job['description']))*5+bool(s.get('metrics'))*15+bool(re.search(r'\bI\b',text))*10
        stories.append((s['story_id'] in used,-score,s))
    return [s for _,_,s in sorted(stories,key=lambda x:(x[0],x[1],x[2]['story_id']))]


def generate_answer(user_profile,target_jd,question,*,max_words=None,max_characters=None,mode='draft',used=None,router=None):
    ctx=context(user_profile,target_jd);check=Validation();kind=classify_question(question);router=router or ModelRouter();stories=retrieve_stories(ctx['profile'],question,ctx['job'],used)
    story=None;claims=[]
    if kind['behavioural']:
        if stories:
            story=stories[0];parts=[story['situation'],story['task']]+story['actions']+[story['result']]
            text=' '.join(p.strip().rstrip('.')+'.' for p in parts if p.strip())
            claims=[{'source_id':story['story_id'],'text':p} for p in parts if p.strip()]
            check.require(any(re.search(r'\bI\b',a) for a in story['actions']),'ownership','Record what you personally did in the story actions.')
        else:
            text='';check.require(False,'missing_story','Add a verified '+kind['category'].replace('_',' ')+' story with context, your actions, and the actual result.')
    else:
        entries=_ranked_evidence(ctx,router,'application_answer',{'question':question,'category':kind['category']});selected=[];size=0
        for e in entries:
            if size+words(e['text'])>85:continue
            selected.append(e);size+=words(e['text'])
            if size>=55:break
        facts=' '.join('At '+e['company']+', '+('I '+e['text'][0].lower()+e['text'][1:] if not e['text'].startswith('I ') else e['text']) for e in selected)
        if kind['category']=='company_interest':
            text=f'The {ctx["job"]["job_title"]} role at {ctx["job"]["company_name"]} connects with my background in '+(', '.join(ctx['skills'][:3]) or 'the work described in my profile')+'. '+facts+' I would welcome the opportunity to discuss how these examples relate to the team\'s priorities and the responsibilities described in the posting.'
        else:text=f'My experience most relevant to the {ctx["job"]["job_title"]} role includes the following work. '+facts+' These are the examples I would bring to a discussion about the requirements in this job description.'
        claims=[{'source_id':e['source_id'],'text':e['text']} for e in selected]
        check.require(bool(selected),'answer_evidence','Add relevant candidate experience before generating an answer.')
    text=clean_text(text)
    default_min=100 if kind['behavioural'] else 80
    upper=max_words or 150;lower=min(default_min,upper)
    check.require(lower<=words(text)<=upper,'answer_length',f'Answer must contain {lower}–{upper} words. Add concise supported detail or shorten your story; no invented detail is added to meet a limit.')
    if max_characters:check.require(len(text)<=max_characters,'answer_character_limit',f'Answer must fit within {max_characters} characters, including spaces. Shorten the source story or requested answer.')
    if mode=='autonomous':check.require(max_words is not None or max_characters is not None,'limits_required','Autonomous-ready output requires an explicit form limit.')
    result=output('application_answer',text,check,ctx,data={'question':question,'category':kind['category'],'story_id':story['story_id'] if story else None,'claims':claims,'mode':mode},router=router)
    result.update(answer=result['text'],needs_user_review=result['status']!='valid',factual_confidence=1 if result['status']=='valid' else 0,story_confidence=1 if story else None)
    return result


def answer_questions(profile,job,questions,router=None):
    used=set();results=[];router=router or ModelRouter()
    for q in questions:
        key=digest([profile,job,q,dict(PROMPT_VERSIONS),sorted(used),'answers-v2'])
        path=db.DATA/'answer-cache'/f'{key}.json'
        if path.exists():result=json.loads(path.read_text());result['cache_hit']=True
        else:
            result=generate_answer(profile,job,used=used,router=router,**q);result['cache_hit']=False
            if result['status']=='valid':
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result))
        if result['data'].get('story_id'):used.add(result['data']['story_id'])
        results.append(result)
    return results
