#let d = json("resume.json")
#set page(paper: "us-letter", margin: (left: 54pt, right: 54pt, top: 38pt, bottom: 32pt))
#set text(font: "Carlito", size: d.font_size * 1pt, fill: black)
#set par(leading: 0.28em, spacing: 2pt)
#set list(indent: 0pt, body-indent: 14pt, spacing: 1.5pt, tight: true)
#align(center)[
  #text(size: 16pt, weight: "bold", upper(d.personal.full_name))
  #linebreak()
  #text(size: 10pt, d.contact)
  #if d.links != "" {linebreak();text(size: 9pt, d.links)}
]
#let heading(label) = block(above: 6pt, below: 3pt, breakable: false)[
  #line(length: 100%, stroke: 0.45pt)
  #v(1pt, weak: false)
  #align(center, text(weight: "bold", size: 11pt, label))
  #v(1pt, weak: false)
  #line(length: 100%, stroke: 0.45pt)
]
#if d.education.len() > 0 [
  #heading("EDUCATION")
  #for e in d.education [
    #block(breakable: false, above: 2pt, below: 3pt)[
      #grid(columns: (1fr, auto), column-gutter: 10pt,
        text(weight: "bold", e.institution),
        align(right, text(weight: "bold", e.graduation_year)))
      #text(weight: "bold", e.degree + if e.field_of_study != "" {", " + e.field_of_study} else {""})
    ]
  ]
]
#heading("EXPERIENCE")
#for e in d.experience [
  #block(breakable: false, above: 3pt, below: 6pt)[
    #grid(columns: (1fr, auto), column-gutter: 10pt,
      [#text(weight: "bold", e.company)#if e.location != "" {text(", " + e.location)}],
      align(right, text(weight: "bold", e.dates)))
    #text(weight: "bold", style: "italic", e.role)
    #list(..e.bullets.map(b => b.text))
  ]
]
#if d.skills.len() > 0 or d.languages.len() > 0 or d.certifications.len() > 0 [
  #heading("ADDITIONAL")
  #let items = ()
  #if d.skills.len() > 0 { items.push([#text(weight: "bold", "Skills: ")#text(d.skills.join(", "))]) }
  #if d.languages.len() > 0 { items.push([#text(weight: "bold", "Languages: ")#text(d.languages.map(l => l.language + " - " + l.level).join(", "))]) }
  #if d.certifications.len() > 0 { items.push([#text(weight: "bold", "Certifications: ")#text(d.certifications.join(", "))]) }
  #list(..items)
]
