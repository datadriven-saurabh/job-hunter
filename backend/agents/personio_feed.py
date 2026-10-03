"""One fixed public employer feed; never accepts caller-supplied hosts."""
import re
from xml.etree import ElementTree as ET


def parse_ja_solar(markup, keywords='', limit=20):
    from backend.agents.job_sources import clean, SourceUnavailable
    if len(markup.encode('utf-8')) > 2 * 1024 * 1024:
        raise SourceUnavailable('Employer XML exceeded 2 MB.')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', markup, re.I):
        raise SourceUnavailable('Unsupported employer XML declarations.')
    try:
        root = ET.fromstring(markup)
    except ET.ParseError as exc:
        raise SourceUnavailable('Unreadable employer XML feed.') from exc
    if root.tag != 'workzag-jobs':
        raise SourceUnavailable('Expected a public Personio jobs feed.')
    jobs, seen = [], set()
    words = keywords.casefold().split()
    cap = max(0, min(int(limit), 200))
    for position in root.findall('position')[:200]:
        identifier = (position.findtext('id') or '').strip()
        title = clean(position.findtext('name'))
        if not re.fullmatch(r'[0-9]+', identifier) or not title or identifier in seen:
            continue
        seen.add(identifier)
        sections = []
        for section in position.findall('./jobDescriptions/jobDescription'):
            sections.extend([clean(section.findtext('name')), clean(section.findtext('value'))])
        description = '\n'.join(value for value in sections if value)
        if not all(word in (title + ' ' + description).casefold() for word in words):
            continue
        offices = [clean(position.findtext('office'))]
        offices.extend(clean(office.text) for office in position.findall('./additionalOffices/office'))
        url = 'https://ja-solar.jobs.personio.de/job/' + identifier
        jobs.append({'company_name': 'JA Solar GmbH', 'job_title': title,
                     'job_url': url, 'source_url': url, 'source': 'JA Solar Europe careers',
                     'requisition_id': identifier, 'description': description,
                     'description_incomplete': len(description) < 200,
                     'location': ', '.join(dict.fromkeys(x for x in offices if x)),
                     'employment_type': clean(position.findtext('employmentType')),
                     'schedule': clean(position.findtext('schedule'))})
        # createdAt describes the ATS record; it is not verified publication time.
        if len(jobs) >= cap:
            break
    return jobs[:cap]
