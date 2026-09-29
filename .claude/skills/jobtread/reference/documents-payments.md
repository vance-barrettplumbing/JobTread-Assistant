# 04 — Documents, Payments, Templates, Recipients (Pave API)

Org `22Nttsgz8iVp`. All below verified by introspection or live read unless marked UNVERIFIED. No mutations were executed.

## 1. Document model

`documentType` enum: `customerOrder` | `customerInvoice` | `vendorOrder` | `vendorBill` | `bidRequest`
`documentStatus` enum: `draft` | `pending` | `approved` | `denied`
`paymentMethod` enum: `ach` | `card`. `qboDocumentType`: bill, creditCardCredit, creditMemo, invoice, purchase, refundReceipt, vendorCredit.

There are NO separate types for estimate / change order / credit memo / PO. The kind is `type` + `name` (the name comes from the template):
| Business doc | type | name(s) seen |
|---|---|---|
| Estimate / Quote / Proposal / Selection / T&M order / Membership | customerOrder | Estimate, Quote, Proposal, Selection(s), Time & Material Order, Membership |
| Change order | customerOrder | `Change Order` |
| Customer invoice | customerInvoice | Invoice, Deposit, Progress Invoice, AIA Invoice, Membership Invoice |
| Credit memo | customerInvoice | `Credit Memo` (negative `price`, e.g. -150; amountPaid = price, balance 0) |
| PO / work order / SOW | vendorOrder | Purchase Order, Work Order, SOW, Stocked Parts, Misc |
| Vendor bill | vendorBill | Bill, Expense, Stocked Material Costing |
| RFQ | bidRequest | Bid Request, RFQ |

### Status meaning (verified by grouping all 3768 docs)
- Invoices & bills: `pending` = open/unpaid (ONLY status with balance != 0), `approved` = paid in full, `denied` = voided, `draft` = not sent.
- Orders (customer/vendor): `pending` = sent/awaiting, `approved` = accepted (sets `closedAt`), `denied` = declined. Orders always have `balance` 0.

### Key fields (document)
- Ids/links: `id`, `type`, `name`, `number` (int, per-job sequence), `fullName` (e.g. `"Invoice 645-36"` = name + jobNumber-number; filterable), `job{}`, `account{}` (customer or vendor), `organization`, `task`, `jobArea`.
- Money (number): `price` (customer-side sell), `priceWithTax`, `tax`, `taxRate` (0–1), `cost`, `amountPaid`, `balance`, `nonRecoverableTax`.
  - **GOTCHA: vendor docs (vendorOrder/vendorBill) have price = 0; their amount is `cost`.** Bill balance = cost − payments.
  - Customer docs: amount is `price`/`priceWithTax`; `cost` = internal cost of lines.
- Dates: `issueDate`, `dueDate` (date `YYYY-MM-DD`), `dueDays`, `createdAt`, `closedAt`, `signedAt`.
- Party: `fromName`, `toName`, `toEmailAddress`, `toPhoneNumber`, `toAddress`, `toOrganizationName`, `from*` equivalents.
- Content: `subject`, `description`, `footer`, `emailMessage`, `closeMessage`, cover page fields.
- Flags: `includeInBudget`, `requireSignature`, `allowPartialPayments`, `isPaymentApplication`, `showProgress`, `showProfit`, `showQuantity`, `showChildCosts`, `qboIsIgnored`…
- QBO: `qboId`, `qboDocumentType`, `qboInvoiceLink`.
- Connections: `costItems`, `costGroups`, `documentPayments`, `documentRecipients`, `referencedDocuments`, `referencedTimeEntries`, `scheduledDocuments`, `files`, `comments`, `events`.
- `signedByUser`, `closedByUser`, `allowanceCostItem`, `profitBreakdown[{name,percentage}]`.

Filterable/sortable verified: `type`, `status`, `name`, `fullName`, `balance`, `dueDate`, `issueDate`, `number`, `createdAt`, `[ "job","id" ]`, `["job","number"]`, `["account","name"]`, `["account","type"]`.
Aggregatable (sum/avg/min/max) verified: `price`, `cost`, `balance`, `amountPaid`, `priceWithTax`.
`["document","id"]` is queryable on costItems; bare `"document"` is not (`document is not queryable`). Same for `job` → use `["job","id"]`.

### Document cost items
`document.costItems.nodes{ name cost price quantity unitCost unitPrice costCode{name} jobCostItem{id name} sourceCostItem{id} }`
`jobCostItem` = link to the job budget line (verified on bills). Budget lines = job costItems with `[["document","id"],"=",null]`.

### Parent/child docs
`referencedDocuments` (connection) + `createDocumentReference{documentId, reference:{_type:"document"|"timeEntry", id}}`. In samples bills/invoices had empty `referencedDocuments`; costItem-level linkage (`jobCostItem`, `sourceCostItem`) is how invoices/bills tie to budget/orders.

## 2. Templates (org, 36 total) — `organization.documentTemplates{id name templateName type}`
| id | name | templateName | type |
|---|---|---|---|
| 22P4uP9ikTkL | Estimate | With Deposit | customerOrder |
| 22P4uQMaYcLq | Estimate | No Deposit | customerOrder |
| 22PTD4jXMg2t | Estimate | Renovation, With Deposit | customerOrder |
| 22Nttshd4XSu | Quote | Quote w/ Deposit | customerOrder |
| 22PHGvHE39A3 | Quote | Quote no Deposit | customerOrder |
| 22NvBdxGs6W9 | Proposal | New Residential Build | customerOrder |
| 22P53DgzR4m9 | Proposal | Cost Plus, No Deposit | customerOrder |
| 22PU47S6sANC | Proposal | Cost Plus, w/ Deposit | customerOrder |
| 22P6YZNNuAhY | Proposal | Commercial Proposal | customerOrder |
| 22Nttshd4XSw | Change Order | Default | customerOrder |
| 22Nttshd4XSv | Selections | Default | customerOrder |
| 22NuJthYfXSD | Time & Material Order | Default | customerOrder |
| 22PUVMivTv2J | Membership | Gold Shield Care Plan | customerOrder |
| 22Nttshd4XSx | Deposit | Default | customerInvoice |
| 22Nttshd4XSy | Invoice | Builder Invoice | customerInvoice |
| 22Nuh6M6sDkA | Invoice | Builder (T&M) | customerInvoice |
| 22NzMFssMDRZ | Invoice | Customer Invoice | customerInvoice |
| 22NzMGWyk84M | Invoice | Customer T&M | customerInvoice |
| 22PAJ9YszKem | Invoice | Company T&M Invoice | customerInvoice |
| 22PU45Btnu82 | Invoice | Builder, Cost Plus | customerInvoice |
| 22PU488Jq4Fi | Invoice | Cost Plus | customerInvoice |
| 22Nttshd4XSz | Progress Invoice | Default | customerInvoice |
| 22PULQu8ZeSF | AIA Invoice | Default | customerInvoice |
| 22PUVPHPDhmf | Membership Invoice | Default | customerInvoice |
| 22PFfWNvJkms | Credit Memo | Credit | customerInvoice |
| 22Nttshd4XT2 | Purchase Order | Default | vendorOrder |
| 22NxeCCsdp7v | Purchase Order | Stock Order | vendorOrder |
| 22NzMFawTC7B | Work Order | Default | vendorOrder |
| 22PJb7JgaT3Q | SOW | Subcontractor Scope of Work | vendorOrder |
| 22PDVxz2ksU4 | Stocked Parts | Default | vendorOrder |
| 22P6m2seAiVb | Misc | Counts | vendorOrder |
| 22Nttshd4XT3 | Bill | Default | vendorBill |
| 22PTcTZgJj4e | Expense | Default | vendorBill |
| 22PdyqHNxF7F | Stocked Material Costing | Default | vendorBill |
| 22Nttshd4XSt | Bid Request | Default | bidRequest |
| 22P5xELcaDkC | RFQ | Default | bidRequest |
Template fields also: fromName, footer, emailMessage, dueDays, requireSignature, taxName, scheduledDocuments, show* flags.
**GOTCHA: `createDocument` has NO documentTemplateId input.** Copy the template's fields (name, footer, emailMessage, dueDays, fromName, flags…) into createDocument yourself. Template id is only used in `scheduledDocuments[].createFromDocumentTemplateId`.

## 3. Mutations (from schema; none executed)
Result selection pattern: `{"createDocument":{"$":{...},"createdDocument":{"id":{},"fullName":{}}}}`. Root result fields exist: `createdDocument`, `createdDocumentPayment`, `createdDocumentRecipient`, `createdDocumentTemplate`, `createdPayment`.

### createDocument — required: `jobId`, `type`, `name`(≤128), `fromName`, `toName`, `taxRate`(0–1)
Optional: `accountId` (customer/vendor account), `issueDate`, `dueDate`, `dueDays`, `subject`, `description`, `footer`, `emailMessage`, `tax`, `taxName`, `toEmailAddress`, `toPhoneNumber`, `toAddress`, `toOrganizationName`, `from*`, `jobLocationName/Address`, `includeInBudget`(default true), `requireSignature`(false), `allowPartialPayments`(false), `paymentMethods`[ach,card], `isPaymentApplication`, `taskId`, `references[{_type:"document"|"timeEntry",id}]`, `scheduledDocuments[{name,amount|percentage,createFromDocumentTemplateId,taskId,sendOnCreation}]`(≤20), `files[]`, `qbo*`, show* flags, `lineItems[]` (≤1500).
No `status` input on create (new docs start as draft — UNVERIFIED); set status via updateDocument.

`lineItems` = array of oneOf; each element has `_type`:
- new cost item `{_type:"costItem", name(req, ≤250), quantity, unitCost, unitPrice, costCodeId, costTypeId, unitId, description, isTaxable(true), jobCostItemId, organizationCostItemId, sourceCostItemId, customFieldValues, allowanceType, *Formula}`
- existing cost item: same + `id`
- new cost group `{_type:"costGroup", name(req), description, quantity, lineItems:[...nested], showChildren, isSelected, min/maxSelections…}`; existing group adds `id`.
- Link a doc line to a budget line with `jobCostItemId` (how invoices/bills/POs hit budget items).
```json
{"createDocument":{"$":{"jobId":"JOB","type":"customerInvoice","name":"Invoice","fromName":"Barrett Plumbing, Inc.","toName":"Hope Builders","accountId":"ACCT","taxRate":0,"issueDate":"2026-09-29","dueDays":30,
 "lineItems":[{"_type":"costItem","name":"Rough-in","quantity":1,"unitCost":800,"unitPrice":1000,"jobCostItemId":"JCI"}]},
 "createdDocument":{"id":{},"fullName":{},"price":{}}}}
```
Alternative: `createCostItem` / `createCostGroup` accept `documentId` to add lines to an existing doc.

### updateDocument — required `id`; everything else optional
Includes `status` (draft/pending/approved/denied), `lineItems` (full replace — UNVERIFIED semantics), dates, to/from, tax, `closeMessage`, `signaturePath`, `accountId`, `scheduledDocuments[{id,…}]`, etc.
**GOTCHA: `notify` defaults to TRUE** → pass `"notify":false` to avoid emailing on status/edits.
- Approve: `{"status":"approved"}`; Void invoice/bill: `{"status":"denied"}` (matches observed voided docs); Back to draft: `"draft"`.
No `closedAt` input; closing happens on approval.

### deleteDocument `{id}`
### sendDocument `{documentRecipientId (req), emailMessage?}` — sends to ONE recipient; create recipient first.
### createDocumentRecipient `{documentId, assignee, requireSignature=false}`
`assignee` oneOf: `{"membership":{"membershipId":"…"}}` | `{"role":{"roleId":"…"}}` | `{"user":{"name":"…","emailAddress":"…","phoneNumber?":…,"accountType?":…}}`.
updateDocumentRecipient `{id, requireSignature?, signatoryName?, signaturePath?, footerSignaturePaths?}`; deleteDocumentRecipient `{id}`.
Flow to email an invoice: createDocumentRecipient → createdDocumentRecipient.id → sendDocument.

### Payments: two layers
- `payment` = money movement (includes bank-feed transactions!). `createPayment` required: `organizationId`, `amount`(>0, 2dp), `type` (`credit`=money in | `debit`=money out), `paidAt` (datetime). Optional: `accountId`, `description`, `source`(≤100, e.g. "Check #123","Card"), `externalId`, `attemptAutoMatch`(false). deletePayment `{id}` (UNVERIFIED input).
- `documentPayment` = application of a payment to a document. `createDocumentPayment` required: `documentId`, `paymentId`, `amount`(>0); optional `isLinkedToQbo`(false). updateDocumentPayment `{id, amount}`; deleteDocumentPayment `{id}`.
Record a customer check: createPayment(type credit, accountId customer) → createDocumentPayment(invoice, paymentId, amount). Vendor bill payment: type `debit`.
`closeNegativePayable {id, type: credit|refund, createCreditPayment=true, description?, paidAt?}` — for negative payables.

### pdf (isWrite, returns `uploadRequest`) — not executed
`{"pdf":{"$":{"id":"document","options":{"id":"DOC_ID"},"download":false}, ...uploadRequest fields UNVERIFIED}}`. Other variants: budget, dailyLogs, formSubmission, selections, specifications, tasks.

## 4. Related types
- `payment{ id type amount amountApplied amountUnapplied feeAmount paidAt source description externalId account{} documentPayments{} qboId stripeId }` — bank-feed rows have `account:null`, `amountUnapplied=amount`.
- `documentPayment{ id amount createdAt isLinkedToQbo document{} payment{} }`
- `documentRecipient{ id user{id name emailAddress} emailDeliveryStatus documentLastViewedAt requireSignature signedAt signatoryName }`; `emailDeliveryStatus`: pending|delivered|opened|softBounced|hardBounced.
- Retainage: job-level only — `job.defaultRetainagePercentage`, `job.retainageCostItem{}`; set via `createJob/updateJob.$.defaultRetainagePercentage`, `updateJob.$.retainageCostItemId`. No retainage field on document.
- Job money fields: `job.priceType` (fixed/…), `projectedPrice`, `projectedPriceWithTax`, `projectedCost`, `actualCost`.

## 5. Group/aggregate syntax (verified)
`group:{by:[["type"],["status"]], aggs:{n:{count:[]}, bal:{sum:"balance"}}}` and read results from **`withValues`** (not nodes). Each row = group keys + agg names. Use agg names that don't collide with field names.
Simple connection sums: `"bal":{"_":"sum","$":"balance"}` or `"sum":{"$":"balance"}`.

## 6. Recipes (all run successfully)
Open AR (35 invoices, $156,751 at time of check):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"documents":{"$":{"size":20,"where":{"and":[["type","customerInvoice"],["status","pending"],["balance",">",0]]},"sortBy":[{"field":"dueDate","order":"asc"}]},
 "count":{},"bal":{"_":"sum","$":"balance"},"nodes":{"id":{},"fullName":{},"dueDate":{},"balance":{},"account":{"id":{},"name":{}},"job":{"id":{},"number":{},"name":{}}}}}}
```
Overdue: add `["dueDate","<","2026-09-29"]` (today). Add `documentRecipients{nodes{emailDeliveryStatus documentLastViewedAt user{name emailAddress}}}` for follow-up context.

AP (unpaid bills): `where {"and":[["type","vendorBill"],["status","pending"]]}`, sum `balance` (and `cost` for gross). Bills can have partial payments (balance < cost).

AR/AP snapshot by type+status:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"documents":{"$":{"group":{"by":[["type"],["status"]],"aggs":{"n":{"count":[]},"bal":{"sum":"balance"}}}},"withValues":{}}}}
```
All docs for a job:
```json
{"job":{"$":{"id":"JOB_ID"},"documents":{"$":{"size":50,"sortBy":[{"field":"number","order":"asc"}]},"nodes":{"id":{},"fullName":{},"type":{},"status":{},"price":{},"cost":{},"balance":{},"account":{"name":{}}}}}}
```
Invoiced vs budget for a job:
```json
{"job":{"$":{"id":"JOB_ID"},"projectedPrice":{},"projectedCost":{},"actualCost":{},
 "docs":{"_":"documents","$":{"where":["status","!=","denied"],"group":{"by":[["type"]],"aggs":{"n":{"count":[]},"sp":{"sum":"price"},"sc":{"sum":"cost"},"sb":{"sum":"balance"},"sa":{"sum":"amountPaid"}}}},"withValues":{}},
 "budget":{"_":"costItems","$":{"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"},"c":{"_":"sum","$":"cost"}}}}
```
(customerInvoice `sp` = invoiced; vendorBill `sc` = billed cost; budget `p`/`c`.)

Approved estimates / change orders for a job: `where {"and":[["type","customerOrder"],["status","approved"]]}` under `job.documents`; add `["name","Change Order"]` for COs only.

Recent payments received (customer, excludes bank feed):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"payments":{"$":{"size":20,"where":{"and":[["type","credit"],[["account","type"],"customer"],["paidAt",">=","2026-09-01"]]},"sortBy":[{"field":"paidAt","order":"desc"}]},
 "count":{},"total":{"_":"sum","$":"amount"},"nodes":{"amount":{},"paidAt":{},"source":{},"account":{"name":{}},"documentPayments":{"nodes":{"amount":{},"document":{"fullName":{}}}}}}}}
```
POs for a vendor: `documents where {"and":[["type","vendorOrder"],[["account","name"],"like","%Richards%"]]}`, sum `cost` (not price). Prefer `[["account","id"],"ID"]` when known.

Find doc by display name: `where ["fullName","Invoice 645-36"]`.

## 7. Gotchas
- `where` on relation needs path array: `[["job","id"],"X"]` — `["job","X"]`/`["jobId",…]` error (`job is not queryable` / field does not exist).
- `values` on a connection requires `$` arg; grouped results come via `withValues`.
- Vendor docs: use `cost`, not `price`.
- `payments` includes bank-feed debits/credits with `account:null` — filter by account type or `amountApplied>0`.
- updateDocument emails by default (`notify:true`).
