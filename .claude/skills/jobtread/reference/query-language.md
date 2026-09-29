# 01 — Pave Query Language Mechanics (verified 2026-09-29)

Org `22Nttsgz8iVp`. All examples below ran successfully unless marked UNVERIFIED.

## 1. Shape recap
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},
  "jobs":{"$":{"size":3,"where":[...],"sortBy":[...]},"count":{},"nextPage":{},"nodes":{"id":{},"name":{}}}}}
```
- Connection args (`$`): `where`, `sortBy`, `size`, `page`, `group`, `with`, `expressions`. Same on every connection (org-level, nested inside nodes, `whoCan`).
- Connection outputs: `nodes`, `count`, `nextPage`, `previousPage`, `sum`, `avg`, `min`, `max`, `values`, `withValues`.
- Alias with `_`: `"openJobs":{"_":"jobs","$":{...},"count":{}}` — lets you run many filtered counts/sums in ONE request (e.g. `"a":{"_":"jobs",...},"b":{"_":"jobs",...}`).
- Nested connections inside nodes take full args: `"nodes":{"documents":{"$":{"where":["type","customerOrder"]},"count":{},"total":{"_":"sum","$":"price"}}}`.

## 2. `where`
`where` is an **expression** (see §3). Two syntaxes, freely mixable:

| Short form | Meaning |
|---|---|
| `["field", value]` | equals |
| `["field", "op", value]` | op ∈ `= != < <= > >= like "not like" in "not in" between "not between"` |
| `[["rel","rel2","field"], ...]` | path into to-one relations (max 10 segments) |
| `{"and":[...]}` / `{"or":[...]}` | nest arbitrarily (1–100 items) |
| `["field", null]` / `["field","!=",null]` | IS NULL / IS NOT NULL |

Long form: `{"op":[exprA, exprB]}` e.g. `{">=":[{"field":"createdAt"},{"datetime":{"fromNow":"-P30D"}}]}`. In short form the 3rd element may itself be an expression object (`["createdAt",">=",{"datetime":{"startOf":"month"}}]` works). A bare string in a long-form operand is treated as a value.

Verified examples (jobs):
```json
["closedOn", null]                                   // open jobs (138)
["closedOn", "!=", null]                             // closed
["name", "like", "%Lot%"]                            // % wildcard
["name", "not like", "%Lot%"]
["createdAt", ">=", "2026-09-01"]                    // date string OK for datetime field
["createdAt", "between", ["2026-09-01","2026-09-15"]]  // 2nd arg MUST be a 2-array
["number", "in", ["1000","1001","1002"]]             // in/not in: max 100 items
[["location","account","name"], "like", "A%"]        // related-field filter
[["job","id"], "22PJRbj6Wu9K"]                       // filter by related id (NOT ["job", id], NOT "jobId")
[["job","id"], null]                                 // tasks with no job
["isToDo", true]                                     // booleans: plain true/false
{"and":[["closedOn",null],{"or":[["name","like","%Lot%"],{"and":[[["location","account","name"],"like","Clifford%"],["createdAt",">","2026-06-01"]]}]}]}
```
Gotchas:
- **String compare is case-insensitive for both `=` and `like`** (`["name","=","hope builders"]` matches "Hope Builders").
- **`job.number` is a STRING** → `>`/sort are lexical (`"999" > "1000"`). Cast it (see §3). `document.number` is an int.
- Relation fields are not directly comparable: `["job", X]` → error "job is not queryable". Use `[["job","id"], X]`.
- Dates: ISO `YYYY-MM-DD` or full ISO datetime. Bad value → `Expected a date and time but found "..."`.

### Filter by custom field value (verified)
Use `with` to pull the related customFieldValues, then filter on the `with` alias:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":20,
  "with":{"cf":{"_":"customFieldValues","$":{"where":[["customField","name"],"Phase"]},"values":{"$":"value"}}},
  "where":[["cf","values"],"in",["2-Active: Scheduled","3-Active: Underground"]]},
  "count":{},"nodes":{"id":{},"number":{},"name":{}}}}}
```
- `["cf","values"]` is an array; `=`/`in`/`>=` match if any element matches.
- Filter customField by id for safety: `[["customField","id"],"22Nuh4aSVtcP"]` (Phase). Name works too.
- Boolean CF: `[["cf","values"],"=",true]` and `"true"` both worked.
- Date CF values are `YYYY-MM-DD` strings → `[["fi","values"],">=","2026-09-01"]` works.
- "Has no value": use `"count":{}` in the with and `[["cf","count"],0]` — NOTE: returned 0 for Phase (every job has a row, possibly null value). To find blank, try `[["cf","values"],null]` (UNVERIFIED).

## 3. Expressions (`expression` oneOf)
| Form | Example |
|---|---|
| value | `{"value":1000}` |
| field | `{"field":"price"}` / `{"field":["job","location","account","name"]}` |
| subfield | `{"subfield":[expr,["path"]]}` — errors "X is not subqueryable" on relations and with-aliases; use `field` path instead. Purpose UNVERIFIED |
| if | `{"if":[cond, then, else]}` (2–100 items) |
| cast | `{"cast":[expr,"int"]}` types: `string number int boolean date datetime` |
| formatDatetime | `{"formatDatetime":[expr,{"value":"YYYY-MM"}]}` — Postgres to_char patterns (`Mon DD, YYYY HH24:MI`). Output in UTC (root timeZone did NOT change it) |
| date / datetime | `{"date":{}}` = today; `{"datetime":{"fromNow":"-P30D","startOf":"month"}}`. `fromNow` = ISO-8601 duration (`-P30D`,`-P1M`,`-P1W`,`-PT48H`); `"-30 days"` → error. startOf/endOf: `year quarter month week day` (+ `hour minute second millisecond` for datetime) |
| arithmetic | `+ - * /` (arrays 1–100), `^` (2), `round` ([x] or [x,digits]), `sqrt floor ceil` |
| misc | `coalesce`, `max`, `min`, `concat`, `!`, `and`, `or`, comparison ops, `distance` (two `{latitude,longitude}`) |

Define named expressions per connection and reference them by name in `where`, `sortBy`, `group`, aggregates, and read them back via `withValues` or `values`:
```json
"jobs":{"$":{"size":3,
  "expressions":{"num":{"cast":[{"field":"number"},"int"]}},
  "where":["num",">",1000],
  "sortBy":[{"field":"num","order":"desc"}]},
  "maxNum":{"_":"max","$":"num"},"nodes":{"number":{}}}
```
Other verified expressions (documents): `{"concat":[{"field":"type"},{"value":" #"},{"cast":[{"field":"number"},"string"]}]}`, `{"round":[{"*":[{"field":"price"},{"value":0.06}]},{"value":2}]}`, `{"if":[{">":[{"field":"price"},{"value":1000}]},{"value":"big"},{"value":"small"}]}`, `{"coalesce":[{"field":"dueDate"},{"field":"issueDate"}]}`, `{"!":{">":[...]}}`.

**Gotcha:** type-mismatched expressions (e.g. `coalesce` of a date and a string `"none"`) cause a generic 500 "Something went wrong on our end" — even if the expression is unused. Keep coalesce/if branches the same type.

## 4. `with` (per-node subqueries; like a correlated subquery / join)
`with: {alias: {"_":"<connection on the node>","$":{where...}, <aggregates>}}`. Aggregates inside: `count:{}`, `"x":{"_":"sum","$":"price"}`, `values:{"$":"value"}`, etc. Reference in where/sortBy/expressions as `["alias","aggName"]`. Read results via `withValues` (one object per node, includes `id`, with-values AND named expressions).
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":5,
  "with":{
    "inv":{"_":"documents","$":{"where":["type","customerInvoice"]},"amt":{"_":"sum","$":"price"}},
    "co":{"_":"documents","$":{"where":{"and":[["type","customerOrder"],["status","approved"]]}},"amt":{"_":"sum","$":"price"}}},
  "expressions":{"unbilled":{"-":[{"coalesce":[{"field":["co","amt"]},{"value":0}]},{"coalesce":[{"field":["inv","amt"]},{"value":0}]}]}},
  "where":["closedOn",null],
  "sortBy":[{"field":"unbilled","order":"desc"}]},
  "withValues":{},"nodes":{"number":{},"name":{}}}}}
```
→ `withValues:[{"inv":{"amt":null},"co":{"amt":59478},"unbilled":59478,"id":"22PJRbj6Wu9K",...}]`.
- `sum` over zero rows = `null` → wrap in `coalesce`.
- Jobs having ≥1 pending invoice, sorted by amount: with `inv` (count + sum), `where:[["inv","count"],">",0]`, `sortBy:[{"field":["inv","amt"],"order":"desc"}]` ✔.
- withValues also echoes referenced plain fields as `null` noise (e.g. `closedOn:null`) — ignore.

## 5. sortBy
`[{"field":"createdAt","order":"desc"}]` — `field` string or path array; max **5** entries (6 → "must be at most length 5").
- order: `asc` (default), `desc`, `asc nulls first`, `desc nulls last`.
- Related-field sort ✔: `{"field":["location","account","name"]}`.
- Sort by expression name or with-aggregate (`["inv","amt"]`) or group agg alias ✔.

## 6. Paging
- Default page size **10**; max **100** (`size:1000` → "Expected size of 1000 to be no more than 100").
- `nextPage`/`previousPage` are opaque tokens; pass as `"page":"<token>"` with the SAME where/sortBy/size. `nextPage:null` = last page.
- Loop: request `nextPage`, repeat until null. Use `count` first to decide whether paging is needed.

## 7. Aggregates (connection-level, over the WHOLE filtered set, not the page)
```json
"documents":{"$":{"where":{"and":[["type","customerInvoice"],["status","pending"],["dueDate","<",{"date":{}}]]}},
  "count":{},"bal":{"_":"sum","$":"price"},"avgP":{"_":"avg","$":"price"},"minD":{"_":"min","$":"issueDate"},"maxP":{"_":"max","$":"price"}}
```
- Arg is field name string, path array, or expression name. `sum`/`avg` → number|null; `min`/`max` any type.
- `values` → **NOT distinct**, raw per-row values, capped at 100 rows, not in sortBy order. For distinct values use `group`.
- `count` with an argument (`{"_":"count","$":"dueDate"}`) → 500 error. Use plain `count:{}` + a where filter.
- Multiple sums: alias each (`"billed":{"_":"sum","$":"price"},"cost":{"_":"sum","$":"cost"}`).

## 8. group (GROUP BY)
```json
"documents":{"$":{"size":50,
  "where":["createdAt",">=","2026-01-01"],
  "group":{"by":[["job","location","account","name"]],
           "aggs":{"n":{"count":"id"},"total":{"sum":"price"}},
           "where":["total",">",50000]},          // HAVING
  "sortBy":[{"field":"total","order":"desc"}]},
 "count":{},"withValues":{}}
```
- `by`: array of path arrays (1–5), e.g. `[["type"],["status"]]`; may be an expression name (`[["mon"]]` with `expressions:{"mon":{"formatDatetime":[{"field":"issueDate"},{"value":"YYYY-MM"}]}}`) → monthly totals ✔.
- `aggs`: `{alias:{count|sum|avg|min|max|values:"field"}}`. **count needs a field string** (`{"count":"id"}`); `{"count":{}}` → `The field "[object Object]" does not exist`, `null` → non-null required.
- `group.where` filters groups (HAVING) on agg aliases.
- Results are in **`withValues`** (one row per group: group keys + aggs + a representative `id`). `count` = number of groups. `nodes` = representative record per group (choose with `firstIdBy:[{field,order}]`, UNVERIFIED). size/page apply to groups.
- Verified doc totals by type/status: customerInvoice approved n=954 total 2,392,755.41; pending n=35 205,331.26; customerOrder approved n=525 2,719,076.04 (as of 2026-09-29).

## 9. Root options & root utility fields
Root `$` (top-level key `"$"` beside root fields):
| key | effect |
|---|---|
| `notify:false` | suppress notifications for mutations in this request (accepted; recommend on all writes) |
| `timeZone:"America/Detroit"` | IANA zone for tz-aware data (e.g. `{"date":{}}` "today"). Did not change `formatDatetime` output (UTC) |
| `viaUserId:"<userId>"` | "restrict results to a user scope"; with a Plumber user, org job count unchanged — effect not observed |
| `grantKey` | alternate grant key (not needed via MCP) |
```json
{"$":{"timeZone":"America/Detroit","notify":false},"organization":{...}}
```
Root fields:
- `version:{}` → API build hash string.
- `currentGrant:{id{},name{},expiresAt{},allowedActions{},user{name{}},organization{id{},name{}}}`. This MCP grant ("Access for claude.ai", expires 2026-12-27) allows create/read/update actions but **NO delete* actions** (deleteJob, deleteDocument, etc. not allowed) and no integrations. Check `allowedActions` before planning a write.
- `can:{"$":{"action":"readJob","id":"<id>"}}` → boolean. Asking about an action the grant lacks errors: `This request requires the "deleteJob" action but the provided grant does not allow it.`
- `whoCan:{"$":{"action":"readJob","id":"<id>","size":5},"count":{},"nodes":{"user":{"name":{}}}}` → membership connection (full connection args).
- `eventTypes:{}` → list of webhook event names: `{account,comment,contact,dailyLog,document,documentPayment,documentRecipient,file,formSubmission,job,location,payment,task,timeEntry}{Created,Updated,Deleted}` + `documentSent`.
- `signQuery:{"$":{"query":{...}}}` → string token to run that query later with this grant (not executed).
- `pdf` — **isWrite**; input oneOf `budget|dailyLogs|document|formSubmission|selections|specifications|tasks` each `{id:"<constant>",download:bool,options:{...}}` (e.g. `{"document":{"id":"document","options":{"id":"<docId>"}}}`), returns `uploadRequest` (url). Not executed.
- `tutorials:{"$":{"search":"x"}}` → JobTread help videos (not API docs).

## 10. Error messages
| Message | Cause / fix |
|---|---|
| `The field "foo" does not exist at "job"` (+ `Did you mean "job"?`) | bad field name in where/select; introspect `{"schema":{"$":{"path":"job"}}}` |
| `job is not queryable` | compared a relation directly → use `[["job","id"],X]` |
| `X is not subqueryable` | `subfield` on relation/with alias → use `field` path |
| `The value {...} does not resolve to "value","field",...` | unknown operator (e.g. `contains`) → use `like "%x%"` |
| `... "between"."1" must be an object` | between needs `[low,high]` array |
| `must be at most length 5` | sortBy >5 entries |
| `Expected size of N to be no more than 100` | size cap |
| `Expected a date and time but found "..."` | bad date literal |
| `Expected an ISO8601 duration` | fromNow must be like `-P30D` |
| `Expected a JobTreadID but got "..."` | malformed id (well-formed but missing id → `null`, no error) |
| `A non-null value is required at ...` | required arg null |
| `Something went wrong on our end...` (500) | expression type mismatch, or `count` with a field arg. Bisect the query |
| `This request requires the "X" action but the provided grant does not allow it` | grant lacks permission |

## 11. Token-efficiency tips
- Select only needed scalars; never select a whole object (`"location":{}` returns `{}` — you must name subfields).
- Need a number? Use `count` / aliased `sum` instead of pulling nodes. Batch many counts in one request with `_` aliases.
- Use `group` + `withValues` for breakdowns (by type/status/customer/month) instead of paging raw rows.
- Use `with` + `expressions` + `sortBy` to compute & rank server-side (e.g. unbilled per job) and `size` small.
- Default size is 10 — always set `size` explicitly; ≤100.
- Filter custom fields server-side with the `with` pattern rather than fetching all `customFieldValues`.
- Cache stable ids (org, custom field ids e.g. Phase `22Nuh4aSVtcP`, Job Type `22NtuVAwrQWC`) rather than re-looking them up.
- Narrow schema introspection with `path` + `search`; expand only specific leaves (`organization.jobs.$.group`).
