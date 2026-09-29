---
name: jobtread
description: >
  Fast, token-efficient operating manual for JobTread (Barrett Plumbing, Inc.) via the JobTread
  Pave API (`mcp__JobTread__query` / `JobTread:query`). Use it ANY time the user wants to look up,
  report on, create, or change anything in JobTread — jobs, customers/vendors, contacts, locations,
  custom fields (Phase, Stage, Job Type…), budgets/cost items/catalog, estimates, invoices, bills,
  POs, payments, AR/AP, schedule/tasks/to-dos, daily logs, time entries, comments, files. Also use it
  whenever another skill (create-job, create-service-job, create-budget, collections-triage,
  job-postmortem) calls `jobtread_*` tools, to translate those steps into Pave queries. Contains
  verified org IDs, schema, filter syntax and recipes so you do NOT need to introspect the schema.
---

# JobTread (Pave API) — Barrett Plumbing

Everything here was verified against the live org on 2026-09-29. **Do not introspect the schema
unless a query errors or you need something not covered here/in `reference/`.**

## Tool
One tool: `mcp__JobTread__query` (in claude.ai it may be named `JobTread:query`), arg `{"query": {...}}`.
Older skills mention `jobtread_search_jobs`, `jobtread_create_job`, `jobtread_add_budget_line_items`,
etc. — those tools don't exist here; do the equivalent with the recipes below.

## Constants (stable)
| Thing | ID |
|---|---|
| Organization (Barrett Plumbing, Inc.) | `22Nttsgz8iVp` |
| Vance McClenton user / membership | `22NttsgymKnw` / `22Nttsgz8iVq` |
| CF Phase / Stage / Job Type / Category | `22Nuh4aSVtcP` / `22PWKUDHJHj5` / `22NtuVAwrQWC` / `22NtuVNPeBDB` |
| CF RYG / Job Bid Won? / Time & Material? | `22P7sttAr6Je` / `22PNFqqnCnDc` / `22NxLZJtH5yV` |
| CF Permit Authority / Notes / Lead Source | `22NwvgcvUTpd` / `22NtuVH4QTJY` / `22PdvqBZgZcD` |
| CF customer Type / contact Email / Mobile / Office | `22NtuUffekM7` / `22Nttshd5e9u` / `22NtuUntj3U9` / `22NtuUs8sjn3` |
| Units Each / Man Hour / Lump Sum / Foot | `22Nttshd4XRk` / `22Nttshd4XRn` / `22Nttshd4XRq` / `22Nttshd4XRp` |
| Cost types Labor / Materials / Fixtures / Other / Permit | `22Nttshd4XSV` / `22Nttshd4XSW` / `22Nu4hSz5GP6` / `22Nttshd4XSY` / `22Nu4vPkEzVH` |
Full tables (all 60 custom fields + option lists, 31 cost codes, 9 cost types, units, staff,
roles, task types/templates, document templates, file tags) are in `reference/`.

## Golden rules
1. **Writes are live production data.** Before any create/update, state exactly what you'll change and
   get the user's OK (unless they already clearly asked for that exact change). Read back after writing.
2. **The claude.ai grant CANNOT delete** (no `delete*` actions). To "remove" things: close jobs
   (`closedOn`), void docs (`status:"denied"`), archive accounts (`archive:true`), or tell the user to
   delete in the UI.
3. **Suppress emails/pings**: put `"$":{"notify":false}` at the query root on writes, and also pass
   `notify:false` where an input has it (updateDocument, createAccount, createTask, copyTaskTemplateToTarget,
   createDailyLog default to `true`). Only notify when the user asks to send/notify.
4. JobTread **workflows/webhooks fire on your writes** (jobCreated, jobUpdated, taskUpdated,
   documentUpdated, contactCreated, accountCreated, locationCreated → Zapier/Make). Expect side effects.
5. **Never invent prices.** Copy unitCost/unitPrice from the catalog/templates; only change quantities
   unless told otherwise.
6. Confirm fuzzy matches (customer, location, job) with the user before using them.

## Syntax cheat sheet
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},
  "jobs":{"$":{"size":20,"where":{"and":[["closedOn",null],["name","like","%smith%"]]},
               "sortBy":[{"field":"createdAt","order":"desc"}]},
    "count":{},"nextPage":{},"nodes":{"id":{},"number":{},"name":{}}}}}
```
- Select scalars with `{}`; must name subfields of objects. Args go in `"$"`.
- Connections: `nodes count nextPage sum avg min max values withValues`; args `where sortBy size page group with expressions`.
- **Default size 10 (also for nested lists like customFieldValues!), max 100.** Page with `"page":"<nextPage>"`.
- `where`: `["f",v]` (=), `["f","op",v]` op ∈ `= != < <= > >= like "not like" in "not in" between "not between"`;
  `{"and":[..]}`/`{"or":[..]}`; null: `["f",null]` / `["f","!=",null]`; between: `["f","between",[a,b]]`.
- Related fields need a path array: `[["job","id"],X]`, `[["location","account","name"],"like","A%"]`.
  `["job",X]` or `"jobId"` → error "not queryable".
- `=` and `like` are **case-insensitive**; `%` wildcard.
- Aliases: `"openCount":{"_":"jobs","$":{...},"count":{}}`; sums: `"total":{"_":"sum","$":"price"}`. Batch many in one call.
- Dates: `"YYYY-MM-DD"`; relative: `{"date":{}}` (today), `{"datetime":{"fromNow":"-P30D","startOf":"month"}}`.
- Group by: `"$":{"group":{"by":[["type"],["status"]],"aggs":{"n":{"count":"id"},"t":{"sum":"price"}}}}` → read `withValues`.
- `job.number` is a **string** (sort by `createdAt`, not number). `document.number` is an int (per-job).
- Mutations: `{"createX":{"$":{...},"createdX":{"id":{},"name":{}}}}`. Updates return root — read back with
  e.g. `{"updateJob":{"$":{...}},"job":{"$":{"id":"J"},"name":{}}}` in the same request or a follow-up.
- Custom field values on create/update: `"customFieldValues":{"<customFieldId>":"<exact option string>"}`
  (bool → true/false, date → "YYYY-MM-DD", null clears).
- Deeper: `reference/query-language.md` (expressions, `with` subqueries, HAVING, error table).

## Data model
`account` (type `customer`|`vendor`) → `contact`s, `location`s → `job` (belongs to location).
Job's customer = `job.location.account` (no `job.account`). Contact email/phone are **customFieldValues**, not fields.
Budget = `job.costItems/costGroups` where `[["document","id"],"=",null]` (without that filter you also get document lines).
Documents: `type` ∈ `customerOrder` (estimate/quote/proposal/change order) · `customerInvoice` (invoice/deposit/credit memo)
· `vendorOrder` (PO/work order) · `vendorBill` (bill/expense) · `bidRequest`. Kind is told by `name`.
`status` ∈ `draft pending approved denied`. Invoices/bills: pending = open, approved = paid, denied = void.
**Vendor docs carry their amount in `cost` (price = 0).**
Money on job: `projectedPrice` (approved customer orders), `actualCost` (vendor bills + time), `projectedCost`.

## Core recipes (read)
Find job by number / text (then use its id everywhere):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":5,"where":{"or":[["number","1097"],["name","like","%1097%"],[["location","address"],"like","%1097%"]]}},"nodes":{"id":{},"number":{},"name":{},"closedOn":{},"location":{"id":{},"formattedAddress":{},"account":{"id":{},"name":{}}}}}}}
```
Job snapshot (custom fields, money, doc totals, budget totals) in ONE call:
```json
{"job":{"$":{"id":"J"},"number":{},"name":{},"priceType":{},"closedOn":{},"projectedPrice":{},"projectedCost":{},"actualCost":{},
 "location":{"formattedAddress":{},"account":{"name":{}}},
 "customFieldValues":{"$":{"size":30},"nodes":{"value":{},"customField":{"name":{}}}},
 "docs":{"_":"documents","$":{"where":["status","!=","denied"],"group":{"by":[["type"],["status"]],"aggs":{"n":{"count":"id"},"p":{"sum":"price"},"c":{"sum":"cost"},"b":{"sum":"balance"}}}},"withValues":{}},
 "budget":{"_":"costItems","$":{"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"},"c":{"_":"sum","$":"cost"}}}}
```
Open jobs by Phase (custom-field filter pattern — reuse for any CF):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":50,"with":{"cf":{"_":"customFieldValues","$":{"where":[["customField","id"],"22Nuh4aSVtcP"]},"values":{"$":"value"}}},"where":{"and":[["closedOn",null],[["cf","values"],"in",["2-Active: Scheduled","3-Active: Underground","4-Active: Rough-In","5-Active: Finish"]]]}},"count":{},"nodes":{"id":{},"number":{},"name":{}}}}}
```
Open AR (add `["dueDate","<",{"date":{}}]` for overdue); AP = `vendorBill` + pending:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"documents":{"$":{"size":50,"where":{"and":[["type","customerInvoice"],["status","pending"],["balance",">",0]]},"sortBy":[{"field":"dueDate"}]},"count":{},"total":{"_":"sum","$":"balance"},"nodes":{"id":{},"fullName":{},"dueDate":{},"balance":{},"account":{"name":{}},"job":{"number":{},"name":{}}}}}}
```
Schedule next 7 days (overlap filter; always `targetType job` to skip template tasks):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"tasks":{"$":{"size":50,"where":{"and":[["isToDo",false],["targetType","job"],["startDate","<=","END"],["endDate",">=","START"],[["job","closedOn"],"=",null]]},"sortBy":[{"field":"startDate"},{"field":"startTime"}]},"nodes":{"id":{},"name":{},"startDate":{},"startTime":{},"endDate":{},"completed":{},"job":{"number":{},"name":{}},"assignedMemberships":{"nodes":{"user":{"name":{}}}}}}}}
```
Customer / vendor lookup: `organization.accounts` where `{"and":[["type","customer"],["name","like","%x%"]]}` →
`id name primaryContact{name customFieldValues{nodes{value customField{name}}}} locations{nodes{id name address}}`.
Catalog item search: `organization.costItems` where `{"and":[[["job","id"],"=",null],[["document","id"],"=",null],["name","like","%water heater%"]]}`.

## Core recipes (write) — confirm first, `"$":{"notify":false}` at root
New customer → location → job (job name ≤ 30 chars, format `"<number> | <desc>"`; next number = `organization.nextRecordNumber`):
```json
{"$":{"notify":false},"createAccount":{"$":{"organizationId":"22Nttsgz8iVp","name":"Jane Doe","type":"customer","notify":false},"createdAccount":{"id":{}}}}
{"$":{"notify":false},"createLocation":{"$":{"accountId":"A","address":"123 Easy St, Muskegon, MI 49441","name":"123 Easy St"},"createdLocation":{"id":{}}}}
{"$":{"notify":false},"createJob":{"$":{"locationId":"L","number":"1102","name":"1102 | 123 Easy St","priceType":"fixed","customFieldValues":{"22NtuVNPeBDB":"Residential","22NtuVAwrQWC":"New Construction","22Nuh4aSVtcP":"Pipeline: Bidding","22PNFqqnCnDc":"Pending"}},"createdJob":{"id":{},"number":{},"name":{}}}}
```
Contact: `createContact{accountId,name,customFieldValues:{"22Nttshd5e9u":"a@b.com","22NtuUntj3U9":"+12315551234"}}`.
Update CF / close job: `updateJob{id, customFieldValues:{...}}`, `updateJob{id, closedOn:"YYYY-MM-DD"}`.
**Add** budget lines (safe append — do NOT use `updateJob.lineItems` to append; it likely replaces the whole budget):
```json
{"$":{"notify":false},"createCostItem":{"$":{"jobId":"J","name":"Labor - RS","costCodeId":"22PGv5xRw2P7","costTypeId":"22Nttshd4XSV","unitId":"22Nttshd4XRn","quantity":2,"unitCost":91.4,"unitPrice":130,"isTaxable":false},"createdCostItem":{"id":{}}}}
```
Into a group: `createCostGroup{jobId,name}` → `createCostItem{costGroupId, ...}` (use `costGroupId` alone). Nested groups:
`createCostGroup{parentCostGroupId, name}` or pass nested `lineItems` to createCostGroup. Details: `reference/budget-catalog.md`.
Task: `createTask{targetType:"job",targetId:J,name,isToDo:false,startDate,endDate,startTime:"07:30",taskTypeId,assignedMembershipIds:[..],notify:false}`;
complete = `updateTask{id,progress:1}`; apply template = `copyTaskTemplateToTarget{taskTemplateId,targetType:"job",targetId,startDate,notify:false}`.
Internal note: `createComment{targetType:"job",targetId:J,name:"Subject",message:"...",isVisibleToInternalRoles:true,isVisibleToCustomerRoles:false,isVisibleToVendorRoles:false}`.
Documents, payments, sending: `reference/documents-payments.md` (createDocument needs `jobId,type,name,fromName,toName,taxRate`; no template-id input; `updateDocument` notifies by default).

## Staff (membershipId for tasks; userId for time entries)
Vance `22Nttsgz8iVq`/`22NttsgymKnw` · Noah Carter `22NupN9w3esb`/`22NupN9w2v62` · Daryk Swanson `22NupN9wh5nF`/`22NupN9weqQW`
· Chris Barrett `22NupP4EhDFQ`/`22NupP4EgTSp` · John McCarthy `22Nv8KKhSB5y`/`22Nv8KKhRRHP` · Lucas Burns `22P3z3jqUgZB`/`22P3z3jqVpG4`

## Conventions (Barrett Plumbing)
- Service job: priceType `costPlus` when T&M, T&M?=true, Job Bid Won?=N/A, Stage=Active, RYG=🟢, Job Type=Service,
  Permit Authority=No Permit; template `*Service - Generic` `22PDZsraKgrY`; schedule template `*Service Job` `22PV95WNRxYJ`.
- Bid/construction/renovation: priceType `fixed`, Job Bid Won?=Pending, Phase=Pipeline: Bidding, Stage=Not Started, RYG=❔.
- Budget templates: `*New Construction - Residential` `22PUu9kHNteF`, `*Renovation - Residential` `22PdWL4tJjXB`,
  `*New Commercial Job` `22P5x4sLCTad`, `*Fixture Allowances` `22P9dyh7S3uV`. (`22Nu4zsM2pmU` "*Residential New Build" is DELETED.)
- Times are stored UTC; org time zone America/Detroit. Time-entry week starts Thursday.

## Reference files (read only the one you need)
| File | Covers |
|---|---|
| `reference/query-language.md` | where/expressions/with/group/paging/aggregates, root options, grant permissions, error table, token tips |
| `reference/jobs-crm-customfields.md` | job/account/contact/location inputs, ALL custom fields + options (Permit Authority list), QBO class ids, users, roles |
| `reference/budget-catalog.md` | cost items/groups, lineItems shape, cost codes/types/units, catalog templates, template tree query, actual cost per line, formulas, selections |
| `reference/documents-payments.md` | document types/status, 36 document templates, createDocument/updateDocument/sendDocument, payments, AR/AP recipes |
| `reference/tasks-logs-time-files.md` | tasks/to-dos, task types & templates, daily logs, time entries, comments, files/uploads, events, webhooks, workflows |

If something here turns out wrong, fix it with a quick introspection
(`{"schema":{"$":{"path":"job"}}}`, `{"schema":{"$":{"expand":true,"path":"root.createJob"}}}`,
`{"schema":{"$":{"path":"root","search":"kw"}}}`) and tell the user so the skill can be updated.
