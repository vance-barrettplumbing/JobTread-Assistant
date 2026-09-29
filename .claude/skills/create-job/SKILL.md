---
name: create-job
description: >
  Create a new job in JobTread for Barrett Plumbing Inc. Use this skill any time the user
  wants to set up a new construction, renovation, commercial, water service, or warranty job. This is NOT
  for service jobs — use the create-service-job skill for those. Trigger phrases include:
  "create a job", "new job", "add a job", "set up a job for [builder/address]", "create a
  new construction job", "add a renovation job", "create a commercial job", "set up a
  warranty job", or any time the user describes a plumbing job that needs to be added to
  JobTread and it is not a service call. Always use this skill when the user provides a job
  address or job name and wants it added to the system.
compatibility: JobTread connector (mcp__JobTread__query / JobTread:query). Pairs with the `jobtread` skill.
---

# Create Job

Creates a complete job in JobTread (customer → location → job with all custom fields) in as few
API calls as possible. All calls use the single JobTread query tool (`JobTread:query` /
`mcp__JobTread__query`). IDs below were verified against the live org on 2026-09-29. For
anything not covered here, see the `jobtread` skill.

Org ID: `22Nttsgz8iVp`. Put `"$":{"notify":false}` at the root of every write.

---

## Inputs

| Field | Required? | Notes |
|-------|-----------|-------|
| Job address or name | Required | Used in job name and location |
| Customer name | Required | Builder or homeowner |
| Category | Required | Residential · Commercial · Water Service · Misc |
| Job Type | Required | New Construction · Renovation · Maintenance / Repair · Warranty (Service → use create-service-job) |
| Price type | Required | Fixed-Price (default) or T&M / Time & Material → Cost-Plus |
| Requested start date | Optional | Ask; leave blank if unknown |
| Water | Optional | City Water or Well Water |
| Sewer | Optional | City Sewer or Septic System |
| Lead source | Optional | Existing Customer (default) · Referral · Google Local Service Ads · Google Ads · Yard Sign · Website |
| Additional notes | Optional | Anything that doesn't fit other fields |

"T&M", "time and material", "time & material", "T and M" → Cost-Plus. Everything else → Fixed-Price.

---

## Steps

### Step 1: Look up next job number, customer and locations (ONE call)

```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"nextRecordNumber":{},
 "accounts":{"$":{"size":5,"where":{"and":[["type","customer"],["name","like","%<customer words>%"]]}},
  "nodes":{"id":{},"name":{},"locations":{"$":{"size":20},"nodes":{"id":{},"name":{},"address":{}}}}}}}
```
- `nextRecordNumber` = the job number to use (string). If missing, ask the user.
- `like` is case-insensitive; try a shorter/distinctive word if no hit.
- **Exact match:** use it. **Close match:** ask *"I found [Name] — is that the right customer?"* **No match:** create it (Step 3).
- Location: exact address match → use it. Close match → confirm. Multiple candidates → ask. None → create (Step 3).

### Step 2: Collect missing inputs
Ask once for anything missing from the Inputs table (always ask about start date, water, sewer if
not mentioned; leave blank if unknown).

### Step 3: Create customer / location if needed
```json
{"$":{"notify":false},"createAccount":{"$":{"organizationId":"22Nttsgz8iVp","name":"<Customer>","type":"customer","notify":false,
  "customFieldValues":{"22NtuUcUet4g":["Residential"]}},"createdAccount":{"id":{},"name":{}}}}
```
(Customer `Category` 22NtuUcUet4g is required and multi-select: Commercial · Residential · Other. Customer
`Type` 22NtuUffekM7 is also required/multi-select — set `["Builder"]`, `["Contractor"]`, `["Homeowner"]`,
or `["Company/Business"]` as appropriate. If the create errors on the array form, retry with a plain string.)

```json
{"$":{"notify":false},"createLocation":{"$":{"accountId":"<accountId>","address":"<full street, city, MI zip>","name":"<street address>"},
  "createdLocation":{"id":{},"formattedAddress":{}}}}
```
Location name = street address (e.g. "123 Easy Street") unless the user specifies otherwise.
Don't ask for contact details unless the user volunteers them (then `createContact` — see `jobtread` skill).

### Step 4: Resolve field values

**Job name:** `<number> | <address or job name>` e.g. `1102 | 123 Easy Street`.
**JobTread limits job names to 30 characters** — abbreviate (St, Ave, Dr, drop city) if needed and tell the user.

**Description:** 1–2 professional, plumbing-specific sentences, e.g. *"New construction underground,
rough-in and finish plumbing for a single-family home."*

**Job-level fields (not custom fields):**
| Field | Rule |
|---|---|
| `priceType` | `fixed` (Fixed-Price) or `costPlus` (T&M) |
| `defaultRetainagePercentage` | Residential: `0`. Commercial: ask *"Should I turn on retainage for this job?"* Yes → `0.1` (org default 10%, or the % they give); No → `0` |
| `qboClassId` (QBO class) | see table below |

QBO class (ids inferred from existing jobs):
| Category / Job Type | qboClassId |
|---|---|
| Residential New Construction | `1054766` |
| Residential Renovation | `1054768` |
| Commercial New Construction | `1054765` |
| Commercial Renovation | `1054767` |
| Water Service (category) | `1054764` |
| Residential Service / Maintenance / Repair | `1054763` |
| Commercial Service / Maintenance / Repair | `1054762` |
| Warranty or Misc | no class exists — leave unset and tell the user to set it in JobTread if needed |

**Custom fields** (key = custom field id, value = exact option string):
| Field | id | Value |
|---|---|---|
| Category | `22NtuVNPeBDB` | per input |
| Job Type | `22NtuVAwrQWC` | per input |
| Phase | `22Nuh4aSVtcP` | `Pipeline: Bidding` (or `1-Won: Not Scheduled` if user says it's already won) |
| Job Bid Won? | `22PNFqqnCnDc` | `Pending` (or `Yes` if already won) |
| Time & Material? | `22NxLZJtH5yV` | `true` if T&M, else omit (defaults false) |
| Water | `22PHPBrdSr9U` | `City Water` / `Well Water` — only if known |
| Sewer | `22PHn4jUqgg4` | `City Sewer` / `Septic System` — only if known |
| Permit Authority | `22NwvgcvUTpd` | matched option string — only if matched (see below) |
| Lead Source | `22PdvqBZgZcD` | only if user gave one (defaults to Existing Customer) |
| Notes | `22NtuVH4QTJY` | markdown bullet list of extras, incl. `- Requested start: YYYY-MM-DD` |

Leave these at their defaults (don't send): Stage (Not Started), RYG (❔), Rough-In Fixtures Ordered,
Fixtures Ordered, Post-Mortem Done, Financial Review Done.

There is no "Requested Start Date", "AIA Billing" or "Track Retainage" custom field — start date goes in
Notes, retainage is `defaultRetainagePercentage`, and AIA billing is chosen later by using the
"AIA Invoice" document template.

**Permit Authority:** fetch the live option list and match the job's city/township:
```json
{"customField":{"$":{"id":"22NwvgcvUTpd"},"options":{}}}
```
Options look like `"Norton Shores: 231-799-6801, 1 | Water Dept: 231-799-6804"` — match on the name before
the first `:`; send the **entire** option string exactly. Note aliases in the list (e.g. Fruitland,
Ravenna, Spring Lake Twp/Village → "… = Michigan Township"). Service area: Muskegon, Ottawa, Kent,
Oceana counties. No confident match → leave blank and tell the user.

### Step 5: Create the job — ONE call, all fields
Set Category and Job Type **in this create call** (not afterward): the "Job Created Trigger" workflow reads
them at creation to auto-import the right to-do template (Residential New Construction → "Residential New
Build Estimating"; Commercial → "New Commercial Job (Planning)"; Water Service → "Water Service"). Don't add
those to-dos yourself.

```json
{"$":{"notify":false},"createJob":{"$":{
   "locationId":"<locationId>","number":"<nextRecordNumber>","name":"1102 | 123 Easy Street",
   "description":"<description>","priceType":"fixed","defaultRetainagePercentage":0,"qboClassId":"1054766",
   "customFieldValues":{
     "22NtuVNPeBDB":"Residential","22NtuVAwrQWC":"New Construction","22Nuh4aSVtcP":"Pipeline: Bidding",
     "22PNFqqnCnDc":"Pending","22PHPBrdSr9U":"City Water","22PHn4jUqgg4":"City Sewer",
     "22NwvgcvUTpd":"<exact Permit Authority option>","22NtuVH4QTJY":"- Requested start: 2026-11-01\n- Lot 14, Sunrise Estates"}},
 "createdJob":{"id":{},"number":{},"name":{}}}}
```
If the call errors on a custom field value, fix that value (check spelling/options) and retry — don't drop it silently.

### Step 6: Verify and confirm
Read it back in one call:
```json
{"job":{"$":{"id":"<jobId>"},"number":{},"name":{},"priceType":{},"defaultRetainagePercentage":{},"qboClassId":{},
 "location":{"formattedAddress":{},"account":{"name":{}}},
 "customFieldValues":{"$":{"size":30},"nodes":{"value":{},"customField":{"name":{}}}}}}
```
Report:
```
✅ Job #[number] created: "[job name]"
   Customer: [customer] | Location: [address]
   Category: [..] | Type: [..] | Phase: [..] | Bid Won: [..]
   Price Type: [Fixed-Price / Cost-Plus] | Retainage: [0% / 10%]
   QBO Class: [id / —] | Water: [..] | Sewer: [..]
   Permit Authority: [name / —]
   Notes: [summary / —]
```

---

## Edge Cases
- **Fuzzy customer/location match:** always show and ask. Unit numbers / spelling differences → confirm.
- **Service job routed here:** if they want a full service setup (budget + schedule task), use `create-service-job`.
- **Name > 30 chars:** shorten and show the user the final name.
- **Commercial retainage:** always ask — never assume.
- **Duplicate check:** if a job at the same location already exists (`location.jobs`), mention it before creating.
- **Can't delete:** the Claude connector cannot delete jobs. If a job was created wrong, fix it with `updateJob`
  (same fields; `customFieldValues` merges), or close it with `updateJob{id, closedOn:"YYYY-MM-DD"}` and tell the user.
