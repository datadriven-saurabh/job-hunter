"""Deterministic guardrails; unvalidated model prose is never an exportable asset."""
import re
from dataclasses import dataclass,field


def words(text):return len(re.findall(r"\S+",text.strip()))


def clean_text(value):
    return str(value).replace('\u2013','-').replace('\u2014','-').replace('\u2011','-').replace('\u2018',"'").replace('\u2019',"'").replace('\u201c','"').replace('\u201d','"').strip()


@dataclass
class Validation:
    errors:list=field(default_factory=list)
    warnings:list=field(default_factory=list)

    def require(self,condition,code,message):
        if not condition:self.errors.append({'code':code,'message':message})

    def result(self,text='',**extra):
        return {'valid':not self.errors,'word_count':words(text),'character_count':len(text),'errors':self.errors,'warnings':self.warnings,**extra}


def validate_ats(text):
    check=Validation()
    check.require(400<=words(text)<=750,'resume_word_count','Resume must contain 400–750 words from supported facts.')
    check.require(not re.search(r'<[^>]+>',text),'html','HTML is not allowed in ATS Markdown.')
    check.require(not re.search(r'^\s*\|.*\|\s*$|^\s*[+=_-]{3,}\s*$|^\s*\+[-+]+\+\s*$',text,re.M),'table','Tables and ASCII borders are not allowed.')
    check.require(not re.search(r'[●○★✓✦→←☎✉]|[\x00-\x08\x0b\x0c\x0e-\x1f]',text),'symbols','Use text and standard Markdown bullets, not icons, rating dots or control characters.')
    check.require(not re.search(r'^\s*[-+]\s',text,re.M),'bullets','Use standard * bullets.')
    return check


def validate_xyz(value):
    check=Validation()
    check.require(bool(re.match(r'^(?:Accomplished|Built|Developed|Created|Designed|Improved|Reduced|Increased|Optimized|Optimised|Automated|Delivered|Led|Co-led|Co-developed|Implemented|Architected|Engineered|Refactored|Deployed|Streamlined|Spearheaded|Established|Enabled|Achieved|Analyzed|Analysed|Defined|Refined|Partnered|Launched|Standardized|Standardised)\b',value['outcome'],re.I)),'xyz_action','Outcome must begin with a supported action verb.')
    check.require(bool(re.search(r'\d',value['measurement'])),'xyz_measurement','Supply the actual measured result; never estimate a missing metric.')
    check.require(len(value['method'].strip())>2,'xyz_method','Supply the actual method or action that produced this result.')
    return check


def source_span(span,source):
    # Exact contiguous evidence: cannot join a number from one role to another role.
    return bool(span.strip()) and ' '.join(clean_text(span).casefold().split()) in ' '.join(clean_text(source).casefold().split())


def check_facts(claims,registry):
    check=Validation()
    for claim in claims:
        source=registry.get(claim.get('source_id',''))
        check.require(source is not None and source_span(claim.get('text',''),source or ''),'unsupported_claim','A candidate claim does not match its cited source evidence.')
    return check


def validate_referral(text,message_type,job_title,requisition_id,resume_url,skills):
    check=Validation()
    if message_type=='invite_note':check.require(len(text)<300,'invite_length','Connection notes must be fewer than 300 characters. Shorten recipient/company wording or provide a shorter public URL; the exact job title and ID cannot be dropped.')
    else:
        check.require(75<=words(text)<=125,'message_word_count','Referral messages must contain 75–125 words.')
        check.require(len(re.split(r'\n\s*\n',text.strip()))<=3,'message_paragraphs','Use no more than three short paragraphs.')
    for key,value in [('job_title',job_title),('job_id',requisition_id),('resume_url',resume_url)]:check.require(value in text,key,'Missing required '+key.replace('_',' ')+'.')
    check.require(bool(skills) and any(skill in text for skill in skills),'skills','Include at least one evidenced skill matching the posting.')
    check.require('if you feel comfortable' in text.lower(),'closing','Use a low-pressure closing.')
    return check
