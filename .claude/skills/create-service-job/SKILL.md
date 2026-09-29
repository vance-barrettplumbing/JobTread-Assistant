---
name: create-service-job
description: >
  Create a new service job in JobTread for Barrett Plumbing Inc. Use this skill any time
  the user wants to add a new service job, create a service ticket, set up a service call,
  or log new service work. Handles customer lookup (or creation), job setup, budget line
  items, and schedule task — all in one workflow. Trigger phrases include: "create a service
  job", "new service job", "add a service job", "set up a service call", "create a job for
  [customer]", "log a service job", or any time the user describes service work that needs
  a job in JobTread.
compatibility: JobTread connector (mcp__JobTread__query / JobTread:query). Pairs with the `jobtread` skill.
---

# Create Service Job

Creates a complete service job: customer/location lookup or creation, job with all custom fields,
budget (service call + labor), and the schedule task. Mirrors how recent service jobs (#1099, #1100)
are actually set up. All calls use the single JobTread query tool. IDs verified 2026-09-29.

Org ID: `22Nttsgz8iVp`. Put `"$":{"notify":false}` at the root of every write.

---

## Step 1: Gather information

Use **AskUserQuestion** for anything not already given:

1. **Service description** — short, e.g. "Replace Valve", "Water Heater Replacement". Used in the job name,
   budget group and schedule task.
2. **Customer name** (and address if new customer / new location).
3. **Category** — Residential or Commercial.
4. **Emergency?** — Emergency → "Service Call - Emergency"; standard → "Service Call - Trip Charge".
5. **Phase** — usually `2-Active: Scheduled` or `1-Won: Not Scheduled`. Full list:
   Pipeline: Bidding · Pipeline: Awaiting Decision · 1-Won: Not Scheduled · Waiting on Builder/Client ·
   Waiting: Post-Underground · Waiting: Post-Rough-In · 2-Active: Scheduled · 3-Active: Underground ·
   4-Active: Rough-In · 5-Active: Finish · Complete: Awaiting Billing · Complete: Awaiting Payment ·
   Complete: Paid · On Hold · Bid Lost · Canceled · N/A · Active: Membership
6. **Scheduled date** (+ start time and which plumber, if known) — for the schedule task. Optional.
7. **T&M or flat rate?** — default T&M (Cost-Plus). Flat rate → Fixed-Price, T&M? false.

Fixed values — never ask: Job Type **Service**, RYG **🟢**, Job Bid Won? **N/A**, Stage **Active**,
Permit Authority **No Permit** (default).

---

## Step 2: One lookup call — job number, customer, locations, current catalog prices

```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"nextRecordNumber":{},
 "accounts":{"$":{"size":5,"where":{"and":[["type","customer"],["name","like","%<customer words>%"]]}},
   "nodes":{"id":{},"name":{},"locations":{"$":{"size":20},"nodes":{"id":{},"name":{},"address":{}}}}},
 "catalog":{"_":"costItems","$":{"size":10,"where":["id","in",["22Nu4wTw3zyt","22PAdLTTW6CQ","22NxtrYitZWQ","22PGv6pa4e4x"]]},
   "nodes":{"id":{},"name":{},"unitCost":{},"unitPrice":{},"isTaxable":{},"costCode":{"id":{}},"costType":{"id":{}},"unit":{"id":{}}}}}}
```
Catalog items (always use the **live** unitCost/unitPrice returned — never hardcode prices):
| Item | catalog id | code / type / unit |
|---|---|---|
| Service Call - Trip Charge | `22Nu4wTw3zyt` | 8000 Fees / Other / Each |
| Service Call - Emergency | `22PAdLTTW6CQ` | 8000 Fees / Other / Each |
| Labor - RS (Residential Service) | `22NxtrYitZWQ` | 1106 / Labor / Man Hour |
| Labor - CS (Commercial Service) | `22PGv6pa4e4x` | 1206 / Labor / Man Hour |

Customer match rules: exact → use; close → confirm with user; none → create. Multiple locations → ask.
If no customer match, also try `organization.contacts` `where ["name","like","%..%"]` → `account{id name}`
(homeowners are sometimes stored under a different account name).

**New customer** (only if needed):
1. `createAccount` `{organizationId:"22Nttsgz8iVp", name, type:"customer", notify:false,
   customFieldValues:{"22NtuUcUet4g":["Residential"], "22NtuUffekM7":["Homeowner"]}}` → `createdAccount{id}`
   (customer Category & Type are required multi-selects; if the array form errors, retry with plain strings)
2. `createLocation` `{accountId, address:"<street, city, MI zip>", name:"<street address>"}` → `createdLocation{id}`
3. `createContact` `{accountId, name, customFieldValues:{"22Nttshd5e9u":"<email>","22NtuUntj3U9":"+1<mobile digits>"}}`
   (Email / Mobile; Office phone is `22NtuUs8sjn3`). Ask the user for name, phone, email.

---

## Step 3: Create the job (ONE call, all fields)

Job name: `<nextRecordNumber> | <Service description>` (≤ 30 characters total — abbreviate if needed).
Setting Job Type = Service **in this call** makes the "Job Created Trigger" workflow auto-import the
"New Service Job" to-do list (Schedule the job, Set budget, Send invoice, etc.) — don't create those to-dos.

```json
{"$":{"notify":false},"createJob":{"$":{
  "locationId":"<locationId>","number":"<nextRecordNumber>","name":"1102 | Replace Valve",
  "priceType":"costPlus","qboClassId":"1054763",
  "customFieldValues":{
    "22NtuVAwrQWC":"Service","22NtuVNPeBDB":"Residential","22Nuh4aSVtcP":"2-Active: Scheduled",
    "22PWKUDHJHj5":"Active","22P7sttAr6Je":"🟢","22NxLZJtH5yV":true,"22PNFqqnCnDc":"N/A"}},
 "createdJob":{"id":{},"number":{},"name":{}}}}
```
| Setting | T&M (default) | Flat rate |
|---|---|---|
| `priceType` | `costPlus` | `fixed` |
| Time & Material? `22NxLZJtH5yV` | `true` | `false` |

`qboClassId`: Residential Service `1054763`, Commercial Service `1054762`.
Custom field ids: Job Type `22NtuVAwrQWC`, Category `22NtuVNPeBDB`, Phase `22Nuh4aSVtcP`, Stage `22PWKUDHJHj5`,
RYG `22P7sttAr6Je`, Time & Material? `22NxLZJtH5yV`, Job Bid Won? `22PNFqqnCnDc`.

---

## Step 4: Add the budget (ONE call per item — appends, never replaces)

Recent service jobs have exactly two budget lines:
1. **Service call** (ungrouped, at the job root): Trip Charge *or* Emergency.
2. **Group named after the service description** containing the labor line (Labor - RS or Labor - CS).

Do NOT use `updateJob.lineItems` (it can replace the whole budget). Use:

```json
{"$":{"notify":false},
 "createCostItem":{"$":{"jobId":"<jobId>","name":"Service Call - Trip Charge","organizationCostItemId":"22Nu4wTw3zyt",
   "costCodeId":"<from catalog>","costTypeId":"<from catalog>","unitId":"<from catalog>",
   "quantity":1,"unitCost":<catalog unitCost>,"unitPrice":<catalog unitPrice>,"isTaxable":false},
  "createdCostItem":{"id":{}}}}
```
```json
{"$":{"notify":false},
 "createCostGroup":{"$":{"jobId":"<jobId>","name":"<Service description>","lineItems":[
   {"_type":"costItem","name":"Labor - RS","organizationCostItemId":"22NxtrYitZWQ",
    "costCodeId":"<from catalog>","costTypeId":"<from catalog>","unitId":"<from catalog>",
    "quantity":1,"unitCost":<catalog unitCost>,"unitPrice":<catalog unitPrice>,"isTaxable":false}]},
  "createdCostGroup":{"id":{}}}}
```
If `createCostGroup` rejects `lineItems`, create the group without it, then `createCostItem` with
`costGroupId:"<groupId>"` (and no jobId).

| Condition | Service call item | Labor item |
|---|---|---|
| Residential, standard | Service Call - Trip Charge | Labor - RS |
| Residential, emergency | Service Call - Emergency | Labor - RS |
| Commercial, standard | Service Call - Trip Charge | Labor - CS |
| Commercial, emergency | Service Call - Emergency | Labor - CS |

Labor quantity: 1 hour unless the user gives an estimate. **Do NOT add CC Service Fee or Warranty Accrual
items** to service jobs. Add materials only if the user asks — look them up in the catalog the same way and
copy their catalog prices.

---

## Step 5: Create the schedule task

```json
{"$":{"notify":false},"createTask":{"$":{
  "targetType":"job","targetId":"<jobId>","name":"<Service description>","isToDo":false,
  "taskTypeId":"22P79bpNExFn","startDate":"<YYYY-MM-DD or omit>","endDate":"<same day or omit>",
  "startTime":"<HH:MM or omit>","assignedMembershipIds":["<membershipId if plumber given>"],"notify":false},
 "createdTask":{"id":{},"name":{}}}}
```
Task type `T&M` = `22P79bpNExFn`. Plumber membership ids: Noah Carter `22NupN9w3esb`, Daryk Swanson
`22NupN9wh5nF`, Chris Barrett `22NupP4EhDFQ`, John McCarthy `22Nv8KKhSB5y`, Lucas Burns `22P3z3jqUgZB`,
Vance `22Nttsgz8iVq`. Omit `assignedMembershipIds`/dates if unknown.
Only notify the plumber (`notify:true`) if the user asks.

---

## Step 6: Verify and confirm

```json
{"job":{"$":{"id":"<jobId>"},"number":{},"name":{},"priceType":{},
 "location":{"formattedAddress":{},"account":{"name":{}}},
 "customFieldValues":{"$":{"size":30},"nodes":{"value":{},"customField":{"name":{}}}},
 "budget":{"_":"costItems","$":{"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"},"c":{"_":"sum","$":"cost"},
   "nodes":{"name":{},"quantity":{},"unitPrice":{}}},
 "tasks":{"$":{"size":20},"nodes":{"name":{},"isToDo":{},"startDate":{}}}}}
```
> Job #1102 **"1102 | Replace Valve"** created for **John Smith** (123 Main St).
> Phase: 2-Active: Scheduled | Residential | T&M | RYG 🟢
> Budget: Trip Charge $75 + Labor - RS 1 hr $150 = $225 price / $96.42 cost
> Schedule: Replace Valve — Tue 9/30 7:30am, Noah | To-dos auto-added: [count]

---

## Notes
- Never invent or recalculate prices — always the live catalog values.
- The Claude connector cannot delete. If something was created wrong, fix it with `updateJob` /
  `updateCostItem` / `updateTask`; tell the user if a record needs deleting in JobTread.
- If the user's phase doesn't exactly match an option, pick the closest and confirm.
