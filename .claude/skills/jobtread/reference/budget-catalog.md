# 03 — Budgets, Cost Items/Groups, Catalog, Codes/Types/Units, Selections, Backups

Org `22Nttsgz8iVp`. All IDs below verified by live read on 2026-09-29.

## 1. Where cost items/groups live (one type, 3 contexts)
`costItem` / `costGroup` are the same types in every context; context = which of `job` / `document` / (neither) is set.

| Context | job | document | Notes |
|---|---|---|---|
| Catalog item/template | null | null | `organization.costItems` / `organization.costGroups` |
| Job budget | set | null | |
| Document line (estimate/order/bill/invoice) | set | set | `jobCostItem` links back to budget line |

GOTCHAS
- `job.costItems` / `job.costGroups` INCLUDE document lines. Always filter budget: `"where":[["document","id"],"=",null]`.
- `organization.costGroups` includes every job/doc group (6k+). Catalog top-level templates: `and` of `[["parentCostGroup","id"],"=",null]`, `[["job","id"],"=",null]`, `[["document","id"],"=",null]`.
- `where:["parentCostGroup","=",null]` -> error "parentCostGroup is not queryable". Use nested path `[["parentCostGroup","id"],"=",null]`. `parentCostGroupId` does not exist.
- `where` must be the triple itself, not wrapped: `["quantityFormula","!=",null]` OK; `[["quantityFormula","!=",null]]` errors.
- `like` is case-insensitive (`%water heater%` matches "Water Heater").
- Too-big response -> "Request Entity Too Large": shrink `size` / fewer fields.
- `page` must be a `nextPage` token, not a number.

## 2. Fields (compact)
**costItem**: id, name, description, quantity, quantityFormula, unitCost, unitCostFormula, unitPrice, unitPriceFormula, cost, price, priceWithTax, isTaxable, allowanceType, costCode, costType, unit, costGroup, job, document, organization, jobArea (string), position (string sort key), organizationCostItem (catalog source), organizationCostGroup, sourceCostItem, jobCostItem (doc line -> budget line), jobCostItems, documentCostItems (budget line -> doc lines), timeEntries, hasFinalActualCost, isSpecification, requireSpecificationApproval, isSelected, isEditable, showDescription, showQuantity, customFieldValues, files, globalId, createdAt.
- No `actualCost` field on costItem (see §7).

**costGroup**: id, name, description, quantity, quantityFormula, unit, parentCostGroup, descendentCostGroups (ALL levels, not just children), descendentCostItems (ALL levels), job, document, organization, position, isSelected, isSimpleSelection, minSelectionsRequired, maxSelectionsAllowed, showChildren, showChildCosts, showChildDeltas, showDescription, files, createdAt.
- No direct `children`/`costItems` field; build tree from `parentCostGroup.id` + `costItem.costGroup.id`.

**costCode**: id, number, name, fullName, isActive, parentCostCode, qboId, qbdIntegrationItem, qboIntegrationItems.
**costType**: id, name, margin (0.25 = 25%), isTaxable, isTimeTrackable, isActive.
**unit**: id, name, isActive.
**allowanceType** enum: `"cost"` | `"costAndFee"` | `"price"` | null.

## 3. Reference tables (live, 2026-09-29)
### Cost codes (31)
| # | Name | id |
|---|---|---|
|0000|General|22PGuaqndJtF|
|0100|Permits|22PGuay8qTfR|
|0110|Residential Permits|22PGuaz95wxd|
|0120|Commercial Permits|22PGub2gzDsz|
|0200|Project Management|22PGuafWaht6|
|0210|Residential - Project Management|22PGuahjamFX|
|0220|Commercial - Project Management|22PGuakCUkki|
|1000|Labor|22P26sJzicHp|
|1100|Residential|22Nu4wQ9vk7v|
|1101|Residential - Demo|22PGuXLYB24i|
|1102|Residential - Underground|22PGuXWwuQSb|
|1103|Residential - Rough-In|22PGuXaBG6qU|
|1104|Residential - Finish|22PGuXbrubGn|
|1105|Residential - Warranty|22PGuXetKxkk|
|1106|Residential - Service|22PGv5xRw2P7|
|1200|Commercial|22NzQN5bNnct|
|1201|Commercial - Demo|22PGuYAvHCgp|
|1202|Commercial - Underground|22PGuYAxjPve|
|1203|Commercial - Rough-In|22PGuYAztbzZ|
|1204|Commercial - Finish|22PGuYB3iY5d|
|1205|Commercial - Warranty|22PGuYB5cPdZ|
|1206|Commercial - Service|22PGv5yhrcbW|
|1300|Other|22NzQNBF2DJJ|
|1400|Office|22PL8YtZfRHa|
|2000|Materials|22P26sPjEr7S|
|3000|Fixtures|22Nu4vetSqT8|
|4000|Appliances|22Nu4vZT4zks|
|5000|Subcontractor|22PGubiJwRsx|
|6000|Equipment Rentals|22PGubiLB9Bd|
|8000|Fees|22PGui5SvLEn|
|9999|Miscellaneous|22Nttshd4XSU|

NOTE: `3100 Residential Fixtures 22PGubiGEmz8` (cited in create-budget skill) does NOT exist anymore -> use 3000.

### Cost types (9)
| Name | id | margin |
|---|---|---|
|Labor|22Nttshd4XSV|0.25|
|Materials (Commodity)|22Nttshd4XSW|0.28|
|Subcontractor|22Nttshd4XSX|0.10|
|Other|22Nttshd4XSY|0.30|
|Fixtures|22Nu4hSz5GP6|0.35|
|Appliance|22Nu4v2LMuW7|0.30|
|Permit|22Nu4vPkEzVH|0|
|Fixtures (High-End)|22PVNw3Vqjux|0.23|
|Materials (Low Cost)|22PVNw88LHYW|0.50|

(create-budget skill's margin table is stale: says Materials 40%, Fixtures 20%, Appliance 25%.)

### Units (7)
Day 22Nttshd4XRj · Each 22Nttshd4XRk · Man Hour 22Nttshd4XRn · Foot 22Nttshd4XRp · Lump Sum 22Nttshd4XRq · Pound 22NxtezBSXpE · Pack 22PGW5rQYrRL

Verified present: 1106, 1206, 8000, 1300 codes; Labor/Other types; Man Hour/Lump Sum/Each units.

Re-enumerate query:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},
 "costCodes":{"$":{"size":100,"sortBy":[{"field":"number"}]},"nodes":{"id":{},"number":{},"name":{}}},
 "costTypes":{"$":{"size":50},"nodes":{"id":{},"name":{},"margin":{}}},
 "units":{"$":{"size":50},"nodes":{"id":{},"name":{}}}}}
```

## 4. Catalog templates (top-level catalog costGroups)
106 top-level catalog groups total. `*`-prefixed = main templates (23):

| Name | id | items |
|---|---|---|
|*New Construction - Residential|22PUu9kHNteF|126|
|*Renovation - Residential|22PdWL4tJjXB|106|
|*New Commercial Job|22P5x4sLCTad|98|
|*New Commercial Job (w/ Parameters)|22PMwbcBnF78|97|
|*Service - Generic|22PDZsraKgrY|6|
|*Fixture Allowances|22P9dyh7S3uV|2|
|*Eastwind Finish Plumbing|22PK5jgpg8Sb|45|
|*Water Service - Muskegon|22PR8QxwGQk2|18|
|**New Bathroom|22PUYabkBbJG|18|
|**New Kitchen|22PUYaYFRV4U|20|
|**Remodel Bathroom|22PUYadBSYKf|19|
|**Remodel Kitchen|22PUYaa7VRbr|20|
|**Materials - Copper & Brass|22PMb6BNhx9J|26|
|**Materials - PEX|22PMb65bXqm2|13|
|**Materials - Press Fittings|22PMb6Ei9WRE|18|
|**Materials - PVC|22PMb6N5evA8|76|
|**Stock Reorder|22PCa4QpZuXe|167|
|**Copper Materials|22NutnbMDxUg|5|
|**PEX Materials|22P52q7HQ2Hf|2|
|**PVC Materials|22NxtkbA47Y4|4|
|***Lavatory Components|22PCGzUkEW2A|4|
|***Shower Components|22PA2GZTPmJH|3|
|***Tub/Shower Components|22PA2GcUTPwH|2|

STALE ID: `*Residential New Build 22Nu4zsM2pmU` (used by create-budget skill) returns `null` — deleted. Current equivalent: `*New Construction - Residential 22PUu9kHNteF`. No `*Service Job` group exists; use `*Service - Generic 22PDZsraKgrY`.
`*Fixture Allowances` 22P9dyh7S3uV: subgroup "Fixture Allowances" 22PHFm8gKf2t; items Kitchen Fixture Allowance 22P9dyh7TXVe, Bathroom Fixture Allowance 22P9dyh7TXVf (allowanceType "price", unitCost/unitPrice null).
New Construction top sections: Underground Plumbing 22PUu9kHSFiq, Rough In Plumbing 22PUu9kHSFjJ, Finish Plumbing 22PUu9kHSFk2, Optional Additions 22PXc7cpJYBb (37 subgroups total, nested up to 4 deep).

List templates:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"costGroups":{"$":{"size":50,"sortBy":[{"field":"name"}],
 "where":{"and":[[["parentCostGroup","id"],"=",null],[["job","id"],"=",null],[["document","id"],"=",null],["name","like","*%"]]}},
 "count":{},"nodes":{"id":{},"name":{},"descendentCostItems":{"count":{}}}}}}
```

Full template tree + prices in ONE query (flat lists; rebuild tree via parent ids):
```json
{"costGroup":{"$":{"id":"22PDZsraKgrY"},"id":{},"name":{},
 "descendentCostGroups":{"$":{"size":100},"nodes":{"id":{},"name":{},"position":{},"quantity":{},"parentCostGroup":{"id":{}}}},
 "descendentCostItems":{"$":{"size":100},"count":{},"costSum":{"_":"sum","$":"cost"},"priceSum":{"_":"sum","$":"price"},
  "nodes":{"id":{},"name":{},"position":{},"costGroup":{"id":{}},"description":{},"quantity":{},"quantityFormula":{},
   "unitCost":{},"unitPrice":{},"isTaxable":{},"costCode":{"id":{}},"costType":{"id":{}},"unit":{"id":{}},
   "organizationCostItem":{"id":{}}}}}}
```
- Sort siblings by `position` (string, lexical). Template items carry `organizationCostItem.id` = the catalog item to pass as `organizationCostItemId` when copying.
- For 126-item templates use size 100 + `nextPage`, or split fields; watch response size.
- `*Service - Generic` contents: Service Call/Diagnostic Fee (9999/Other/Each, price 100), group "Service Description" 22PDZsraMZM2 > Plumbing Labor (Service) (1000/Labor/Man Hour 70/130), Labor - CS (1206), group "Plumbing Materials" 22PDZsraMZM4 > Warranty Accrual (1300/Other/Lump Sum); Service Call/Trip Charge (8000/Other/Each); Service Margin Target (9999, note item).

## 5. Catalog item search
Standalone catalog items: job, document AND costGroup all null.
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"costItems":{"$":{"size":10,
 "where":{"and":[[["job","id"],"=",null],[["document","id"],"=",null],[["costGroup","id"],"=",null],["name","like","%water heater%"]]}},
 "count":{},"nodes":{"id":{},"name":{},"unitCost":{},"unitPrice":{},"isTaxable":{},
  "costCode":{"id":{},"number":{}},"costType":{"id":{},"name":{}},"unit":{"id":{},"name":{}}}}}}
```
(46 hits for water heater; e.g. Rheem Gas WH 50 Gal Power Vent 22Nv2T5yf2J9 cost 1210 / price 1728.57, 4000/Appliance/Each.) Drop the costGroup filter to also match items inside catalog templates.

## 6. Reading a job budget
```json
{"job":{"$":{"id":"<jobId>"},"priceType":{},"lineItemsUpdatedAt":{},
 "projectedCost":{},"projectedPrice":{},"projectedPriceWithTax":{},"actualCost":{},
 "budgetGroups":{"_":"costGroups","$":{"size":50,"where":[["document","id"],"=",null]},
   "nodes":{"id":{},"name":{},"position":{},"parentCostGroup":{"id":{}}}},
 "budgetItems":{"_":"costItems","$":{"size":100,"where":[["document","id"],"=",null]},
   "count":{},"cost":{"_":"sum","$":"cost"},"price":{"_":"sum","$":"price"},
   "nodes":{"id":{},"name":{},"costGroup":{"id":{}},"quantity":{},"unitCost":{},"unitPrice":{},"cost":{},"price":{},
    "costCode":{"number":{}},"costType":{"name":{}},"unit":{"name":{}}}}}}
```
- Budget totals = sum over budget costItems (`cost`,`price`). `costItem.cost = quantity*unitCost`, `price = quantity*unitPrice`; null unitCost -> cost 0.
- Item with `costGroup: null` sits at job root.
- `job.projectedPrice` = sum of APPROVED customerOrder prices (verified 39965+274=40239). `projectedCost/projectedPrice` are null when no approved customer order (e.g. new jobs with only pending estimate). projectedCost is JT-computed (not equal to budget cost or approved-order cost; likely max(budget, actual) per line — unverified).
- `job.actualCost` (args optional `documentEndDate`, `timeEntryEndAt`) = sum(vendorBill document cost) + sum(timeEntry cost) — verified 8924.73+16749.79=25674.52.

## 7. Actual cost per budget line
```json
{"costItem":{"$":{"id":"<budgetCostItemId>"},"name":{},"cost":{},"hasFinalActualCost":{},
 "bills":{"_":"documentCostItems","$":{"where":[["document","type"],"=","vendorBill"]},"count":{},"c":{"_":"sum","$":"cost"}},
 "timeEntries":{"count":{},"c":{"_":"sum","$":"cost"},"min":{"_":"sum","$":"minutes"}}}}
```
- Vendor bill lines point at budget lines via `jobCostItem`; budget line's `documentCostItems` = all doc lines (estimates, orders, bills, invoices) — filter by `["document","type"]`.
- Time entries attach to a budget costItem (`timeEntry.costItem`), with `cost`, `minutes`, `hourlyRate`.
- `hasFinalActualCost` flag = actuals are final for that line.

## 8. Mutations (schema-verified; NOT executed)
Result read: mutations return `root`; select `createdCostItem` / `createdCostGroup` (root fields exist) inside, e.g.
`{"createCostItem":{"$":{...},"createdCostItem":{"id":{},"name":{}}}}`.

### createCostItem
Description: "Create a catalog cost item with an organizationId, a job budget cost item with a jobId, a document costItem with a documentId or an item in a group in any of those contexts with a costGroupId."
Context (give exactly one): `organizationId` | `jobId` | `documentId` | `costGroupId` (group implies its context).
Required: `name` (≤250). All else optional/nullable:
costCodeId, costTypeId, unitId, quantity, quantityFormula, unitCost, unitCostFormula, unitPrice, unitPriceFormula, description (≤4096), isTaxable (default **true**), allowanceType, organizationCostItemId (link to catalog), jobCostItemId (doc line -> budget line), sourceCostItemId, jobArea, customFieldValues {}, files [≤10], globalId, hasFinalActualCost (false), isEditable (false), isSelected (false), isSpecification (false), requireSpecificationApproval (true), showDescription (true), showQuantity (true), positionAfter `{"type":"costItem"|"costGroup","id":"..."}`.
```json
{"createCostItem":{"$":{"jobId":"<jobId>","costGroupId":null,"name":"Labor - RS","costCodeId":"22PGv5xRw2P7",
  "costTypeId":"22Nttshd4XSV","unitId":"22Nttshd4XRn","quantity":2,"unitCost":70,"unitPrice":130,"isTaxable":false,
  "organizationCostItemId":"<catalogItemId>"},"createdCostItem":{"id":{}}}}
```
(In a group: pass `costGroupId` instead of/with jobId — unverified whether both may be sent together; safest is costGroupId alone.)

### updateCostItem
`id` required; every createCostItem field optional (same names) + `costGroupId` (move), `positionAfter`. No context ids.
### deleteCostItem / deleteCostGroup
`{"id":"..."}` only. deleteCostGroup presumably deletes descendants (unverified).

### createCostGroup
Context: `organizationId` | `jobId` | `documentId` | `parentCostGroupId`. Required `name`.
Optional: description, quantity, quantityFormula, unitId, files, isSelected (false), isSimpleSelection (false), minSelectionsRequired (int≥0), maxSelectionsAllowed (int≥1), showChildren (true), showChildCosts (true), showChildDeltas (false), showDescription (true), positionAfter, **lineItems** (nested children, same shape as job lineItems below, max 1500).
### updateCostGroup
`id` + same optional fields + `parentCostGroupId`, `lineItems`.

### createJob / updateJob `lineItems`
Descriptions only say "Budget line items can be set with the `lineItems` input." createJob also has `copyCostsFromJobId` ("Copy the budget cost groups and cost items from another job").
`lineItems`: array (max 1500) of oneOf, discriminated by `_type` constant + presence of `id`:
- `newCostItem`: `{"_type":"costItem", name, ...createCostItem fields (no context ids)}`
- `existingCostItem`: `{"_type":"costItem","id":"...", ...optional updates}`
- `newCostGroup`: `{"_type":"costGroup", name, ..., "lineItems":[ ...recursive ]}`
- `existingCostGroup`: `{"_type":"costGroup","id":"...", ..., "lineItems":[...] }`
Groups nest by putting children in the group's own `lineItems`.
```json
{"updateJob":{"$":{"id":"<jobId>","lineItems":[
  {"_type":"costItem","name":"Service Call/Trip Charge","costCodeId":"22PGui5SvLEn","costTypeId":"22Nttshd4XSY",
   "unitId":"22Nttshd4XRk","quantity":1,"unitCost":0,"unitPrice":75,"isTaxable":false},
  {"_type":"costGroup","name":"Replace Shower Drain","lineItems":[
    {"_type":"costItem","name":"Labor - CS","costCodeId":"22PGv5yhrcbW","costTypeId":"22Nttshd4XSV","unitId":"22Nttshd4XRn",
     "quantity":4,"unitCost":90.92,"unitPrice":150,"isTaxable":false},
    {"_type":"costGroup","name":"Plumbing Materials","lineItems":[]}]}]}}}
```
REPLACE vs APPEND: NOT stated in schema and not testable read-only. The `existing*` variants (keep by id) strongly imply **updateJob.lineItems is the full desired budget (sync)** — items/groups omitted are likely deleted. Treat as REPLACE: to modify, read full budget and resend existing items with `id` plus new ones. To safely APPEND, use `createCostItem`/`createCostGroup` with `jobId` (or `costGroupId`/`parentCostGroupId`) instead. Every lineItems change bumps `job.lineItemsUpdatedAt` and auto-creates a `jobBudgetBackup` (observed backup ~1s after update).

### Formulas
`quantityFormula` / `unitPriceFormula` / `unitCostFormula` reference job parameters and built-ins in braces, e.g.
`5+if({waste type}="sewer",0,1)+if({house size}="small",-1,0)`, `if({Price-Structure}='Service',{Unit Cost}*3,{Unit Cost}/(1-{Margin}))`. Job parameters set via createJob/updateJob `parameters` (see jobs ref). `quantity` holds evaluated result.

### Other cost-related root mutations (exist; inputs not expanded)
createCostCode/updateCostCode/deleteCostCode, createCostType/deleteCostType, createUnit/deleteUnit, create/deleteCostCodeMapping, create/deleteCostTypeMapping, create/deleteUnitMapping, `createTasksFromBudget {jobId}`.

## 9. Specifications / selections
- Item as spec: `isSpecification: true`, `requireSpecificationApproval` (default true). Job fields: `specificationsDescription`, `specificationsFooter`, `specificationsKey`, `useSimpleSelections`.
- Selection groups: costGroup with `minSelectionsRequired` / `maxSelectionsAllowed`, `isSimpleSelection`; chosen options flagged `isSelected` on items/groups. `showChildDeltas` shows price deltas.
- `createSelectionAssignment {jobId, assignee, isDocumentRecipient:boolean, requireSignature:boolean}`; type `selectionAssignment {id, job, membership, isDocumentRecipient, requireSignature}`; `job.selectionAssignments`. update/deleteSelectionAssignment exist.
- Allowances: `allowanceType` "price" | "cost" | "costAndFee".

## 10. Job budget backups
Type `jobBudgetBackup {id, createdAt, createdByUser, job, url}` (`url` = download file). Read-only via `job.jobBudgetBackups`; NO create/restore mutation in API.
```json
{"job":{"$":{"id":"<jobId>"},"jobBudgetBackups":{"$":{"size":5,"sortBy":[{"field":"createdAt","order":"desc"}]},
 "nodes":{"id":{},"createdAt":{},"createdByUser":{"name":{}},"url":{}}}}}
```
