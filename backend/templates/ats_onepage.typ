#let d = json("resume.json")
#set page(paper: "a4", margin: (x: 15mm, y: 12mm))
#set text(font: ("Arial", "DejaVu Sans", "Liberation Sans"), size: d.font_size * 1pt, fill: rgb("303438"))
#set par(leading: 0.55em, spacing: 4pt)
#align(center)[
  #text(size: 19pt, weight: "bold", upper(d.name))
  #linebreak()
  #text(size: 10pt, fill: rgb("667275"), d.headline)
  #linebreak()
  #text(size: 8.5pt, d.contact)
]
#for section in d.sections [
  #v(4pt)
  #align(center, text(size: 11pt, section.title))
  #v(-3pt)
  #line(length: 100%, stroke: 0.4pt)
  #for item in section.items [
    #if type(item) == dictionary {
      block(breakable: false, above: 5pt, below: 5pt)[
        #text(weight: "bold", fill: rgb("59686d"), item.company)
        #h(1fr) #text(size: 9pt, item.dates)
        #linebreak()
        #text(weight: "bold", item.role)
        #for bullet in item.bullets [
          #parbreak()
          #block(inset: (left: 8pt))[#text("• ")#text(bullet)]
        ]
      ]
    } else {text(item); parbreak()}
  ]
]
