---
name: "create-budget-commercial"
description: >
  Create a budget for an existing commercial job in JobTread for Barrett Plumbing Inc., starting from the
  "*New Commercial Job" template and sizing labor with Barrett's commercial estimator spreadsheet.
  Use this skill any time the user wants to budget, estimate, or bid a commercial job — restaurants,
  retail, offices, schools, churches, medical, bathhouses/restroom buildings, GC-bid apartments, tenant
  build-outs, or any job whose Category is Commercial. Trigger phrases include: "create a commercial
  budget", "budget this commercial job", "build the budget for job [number]" (commercial job), "estimate the
  [restaurant/school/bathhouse] job", "budget from the plans / fixture schedule", "run the commercial
  estimator", "price out the fixture schedule", or any time the user brings plumbing plans, a fixture
  schedule with tags (WC-1, LAV-1, FD-1…), a supplier fixture quote, or a filled-in commercial estimator.
  Residential new construction uses create-budget-residential; service jobs use create-service-job.
compatibility: JobTread connector (mcp__JobTread__query / JobTread:query). Pairs with the `jobtread` skill. Python 3 + openpyxl for scripts/labor_estimate.py.
---

# Create Budget — Commercial

Builds a full plumbing budget on an existing commercial job from Barrett Plumbing's live catalog template
**`*New Commercial Job`** (`22P5x4sLCTad`), customized to the plans. (Not "*New Commercial Job (w/ Parameters)".)
All calls use the single JobTread query tool. IDs verified 2026-09-29. Org `22Nttsgz8iVp`.
Put `"$":{"notify":false}` at the root of every write.

Commercial differs from residential in three ways that drive this skill:
- **Labor** comes from the commercial estimator (pipe footage by location + fixture/equipment counts),
  not a house configuration — and the estimator's hours are by system, so they are split into phases.
- **Fixtures and equipment are tagged** from the plan's fixture schedule (WC-1, LAV-1, FD-1, WH-1…) and are
  priced from a supplier quote, not the catalog.
- **Materials are sized from the takeoff** (pipe LF, hangers, rod, beam clamps) instead of a fixed house kit.

## Pricing rule — critical
**Never invent, calculate, or modify unitCost / unitPrice.** Copy them from the template; where a template item
has `unitCost`/`unitPrice` = null it inherits from its catalog item, so copy the catalog item's values. Only
change **quantity**. The only exceptions, each defined below: tagged fixtures/equipment (supplier quote),
subcontractor items (sub quote), the Permit (AHJ fee), Buffer, and Warranty Accrual. A price that comes from a
quote uses `unitCost` = the quoted cost and `unitPrice` = cost ÷ (1 − the item's cost-type margin), rounded to
cents, unless Vance gives a different margin for this bid. Live margins:
`{"organization":{"$":{"id":"22Nttsgz8iVp"},"costTypes":{"nodes":{"id":{},"name":{},"margin":{}}}}}`
(2026-09-29: Fixtures 35% · Materials (Commodity) 28% · Appliance 30% · Subcontractor 10% · Permit 0%).
Never use the estimator's dollar figures (material $/LF, blended rate, overhead/profit) as prices.

---

## Step 1: Find the job and check for an existing budget (ONE call)
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"jobs":{"$":{"size":5,"where":{"or":[["number","<n>"],["name","like","%<text>%"],[["location","address"],"like","%<text>%"]]}},
  "nodes":{"id":{},"number":{},"name":{},"location":{"formattedAddress":{}},
   "customFieldValues":{"$":{"where":[["customField","id"],"=","22NtuVNPeBDB"]},"nodes":{"value":{}}},
   "budget":{"_":"costItems","$":{"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"}}}}}}
```
Multiple matches → confirm. If `budget.count > 0`, warn and confirm before adding more. The custom field is
Category — if it says Residential, confirm with Vance and hand off to create-budget-residential.

## Step 2: Gather the bid inputs
Work from what Vance provides — plans/specs PDF, the fixture schedule, a takeoff, supplier and sub quotes,
or a filled-in copy of his estimator workbook. Read attachments first; only ask about what's missing.
1. **Fixture schedule:** every tag, its description (make/model), and count. Note which tags are rough-in items
   (CO, FCO, WCO, FD, FS) vs finish fixtures/equipment.
2. **Quotes:** supplier fixture/equipment quote (unit cost per tag); sub quotes (insulation, excavation,
   fire stop, core drilling…); permit fee from the AHJ. Missing quotes don't block the budget — those lines go
   in at $0 and are listed under "Needs pricing" in the report.
3. **Takeoff:** pipe LF per system (DWV / cold / hot / recirc / compressed air) and size, split underground /
   in-wall / ceiling; CMU block wall drops; masonry sleeves; demo LF and fixtures to remove (renovations).
4. **Scope:** demo, excavation, concrete cutting, insulation (Barrett or sub), fire stop, lift rental, grease
   interceptor, RPZ/PRV, compressed air, roof drains, anything the estimator has no row for (see Step 3).
5. **Defaults** — list back in one line so Vance can correct any:
   complexity Normal · wall type from plans (CMU Block if block) · slab on grade Y · hanger Single Clevis ·
   water pipe Type L Copper (or Type K Copper / PEX-B — this changes the water labor rates) · crew 2 plumbers × 8 hr ·
   plan confidence High (5% buffer) ·
   PM-Commercial 1 hr per phase (template) · no Travel Charge · quoted items at their cost-type margin.

## Step 3: Estimate labor hours with the v3.1 estimator
Labor hours come from Vance's estimator, bundled as `BP_Commercial_Estimator_v3.1.xlsx` (his v3 with its formula
bugs fixed — see the workbook's "CHANGES v3.1" sheet). `scripts/labor_estimate.py`
reproduces its labor math exactly (PIPE ESTIMATE, FIXTURE ESTIMATE incl. hangers, CMU drops, SLEEVE SCHEDULE,
DEMO ESTIMATE → SUMMARY hours) and reads every rate — and the row-to-rate wiring — live from the workbook, so
use the script rather than doing the math by hand, and never hard-code table values into this skill. If Vance
sends an updated estimator, replace the xlsx and the script picks up his numbers.

**If Vance sends a filled-in estimator**, run it directly (inputs and his rates come from his copy):
```bash
python3 <skill-dir>/scripts/labor_estimate.py --from-xlsx /path/to/his_estimate.xlsx
```
**Otherwise** write a config JSON (keys and formats are in the script docstring; names accept a short
unambiguous prefix of the sheet's row name):
```bash
cat > /tmp/labor.json <<'JSON'
{"wall_type":"CMU Block","complexity":"Normal","hanger_type":"Single Clevis Hanger","water_material":"Type L Copper",
 "pipe":{"dwv":{"4\"":[120,0,0],"2\"":[0,0,80],"1-1/2\"":[0,0,130]},
         "cold":{"1\"":[0,0,80],"1/2\"":[0,280,120]}},
 "fixtures":{"Water Closet (Flush":6,"Lavatory (Single)":6,"Floor Drain (4":9,"Mop Sink":1,"Cleanout":4},
 "cmu_drops":28,"sleeves":[{"size":"2\"","qty":1}],
 "extra_hours":[{"item":"Showers SH-1 x2","phase":"RI","hours":6}]}
JSON
python3 <skill-dir>/scripts/labor_estimate.py /tmp/labor.json          # add --format json for full detail
```
Pipe values are `[underground LF, in-wall LF, ceiling LF]` (or `{"ug":..,"wall":..,"ceiling":..,"override":final_lf}`).

**Map the fixture schedule to estimator rows** (FIXTURE SCHEDULE names):
| Plan item | Estimator row |
|---|---|
| Water closet, flush valve / tank | `Water Closet (Flush Valve)` / `Water Closet (Tank Type)` |
| Urinal · lavatory · group/trough lav | `Urinal (Flush Valve)` · `Lavatory (Single)` · `Lavatory (Multiple / Group)` |
| 3-comp sink · hand/prep/scrub/single-bowl sink | `3-Compartment Sink` · `Prep Sink / Hand Sink` |
| Break-room/kitchen sink · dishwasher · ice machine | `Kitchen Sink (Double Basin)`/`(Single Basin)` · `Commercial Dishwasher` · `Ice Maker Connection` |
| Mop/service sink · floor drain · floor sink · cleanout (CO/FCO/WCO) | `Mop Sink / Service Sink` · `Floor Drain (2"/3"/4")` · `Floor Sink` · `Cleanout` |
| EWC / drinking fountain / bottle filler · eyewash | `Drinking Fountain` · `Emergency Eyewash / Shower` |
| Hose bibb · wall hydrant · roof drain · trap primer | `Hose Bib / Yard Hydrant` · `Wall Hydrant (Non-Freeze)` · `Roof Drain` · `Trap Primer Valve` |
| Water heater · tankless · expansion tank · T&P/drain · TMV · recirc pump | `Commercial Water Heater (Tank)` · `Tankless Water Heater` · `Expansion Tank Connection` · `Water Heater Drain / Relief` · `Mixing Valve / TMV` · `Recirculation Pump` |
| RPZ/backflow · PRV | `Backflow Preventer (1" and under)`/`(over 1")` · `PRV Station` |
| Grease interceptor indoor · exterior/in-ground, sand separator | `Grease Interceptor (Indoor)` · `Ext. Grease Interceptor / Sand Sep.` |
**No estimator row** for showers, gas piping,
pressure testing/inspection attendance (LABOR TABLES Table G is unused), roof-drain leaders, etc. — ask Vance for
hours and add them with `extra_hours` (never estimate them yourself).

**Phase split** (the sheet reports hours by system; JobTread budgets by phase):
- Pipe: underground LF → Underground; in-wall + ceiling LF → Rough-In.
- Fixtures with separate Table D values: the `— Rough-In` part → Rough-In, the `— Final Set` part → Finish.
- Floor drains, floor sinks, cleanouts → Underground on slab on grade (else Rough-In); exterior grease
  interceptor → Underground; hose bibs, wall hydrants, roof drains, trap primers, PRV, RPZ, indoor interceptor
  → Rough-In; everything else (sinks, eyewash, dishwasher/ice connections, water heater items) → Finish.
- Hangers, CMU drops, sleeves → Rough-In. Demo pipe + fixture removal + cap/stub → Demo.
Vance can move anything: `"phase_overrides":{"sleeves":"UG","Commercial Water Heater":"RI"}`.

The output gives, per phase: raw man-hours, **Labor qty** (rounded up to the whole hour), **Mobilization qty**
(= man-hours ÷ shift hours, rounded up — the template's "1 hr per guy per day"), elapsed days; plus the
sheet's SUMMARY hours, the takeoff quantities for Step 5, the contingency % table, and ⚠ warnings. Present:
> | Phase | Labor Hrs | Mobilization Hrs | Elapsed days |
> |---|---|---|---|
> | Underground | 35 | 5 | 2.16 |
> | Rough-In | 280 | 35 | 17.46 |
> | Finish | 43 | 6 | 2.66 |
Also show the phase-detail lines, the SUMMARY line, key inputs, and every ⚠ warning. User-supplied hours
override the script; changed inputs → rerun.

**Older v3 copies.** If Vance sends a filled-in copy of his original v3, the script still reads it. It shows
that sheet's own totals and warns where v3 was wrong: pipe demo double-counted, cap/stub hours missing from the
hours, one grease interceptor charged as indoor + exterior (zero one with
`"qty_overrides":{"Grease Interceptor (Exterior":0}`), recirc LF with no labor, and water labor always at
Type L copper rates. JobTread phases always use the corrected hours. Suggest he move to v3.1.

## Step 4: Fetch the live template (1–2 pages of items)
```json
{"costGroup":{"$":{"id":"22P5x4sLCTad"},
 "descendentCostGroups":{"$":{"size":60},"nodes":{"id":{},"name":{},"description":{},"position":{},"quantity":{},"parentCostGroup":{"id":{}}}},
 "descendentCostItems":{"$":{"size":100},"nextPage":{},
  "nodes":{"id":{},"name":{},"description":{},"position":{},"costGroup":{"id":{}},"quantity":{},"unitCost":{},"unitPrice":{},
   "isTaxable":{},"costCode":{"id":{}},"costType":{"id":{}},"unit":{"id":{}},
   "organizationCostItem":{"id":{},"unitCost":{},"unitPrice":{}}}}}}
```
Repeat `descendentCostItems` with `"page":"<nextPage>"` until `nextPage` is null (~95 items). Rebuild the tree:
groups by `parentCostGroup.id`, items by `costGroup.id`, siblings sorted by `position`. Price per item = the
template's `unitCost`/`unitPrice`, or the `organizationCostItem`'s when the template's are null.

Template layout (as of 2026-09-29 — trust the live fetch if it differs):
```
*New Commercial Job
  ├─ Commercial Margin Target   [note: GPM floor 30% / target 35% — don't copy; used in Step 6]
  ├─ Permit
  ├─ Demo Existing Plumbing     [Labor - CD, Mobilization, PM-Commercial, Travel Charge]
  │    └─ Excavation            (empty)
  ├─ Underground Plumbing       [Labor - CU, Mobilization, PM-Commercial, Travel Charge]
  │    └─ Plumbing Materials    [4"/3"/2" PVC Pipe, *PVC Fittings, PVC cement, primer, Buffer]
  ├─ Rough-in Plumbing
  │    ├─ Plumbing Labor & Materials [Labor - CR, Mobilization, PM-Commercial, Travel Charge, Core Boring, Buffer]
  │    │    ├─ PVC Materials    [3"/2"/1-1/2" PVC, fittings, cement, primer, J-hooks, strut, cushion clamp, beam clamp, threaded rod, 3"/2" swivel hangers]
  │    │    ├─ Copper Materials [2"–1/2" copper tube, *Copper Fittings, *ProPress Fittings*, solder, flux, strut, cushion clamp, beam clamp, threaded rod, 2" swivel hanger, 3/4" bell hanger]
  │    │    └─ PEX Materials    [1" blue/white, 3/4" + 1/2" blue/red PEX, *PEX Fittings & Crimp Rings]
  │    └─ tag placeholders: CO-1, CO-2, FD-1…FD-3, FCO-1, FCO-2, WCO-1, WCO-2
  ├─ Finish Plumbing
  │    ├─ Plumbing Labor & Materials [Labor - CF, Mobilization, PM-Commercial, Travel Charge, Buffer, Warranty Accrual]
  │    ├─ tag placeholders: WC-1, WC-2, U-1, U-2, LAV-1, LAV-2, S-1…S-4, EWC-1, EWC-2, SH-1, SH-2, HB-1…HB-3, MS-1, RCP-1, RPZ
  │    └─ WH-1 (group: "Water Heater & Expansion Tank") [WH-1, EXP-1]
  └─ Pipe Insulation            (empty)
```
Template quantities for tags and materials are placeholders (qty 1/10/20) — every quantity is set from the
plans, takeoff and Step 3, and zero-quantity lines are omitted from the job budget.

## Step 5: Build the budget
Create **Permit** as a top-level item: `createCostItem{jobId, name:"Permit", …template fields}`. Then build each
phase as ONE nested `lineItems` tree in a single `createCostGroup` call, in template order:
Demo Existing Plumbing (only if there is demo) → Underground Plumbing → Rough-in Plumbing → Finish Plumbing →
Pipe Insulation (only if insulation is in scope). This appends to the job and never touches other budget lines.
(Never use `updateJob.lineItems` — it can replace the whole budget.) Leave the template's Buffer lines out
of the trees; Buffers are added afterward.

For every copied item send: `_type:"costItem"`, `name`, `description`, `quantity` (adjusted), `unitCost`,
`unitPrice`, `isTaxable`, `costCodeId`, `costTypeId`, `unitId` (all from the template, prices resolved per
Step 4), and `organizationCostItemId` = the template item's `organizationCostItem.id` (keeps catalog linkage).
Groups: `{"_type":"costGroup","name":..,"description":..,"lineItems":[...]}`.
```json
{"$":{"notify":false},"createCostGroup":{"$":{"jobId":"<jobId>","name":"Underground Plumbing","lineItems":[
   {"_type":"costItem","name":"Labor - CU","quantity":35,"unitCost":96.42,"unitPrice":147,"isTaxable":false,
    "costCodeId":"..","costTypeId":"..","unitId":"..","organizationCostItemId":".."},
   {"_type":"costItem","name":"Mobilization","quantity":5, "...":"template values"},
   {"_type":"costGroup","name":"Plumbing Materials","lineItems":[ "..." ]}]}]},
 "createdCostGroup":{"id":{}}}}
```
After the first call, read the job budget back to confirm nesting worked before sending the rest. If
`createCostGroup` rejects nested `lineItems`, fall back to `createCostGroup{jobId|parentCostGroupId,name}` +
`createCostItem{costGroupId,...}` per item.

### Labor lines
- **Labor - CD / CU / CR / CF** = Step 3 Labor qty for Demo / Underground / Rough-In / Finish.
- **Mobilization** in each phase = Step 3 Mobilization qty.
- **PM-Commercial** = Vance's PM hours per phase (default: template qty 1 each).
- **No Travel Charge** — Mobilization replaces it (the estimator's travel/per-diem is $0). Keep it only if
  Vance asks for travel/per diem, at the quantity he gives.

### Tagged fixtures and equipment (from the plan's fixture schedule)
- **Tag in the template** (WC-1, LAV-1, FD-1, WH-1…): copy that line (keeps catalog link, cost code, cost
  type, taxable flag); `quantity` = plan count; `description` = the plan's make/model and notes.
- **Tag not in the template** (WC-3, S-5, FS-1, DF-1, SS-1, LB-1…): look for a catalog item with that exact name
  (query below); if none, create the line with the tag as its name and copy cost code / cost type / unit /
  taxable from the closest template tag (fixtures: 3000 Fixtures / Fixtures / Each). Put rough-in tags (CO,
  FCO, WCO, FD, FS) directly in "Rough-in Plumbing"; everything else directly in "Finish Plumbing"; water
  heaters and their parts in the WH-1 group (one group per heater tag: WH-1, WH-2…).
- **Template tags not on the plans** → omit. If the plans' letters mean something else (e.g. "WH-1" = wall
  hydrant), map by description, not by tag.
- **Price** = supplier quote (the quote exception above). No quote → `unitCost` 0 / `unitPrice` 0 and list
  it under "Needs pricing". Never use a tag's catalog price — the tag items are placeholders (catalog FD-1
  carries a $1,876.39 price with $0 cost).
- Carriers, air gaps, vent kits, strainers, arrestors and other accessories on the quote → their own lines
  (catalog item if one exists, else Materials (Commodity)) beside the tag they serve.
- Alternates/options the plans or Vance call out → a sub-group named for the tag holding the specified item
  plus the alternate (e.g. "WC-1 (ALT - Porcelain)") with a description explaining the options.

### Materials from the takeoff (Step 3 output)
Catalog lookup for any item not in the template:
```json
{"organization":{"$":{"id":"22Nttsgz8iVp"},"costItems":{"$":{"size":20,"where":{"and":[[["job","id"],"=",null],[["costGroup","id"],"=",null],["name","like","%<text>%"]]}},
  "nodes":{"id":{},"name":{},"description":{},"unitCost":{},"unitPrice":{},"isTaxable":{},"costCode":{"id":{}},"costType":{"id":{}},"unit":{"id":{}}}}}}
```
- **Pipe** (quantity in feet, rounded up): underground LF → Underground > Plumbing Materials; the rest of the
  final LF → the system's Rough-In group (PVC Materials for DWV; Copper Materials or PEX Materials for water).
  Sizes the template group lacks → catalog item by name (e.g. `6" PVC Pipe`); none → the generic `*PVC Pipe` /
  `*Copper Tube` / `*PEX Tube` item, flagged. PEX: cold → Blue, hot/recirc → Red (1" hot → White).
  Catalog copper tube is Type M hard — if the spec calls for Type L/K, flag it (don't substitute prices).
  Compressed air (black iron) has no catalog items — ask Vance. Keep only the water group that's used.
- **Hangers** (single clevis): each system's hanger points by size → `<size> Swivel Hanger, Galvanized` (2", 3",
  4" in catalog) in that system's group; copper ≤ 3/4" → `Bell Hanger, 1/2"` / `3/4"`; a size with no catalog
  hanger → nearest larger one, flagged. `3/8" Threaded Rod` (`22P2cBkKRVH5`, priced per foot) qty = that
  group's points × rod-per-point LF; `Beam Clamp` qty = points (steel structure — ask if wood or concrete deck).
  Trapeze: rod and beam clamps from the script's totals; `Green Strut Channel` ft = trapezes × strut length
  (ask Vance — the sheet doesn't give it); cushion clamps = hanger points.
- **Items the estimator doesn't count** — fittings, cement/primer, solder/flux, crimp rings, ProPress, J-hooks,
  roof flashing, AAVs, hammer arrestors: use Vance's takeoff counts; if he has none, keep the template quantity
  and list them under "Placeholder quantities".
- **CMU drops** are labor only. **Sleeves**: no catalog item — ask Vance for the sleeve price (the estimator's
  unit cost is a reference he can approve).

### Subcontractors, permit, insulation
- **Sub quotes** (quote exception, Subcontractor cost type): Excavation → catalog `Excavation` (`22PQMSn82PN9`)
  in the Excavation group (under Demo, or under Underground Plumbing when there's no demo); fire stop, lift
  rental, etc. → catalog item if one exists, else ask. No quote → $0 + "Needs pricing".
- **Core Boring** (Rough-In, catalog price) qty = number of cores; omit if none. **Concrete cutting**
  (renovations) → catalog `Concrete Cutting & Filling` (`22P6f6pCekbg`, per ft) in Underground Plumbing, qty =
  trench LF.
- **Permit**: AHJ fee → `unitCost` = `unitPrice` = fee (Permit margin 0). No fee yet → catalog $325, flagged
  (the estimator's SETTINGS sheet has a valuation-based fee table Vance can use).
- **Pipe Insulation** group: by a sub → `Fiberglass Pipe Insulation` (`22PCssFHKRSQ`) qty 1, `unitId` Lump Sum
  (`22Nttshd4XRq`), `unitCost` = quote. By Barrett → catalog foam insulation per pipe size, LF from the
  takeoff for the lines the spec requires (ask). Not in scope → omit the group.

### Buffer (one per phase, after items are in)
Pad each phase by the estimator's contingency for the plan confidence (script output; 2026-09-29: High 5% —
default, complete coordinated drawings · Mid 12% · Low 20%), rounded so the phase total is whole dollars:
target = ROUNDUP(phase price sum × (1 + pct)) to the nearest dollar; Buffer = target − phase sum.
Place it where the template does — Underground > Plumbing Materials, Rough-in > Plumbing Labor & Materials,
Finish > Plumbing Labor & Materials; Demo → the Demo Existing Plumbing group; Pipe Insulation → none.
Create with `createCostItem{costGroupId:<that group id>, name:"Buffer", quantity:1, unitCost:0,
unitPrice:<buffer>, isTaxable:false, organizationCostItemId:"22PHmgptrrEK", costCodeId:"22Nttshd4XSU"
(9999 Miscellaneous), costTypeId:"22Nttshd4XSY" (Other), unitId:"22Nttshd4XRq" (Lump Sum)}`.
**Always 9999 Miscellaneous / Other** — the template's Buffer lines are coded 2000 Materials; override them.

### Warranty Accrual (last)
The template includes "Warranty Accrual" (1300 Other / Lump Sum) in Finish > Plumbing Labor & Materials — copy it
with price 0. After everything else (incl. buffers), set it with `updateCostItem{id, unitCost:0, unitPrice:<amount>}`:
amount = a round number (e.g. $500, $1,000, $2,500) between 0.5% and 1% of the whole-job price total.

## Step 6: Verify and report
```json
{"job":{"$":{"id":"<jobId>"},
 "groups":{"_":"costGroups","$":{"size":100,"where":[["document","id"],"=",null]},"nodes":{"id":{},"name":{},"parentCostGroup":{"id":{}}}},
 "items":{"_":"costItems","$":{"size":100,"where":[["document","id"],"=",null]},"count":{},"p":{"_":"sum","$":"price"},"c":{"_":"sum","$":"cost"},
   "nodes":{"name":{},"quantity":{},"price":{},"costGroup":{"id":{}}}}}}
```
(page with `nextPage` if count > 100). Report:
- Total cost / total price / **GPM %** vs the template's Commercial Margin Target (floor 30%, target 35% — re-read
  its description from the Step 4 fetch). Below the floor → say so plainly and show what's driving it.
- Per-phase totals (Permit, Demo, Underground, Rough-In, Finish, Pipe Insulation); line item count.
- Fixture schedule recap: each tag, qty, make/model, quoted unit cost, price.
- **Needs pricing:** tags/subs at $0, permit at the catalog default, sleeves, black iron, anything flagged.
- **Placeholder quantities:** material lines left at template quantities.
- **Rationale:** estimator inputs, SUMMARY hours, phase split (phase-detail lines), mobilization math, every ⚠
  warning, buffer % and math per phase, warranty accrual math, assumptions (defaults used).

Offer adjustments ("+20 rough-in hours", "WC-1 quote came in at $412", "move sleeves to underground") via
`updateCostItem{id, quantity}` — or unitCost/unitPrice for quoted lines — then recompute buffers.

## Notes
- The Claude connector cannot delete. To "remove" a line, `updateCostItem{id, quantity:0}` and tell the user;
  to remove a whole wrong group, ask the user to delete it in JobTread (a budget backup is auto-saved on changes).
- `isTaxable`: copy from template (permits, labor, mobilization and PM are non-taxable).
- Always pass `organizationCostItemId` for catalog items so budget lines stay linked to the catalog.
- Retainage and AIA billing are job settings (create-job), not budget lines.
- Labor estimator: `BP_Commercial_Estimator_v3.1.xlsx` + `scripts/labor_estimate.py` (verified against the
  LibreOffice-recalculated workbook on the sample job and 30 randomized jobs, plus 50 on the original v3,
  2026-09-29). Needs `openpyxl`.
