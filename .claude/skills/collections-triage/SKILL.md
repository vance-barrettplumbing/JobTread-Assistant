---
name: collections-triage
description: Pulls overdue customer invoices from JobTread and routes them by customer type. Builder/GC invoices surface as a manual call-list only — no drafts, no lien language, ever. Homeowner invoices get a Gmail draft using the existing Day 7/14/30 sequence, held for human review before sending. Run this on a schedule (Monday/Thursday) or on demand when asked to check overdue invoices, AR, or collections status.
---

# Collections Triage

Pulls overdue invoices from JobTread, splits them by customer type, and takes
different action on each track. This is a data-pulling and drafting layer —
it never sends anything and it never threatens a builder.

**Two tracks, not one aging ladder:**

- **Builder/Contractor track** — surfaces as a call-list. No draft, no tier
  language, no internal note implying escalation. Barrett Plumbing depends on
  repeat builder relationships; a formulaic dunning process is the wrong tool
  for a 2-4 account relationship where a late invoice is often just a normal
  AP cycle or an unresolved punch-list item, not delinquency.
- **Homeowner track** — the tier-ladder / auto-draft workflow, using the tone
  from Vance's existing three-stage sequence (Day 7 / 14 / 30).

**Retainage check:** Some jobs withhold retainage on each invoice (job `defaultRetainagePercentage`,
e.g. 0.1 = 10%), which leaves the withheld amount as an open `balance` on an otherwise-paid invoice. If an
invoice's `balance` ≈ the job's retainage % × `price` (within $1) and `amountPaid` > 0, tag it
**"likely retainage"** — list it in its own summary section and take no action on it (no note, no draft).
Retainage is released at project close-out, not chased as past due. Otherwise treat the balance as valid
and past due; don't second-guess it against job status.

---

## WORKFLOW

1. Pull all overdue customer invoices from JobTread
2. Classify each invoice's account as Builder or Homeowner via the `Type`
   custom field
3. For each invoice, check its last-logged stage (state check, not a time
   window) and act only if the stage has changed
4. Builder track → internal note only, added to call-list output
5. Homeowner track → internal note + Gmail draft (never sent)
6. Present a single summary split by track

---

## STEP 1: PULL OVERDUE INVOICES

Use the JobTread query tool (`JobTread:query` / `mcp__JobTread__query`). Org id `22Nttsgz8iVp`.
One call returns everything needed (verified 2026-09-29). Open invoices are `status: "pending"`;
`{"date":{}}` = today. Page with `"page":"<nextPage>"` if `nextPage` is not null.

```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},
 "documents":{"$":{"size":100,
   "where":{"and":[["type","customerInvoice"],["status","pending"],["balance",">",0],["dueDate","<",{"date":{}}]]},
   "sortBy":[{"field":"dueDate"}]},
  "count":{},"nextPage":{},"total":{"_":"sum","$":"balance"},
  "nodes":{"id":{},"fullName":{},"number":{},"balance":{},"price":{},"amountPaid":{},"dueDate":{},"description":{},
   "job":{"id":{},"number":{},"name":{},"defaultRetainagePercentage":{},"location":{"formattedAddress":{}}},
   "account":{"id":{},"name":{},
     "type":{"_":"customFieldValues","$":{"size":20,"where":[["customField","id"],"22NtuUffekM7"]},"nodes":{"value":{}}},
     "primaryContact":{"name":{},"firstName":{},
       "email":{"_":"customFieldValues","$":{"where":[["customField","id"],"22Nttshd5e9u"]},"nodes":{"value":{}}}}}}}}}
```
Notes:
- The customer is `document.account` (there is no `job.account`).
- `Type` = customer custom field `22NtuUffekM7` (multi-select; one value row per selected option).
  Current options: New Lead · Discovery · New Customer · Current Customer · Previous Customer ·
  Rely Home Lead · Key Customer · Builder · Contractor · Homeowner · Company/Business · Lead Lost.
- Email = contact custom field `22Nttshd5e9u`. `fullName` is like "Invoice 645-36"; use `number` as the invoice #.
- Invoice "description"/"covering the …" text: use the job name (minus the "#### | " prefix) if the
  document description is boilerplate.

For each invoice, compute:
- **Days past due**: today minus `dueDate`
- **Customer type**: `Type` is a multi-select dropdown — an account can have
  more than one value selected. Read **all** `customFieldValues` nodes
  returned for that account's `Type` field, not just the first one.
  - If **any** selected value exactly matches "Builder" or "Contractor"
    (case-insensitive exact match — these are fixed dropdown option
    strings, not free text, so do not substring-match) → **Builder track**,
    overriding any other value selected on that account.
  - No values returned (blank/unset), or values returned but none match
    "Builder"/"Contractor" → **Homeowner track**.
  - Verified 2026-09-29: "Builder" and "Contractor" are the only
    builder-adjacent options in the dropdown (full list in Step 1 notes).
  - Values other than Builder/Contractor that are known options (e.g. Key
    Customer, Current Customer, Homeowner, Company/Business) are NOT
    "unrecognized" — they route to Homeowner silently unless the account
    also has Builder/Contractor. Only flag values not in the Step 1 list.
  - **Unknown-value flag:** if an account's `Type` field returns a value
    that is neither "Builder," "Contractor," nor blank (i.e. some other
    dropdown option, including ones that don't exist yet), do not silently
    classify it as Homeowner. Route it to Homeowner track as the default,
    but add it to a separate "⚠️ UNRECOGNIZED TYPE VALUE" section in the
    Step 6 summary so a newly added dropdown option doesn't quietly get
    misrouted without anyone noticing.

---

## STEP 2: DETERMINE STAGE

Same stage boundaries apply to both tracks — they're used for state-tracking
("has this invoice moved since we last touched it"), not for tone on the
builder side.

| Stage | Days Past Due |
|-------|---------------|
| Stage 1 | 7-13 |
| Stage 2 | 14-29 |
| Stage 3 | 30+ |

Invoices at 1-6 days past due: skip entirely, no action, not included in
output. Too early to be meaningful on either track.

---

## STEP 3: CHECK STATE (NO TIME WINDOW)

This runs on a fixed schedule (Monday/Thursday), so dedup is based on the
**last stage logged**, not a rolling day-count window.

For each invoice, pull the most recent internal note/comment matching the
`Collections:` prefix:

```json
{"job":{"$":{"id":"<jobId>"},
 "comments":{"$":{"where":{"and":[["targetType","job"],["name","like","Collections:%"]]},
   "sortBy":[{"field":"createdAt","order":"desc"}],"size":1},
  "nodes":{"name":{},"createdAt":{}}}}}
```
(Batch several jobs in one request with aliases: `"j1":{"_":"job","$":{"id":"A"},...},"j2":{"_":"job",...}`.)

Parse the stage out of the note name (format defined in Step 4/5 below). If
the parsed stage matches the invoice's current computed stage, **skip** —
already handled at this stage, nothing has changed. If the stage is
different (including "no note found" → any stage is new), proceed to act.

---

## STEP 4: BUILDER/CONTRACTOR TRACK — CALL LIST ONLY

**Do not create a Gmail draft. Do not use lien, work-stoppage, or demand
language anywhere in this track — not in the note, not in the summary.**

### A. Log an internal note (state marker only, neutral tone)

```json
{
  "$": { "notify": false },
  "createComment": {
    "$": {
      "targetType": "job",
      "targetId": "<jobId>",
      "isVisibleToInternalRoles": true,
      "isVisibleToCustomerRoles": false,
      "name": "Collections: Stage <N> — Invoice #<number>",
      "message": "Flagged for manual follow-up. Balance $<balance>, <days> days past due. Surfaced on <date> collections run."
    }
  }
}
```

The note exists purely so the next run can read it back for the state check
— it is not an escalation record and should never be phrased as one.

### B. Add to the call-list section of the summary

No draft is generated. This invoice goes into the output for Vance to make
a judgment call on — a phone call, a note on the next builder check-in, or
nothing at all if he already knows why it's sitting there.

---

## STEP 5: HOMEOWNER TRACK — DRAFT FOR REVIEW

### A. Log the internal note (same format as Step 4A)

Same note format, same purpose — state tracking for the next run.

### B. Consolidate by customer

If a homeowner has more than one overdue invoice, combine them into a
single draft rather than sending one per invoice. Use the **highest** stage
among their invoices to select the tone/template. List every invoice
number and its individual balance in the body — never just a total.

### C. Create the Gmail draft — never send

Pull the customer's email from `contacts.customFieldValues` (type
`emailAddress`) resolved in the Step 1 query. Use the template matching the
stage below (Step 5D). Use the multi-invoice version whenever more than
one invoice is being consolidated for this homeowner (Step 5B), and fill
`{invoice_count}`, `{invoice_numbers}` (comma-separated), `{total_balance}`
accordingly.

**Multi-property check:** if the consolidated invoices are tied to more
than one distinct `job_address`, do not auto-fill the Stage 3 lien bullet.
Instead, generate the draft with the lien bullet left as
`[MULTIPLE PROPERTIES — REVIEW LIEN LANGUAGE BEFORE SENDING]` and call this
out explicitly in the Step 6 summary. This is a legal-language edge case
that needs a human decision, not a template fill.

`{followup_date}` (Stage 3 only) = today + 7 days, computed by the skill —
not left blank.

Phone and mailing address are hardcoded into the templates below
(231-865-6356 / 3720 Ida Ave, Fruitport, MI 49415). If either changes,
edit them directly in this file — nothing else references these values.

```json
Gmail:create_draft
{
  "to": ["<customer email>"],
  "subject": "<from template below, invoice number(s) filled in>",
  "body": "<from template below, balance/due date/invoice number(s) filled in>"
}
```

Verify the exact Gmail tool name in this environment before running.

**Never call any send/mark-as-sent function. Draft only.**

---

### D. Homeowner Email Templates

Pulled from Vance's existing overdue invoice sequence (Mike/Comms agent
config), with signature corrected — original drafts read "Vance Barrett,"
which is wrong; the owner is Vance McClenton, "Barrett Plumbing" is the
company name only. Do not write new copy — use these exactly.

#### Stage 1 — 7-13 days past due (Friendly reminder)

**Subject (single invoice):**
`Friendly reminder — Invoice #{invoice_numbers} from Barrett Plumbing`

**Subject (multiple invoices):**
`Friendly reminder — {invoice_count} open invoices from Barrett Plumbing`

**Body:**

```
Hi {first_name},

Hope the project is coming along well. I wanted to send a quick note —
{invoice_line} had a due date of {due_date}.

If payment has already been sent, please disregard this — and thank you!
If not, no worries, we just wanted to make sure it didn't slip through the
cracks.

You can pay by check made out to Barrett Plumbing Inc., or reach out and we
can discuss other arrangements.

Thanks as always for the opportunity to work together. Let me know if you
have any questions.

Vance McClenton
Barrett Plumbing Inc.
231-865-6356 | barrettplumbing.com
```

Where `{invoice_line}` is:
- Single: `Invoice #{invoice_number} for ${amount}, covering the {description} at {job_address},`
- Multiple: `you have {invoice_count} open invoices totaling ${total_balance} — #{invoice_numbers}, for work at {job_address_or_addresses} —`

---

#### Stage 2 — 14-29 days past due (Firm follow-up)

**Subject (single invoice):**
`Second notice — Invoice #{invoice_numbers} now {days_past_due} days past due`

**Subject (multiple invoices):**
`Second notice — {invoice_count} invoices now past due, ${total_balance} total`

**Body:**

```
Hi {first_name},

I'm following up on my message from last week regarding {invoice_line}

{invoice_line_2} now {days_past_due} days past the original due date. We
haven't received payment or a response to our earlier reminder, so I
wanted to reach out directly to make sure everything is okay on your end.

If there's a billing question, a dispute, or something we can help
resolve, please let me know — I'm happy to talk through it. If payment is
simply delayed, I'd appreciate a quick note so we can note that on our
end.

We take pride in our work and value the relationship, and I'd like to get
this resolved without any further escalation.

Please remit payment or contact me at 231-865-6356 at your earliest
convenience.

Vance McClenton
Barrett Plumbing Inc.
231-865-6356 | barrettplumbing.com
```

Where:
- Single: `{invoice_line}` = `Invoice #{invoice_number} for ${amount} — the {description} completed at {job_address}.` / `{invoice_line_2}` = `This invoice is`
- Multiple: `{invoice_line}` = `the {invoice_count} open invoices — #{invoice_numbers}, totaling ${total_balance}.` / `{invoice_line_2}` = `These invoices are`

---

#### Stage 3 — 30+ days past due (Final notice)

**Subject (single invoice):**
`FINAL NOTICE — Invoice #{invoice_numbers} | Immediate payment required`

**Subject (multiple invoices):**
`FINAL NOTICE — {invoice_count} invoices, ${total_balance} | Immediate payment required`

**Body:**

```
Hi {first_name},

This is a formal final notice regarding {invoice_line}

Despite two prior reminders, {this_that} remains unpaid as of today — now
{days_past_due} days past the original due date.

If we do not receive payment or a confirmed payment arrangement by
{followup_date}, Barrett Plumbing Inc. will have no choice but to pursue
the following:

  • Filing a mechanics lien against the property at {job_address}
  • Referral of the account to a collections agency
  • Suspension of services on any open or future projects

We do not take these steps lightly, and we would strongly prefer to
resolve this directly. If there is a legitimate dispute or a situation
we're not aware of, please contact me immediately.

Payment can be made by check payable to Barrett Plumbing Inc., mailed to
3720 Ida Ave, Fruitport, MI 49415.

Vance McClenton
Barrett Plumbing Inc.
231-865-6356 | barrettplumbing.com
```

Where:
- Single: `{invoice_line}` = `Invoice #{invoice_number} in the amount of ${amount} for plumbing services completed at {job_address}.` / `{this_that}` = `this invoice`
- Multiple: `{invoice_line}` = `{invoice_count} invoices — #{invoice_numbers}, totaling ${total_balance}, for plumbing services completed at {job_address_or_addresses}.` / `{this_that}` = `these invoices`

**Multi-job lien note:** if consolidated invoices span more than one
property, name each property or use "against the relevant properties" —
see the multi-property check in Step 5C. Never auto-generate a
single-address lien bullet against invoices from different job sites.

---

## STEP 6: PRESENT SUMMARY

```
COLLECTIONS TRIAGE — <date>

BUILDER/CONTRACTOR — CALL LIST (no drafts created)
  <Builder name> — Job: <job name> — Invoice #<num> — $<balance> — <days> days past due — Stage <N>
  ...

HOMEOWNER — DRAFTS CREATED FOR REVIEW
  <Homeowner name> — Invoice(s) #<num(s)> — $<total balance> — Stage <N> — draft ready in Gmail
  ...

⚠️ MULTI-PROPERTY LIEN LANGUAGE — NEEDS REVIEW BEFORE SENDING
  <Homeowner name> — invoices span <N> properties — lien bullet left blank in draft
  ...

⚠️ UNRECOGNIZED TYPE VALUE — DEFAULTED TO HOMEOWNER, VERIFY
  <Account name> — Type field value: "<value>" — not "Builder," "Contractor," or blank
  ...

LIKELY RETAINAGE — NO ACTION (balance = job retainage % of invoice)
  <Customer> — Job: <job name> — Invoice #<num> — $<balance> held (<pct>% of $<price>)
  ...

SKIPPED (stage unchanged since last run)
  <count> invoices, no action needed

TOTAL OVERDUE AR: $<sum of all balances>
```

---

## RULES

1. Builder/Contractor track never generates a draft, never uses lien or
   escalation language, in the note or in the summary.
2. Homeowner track drafts are never sent — draft only, always held for
   human review.
3. Dedup is by last-logged stage, not a time window. An invoice sitting at
   the same stage across multiple runs is only touched once, until it
   crosses into the next stage.
4. Invoices 1-6 days past due are ignored entirely.
5. A blank or missing `Type` custom field defaults to Homeowner.
6. Multiple overdue invoices for the same homeowner get consolidated into
   one draft, using the highest stage present.
7. Multiple overdue invoices for the same builder are listed individually
   on the call list — do not consolidate, since Vance may want to raise
   them separately depending on which job they're tied to.
8. Invoices whose open balance matches the job's retainage % of the
   invoice price are "likely retainage" — report separately, no note, no draft.
9. Never fabricate or guess at email copy for the homeowner track — pull
   from the Step 5D templates only.
