"""Conservative language hints from the posting text, separate from fluency requirements."""
import re

MARKERS={
 'English':set('the and with your you our are will for this we skills experience responsibilities requirements work team'.split()),
 'German':set('und die der das wir du mit für deine dein einen eine dich auf sie erfahrung aufgaben kenntnisse'.split()),
 'French':set('les des une vous nous pour dans avec votre notre sont expérience compétences poste travail équipe'.split()),
 'Dutch':set('het een wij jij je voor onze ons zijn werk ervaring naar bij functie vaardigheden'.split()),
 'Spanish':set('los las una para con nuestro nuestra experiencia equipo trabajo buscamos habilidades puesto requisitos'.split()),
 'Italian':set('della delle una per con siamo nostro nostra esperienza lavoro competenze ruolo requisiti squadra'.split()),
}
CODES={'en':'English','de':'German','fr':'French','nl':'Dutch','es':'Spanish','it':'Italian','pt':'Portuguese','hi':'Hindi','pl':'Polish'}

def posting_language(text,explicit=None):
    if isinstance(explicit,str):
        name=CODES.get(explicit.casefold().split('-')[0]) or next((n for n in MARKERS if explicit.casefold()==n.casefold()),None)
        if name:return {'label':name,'method':'Source supplied','confidence':'source'}
    tokens=re.findall(r'[^\W\d_]+',text.casefold(),re.UNICODE)
    if len(tokens)<18:return {'label':'Unknown','method':'Not enough text','confidence':'low'}
    scores=sorted(((sum(t in markers for t in tokens),name,len(set(tokens)&markers)) for name,markers in MARKERS.items()),reverse=True)
    score,name,unique=scores[0];second=scores[1]
    if score<6 or unique<4:return {'label':'Unknown','method':'Language could not be identified reliably','confidence':'low'}
    if second[0]>=6 and second[2]>=4 and second[0]>=score*.6:
        return {'label':name+' / '+second[1],'method':'Likely mixed-language posting','confidence':'estimated'}
    return {'label':name,'method':'Detected from posting text','confidence':'estimated'}
