---
name: job-postmortem
description: >
  Runs a post-mortem review on a completed larger job (or looks up past post-mortems
  before bidding a similar new job). Trigger phrases for the CAPTURE mode: "post-mortem
  this job", "let's do a job review for [address/number]", "close-out review for
  [job]", "record lessons learned on [job]", "review the [job] job". Trigger phrases
  for the LOOKUP mode: "what should I know before bidding [builder]", "check past
  issues with [builder]", "any lessons learned on [job type] jobs", "prep this bid",
  "have we worked with [builder] before, any watch-outs". Use CAPTURE mode any time a
  larger job has just wrapped and Vance wants to record how it went. Use LOOKUP mode
  any time Vance is sizing up or bidding a new job and wants to check history against
  the same builder or job type before finalizing the number.
compatibility: JobTread connector (JobTread:query / mcp__JobTread__query), Notion MCP (notion-* tools). Pairs with the `jobtread` skill.
---

# Job Post-Mortem

Captures structured lessons-learned reviews for completed larger jobs into the
**Job Post-Mortems** Notion database, and surfaces relevant past entries before
Vance bids a new job with a familiar builder or job type.

**Notion database:** `Job Post-Mortems`
**Data source ID:** `aacceccd-ca15-4cb9-ba47-982ae806e2fb`
**Database URL:** https://app.notion.com/p/a3494c23b05e460699b27b9922fd0f14
**JobTread org ID:** `22Nttsgz8iVp`

There is no fixed dollar threshold for what counts as a "larger job" — Vance
decides which completed jobs are worth reviewing (typically NC jobs, or any job
that ran noticeably over/under budget or had a rough builder relationship).
Don't prompt automatically on every job close-out.

---

## MODE 1: CAPTURE — Record a Post-Mortem

### Step 1: Identify the job

Look up the job by number, name, or address (one call; `like` is case-insensitive):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":5,"where":{"or":[["number","<n>"],["name","like","%<text>%"],[["location","address"],"like","%<text>%"]]}},
 "nodes":{"id":{},"number":{},"name":{},"closedOn":{},"location":{"formattedAddress":{},"account":{"name":{}}}}}}}
```
Confirm the match with Vance if it's not exact — show what was found, ask *"Is that the right job?"*

### Step 2: Pull what JobTread already knows (ONE call)

```json
{"job":{"$":{"id":"<jobId>"},"number":{},"name":{},"createdAt":{},"closedOn":{},"priceType":{},
 "projectedPrice":{},"projectedCost":{},"actualCost":{},
 "location":{"formattedAddress":{},"county":{},"account":{"name":{}}},
 "customFieldValues":{"$":{"size":30},"nodes":{"value":{},"customField":{"name":{}}}},
 "budget":{"_":"costItems","$":{"where":[["document","id"],"=",null]},"p":{"_":"sum","$":"price"},"c":{"_":"sum","$":"cost"}},
 "docs":{"_":"documents","$":{"where":["status","!=","denied"],"group":{"by":[["type"]],"aggs":{"n":{"count":"id"},"price":{"sum":"price"},"cost":{"sum":"cost"},"bal":{"sum":"balance"}}}},"withValues":{}},
 "changeOrders":{"_":"documents","$":{"where":{"and":[["type","customerOrder"],["name","Change Order"]]}},"count":{},"p":{"_":"sum","$":"price"}},
 "labor":{"_":"timeEntries","count":{},"min":{"_":"sum","$":"minutes"},"c":{"_":"sum","$":"cost"}},
 "firstTime":{"_":"timeEntries","$":{"size":1,"sortBy":[{"field":"startedAt"}]},"nodes":{"startedAt":{}}},
 "lastTime":{"_":"timeEntries","$":{"size":1,"sortBy":[{"field":"startedAt","order":"desc"}]},"nodes":{"startedAt":{}}},
 "inspections":{"_":"customFieldValues","$":{"where":[["customField","name"],"like","%Inspection%"]},"nodes":{"value":{},"customField":{"name":{}}}}}}
```
How to read it:
- **Builder/GC** = `location.account.name`. **Job Type / Category / Phase** = custom fields.
- **County** = `location.county` (Muskegon/Ottawa/Kent/Oceana); confirm with Vance.
- **Contract value** = `projectedPrice` (sum of approved customer orders incl. change orders).
- **Bid margin** = (budget p − budget c) / budget p. **Actual margin** = (invoiced price − actualCost) / invoiced
  price, where invoiced = `docs` row `customerInvoice.price` and `actualCost` = vendor bills + labor.
- **Change orders** = `changeOrders` count/sum. **Labor hours** = `labor.min` / 60.
- **Timeline** = first/last time entry dates + Underground / Rough-in / Final Inspection dates; `closedOn` if closed.
- `projectedPrice/projectedCost/actualCost` can be null (no approved order / no costs) — then ask Vance.

Never fabricate a figure that isn't in the data — skip it and ask Vance in Step 3.

### Step 3: Walk Vance through the review

Ask through these sections conversationally — don't demand a written essay for
each one, and let Vance skip anything not relevant to this job. Pre-fill
whatever was already pulled from JobTread in Step 2 and just ask him to confirm
or correct it rather than asking from scratch.

1. **Job Overview** — builder/GC, scope, contract value, planned timeline
   (start → rough-in → top-out → trim → final) vs. actual timeline
2. **Bidding & Estimating Accuracy** — was the bid accurate? What got missed
   or underestimated? Hidden conditions or code requirements not anticipated?
   If bidding this exact job again today, what would change in the number?
3. **Scheduling** — did our phases line up with the GC's schedule? Were
   delays ours, the GC's, or another trade's? Crew conflicts with concurrent
   jobs?
4. **Budget & Margin** — final margin vs. bid margin and why; biggest cost
   overruns; were change orders captured and billed or absorbed?
5. **Field & Technical Issues** — inspection/code issues (cite code sections
   if useful for next time), design conflicts, site conditions, material
   substitutions
6. **GC/Builder Relationship** — communication and payment behavior; would
   Vance want more work from this builder; any red flags?
7. **Crew & Labor** — right crew size/skill for the job? Was overtime driven
   by the estimate or by delays?
8. **Lessons Learned / Action Items** — 3-5 specific, actionable takeaways
   framed as things to do differently, not just observations
9. **Watch-Outs for Future Bids** — what should trigger a red flag on a
   similar job or with this same builder next time?

**Sections 8 and 9 are the ones Lookup mode actually surfaces later — don't
let Vance skip past these two even if he breezes through the rest.**

### Step 4: Resolve the Notion page properties

| Property | Source |
|---|---|
| Job Name / Address | Job address/name from Step 1 |
| Builder/GC | From Step 2/3 |
| Job Type | JobTread Job Type custom field → map to NR/NC/RR/CR |
| County | Inferred from address (Step 2), confirm with Vance |
| JobTread Job Link | `https://app.jobtread.com/jobs/<jobId>` (standard JobTread job URL; confirm it opens) |
| Contract Value | From Step 2/3 |
| Completion Date | Actual completion date from Step 1/3 |
| Bid Margin % | From Step 2/3 — enter as a decimal fraction (e.g. `0.22` for 22%) |
| Actual Margin % | From Step 2/3 — same decimal format |
| Issue Tags | Pick from: Scheduling, Bidding/Estimating, Change Orders, Materials, Labor, Inspection/Code, GC Communication, Crew, Design Conflict — select every tag that applied, based on Step 3 |
| Overall Grade | Ask Vance directly: Good / Mixed / Rough |
| Bid This Type Again | Ask Vance directly: Yes / Yes w/ changes / No |

### Step 5: Create the Notion page

Use `notion-create-pages` with `parent: {"data_source_id": "aacceccd-ca15-4cb9-ba47-982ae806e2fb"}`.
Set `properties` per Step 4. Build `content` using this exact section structure
(Notion markdown, `##` headers) filled in with Vance's answers from Step 3:

```
## 1. Job Overview
- **Builder/GC:**
- **Scope:**
- **Contract value:**
- **Planned timeline (start → rough-in → top-out → trim → final):**
- **Actual timeline:**

## 2. Bidding & Estimating Accuracy
...

## 3. Scheduling
...

## 4. Budget & Margin
...

## 5. Field & Technical Issues
...

## 6. GC/Builder Relationship
...

## 7. Crew & Labor
...

## 8. Lessons Learned / Action Items
- ...

## 9. Watch-Outs for Future Bids
- ...
```

### Step 6: Confirm to Vance

```
✅ Post-mortem recorded: "[Job Name / Address]"
   Builder: [name] | Type: [NR/NC/RR/CR] | County: [county]
   Bid margin → Actual margin: [X%] → [Y%]
   Overall grade: [Good/Mixed/Rough] | Bid again: [Yes/Yes w/ changes/No]
   Tags: [issue tags]
   [Notion page URL]
```

---

## MODE 2: LOOKUP — Check History Before Bidding

### Step 1: Identify what to search for

Get the builder name and/or job type Vance is bidding from context. If neither
is clear, ask: *"Which builder, or what type of job, should I check past
post-mortems for?"*

### Step 2: Query the Notion database

Use `notion-query-data-sources` (or `notion-search` scoped to the data source)
against data source `aacceccd-ca15-4cb9-ba47-982ae806e2fb`, filtering by
`Builder/GC` (text match) and/or `Job Type`. Pull matching pages, prioritizing:
- Any entry with `Bid This Type Again` = "No" or "Yes w/ changes"
- Any entry with `Overall Grade` = "Rough" or "Mixed"
- Otherwise, the most recent matches by `Completion Date`

Open the top matches and read their **Lessons Learned** and **Watch-Outs**
sections specifically — that's the content Vance actually needs before bidding.

### Step 3: Present a bid-prep brief

```
PAST POST-MORTEMS — [Builder name and/or Job Type]

[Job Name / Address] — [Completion Date] — Grade: [Good/Mixed/Rough] — Bid again: [Yes/Yes w/ changes/No]
  Margin: bid [X%] → actual [Y%]
  Watch-outs: [pulled from Section 9]
  Lessons: [pulled from Section 8]

... (repeat per matching job, most relevant first)

No matches found → say so plainly: "No past post-mortems on file for [builder/type] yet."
```

Keep it tight — this is meant to be skimmed in the middle of pricing a bid, not
read as a report.

---

## RULES

1. Sections 8 (Lessons Learned) and 9 (Watch-Outs) are the whole point of this
   system — never let a capture skip them, and always surface them first in
   Lookup mode.
2. Notion is the reference/knowledge layer; JobTread stays the transactional
   system of record. Don't duplicate full job data into Notion — only what's
   needed to make the review useful later (Step 4 property list).
3. Never fabricate a financial figure (margin, contract value) that couldn't
   be confirmed from JobTread — ask Vance directly instead.
4. Confirm fuzzy job/builder matches before acting, same as `create-job`.
5. Margin percentages are stored as decimal fractions in Notion (`0.22`, not
   `22`) — the property format is set to percent, so it will display as 22%.
6. Vance decides which jobs get a post-mortem — don't suggest running one
   automatically on every job status change to Closed.
