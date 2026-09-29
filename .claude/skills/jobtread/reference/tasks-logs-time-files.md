# 05 — Tasks/Schedule/To-Dos, Daily Logs, Time, Comments, Files, Events, Webhooks, Workflows

Org `22Nttsgz8iVp`, tz `America/Detroit`, working days Mon–Fri `[1..5]`, time week starts `timeEntryStartDayOfWeek:4` (Thursday).
All mutations below are from schema introspection only (NOT executed). Mutation result read via `created<X>` (confirmed root fields: createdTask, createdTaskTemplate, createdTaskType, createdTimeEntry, createdDailyLog, createdComment, createdFile, createdFileTag, createdUploadRequest, createdWebhook, createdWorkflow).
`{"createTask":{"$":{...},"createdTask":{"id":{},"name":{}}}}`

## Reference IDs (live)
Internal memberships (use membership id for assignees; user id for time entries):
| person | membershipId | userId | role |
|---|---|---|---|
| Vance McClenton | 22Nttsgz8iVq | 22NttsgymKnw | Owner |
| Noah Carter | 22NupN9w3esb | 22NupN9w2v62 | Plumber |
| Daryk Swanson | 22NupN9wh5nF | 22NupN9weqQW | Plumber |
| Chris Barrett | 22NupP4EhDFQ | 22NupP4EgTSp | Plumber |
| John McCarthy | 22Nv8KKhSB5y | 22Nv8KKhRRHP | Plumber Simple |
| Lucas Burns | 22P3z3jqUgZB | 22P3z3jqVpG4 | Plumber |
Lookup: `organization.memberships($:{where:["isInternal",true]}){id user{id name} role{name}}` (423 total incl. customers/vendors).

Task types (15): Planning 22NxLUjP6Ngj · Scheduled (Tentative) 22NxLUmXAwcs · Scheduled (Confirmed) 22NxLUq2JX8n · Subcontractor/Delivery 22Ny7ZLah9dm · Inspection (Planned) 22Ny7adBRLeX · Inspection (Confirmed) 22Ny7ai3xgfe · Time Off 22NychCkxBVe · Milestone 22P5Kw3dyDrm · T&M 22P79bpNExFn · Meeting 22P9HsHLfCuy · 1-Low 22P9J8i8MSPm · 2-Normal 22P9J8hDd6WB · 3-High 22P9J8kK6K2X · Warranty Work 22PE6ZfkJfUD · Rework 22PNX3KvGnii

Task templates (52 total; T=to-do list, S=schedule):
- T: Residential New Build To-Do's 22NvbbraRBZL · New Commercial Job 22P3VAhQkFuZ · New Job (Planning - No Drawing) 22P3VApyRxvx · New Service Job 22P5K4cr248V · Water Service 22PAt547zzQ4 · Residential New Build Estimating 22PHeadrhpD7 · New Commercial Job (Planning) 22PHf7E5tM6H · Underground Checklists 22PWJjp27AXv · Rough-in Checklists 22PWJjtZ9tzr · Finish Plumbing Checklists 22PWJk2bM5Nd
- S: Residential New Build (City Water/Sewer, Muskegon) 22NwqTvSQfQm · Warranty Timeline 22P5KvgrJebt · Water Service 22PAt4hPzkmE · Residential New Build Tasks (City Water/Sewer) 22PHee9ChRAX · Residential New Build Tasks (Well/Septic) 22PHeeDSz59L · Install Irrigation Vacuum Breaker 22PMkqUk9dPi · *General Commercial Schedule 22PTGqNscKCQ · *Service Job 22PV95WNRxYJ
- S "Service Call - X" (~33): Toilet Replacement 22PXVrzMfmvC · Kitchen Faucet Replacement 22PXVtmvdAEc · Bathroom Faucet 22PXVtnFwTqa · Garbage Disposal 22PXVtnYEm6q · Water Heater (Tank) 22PXVtnqf6G7 · Shower/Tub Valve 22PXVtpB9Rdt · Angle Stop 22PXVtpUHRTD · Sump Pump 22PXVtpmcApG · Toilet Repair (Running) 22PXVtq6gBkr · P-Trap/Under-Sink Drain 22PXVtqR72A8 · Dishwasher Supply & Drain 22PXVtqiwyzn · Expansion Tank 22PXVtr3L52m · Ice Maker Line 22PXVtrKiRSj · Hose Bib 22PXVtsDwrMu · R/O System 22PXW72grVYC · Water Softener & Pre-Filter 22PXW72zXMnT · Battery Backup Sump 22PXW73JbDCj · Tub Spout 22PXW7z7kWKn · Shower Cartridge 22PXW7zQfUg4 · Tankless Descaling 22PXW7zhLRf7 · Tankless Install 22PXW7zzytpb · Outdoor Shower Startup 22PXW8UTiWWX · Outdoor Shower Winterization 22PXW8UkmFXv · Irrigation VB Install (New) 22PXXXhCXKzW · Irrigation VB Replacement 22PXXYQ73Tmv · Tankless Replacement 22PXXZf4Yb9N · Sewage Pump 22PXXaw5S3Xz · Washing Machine Box 22PXXbJtMM4M · Toilet Repair (Leaking) 22PXXbkSZZNR · Repair PEX Leak 22PXXeHfBgDi · Repair Copper Leak 22PXXejPDpws · Galvanized to PEX Repipe 22PXXf8VYmNy
Two templates named "Water Service": 22PAt4hPzkmE (schedule) vs 22PAt547zzQ4 (to-do). 2 templates beyond first 50 not listed: fetch with `organization.taskTemplates($:{size:60}){nodes{id name isToDo}}`.

## task — fields
id name description isToDo isGroup targetType(job|account|organization|taskTemplate) job account location organization
startDate startTime endDate endTime startsAt endsAt baselineStart/EndDate/Time
progress (0..1 or null) completed (number 0/1 — filterable) started unstarted position recurrenceRule recurrenceSequenceId
taskType{id name color} taskTemplate parentTask childTasks subtasks(checklist) assignedMemberships{nodes{id user{name}}} taskAssignments{id isAccepted membership task}
dependsOnTasks dependentTasks taskDependencies dependentTaskDependencies comments files documents planTasks
Gotchas:
- Template tasks also appear in queries (targetType `taskTemplate`, dates like `1969-12-31`). Always filter `["targetType","job"]` for real work.
- Cannot filter tasks by `[["taskAssignments","membership","id"],..]` (error: field "membership" does not exist). Use `membership($:{id}).assignedTasks` instead.
- Multi-day tasks: use overlap filter `startDate<=end AND endDate>=start`.
- No `completed` input on update: set `progress: 1` to complete, `0`/null to reopen (inferred; completed==1 where progress==1 in data).

## createTask (input)
| field | type | notes |
|---|---|---|
| targetType | `job`/`account`/`organization`/`taskTemplate` (enum string) | nullable |
| targetId | id | the job etc. |
| name | string | |
| isToDo | bool, default false | false = schedule item |
| startDate/endDate | date `YYYY-MM-DD` | nullable |
| startTime/endTime | time `HH:MM` (stored `07:30:00.000`) | nullable |
| baselineStart/EndDate/Time | | nullable |
| progress | number 0..1 | nullable |
| taskTypeId | id | nullable |
| assignedMembershipIds | [id] max 20 | **simplest way to assign** |
| assignees | [assignee] max 20 | oneOf by shape: `{"membershipId":".."}` / `{"roleId":".."}` / `{"name","emailAddress","phoneNumber","accountType"}` (invite user) — shape UNVERIFIED |
| dependsOnTasks / dependentTasks | [{id, offsetIsLocked:bool, offsetAnchor:"start"\|"end"}] max 25 | |
| parentTaskId | id | put under group (isGroup:true parent) |
| positionAfterTaskId | id | |
| isGroup | bool | |
| subtasks | [{name, isComplete}] max 50 | checklist |
| description | string ≤4096 | |
| recurrenceRule | string (RRULE, format unverified) | |
| files | [{uploadRequestId \| copyFromFileId, name, folder, fileTagIds, description}] | |
| notify | bool default true | set false to avoid pinging crew |
No duration field — use start/end dates.
```json
{"createTask":{"$":{"targetType":"job","targetId":"<jobId>","name":"Rough-in Plumbing","isToDo":false,"startDate":"2026-10-01","endDate":"2026-10-01","startTime":"07:30","taskTypeId":"22NxLUq2JX8n","assignedMembershipIds":["22NupN9w3esb"],"notify":false},"createdTask":{"id":{},"name":{}}}}
```
**updateTask**: `id` + any createTask field (all optional; no targetType/targetId/isToDo/isGroup/files) + `updateDependentTasks` (true|false|{onlyIds:[..]}|{skipIds:[..]}, default true = shift dependents) + `updateRecurringTasks` (default false) + `notify`.
**deleteTask**: `{id, deleteRecurringTasks:false}`.
**notifyTaskAssignees**: `{jobId, membershipIds:[..]}`.
**createTasksFromBudget**: `{jobId}` only.
**createTaskTemplate**: `{organizationId, name(≤128), isToDo:false, copyTasksFromJobId?, copyFrom?: {"_type":"job"|"taskTemplate","id":".."}}`.
**copyTaskTemplateToTarget** (apply template to job): `{taskTemplateId, targetType:"job"|"account"|"organization"|"taskTemplate", targetId, startDate?, startTime?, notify:true, grantAccess:false}` (grantAccess gives assignees job access).
```json
{"copyTaskTemplateToTarget":{"$":{"taskTemplateId":"22PV95WNRxYJ","targetType":"job","targetId":"<jobId>","startDate":"2026-10-01","notify":false}}}
```
**createTaskType**: `{organizationId, name(≤25), color:"#rrggbb"}`. **createTaskTypeMapping**: `{name, taskTypeId}`.

## Recipes (verified)
Schedule next 7 days, all open jobs (26 results for 9/29–10/6):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"tasks":{"$":{"size":50,"where":{"and":[["isToDo",false],["targetType","job"],["startDate","<=","2026-10-06"],["endDate",">=","2026-09-29"],[["job","closedOn"],"=",null]]},"sortBy":[{"field":"startDate"},{"field":"startTime"}]},"count":{},"nodes":{"id":{},"name":{},"startDate":{},"startTime":{},"endDate":{},"completed":{},"taskType":{"name":{}},"job":{"number":{},"name":{}},"assignedMemberships":{"nodes":{"user":{"name":{}}}}}}}}
```
Open to-dos assigned to a user (Vance: 280 incl. closed jobs):
```json
{"membership":{"$":{"id":"22Nttsgz8iVq"},"assignedTasks":{"$":{"size":20,"where":{"and":[["isToDo",true],["completed",0],["targetType","job"]]},"sortBy":[{"field":"endDate"}]},"count":{},"nodes":{"id":{},"name":{},"endDate":{},"job":{"number":{},"name":{}}}}}}
```
(add `[["job","closedOn"],"=",null]` to drop closed jobs — that path works on org.tasks, assumed same here). `membership.assignedTasks` also works for schedule (isToDo false).
A job's schedule (find job by number first):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":1,"where":["number","1048"]},"nodes":{"id":{},"name":{},"tasks":{"$":{"size":50,"where":["isToDo",false],"sortBy":[{"field":"startDate"}]},"nodes":{"id":{},"name":{},"startDate":{},"endDate":{},"completed":{},"progress":{},"isGroup":{},"parentTask":{"name":{}},"dependsOnTasks":{"nodes":{"name":{}}},"taskType":{"name":{}},"assignedMemberships":{"nodes":{"user":{"name":{}}}}}}}}}}
```

## Daily logs
Fields: id date notes job user organization files comments customFieldValues aces weatherCondition minTemperature maxTemperature rainfallAmount snowfallAmount windSpeed createdAt.
**createDailyLog**: `{jobId, date, notes?(≤10000), assignees?[assignee]≤100, customFieldValues?{}, files?[...], notify:true}`. **updateDailyLog**: `{id, date?, jobId?, notes?, customFieldValues?}`.
Recipe — last 7 days (org-wide; for one job use `job($:{id}).dailyLogs` same args):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"dailyLogs":{"$":{"size":20,"where":["date",">=","2026-09-22"],"sortBy":[{"field":"date","order":"desc"}]},"count":{},"nodes":{"id":{},"date":{},"notes":{},"job":{"name":{}},"user":{"name":{}}}}}}
```

## Time entries
Fields: id type startedAt endedAt minutes cost hourlyRate isApproved notes job costItem user comments startCoordinates endCoordinates referencedDocuments qboId createdAt.
`type` = string from `organization.timeEntryTypeNames`: "Regular Pay" | "Overtime Pay" | "Prevailing Wage" | "Salary".
Org has pseudo-jobs `***Driving***`, `***General***` for non-job time; costItem e.g. "Plumbing Labor (Other)", "Labor - RR".
**createTimeEntry**: `{type (required), userId?, jobId?, costItemId?, startedAt?(ISO datetime), endedAt?, notes?, isApproved:false, organizationId?, startCoordinates?, endCoordinates?}`.
**updateTimeEntry**: `{id, type?, startedAt?, endedAt?, jobId?, costItemId?, notes?, isApproved?, applyOvertime?, endNow: false|true|{breakDuration}}` (endNow = clock out).
Recipe — user's time this week with totals (Noah, week from Thu 9/24; datetimes are UTC, Detroit = UTC-4):
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"timeEntries":{"$":{"size":20,"where":{"and":[[["user","id"],"22NupN9w2v62"],["startedAt",">=","2026-09-24T04:00:00Z"]]},"sortBy":[{"field":"startedAt"}]},"count":{},"totalMinutes":{"_":"sum","$":"minutes"},"totalCost":{"_":"sum","$":"cost"},"nodes":{"startedAt":{},"endedAt":{},"minutes":{},"type":{},"job":{"name":{}},"costItem":{"name":{}}}}}}
```
→ `totalMinutes:1089` (hours = /60). Running (clocked-in) entries have `endedAt:null`.

## Comments (notes/messages)
Fields: id name(subject) message targetType job task document dailyLog file timeEntry account createdByUser createdAt isPinned isFromEmail isVisibleToAll/CustomerRoles/InternalRoles/VendorRoles parentComment replyToComment rootComment replies files.
**createComment**: `{targetType: file|dailyLog|timeEntry|task|document|job|account|organization|comment, targetId, message(≤4096, required), name?(subject ≤128), parentCommentId?(thread reply), isPinned:false, isReply:false(=reaction; use emoji), isVisibleToAll?/isVisibleToCustomerRoles?/isVisibleToInternalRoles?/isVisibleToVendorRoles? (nullable bools), assignees?[assignee](notify people), files?[{name,uploadRequestId} | {_type,id,name}]≤10}`.
Internal-only note: `isVisibleToInternalRoles:true, isVisibleToCustomerRoles:false, isVisibleToVendorRoles:false` (semantics inferred).
**updateComment**: `{id, message?, name?, isPinned?, isVisibleTo*?, files?}`. Also deleteComment, markCommentAsUnread exist.
Recipe — `job($:{id}).comments` returns comments on the job AND its documents/tasks (see `targetType`); filter `["targetType","job"]` for job-level only:
```json
{"job":{"$":{"id":"22PcywgmDLBk"},"comments":{"$":{"size":10,"sortBy":[{"field":"createdAt","order":"desc"}]},"count":{},"nodes":{"id":{},"message":{},"targetType":{},"createdAt":{},"createdByUser":{"name":{}}}}}}
```

## Files & uploads
file fields: id name description type(mime) size url(download) folder(string) fileTags{nodes{id name}} job task document dailyLog location contact account createdByUser storageId annotations createdAt.
Flow: 1) `createUploadRequest` → `createdUploadRequest{id url method headers}`; PUT bytes there (or pass `url` of a public file and skip the PUT). 2) `createFile` with `uploadRequestId`.
**createUploadRequest**: `{organizationId, url?(public source), type?: "image/jpeg" | {"fromName":"x.pdf"}, size?}`.
**createFile**: `{targetType: dailyLog|document|task|job|location|contact|account|organization, targetId (required), name (required), uploadRequestId? | copyFromFileId? | copyFromFile?{_type,id}, folder?(string), fileTagIds?[≤10], description?}`.
```json
{"createUploadRequest":{"$":{"organizationId":"22Nttsgz8iVp","url":"https://example.com/plan.pdf"},"createdUploadRequest":{"id":{}}}}
{"createFile":{"$":{"targetType":"job","targetId":"<jobId>","name":"plan.pdf","uploadRequestId":"<id>","folder":"Drawings","fileTagIds":["22Nttshd4XSd"]},"createdFile":{"id":{},"url":{}}}}
```
**updateFile**: `{id, name?, folder?, fileTagIds?, description?}`.
Folders = free strings; org defaults: Bidding, Drawings, Financial, Pictures, Ship Lists, Spec Sheets.
File tags (15): Customer 22Nttshd4XRg · Vendor 22Nttshd4XRh · Demolition 22Nttshd4XSZ · Permits 22Nttshd4XSa · Issues 22Nttshd4XSb · Changes 22Nttshd4XSc · Plans 22Nttshd4XSd · Pre-construction 22Nttshd4XSe · In Progress 22Nttshd4XSf · Completion 22Nttshd4XSg · Quotes 22NyWLS53cYz · Bill 22PGuwA6eHUi · Receipt 22PGuwFAyjTF · QBO 22PNFLeHPgP9 · OLD 22PTc26fkE7d. (create/update/deleteFileTag exist.)
Recipe:
```json
{"job":{"$":{"id":"<jobId>"},"files":{"$":{"size":20,"sortBy":[{"field":"createdAt","order":"desc"}]},"count":{},"nodes":{"id":{},"name":{},"folder":{},"type":{},"size":{},"url":{},"fileTags":{"nodes":{"name":{}}}}}}}
```

## Events (activity feed)
Fields: id type createdAt createdByUser createdByGrantName createdFrom data + nullable links account comment contact dailyLog document documentPayment documentRecipient file form formSubmission job location payment task timeEntry.
Gotcha: event.job/task/etc. are unions (`job` | `deletedJob{id createdAt}`). Select with `"task":{"_on_task":{"name":{}}}`. Cannot filter org.events by job (`job is not queryable`) — use `job($:{id}).events`:
```json
{"job":{"$":{"id":"22PcywgmDLBk"},"events":{"$":{"size":10,"sortBy":[{"field":"createdAt","order":"desc"}]},"count":{},"nodes":{"type":{},"createdAt":{},"createdByUser":{"name":{}},"task":{"_on_task":{"name":{}}}}}}}
```
Event types (same enum as webhooks): account/comment/contact/dailyLog/document/documentPayment/documentRecipient/formSubmission/job/location/payment/task/timeEntry × Created|Updated|Deleted, plus fileCreated/Updated/Deleted, documentSent.

## Webhooks
**createWebhook**: `{organizationId, url, eventTypes:["taskUpdated",...] (≤43)}`; webhook fields: id url eventTypes error createdAt. deleteWebhook exists.
Existing (9): contactCreated→make.com & zapier; jobUpdated→zapier; accountCreated→zapier; taskUpdated→zapier; jobCreated→tnas webhook-test & datax.to; locationCreated→winyourdata satellitephoto; documentUpdated→winyourdata comm-billing.

## Workflows
workflow fields: id name isActive triggerTypeId triggerInput actions customTriggerFields nextRunAt emailAddress url. Mutations: create/update/deleteWorkflow, createWorkflowRun, rerun/cancelWorkflowRun. createWorkflow: `{organizationId, name, triggerTypeId, triggerInput?, actions:[workflowAction], customTriggerFields?, isActive:false}` (workflowAction shape not researched; see `organization.workflowActionTypes`/`workflowTriggerTypes`).
Existing (7, all active): Fill In Job ToDos When Customer Order is Approved (documentUpdated) · Job Created Trigger (jobCreated) · Send Message When Job Stage Is Updated (jobUpdated) · Reminder to Vendor when COI Expires in 30 Days (vendorReminder) · Invoice Past Due - Change Account Status (documentReminder) · Document Updated (documentUpdated) · Task Updated Workflows (taskUpdated).
⚠ Workflows fire on our mutations (e.g. taskUpdated, jobCreated) — expect side effects.

## Forms, dashboards, data views, notifications (brief)
- Forms: `form`, `formSubmission`, create/update/delete Form(Submission). **Current grant lacks `readForm`** → `organization.forms` errors.
- Dashboards (7): Main 22P8qCsv5MCJ · Pipeline 22P8xV9CZdNd · Plumber Dashboard 22P9N2jzphCu · Active Jobs 22P9dTPyvfiy · Completed Jobs This Year 22P9dVVN5H5z · For Review 22PL8uzpET5B · WIP Report 22PQdZYWjdz3.
- dataViews: 125 saved views (`organization.dataViews{id name}`); createDataView exists. Not needed for API queries.
- Notifications: `membership.notifications`, `notificationSubscriptions`; `notify:false` on createTask/updateTask/createDailyLog/copyTaskTemplateToTarget suppresses pings; `notifyTaskAssignees{jobId,membershipIds}` sends manually.
