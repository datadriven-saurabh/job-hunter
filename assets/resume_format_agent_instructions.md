# Resume Format Specification for AI Coding Agent

## Purpose

Generate resumes that preserve the **same visual structure, section order, typography hierarchy, spacing style, and one-page layout** as the reference resume.

The resume content may change completely between candidates or job applications, but the **format must remain consistent**.

The reference resume is a one-page professional data/analytics resume with a centered identity header, horizontal-rule section headers, compact two-column alignment for metadata, and dense but readable experience bullets. The content includes sections for Profile, Education, Work Experience, Skills, Certifications, and Language Skills. The source resume follows this organization and content hierarchy. 

---

# 1. Output Requirements

Generate the resume as:

- **One page whenever reasonably possible**
- Standard **A4 portrait**
- Clean black-and-white professional design
- No decorative colors
- No sidebars
- No multi-column body layout
- No photo
- No graphics except simple contact icons and language proficiency dots
- ATS-friendly text
- Consistent typography throughout

The final PDF should visually resemble the reference resume as closely as possible.

---

# 2. Page Layout

## Page Size

Use:

```text
A4 portrait
210 mm × 297 mm
```

## Margins

Use approximately:

```text
Left:   15–17 mm
Right:  15–17 mm
Top:    10–12 mm
Bottom: 10–12 mm
```

The content should fill the page efficiently without appearing cramped.

---

# 3. Typography

Use a **serif typeface** similar to Times New Roman, Georgia, or Liberation Serif.

Preferred:

```text
Times New Roman
```

Fallback:

```text
Liberation Serif
Georgia
serif
```

Do not use modern sans-serif fonts for the main body.

## Font hierarchy

### Candidate Name

```text
Font size: 22–26 pt
Weight: Bold
Alignment: Center
```

### Section Headers

Examples:

```text
PROFILE
EDUCATION
WORK EXPERIENCE
SKILLS
CERTIFICATIONS
LANGUAGE SKILLS
```

Formatting:

```text
Font size: 10.5–12 pt
Weight: Bold
Case: UPPERCASE
Alignment: Left
```

Each section heading must sit directly above a thin horizontal divider.

### Main Body

```text
Font size: 9.5–10.5 pt
Line height: compact
Color: black
```

### Company / Institution Name

```text
Font size: same as body or slightly larger
Weight: Bold
Case: UPPERCASE for companies
```

### Role / Degree

Use italic formatting.

Example:

```text
EXAMPLE HEALTH, SENIOR ASSOCIATE - ANALYTICS
```

Render as:

- Company name: bold
- Role: italic
- Both on the same line whenever possible

### Dates and Location

```text
Font size: body size
Alignment: Right
```

Use:

```text
MM/YYYY – MM/YYYY | CITY, COUNTRY
```

For current roles:

```text
MM/YYYY – Current | CITY, COUNTRY
```

---

# 4. Header Structure

The top of the resume should follow this hierarchy:

```text
<CANDIDATE NAME>

<email icon> email
<phone icon> phone
<location icon> location

<linkedin icon> linkedin URL
```

## Candidate Name

Centered horizontally.

There should be generous white space above and below the name compared with body sections.

## First Contact Row

Center the following on one row:

```text
Email     Phone     Location
```

Use simple monochrome icons where possible.

Recommended icons:

```text
Envelope
Phone handset
Location pin
```

Do not use colored icons.

## Second Contact Row

Place LinkedIn on a separate centered row below the first contact row.

Example:

```text
[LinkedIn icon] https://www.linkedin.com/in/username/
```

Leave slightly more vertical space after LinkedIn before the first section.

---

# 5. Section Header Style

Every major section should use this pattern:

```text
SECTION TITLE
────────────────────────────────────────────
```

Rules:

- Left-aligned
- Bold
- Uppercase
- Thin black horizontal line extending nearly to the right margin
- Very small spacing between title and line
- Moderate spacing before the section heading
- Small spacing after the line

Do not place section titles inside boxes or shaded backgrounds.

---

# 6. Profile Section

Structure:

```text
PROFILE
────────────────────────────────────────────

One compact paragraph.
```

The paragraph should typically be:

```text
3–5 lines
```

Requirements:

- No bullets
- No first-person pronouns
- Dense, professional summary
- Focus on domain, years/level of experience, technical scope, business impact, and stakeholder ownership

Avoid excessive whitespace.

---

# 7. Education Section

Use a two-sided line:

```text
<Institution / Degree Information>                <Dates | Location>
```

Example structure:

```text
Example Technical University,            08/2016 – 07/2020 | EXAMPLE CITY, COUNTRY
BACHELOR OF TECHNOLOGY IN MECHANICAL
ENGINEERING
```

Formatting rules:

- Institution name: bold
- Degree: italic or italic + uppercase depending on length
- Date/location: aligned to the right
- Allow degree name to wrap naturally to the next line
- No bullets for education
- Keep the section compact

If multiple degrees exist, repeat the same structure vertically.

---

# 8. Work Experience Section

This is the dominant section of the resume.

Each role should follow:

```text
COMPANY, ROLE                                  DATE RANGE | LOCATION
• Achievement bullet
• Achievement bullet
• Achievement bullet
```

## Header line

Left:

```text
COMPANY, ROLE
```

Formatting:

- Company: bold uppercase
- Role: italic
- Same line

Right:

```text
MM/YYYY – MM/YYYY | CITY, COUNTRY
```

If the left side is long, preserve the right alignment by using a two-column row/table rather than spaces.

## Bullet style

Use:

```text
•
```

or a small solid round bullet.

Bullets should have:

```text
Hanging indent
Minimal left indentation
Compact vertical spacing
```

Do not use oversized bullets.

## Bullet writing style

Each bullet should be:

- 1–2 lines when possible
- Result-focused
- Start with a strong action verb
- Include numbers/metrics when genuinely supported
- Avoid filler
- Avoid separate "Responsibilities" subsections

Recommended pattern:

```text
Action + scope + method + measurable result
```

Example:

```text
• Built and scaled a central BI platform for 150+ users, delivering 50+ dashboards and reducing ad-hoc reporting by 60%.
```

## Number of bullets

For the most recent role:

```text
3–5 bullets
```

For older roles:

```text
2–4 bullets
```

The reference layout is dense, so prioritize the strongest achievements.

## Spacing between roles

Use only a small blank gap between companies.

Do not add horizontal lines between individual jobs.

---

# 9. Skills Section

Format skills as one or two compact text lines.

Example:

```text
Git/GitHub, Docker, GitLab, Apache Superset (BI), Airbyte, Power BI, Metabase, ...
```

Rules:

- Comma-separated
- No skill rating bars
- No icons
- No separate categories unless absolutely necessary
- Wrap naturally across lines
- Keep compact

If categories are needed, use inline formatting only:

```text
Data: SQL, Python, ClickHouse | BI: Power BI, Superset, Metabase
```

but prefer a simple comma-separated list to match the reference.

---

# 10. Certifications Section

Use bullet list format.

Example:

```text
• Google Data Analyst - Coursera
```

Rules:

- Small round bullet
- One line per certification where possible
- No detailed descriptions unless essential
- Keep compact

---

# 11. Language Skills Section

The reference resume uses a horizontal language proficiency layout.

Structure:

```text
HINDI        ● ● ● ● ●           ENGLISH        ● ● ● ● ○
```

Requirements:

- Language labels in uppercase
- Multiple languages can appear on the same row
- Use filled and unfilled circles/dots to indicate proficiency
- Maintain clean horizontal spacing
- Do not use progress bars

Suggested scale:

```text
● ● ● ● ● = Native / Full professional
● ● ● ● ○ = Professional
● ● ● ○ ○ = Intermediate
● ● ○ ○ ○ = Basic
● ○ ○ ○ ○ = Beginner
```

If generating a plain-text or ATS-only version, replace dots with a textual level, but the styled PDF should preserve the dot-based appearance.

---

# 12. Spacing Rules

The resume should feel compact.

Use approximately:

```text
Between major sections: 7–12 pt
Between section heading and content: 3–5 pt
Between job entries: 5–8 pt
Between bullets: 0–2 pt
Paragraph line spacing: 1.0–1.1
```

Do not use double spacing.

Do not allow large blank areas.

---

# 13. Alignment Rules

Use precise alignment rather than manual spaces.

Recommended implementation:

- Centered blocks for the header
- 2-column tables or flex rows for:
  - education metadata
  - company/role vs dates/location
- Full-width single column for:
  - profile
  - bullets
  - skills
  - certifications

Dates/locations must visually line up along the right edge.

---

# 14. Horizontal Rules

Use a thin line under every section title.

Suggested properties:

```text
Thickness: 0.5–1 pt
Color: black
Width: full content width
```

Do not use thick dividers.

Do not use gray boxes.

---

# 15. Content Compression Rules

If content exceeds one page, preserve the design by applying these changes in order:

1. Remove weaker or repetitive bullets
2. Shorten overly long bullets
3. Reduce paragraph wording
4. Reduce vertical spacing slightly
5. Reduce body font size slightly, but do not go below ~9 pt
6. Reduce margins slightly

Do NOT:

- Split the resume into two pages unless unavoidable
- Remove section headings
- Remove important quantified achievements
- Change to a completely different template

---

# 16. ATS Compatibility

The generated resume must remain machine-readable.

Requirements:

- Use real text, not images
- Avoid text embedded inside raster graphics
- Avoid complicated floating textboxes where possible
- Preserve logical reading order
- Use standard Unicode bullets
- Keep contact information as selectable text
- Use common fonts

Do not rely on icons alone for contact details.

---

# 17. Content Constraints

Content can change, but layout must remain fixed.

Variable content includes:

```text
Candidate name
Email
Phone
Location
LinkedIn
Profile summary
Education
Companies
Job titles
Dates
Locations
Achievements
Skills
Certifications
Languages
Language proficiency
```

Fixed presentation includes:

```text
One-page A4 layout
Centered header
Two-row contact block
Uppercase section headings
Horizontal divider under headings
Education alignment
Experience structure
Bullet style
Skills as compact inline list
Certification bullets
Language proficiency dots
Black-and-white serif typography
```

---

# 18. Recommended Generation Workflow

The AI agent should follow this sequence:

```text
1. Read candidate data
2. Normalize all dates and locations
3. Rank experience bullets by relevance/impact
4. Build content using the fixed section order
5. Render using the fixed typography/layout rules
6. Check whether the result fits on one page
7. Compress content if required
8. Export to PDF
9. Render PDF to image
10. Visually compare against reference format
11. Fix spacing/alignment issues
12. Export final PDF
```

---

# 19. Validation Checklist

Before finishing, verify:

- [ ] Resume is A4 portrait
- [ ] Resume is one page where feasible
- [ ] Candidate name is centered and bold
- [ ] Email, phone, and location appear in one centered row
- [ ] LinkedIn appears centered beneath them
- [ ] PROFILE appears first
- [ ] EDUCATION appears second
- [ ] WORK EXPERIENCE is the main body
- [ ] SKILLS follows experience
- [ ] CERTIFICATIONS follows skills
- [ ] LANGUAGE SKILLS appears last
- [ ] Every section heading is uppercase and bold
- [ ] Every section heading has a thin horizontal line underneath
- [ ] Company names are bold
- [ ] Roles are italic
- [ ] Dates and locations are right-aligned
- [ ] Experience bullets use compact round bullets
- [ ] Skills are comma-separated rather than boxed/tagged
- [ ] Language proficiency uses dots
- [ ] No colored elements
- [ ] No photo
- [ ] No sidebar
- [ ] No unexpected second page
- [ ] No clipped text
- [ ] No overlapping text
- [ ] PDF text is selectable
- [ ] Visual hierarchy matches the reference

---

# 20. Example Skeleton

```text
                          CANDIDATE NAME

     ✉ email@example.com      ☎ +91XXXXXXXXXX      ● City, Country

                  in linkedin.com/in/username/


PROFILE
────────────────────────────────────────────────────────────
Professional summary paragraph...

EDUCATION
────────────────────────────────────────────────────────────
University / Institution                           MM/YYYY – MM/YYYY | CITY, COUNTRY
DEGREE / PROGRAM

WORK EXPERIENCE
────────────────────────────────────────────────────────────
COMPANY, ROLE                                      MM/YYYY – Current | CITY, COUNTRY
• Achievement with measurable impact.
• Achievement with measurable impact.
• Achievement with measurable impact.

COMPANY, ROLE                                      MM/YYYY – MM/YYYY | CITY, COUNTRY
• Achievement.
• Achievement.

SKILLS
────────────────────────────────────────────────────────────
Skill 1, Skill 2, Skill 3, Skill 4, Skill 5, Skill 6...

CERTIFICATIONS
────────────────────────────────────────────────────────────
• Certification - Provider

LANGUAGE SKILLS
────────────────────────────────────────────────────────────
LANGUAGE 1      ● ● ● ● ●            LANGUAGE 2      ● ● ● ● ○
```

---

# 21. Non-Negotiable Instruction to the Coding Agent

**Do not redesign the resume.**

The candidate data may change, and bullet counts may vary slightly, but the generated resume must preserve the same visual language and structure as the reference:

```text
centered identity header
+
compact serif typography
+
uppercase section headings
+
horizontal divider lines
+
right-aligned dates/locations
+
dense achievement-focused bullets
+
inline skills
+
simple certification bullets
+
dot-based language ratings
```

If there is a conflict between adding more content and preserving the one-page reference layout, prioritize **concise content and format consistency**.
