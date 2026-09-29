---
name: create-budget
description: >
  Create a budget for an existing residential new construction job in JobTread for Barrett Plumbing Inc.
  Use this skill any time the user wants to add a budget, build an estimate, set up cost items,
  or populate a job's budget. Trigger phrases include: "create a budget", "add a budget",
  "build a budget for job [number]", "set up the budget", "add budget to [job]",
  "estimate for [address]", "budget this job", or any time the user mentions adding cost items,
  line items, or budget groups to a job. This skill is for residential new construction budgets
  specifically — it does NOT cover service jobs (those use the create-service-job skill).
compatibility: JobTread connector (mcp__JobTread__query / JobTread:query). Pairs with the `jobtread` skill.
---

# Create Budget — Residential New Construction

Builds a full plumbing budget on an existing job from Barrett Plumbing's live catalog template
**`*New Construction - Residential`** (`22PUu9kHNteF`), customized to the house. All calls use the
single JobTread query tool. IDs verified 2026-09-29. Org `22Nttsgz8iVp`.
Put `"$":{"notify":false}` at the root of every write.

Two approaches:
- **Actual Fixtures** — real fixture selections (toilets, faucets, sinks, trims, tub/shower units) from the template.
- **Fixture Allowances** — install components only; fixtures replaced by lump-sum allowances from
  `*Fixture Allowances` (`22P9dyh7S3uV`).

## Pricing rule — critical
**Never invent, calculate, or modify unitCost / unitPrice.** Copy them exactly from the template/catalog.
Only change **quantity**. Exceptions (defined below): Buffer, Warranty Accrual, and Fixture Allowance amounts.

---

## Step 1: Find the job and check for an existing budget (ONE call)
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":5,"where":{"or":[["number","<n>"],["name","like","%<text>%"],[["location","address"],"like","%<text>%"]]}},
  "nodes":{"id":{},"number":{},"name":{},"location":{"formattedAddress":{}},
   "budget":{"_":"costItems","$":{"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"}}}}}}
```
Multiple matches → confirm. If `budget.count > 0`, warn and confirm before adding more.

## Step 2: Gather house configuration
Ask conversationally; extract what's already given ("3 bed 2 bath, allowances, 50 gal propane power vent").
1. **Fixture approach:** actual fixtures or allowances.
2. **Bathrooms** — for each: name ("Master Bathroom", "Main Floor 1/2 Bath"…), type (full w/ tub/shower,
   full w/ shower only, half), tub/shower drain **LH or RH**, quantity if identical baths, number of sinks,
   allowance amount (if allowances).
3. **Basement bathroom?** → sewage crock with pump is always required (don't ask).
4. **Kitchen:** allowance amount, or sink/faucet (template defaults fine); garbage disposal (default yes).
5. **Water heater:** 40 or 50 gal (default 50); natural gas / propane / electric; atmospheric vs power vent;
   Rheem or Bradford White (default Rheem). Pick the matching item in the template's water heater group.
6. **Sewage** (if no basement bath): pump crock, or empty crock (no pump).
7. **Outside faucets:** count (default 2).
8. **Optional additions** (template group "Optional Additions"): irrigation backflow preventer, heat pump water
   heater, smart leak detection, passive radon. Default: none — ask only if the user brings them up.
9. **Labor hours:** Step 3.

## Step 3: Estimate labor hours
Reference spreadsheet bundled: `labor-hours-estimator.xlsx`.

**Underground** — base 16; per toilet 1.5; per shower/tub drain 2.0; per sink/lav 1.0; kitchen 2.5;
laundry 1.5; floor drain/crock 2.0; per backwater valve 1.0; water service entry 3.0.
**Rough-In** — base 12; per toilet 1.5; per shower 3.0; per tub/shower 3.5; per sink/lav 1.5; kitchen 2.0;
laundry box 1.5; ice maker 0.5; per outside faucet 1.5; water heater 2.0.
**Finish** — base 8; per toilet 1.5; per shower 2.5; per tub/shower 3.0; per sink/lav 1.5; kitchen sink 2.5;
disposal 0.5; water heater 4.0; per outside faucet 0.5; washer box 0.5; ice maker 0.25.
**Mobilization** per phase: days = ROUNDUP(hours / 16); mobilization hours = days × 2.

Present and let the user adjust:
> | Phase | Labor Hrs | Days (2 crew) | Mob Hrs |
> |---|---|---|---|
> | Underground | 34.5 | 3 | 6 |
User-supplied hours override; still compute mobilization from them.

## Step 4: Fetch the live template (2 pages of items)
```json
{"costGroup":{"$":{"id":"22PUu9kHNteF"},
 "descendentCostGroups":{"$":{"size":60},"nodes":{"id":{},"name":{},"description":{},"position":{},"quantity":{},"parentCostGroup":{"id":{}}}},
 "descendentCostItems":{"$":{"size":100},"nextPage":{},
  "nodes":{"id":{},"name":{},"description":{},"position":{},"costGroup":{"id":{}},"quantity":{},"unitCost":{},"unitPrice":{},
   "isTaxable":{},"costCode":{"id":{}},"costType":{"id":{}},"unit":{"id":{}},"organizationCostItem":{"id":{}}}}}}
```
Repeat `descendentCostItems` with `"page":"<nextPage>"` until `nextPage` is null (126 items ≈ 2 pages).
Rebuild the tree: groups by `parentCostGroup.id`, items by `costGroup.id`, siblings sorted by `position`.
Allowances template (if needed): same query with id `22P9dyh7S3uV`.

Template layout (as of 2026-09-29 — trust the live fetch if it differs):
```
Underground Plumbing
  ├─ Permit, Backwater Valve 3", Backwater Valve 2"
  ├─ Crock (Empty-No Pump)                    ← choose one of these two
  ├─ Sewage Crock, Pump & Check Valve         ←
  └─ Plumbing Permit, Labor & Materials  [Labor - RU, Mobilization]
       └─ PVC Pipe & Fittings
Rough In Plumbing
  ├─ Washing Machine Box, Ice-Maker Box, Outside Faucet (qty = count)
  ├─ Tub/Shower     [LH and RH units — set chosen qty, drop the other]
  ├─ Shower Only    [LH/RH seat units, Moen + Delta rough-in valves, drain]
  └─ Rough-In Plumbing Labor & Materials [Labor - RR, Mobilization, PEX, stub outs, nail plates, AAV, flashing, service ell, drop ear]
       ├─ *PVC Pipe & Fittings
       └─ *Copper Tube & Fittings
Finish Plumbing
  ├─ Labor & Materials [Labor - RF, Mobilization, Warranty Accrual]
  ├─ Water Heater > 50 Gallon Water Heater [7 alternative heaters] > Water Heater Components
  ├─ Kitchen > Kitchen Sink & Components [faucet, sinks] > Kitchen Sink Components ; Garbage Disposal
  └─ Bathroom
       ├─ Tub/Shower Trim (Chrome) ; Shower Trim [3 alternatives]
       ├─ Gerber Viper Standard Height, Round Front Toilet > Install Components
       ├─ Gerber Viper Comfort Height, Elongated Toilet > Install Components
       └─ Bathroom Sink [2 faucet alternatives] > Lavatory Components
Optional Additions (Irrigation Backflow Preventer, Heat Pump WH, Smart Leak Detection, Passive Radon)
```
The template holds **alternatives side by side** (qty 0 = not chosen). Include only the chosen alternative;
omit zero-quantity alternatives from the job budget.

## Step 5: Build the budget — one `createCostGroup` call per phase
Build each top-level phase as ONE nested `lineItems` tree and create it in a single call. This appends to
the job and never touches other budget lines. (Never use `updateJob.lineItems` — it can replace the whole budget.)

For every copied item send: `_type:"costItem"`, `name`, `description`, `quantity` (adjusted), `unitCost`,
`unitPrice`, `isTaxable`, `costCodeId`, `costTypeId`, `unitId` (all from the template), and
`organizationCostItemId` = the template item's `organizationCostItem.id` (keeps catalog linkage).
Groups: `{"_type":"costGroup","name":..,"description":..,"lineItems":[...]}`.

```json
{"$":{"notify":false},"createCostGroup":{"$":{"jobId":"<jobId>","name":"Underground Plumbing","lineItems":[
   {"_type":"costItem","name":"Permit","quantity":1,"unitCost":325,"unitPrice":325,"isTaxable":false,
    "costCodeId":"..","costTypeId":"..","unitId":"..","organizationCostItemId":".."},
   {"_type":"costGroup","name":"Plumbing Permit, Labor & Materials","lineItems":[
      {"_type":"costItem","name":"Labor - RU","quantity":34.5, "...":"template values"},
      {"_type":"costGroup","name":"PVC Pipe & Fittings","lineItems":[ "..." ]}]}]},
 "createdCostGroup":{"id":{}}}}
```
Order: Underground → Rough In → Finish → (Fixture Allowances) → (Optional Additions if chosen).
After the first call, read the job budget back to confirm nesting worked before sending the rest. If
`createCostGroup` rejects nested `lineItems`, fall back to `createCostGroup{jobId|parentCostGroupId,name}` +
`createCostItem{costGroupId,...}` per item.

### Customization rules
- **No Travel Charge** — do not add Travel Charge items to any phase.
- **Labor - RU / RR / RF** quantities = Step 3 hours; **Mobilization** in each phase = Step 3 mob hours.
- **Sewage:** include exactly one of "Sewage Crock, Pump & Check Valve" (basement bath or pump requested) or
  "Crock (Empty-No Pump)".
- **Outside Faucet** qty = count. Washer box / ice-maker box qty 1 (0 → omit if user says none).
- **Tub/shower & shower units (Rough In):** one unit per tub/shower or shower bathroom matching LH/RH;
  shower-only baths also get the rough-in valve + drain from "Shower Only" (use the Moen valve unless told Delta).
  Tub/shower baths need a rough-in valve too — use the Moen Rough-In Valve item.
- **Copper stub out elbows:** ~2–3 per fixture location.
- **Water heater:** keep only the selected heater (qty 1) + Water Heater Components. Rename the size group if 40 gal.
- **Kitchen:** Actual → Kitchen Sink & Components (faucet + ONE sink + components). Allowances → only the
  "Kitchen Sink Components" group (no sink/faucet), and set the Kitchen group description to
  `^Fixture Allowance: $[amount]^`. Garbage Disposal group if requested.
- **Bathrooms:** replicate the template's Bathroom group **once per bathroom**, renamed to the bathroom's name:
  - Trim: Tub/Shower Trim (Chrome) for tub/shower baths; Shower Trim (Moen Eva chrome default) for shower-only; none for half baths.
  - Toilet: Comfort Height Elongated group by default (Standard Round if asked) — Actual keeps the toilet +
    seat + Install Components; Allowances keeps **only Install Components**.
  - Bathroom Sink: Actual → one faucet (qty per sink) + Lavatory Components; Allowances → Lavatory Components
    only. Lavatory Components qty × number of sinks.
  - Identical baths (qty > 1): multiply item quantities accordingly.
  - Allowances: set each bathroom group description to `^Fixture Allowance: $[amount]^`.
- **Fixture Allowances** group (allowances only), from `*Fixture Allowances`: Kitchen Fixture Allowance
  (`22P9dyh7TXVe`) and Bathroom Fixture Allowance (`22P9dyh7TXVf`), qty 1, Lump Sum. These are the only
  items where you set price: `unitPrice` = allowance amount (bathroom = sum of all bathroom allowances),
  `unitCost` = amount × 0.65 rounded to cents (Fixtures cost type margin is 35%; margin is on price, so
  cost = price × (1 − margin). Re-check the live margin: `{"costType":{"$":{"id":"22Nu4hSz5GP6"},"margin":{}}}`).
  Keep `allowanceType` as in the template ("price").

### Buffer (one per phase, after items are in)
Target ≈ 5% padding that also rounds the phase total to whole dollars:
target = ROUNDUP(phase price sum × 1.05) to the nearest dollar; Buffer = target − phase sum.
Create with `createCostItem{costGroupId:<phase labor & materials group id>, name:"Buffer", quantity:1,
unitCost:0, unitPrice:<buffer>, isTaxable:false, organizationCostItemId:"22PHmgptrrEK",
costCodeId:"22Nttshd4XSU" (9999 Miscellaneous), costTypeId:"22Nttshd4XSY" (Other), unitId:"22Nttshd4XRq" (Lump Sum)}`.
**Always 9999 Miscellaneous / Other** — the catalog Buffer item is coded 2000 Materials; override it with these ids.

### Warranty Accrual (last)
The template already includes "Warranty Accrual" (1300 Other / Lump Sum) in Finish > Labor & Materials.
After everything else (incl. buffers), set it with `updateCostItem{id, unitCost:0, unitPrice:<amount>}`:
amount = a round number (e.g. $150, $200, $300) between 0.5% and 1% of the whole-job price total.

## Step 6: Verify and report
```json
{"job":{"$":{"id":"<jobId>"},
 "groups":{"_":"costGroups","$":{"size":100,"where":[["document","id"],"=",null]},"nodes":{"id":{},"name":{},"parentCostGroup":{"id":{}}}},
 "items":{"_":"costItems","$":{"size":100,"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"},"c":{"_":"sum","$":"cost"},
   "nodes":{"name":{},"quantity":{},"price":{},"costGroup":{"id":{}}}}}}
```
(page with `nextPage` if count > 100). Report:
- Total cost / total price / margin %
- Per-phase totals (Underground, Rough-In, Finish, Allowances)
- Line item count; bathroom configuration recap
- **Rationale:** labor hour math, water heater chosen and why, sewage choice, buffer math per phase,
  warranty accrual math, assumptions (defaults used: Moen Eva chrome, comfort-height elongated, Rheem, etc.)

Offer adjustments ("switch to Bradford White", "+10 rough-in hours") via `updateCostItem{id, quantity}` —
quantities only, then recompute buffers.

## Notes
- The Claude connector cannot delete. To "remove" a line, `updateCostItem{id, quantity:0}` and tell the user;
  to remove a whole wrong group, ask the user to delete it in JobTread (a budget backup is auto-saved on changes).
- `isTaxable`: copy from template (permits and labor are non-taxable).
- Always pass `organizationCostItemId` so budget lines stay linked to the catalog.
