# 02 — Jobs, Accounts, Contacts, Locations, Custom Fields, Users
Org `22Nttsgz8iVp` (Barrett Plumbing). All verified 2026-09-29 by introspection/read unless marked UNVERIFIED.

## Data model / creation order
`account (customer|vendor)` -> `contact` (belongs to account) ; `account` -> `location` (belongs to account, optional `contactId`) -> `job` (belongs to location).
Job's customer = `job.location.account`. Job's contact = `job.location.contact`. No direct job.account field.
New job for new customer: createAccount -> createLocation -> createJob.

## Type fields (scalars unless noted)
- **job**: id, number (string), name, description, priceType (`fixed`|`costPlus`), closedOn (date|null = open), createdAt, areas (string[]), qboClassId, qboId, qboName, qbdId, companycamId, companycamName, coverPhotoUrl, defaultRetainagePercentage, lineItemsUpdatedAt, scheduleIsPublished, useSimpleSelections, specificationsDescription/Footer/Key, projectedCost, projectedPrice, projectedPriceWithTax, actualCost, qboNextBillIsBillable. Objects/conns: location, organization, customFieldValues, costGroups, costItems, documents, tasks, taskSummary, startTask, endTask, dailyLogs, timeEntries, files, folders, comments, events, calendar, aces, plans, parameters, selectionAssignments, jobBudgetBackups, retainageCostItem.
- **account**: id, name, type (`customer`|`vendor`), isTaxable, archivedAt, createdAt, qboId, accountStatementDescriptors. Objects/conns: primaryContact, primaryLocation, contacts, locations, jobs, documents, customFieldValues, tasks, files, comments, aces, organization, qbdIntegrationSalesTax{Code,Item}.
- **contact**: id, name, firstName, lastName, title, createdAt, nicejobCampaignEnrolledAt; account, locations, customFieldValues, files. **Email/phone are NOT scalars — they are customFieldValues** (see CF table: Email/Office/Mobile).
- **location**: id, name, address (full string), formattedAddress, street, city, state, postalCode, county, country, latitude, longitude, timeZone, taxRate, customTaxRate, qboTaxCodeId, createdAt; account, contact, jobs, customFieldValues, files, aces.
- **customField**: id, name, targetType, type, options (string[]), defaultValue, minValuesRequired (1 = required), maxValuesAllowed (null = multi-select), position, showOnSpecifications, createdAt; organization, customFieldValues (conn).
- **customFieldValue**: id, value (string|bool|number; option = the option string), booleanValue, dateValue, datetimeValue, numberValue, timeValue, createdAt; customField, job, account, contact, location, costItem.
- **membership**: id, isInternal, lastActiveAt, createdAt, accountName, accountType, contactTitle, grantKey, gustoEmployeeId, qboEmployeeId, syncTimeEntriesSince, useRoleNotificationSubscriptions; user, role, account, contact, organization, assignedTasks, timeEntryTypes, parentMembership, childMemberships, notifications, default*DataView...
- **user**: id, name, emailAddress, phoneNumber, avatarUrl, isAdmin, isMachine, lastActiveAt, createdAt; memberships, timeEntries, dailyLogs, grants, defaultMembership.
- **role**: id, name, type (`internal`|`customer`|`vendor`), permissions, defaultIsVisibleToCustomerRoles/VendorRoles; aces, visibleFolders.
- Enums: `customFieldType` = address|boolean|date|datetime|emailAddress|number|option|phoneNumber|text|time|url. `customFieldTargetType` = costItem|customer|customerContact|dailyLog|job|location|vendor|vendorContact.

## Mutations (inputs from schema; NOT executed)
Create returns `createdX` (e.g. `createdJob`, `createdAccount`, `createdContact`, `createdLocation`, nullable X). Update/delete return type `root` — no `updatedX`; to read back, select a root field inside, e.g. `{"updateJob":{"$":{...},"job":{"$":{"id":"..."},"name":{}}}}` (path `root.updateJob.job` resolves; UNVERIFIED at runtime).
```json
{"createJob":{"$":{"locationId":"LOC","name":"1102 | 123 Easy St","priceType":"fixed","qboClassId":"1054766","customFieldValues":{"22NtuVNPeBDB":"Residential","22NtuVAwrQWC":"New Construction"}},"createdJob":{"id":{},"number":{},"name":{}}}}
```
- **createJob**: REQ `locationId`. Opt: `name` (**max 30 chars!**), `number` (string ≤16; omit → auto = `organization.nextRecordNumber`, currently "1102"; UNVERIFIED that omission auto-assigns but number == nextRecordNumber-1 on latest job), `description` (≤32768), `priceType` (default `fixed`), `closedOn` (date), `areas` (default ["General"]), `customFieldValues` (object map), `lineItems` (≤1500; oneOf newCostGroup|newCostItem|existingCostGroup|existingCostItem — see budget ref), `copyCostsFromJobId`, `copyTasksFromJobId`, `coverPhoto` {fromJob{jobId}|fromUploadRequest{uploadRequestId}|fromFile{fileId}}, `qboClassId`, `qboId`, `qbdId`, `companycamId`, `defaultRetainagePercentage`, `scheduleIsPublished`, `specificationsDescription/Footer` (≤10000), `useSimpleSelections`, `parameters`.
- **updateJob**: REQ `id`; all createJob fields optional (no copy*), plus `startTaskId`, `endTaskId`, `retainageCostItemId`, `folders` (string[]), `hoverJobId`. Close job = `closedOn:"YYYY-MM-DD"`; reopen = `closedOn:null`.
- **deleteJob / deleteAccount / deleteContact / deleteLocation**: `{id}` only.
- **createAccount**: REQ `organizationId`, `name`, `type` (customer|vendor). Opt: `customFieldValues`, `isTaxable` (def true), `archive` (def false), `notify` (def **true** — pass false to avoid notifications), `suffixIfNecessary` (def false; appends number for unique name), `qbdIntegrationSalesTaxCodeId/ItemId`.
- **updateAccount**: REQ `id`. Opt: name, customFieldValues, isTaxable, archive (bool), notify, `primaryContactId`, `primaryLocationId`, qboId, accountStatementDescriptors (≤10 × ≤64ch), qbd*.
- **createContact**: REQ `accountId`, `name` (full name; firstName/lastName derived). Opt: `title`, `customFieldValues` (email/phone go here).
- **updateContact**: REQ `id`. Opt: name, title, customFieldValues.
- **createLocation**: REQ `accountId`. Opt: `address` (free string), `parseAddress` (def true → geocodes into street/city/etc), `name` (convention: street address, optionally "addr - Project Name"), `contactId`, `customFieldValues`, `customTaxRate` (0–1), `qboTaxCodeId`.
- **updateLocation**: REQ `id`; opt address, name, contactId, customFieldValues, customTaxRate, qboTaxCodeId.
- **updateJobContact**: NOT a contact editor — sets portal visibility of a job ACE: `{aceId, isVisibleToCustomerRoles:bool, isVisibleToVendorRoles:bool}`. (job.aces nodes have `jobContact{id}`, `membership`, `role`.)

### customFieldValues input
Schema: open object map `{ <key>: value|null }`. Key = **customField id** (UNVERIFIED by write; standard Pave convention). Values: option → option string exactly as in list (incl. emoji); boolean → true/false; date → "YYYY-MM-DD"; text/email/phone/url → string; null clears. Multi-select (maxValuesAllowed null) → probably array of strings (UNVERIFIED). Read side stores multi-select as ONE customFieldValue ROW PER selected option (verified: BP Lead has 42 rows, jobs appear twice).

## Custom fields (all 60; * = required minValuesRequired=1; M = multi-select; default in [])
### job
| id | name | type | options / default |
|---|---|---|---|
| 22Nuh4aSVtcP | Phase* | option | Pipeline: Bidding · Pipeline: Awaiting Decision · 1-Won: Not Scheduled · Waiting on Builder/Client · Waiting: Post-Underground · Waiting: Post-Rough-In · 2-Active: Scheduled · 3-Active: Underground · 4-Active: Rough-In · 5-Active: Finish · Complete: Awaiting Billing · Complete: Awaiting Payment · Complete: Paid · On Hold · Bid Lost · Canceled · N/A · Active: Membership [Pipeline: Bidding] |
| 22PWKUDHJHj5 | Stage* | option | Not Started · Active · Complete [Not Started] |
| 22PNFqqnCnDc | Job Bid Won?* | option | Pending · Yes · No · N/A [N/A] |
| 22P7sttAr6Je | RYG* | option | ❔ · 🔴 · 🟡 · 🟢 [❔] |
| 22NtuVNPeBDB | Category* | option | Residential · Commercial · Water Service · Misc |
| 22NtuVAwrQWC | Job Type | option | New Construction · Renovation · Service · Maintenance / Repair · Warranty |
| 22NxLZJtH5yV | Time & Material?* | boolean | [false] |
| 22P7stgfUp9B | Status | text | |
| 22NtuVH4QTJY | Notes | text | |
| 22PHPBrdSr9U | Water | option | City Water · Well Water |
| 22PHn4jUqgg4 | Sewer | option | City Sewer · Septic System |
| 22NwvgcvUTpd | Permit Authority | option | 33 options, see below [No Permit] |
| 22Nu8VshdDdB | Permit Number | text | |
| 22Nuh3rugbXY | Underground Inspection | date | |
| 22Nuh3u2pHi5 | Rough-in Inspection | date | |
| 22Nuh3uycDBJ | Final Inspection | date | |
| 22PE6ZNv7jfu | Rough-In Fixtures Ordered | boolean | [false] |
| 22PE6ZHby5PY | Fixtures Ordered | boolean | [false] |
| 22P7mgU3ZVz7 | Superintendent | text | |
| 22PVbYYtL9iV | BP Lead/Backup Lead (M) | option | John McCarthy · Daryk Swanson · Chris Barrett · Noah Carter · Lucas Burns |
| 22PMRTZjy5bK | Post-Mortem Done | boolean | [false] |
| 22PMRTcvwkgJ | Financial Review Done | boolean | [false] |
| 22PULQ9rfyGG | Contract Number | text | |
| 22PdvqBZgZcD | Lead Source | option | Existing Customer · Referral · Google Local Service Ads · Google Ads · Yard Sign · Website [Existing Customer] |

Permit Authority options (exact strings; match by prefix before ":"): `No Permit` · `Muskegon: 231-724-6715 | Water Dept: 231-724-4100` · `Muskegon Township: 231-777-2558, Inspector: (Steve) 231-736-8179` · `Muskegon Heights: 231-733-8860 | Water Dept: 231-733-8885` · `Norton Shores: 231-799-6801, 1 | Water Dept: 231-799-6804` · `Michigan Township: 231-865-3310` · `Grand Haven: 616-842-3460 | Water Dept: 616-847-3493` · `Blue Lake Township: 231-894-6335` · `Cedar Creek Township: 231-821-0014 x101` · `Crockery Township: 616-837-6868` · `Dalton Township: 231-766-3043, 5 | Muskegon County: 231-724-6411,2 | Inspector: (Steve Smith) 231-736-8179` · `Ferrysburg City: 616-842-5803 | Water Dept: 616-842-5803` · `Fruitland Township = Michigan Township: 231-865-3310 | Inspector: (Steve Smith) 231-736-8179` · `Grand Haven Township: 616-842-5988, 2` · `Grand Rapids: 616-456-4100, Inspections: inspections.grcity.us` · `Holland Township: 616-396-2345` · `Holton Township: 231-821-2168` · `Laketon Township: 231-744-2454 | Jim Hoppus 231-780-7414` · `Lakewood Club Village: 231-894-9008 | Inspector: 231-206-6563` · `North Muskegon: 231-744-1621, Inspector: 231-780-7414` · `Oceana Township: 231-873-4350` · `Polkton Township: 616-863-9294 | MWF Inspections` · `Ravenna Township = Michigan Township: 231-865-3310` · `Robinson Township: 616-667-8803` · `Spring Lake Township = Michigan Township: 231-865-3310` · `Spring Lake Village = Michigan Township: 231-865-3310` · `Whitehall Township: 231-736-8179 (Inspector)` · `White Lake Area-Montague: 231-736-8179 (Inspector)` · `Byron Township: 616-878-9155 | Water Meter: 616-971-0002` · `Oceana County: 231-873-5355 | bi@oceana.mi.us` · `Cascade Township: 616-949-3765` · `Port Sheldon Twp: 616-399-6121 | Bob Madreski: 616-477-4940`
Tip: fetch live list rather than retyping: `{"customField":{"$":{"id":"22NwvgcvUTpd"},"options":{}}}`.

### customer (account type=customer)
| id | name | type | options |
|---|---|---|---|
| 22NtuUffekM7 | Type* (M) | option | New Lead · Discovery · New Customer · Current Customer · Previous Customer · Rely Home Lead · Key Customer · Builder · Contractor · Homeowner · Company/Business · Lead Lost |
| 22NtuUcUet4g | Category* (M) | option | Commercial · Residential · Other |
| 22NwzUhhYHc9 | $ Account Status | option | 👍 Good Standing · ❌ Past Due · 🔥FIRED |
| 22P26tf9JpsA | Score | option | ⭐ … ⭐⭐⭐⭐⭐ (1–5 stars) |
| 22NtuUbt9zvx | Notes | text | |
### customerContact
Email `22Nttshd5e9u` (emailAddress) · Office `22NtuUs8sjn3` (phoneNumber) · Mobile `22NtuUntj3U9` (phoneNumber) · Notes `22NtuUnicRcv` (text). Phones stored E.164 e.g. "+12317264913".
### vendor (account type=vendor)
Type `22NtuUtuVVut` option: Supplier · Rentals · Subcontractor · Other | Rating `22NtuV4rvVem`: 5 - Excellent · 4 - Above Average · 3 - Average · 2 - Below Average · 1 - Do Not Use | Payment Terms `22NtuV3j9kt2`: Net 15 · Net 30 · Net 45 · Net 60 · COD · None · TBD | Website `22NtuUxKx7xb` url | Email `22NttshdA8vN` | Phone `22NttshnEPwZ` | Notes `22NtuV3BXaCW` | W-9 `22PGbUWqCcF3` bool | COI Expires `22PGbUWvxCse` date
### vendorContact
Mobile `22NtuV6zPWaP` · Email `22Nttshd92EV` · Office `22NtuV7AwLH5` · Notes `22NtuV8aP9Xj`
### location
Notes `22NtuV9TQGa9` (text)
### costItem
Stock `22NuFj6ZZVfr` bool* [false] · Primary Vendor `22Nxcxtvp5uf`: Richards · Ferguson Enterprises · Standard Electric/Ferguson Supply · Builders Supply · Berghorst · Menards · Home Depot · Etna [Richards] · Box Qty `22PCgYdpx6eg` number · Ordering Phase `22PX2WhNDJcP` (M): Any · Underground · Rough-In · Finish [Any] · Lead Time `22PAJYJVfZZW`: In Stock (Normally) · 2-4 Weeks · 4+ Weeks · Internal Notes `22NtuVXRZsru` text · Standard Item `22P3W5Ct8ZFQ` bool · Status `22PMNB39Kxkw`: Active · Obsolete [Active]
### dailyLog
T&M Materials `22PVCXYvnrix` · Material From Supply House/Store `22PVCWkJaEHL` · Issues `22PVCWYTu97H` · Internal/Private Notes `22NtuVw2upa6` (all text) · Personal Car Miles `22PCZrD7C8CJ` number

## QBO class ids (job.qboClassId; no class names exposed in API — mapping INFERRED from Category+Job Type of sampled jobs)
| qboClassId | Category / Job Type | jobs |
|---|---|---|
| 1054762 | Commercial Service | 48 |
| 1054763 | Residential Service | 212 |
| 1054764 | Water Service (Ryerson Bros excavating) | 21 |
| 1054765 | Commercial New Construction | 23 |
| 1054766 | Residential New Construction | 93 |
| 1054767 | Commercial Renovation | 71 |
| 1054768 | Residential Renovation | 85 |
null on 418 jobs (older jobs, templates like "*Small Job", "*Quick Estimating Job", "2026 Q3 STOCK"). No Warranty class seen.

## Conventions (from recent jobs 1096–1101)
- Name: `"<number> | <Short description>"` (some `"1096|..."` without spaces; prefer spaced). Service = work description ("Replace Valve"); construction = project/subdivision name ("Gezelling Place"). ≤30 chars total.
- number = string, sequential; next = `organization.nextRecordNumber`. Name prefix occasionally ≠ number (job 1066 named "1065|...") — trust `number`.
- Location name: street address, often `"<address> - <Project/Owner>"` e.g. "76 South Getty St - RENK America".
- Service jobs: priceType `costPlus` when T&M (Time & Material?=true), Job Bid Won?=N/A, Stage=Active, Phase=2-Active: Scheduled, RYG=🟢, Permit Authority=No Permit, class 1054762/63.
- Bid/construction/reno jobs: priceType `fixed`, Job Bid Won?=Pending, Stage=Not Started, Phase=Pipeline: Bidding, RYG=❔, T&M=false, Permit Authority by municipality, class 65/66/67/68.
- Defaults (Stage, RYG, T&M, Permit Authority, *Ordered, Post-Mortem, Financial Review, Lead Source) are auto-populated on create; only set what differs + Category/Job Type/Phase.

## Recipes (all verified)
Find job by number (number is string):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"where":["number","1097"]},"nodes":{"id":{},"name":{},"closedOn":{},"location":{"formattedAddress":{},"account":{"id":{},"name":{}}}}}}}
```
Fuzzy by name or address (`like` is case-insensitive, `%` wildcard):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":10,"where":{"or":[["name","like","%glenpark%"],[["location","address"],"like","%glenpark%"]]}},"nodes":{"id":{},"number":{},"name":{}}}}}
```
Open jobs in a Phase (custom-field filter via `with`; can use CF name or id; `in` works):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":20,"with":{"cf":{"_":"customFieldValues","$":{"where":[["customField","id"],"22Nuh4aSVtcP"]},"values":{"$":{"field":"value"}}}},"where":{"and":[["closedOn","=",null],[["cf","values"],"in",["2-Active: Scheduled","3-Active: Underground"]]]}},"count":{},"nodes":{"id":{},"number":{},"name":{}}}}}
```
Job → customer + primary contact email/phone:
```json
{"job":{"$":{"id":"JOBID"},"name":{},"location":{"formattedAddress":{},"contact":{"name":{}},"account":{"id":{},"name":{},"primaryContact":{"id":{},"name":{},"customFieldValues":{"nodes":{"value":{},"customField":{"name":{}}}}}}}}}
```
(returns Email / Office / Mobile rows.)
Jobs for an account: `"where":{"and":[[["location","account","id"],"ACCTID"],["closedOn","=",null]]}`.
Customers vs vendors: `accounts` with `"where":{"and":[["type","customer"],["archivedAt","=",null]]}` (436 active customers). Vendor by name:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"accounts":{"$":{"size":5,"where":{"and":[["type","vendor"],["name","like","%fergus%"]]}},"nodes":{"id":{},"name":{},"primaryContact":{"name":{}}}}}}
```
Contact by name: `organization.contacts` `where ["name","like","%zorn%"]` → id, name, title, account{name,type}.
Location by address: `organization.locations` `where ["address","like","%getty%"]` → id, name, account{name}, jobs{count}.
Only certain CFs of a record: `"customFieldValues":{"$":{"where":[["customField","name"],"Phase"]},"nodes":{"value":{}}}`.
All values of one CF across records: `{"customField":{"$":{"id":"CFID"},"customFieldValues":{"$":{"size":20},"nodes":{"value":{},"job":{"number":{}}}}}}`.

## Users / memberships (internal, 6)
| user | userId | membershipId | role |
|---|---|---|---|
| Vance McClenton | 22NttsgymKnw | 22Nttsgz8iVq | Owner |
| Noah Carter | 22NupN9w2v62 | 22NupN9w3esb | Plumber |
| Daryk Swanson | 22NupN9weqQW | 22NupN9wh5nF | Plumber |
| Chris Barrett | 22NupP4EgTSp | 22NupP4EhDFQ | Plumber |
| John McCarthy | 22Nv8KKhRRHP | 22Nv8KKhSB5y | Plumber Simple |
| Lucas Burns | 22P3z3jqVpG4 | 22P3z3jqUgZB | Plumber |
Query: `organization.memberships` `where ["isInternal",true]` → `user{id,name,emailAddress}`, `role{name}`. Task assignment usually uses membershipId (see tasks ref).
Roles: internal — Owner 22NttshBazCi, Plumber 22Nu8Nxpznvk, Team Leader 22NxPnWSN9yn, Admin Assistant 22PH69S62pEZ, Plumber Simple 22PXqxtDJzJn; customer — Customer 22NttshBazCj, Homeowner 22PeMEJ4cf3P, GC/Builder 22PeMEVh3wcg, Accounts Payable 22PeMEaJKb6q; vendor — Vendor 22NttshBazCk, Inspector 22PEVkuWgfDi, Supplier 22PeMEmMV49m, Subcontractor 22PeMEnYtTvP.

## Gotchas
- **Nested connections default to 10 nodes** (job 1101 has 14 CF values; first query showed 10). Pass `"$":{"size":50}` on `customFieldValues`, or filter by customField.
- `sortBy number` is a STRING sort ("977" > "1097"). Sort by `createdAt desc` for newest.
- `values: {"$":["field"]}` returns per-row values (not distinct) and ignores `size`.
- `organization.customFieldValues` doesn't exist — go via `customField(id).customFieldValues` or the record.
- Job name max 30 chars; job number max 16 chars.
- createAccount `notify` defaults true.
- `job` root: `{"job":{"$":{"id":"..."}}}` — lookup by id only; by number use org.jobs where.
- Some older required CFs (Category/Phase) may be missing on jobs despite minValuesRequired=1 (e.g. job 1098 lacks Job Type).
