# Source Selection and License Audit

This benchmark seed uses a conservative source policy because the intended public release is international.

## Inclusion Rules

A source can be used in the public benchmark if at least one condition is true:

1. It is a Public Data Portal source with `이용허락범위 제한 없음`.
2. It is a statute, rule, ordinance, public notice, or similar official text that is outside copyright protection under Korean Copyright Act Article 7.
3. It is marked as KOGL Type 0, KOGL Type 1, or KOGL AI Type.
4. It has explicit written permission for benchmark redistribution.

For KOGL Type 2, Type 3, and Type 4, use only after confirming that the intended release and any transformation obey the type conditions. This seed does not rely on those types.

## Exclusion Rules

Exclude by default:

- Private insurance clauses and riders
- Private bank product descriptions
- Private construction-company brochures, floor plans, images, and announcement PDFs
- Personal application, complaint, consultation, or civil petition documents
- Any source with unclear third-party rights

## Current Evidence

Public Data Portal policy states that public data containing copyrights or third-party rights must secure legitimate permission from the rights holder and that public-domain labels identify permission scope.

The KOGL guide states:

- Type 0 permits free use without attribution.
- Type 1 requires attribution and permits commercial/non-commercial use and derivative works.
- Type 2 is non-commercial only.
- Type 3 prohibits derivatives.
- Type 4 is non-commercial and no-derivatives.
- AI Type permits AI training use without attribution, including commercial and derivative use.

Korean Copyright Act Article 7 excludes categories such as laws, treaties, orders, ordinances, rules, national/local government notices, public announcements, instructions, court judgments, and similar official materials from copyright protection.

## Release Policy

Release:

- QA annotations
- Source IDs
- Official source URLs
- Evidence locators
- Deterministic evaluation scripts
- Small derived factual answers

Do not release:

- Raw PDFs/HWPs unless explicit permission is verified
- Screenshots or rendered pages
- Long copied excerpts
- Private-source text

## Practical Annotation Guidance

For housing announcement tasks, annotators should cite an official source locator such as:

- Portal page URL
- Announcement page URL
- Attachment filename
- Page number
- Section heading
- Table heading
- Row/column key

The public dataset should store only these locators and the short gold answer. Systems under evaluation can fetch or be provided source documents separately under the applicable source terms.

