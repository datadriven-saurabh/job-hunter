'use client';
const boards=[
 ['Arbeitnow Europe','https://www.arbeitnow.com','Public API integrated'],
 ['Arbeitnow UK','https://www.arbeitnow.co.uk','Public API integrated'],
 ['Remote OK','https://remoteok.com','Public feed integrated'],
 ['We Work Remotely','https://weworkremotely.com','Public feed integrated'],
 ['Hacker News','https://news.ycombinator.com/jobs','Browser / manual import'],
 ['Y Combinator Work at a Startup','https://www.workatastartup.com','Browser / manual import'],
 ['Wellfound','https://wellfound.com','Browser / manual import'],
 ['Built In','https://builtin.com/jobs','Browser / manual import'],
 ['Remotive','https://remotive.com','Public feed integrated'],
 ['AIJobs.net','https://aijobs.net','Browser / manual import'],
 ['Indeed','https://www.indeed.com','Browser / manual import'],
 ['Glassdoor','https://www.glassdoor.com','Browser / manual import'],
 ['Google Jobs','https://www.google.com/search?q=data+analyst+jobs','Browser / manual import'],
 ['Greenhouse','https://www.greenhouse.com','Company board slug required'],
 ['Lever','https://www.lever.co','Company board slug required'],
 ['Ashby','https://www.ashbyhq.com','Company board slug required'],
 ['Workable','https://jobs.workable.com','Browser / manual import'],
 ['SmartRecruiters','https://jobs.smartrecruiters.com','Company board API integrated'],
 ['LinkedIn','https://www.linkedin.com/jobs','Public search integrated'],
 ['HiringCafe','https://hiringcafe.com','Public structured pages; access may be blocked'],
];
export default function JobBoardDirectory(){return <details className="board-directory"><summary>Job board access · {boards.length} boards</summary><p>Open a board and sign in directly in your browser if needed. Browser accounts are separate from public discovery; this app does not store passwords or verify your login status. Import a posting’s URL and full description from any board below.</p><div className="board-links">{boards.map(([name,url,note])=><a key={name} href={url} target="_blank" rel="noreferrer"><strong>{name} ↗</strong><small>{note}</small></a>)}</div></details>}
