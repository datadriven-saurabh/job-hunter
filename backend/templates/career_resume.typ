#let d = json("resume.json")
#set page(paper: "a4", margin: (x: 16mm, y: 11mm))
#set text(font: ("Times New Roman", "Liberation Serif", "DejaVu Serif"), size: d.font_size * 1pt, fill: black)
#set par(leading: 0.5em, spacing: 3pt)
#align(center)[
  #text(size: 24pt, weight: "bold", d.personal.full_name)
  #v(5pt, weak: false)
  #text(size: 9pt, d.contact)
  #if d.links != "" {v(3pt, weak: false);text(size: 9pt,d.links)}
  #v(4pt, weak: false)
]
#let heading(label) = block(above: 8pt, below: 5pt)[
  #text(weight: "bold", size: 11pt, label)
  #linebreak()
  #line(length: 100%, stroke: 0.5pt)
]
#heading("PROFILE")
#text(d.summary)
#heading("WORK EXPERIENCE")
#for e in d.experience [
  #block(breakable: false, above: 4pt, below: 2pt)[
    #grid(columns: (1fr, auto), column-gutter: 8pt,
      [#text(weight: "bold", upper(e.company)), #emph(e.role)],
      align(right, text(e.dates)))
    #for bullet in e.bullets [
      #block(above: 3pt, below: 3pt, inset: (left: 7pt))[
        #text("• ")#text(bullet.text)
      ]
    ]
  ]
]
#if d.education.len() > 0 [
  #heading("EDUCATION")
  #for e in d.education [
    #grid(columns:(1fr,auto),column-gutter:8pt,[#text(weight:"bold",e.institution)],[#text(e.graduation_year)])
    #emph(e.degree + ", " + e.field_of_study)
    #parbreak()
  ]
]
#if d.skills.len() > 0 [#heading("SKILLS")#text(d.skills.join(", "))]
#if d.languages.len() > 0 [
  #heading("LANGUAGE SKILLS")
  #text(d.languages.map(l => l.language + " - " + l.level).join(" | "))
]
#if d.certifications.len() > 0 [
  #heading("CERTIFICATIONS")
  #for c in d.certifications [#text("• " + c)#parbreak()]
]
