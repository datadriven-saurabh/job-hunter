#set page(paper: "a4", margin: 1.6cm)
#set text(font: "DejaVu Sans", size: 10pt)
#set par(leading: 0.65em)
#let d = json("resume.json")
#text(size: 21pt, weight: "bold", d.name)
#linebreak()
#text(d.contact)
#v(10pt)
#for section in d.sections [
  #text(size: 12pt, weight: "bold", section.title)
  #line(length: 100%, stroke: 0.4pt)
  #for item in section.items [#text(item) #parbreak()]
  #v(6pt)
]
