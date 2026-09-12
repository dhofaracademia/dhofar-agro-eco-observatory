# Science locks — Phase 4 Site × Species scaffold

**Owner:** Agrofostery Scientist  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-12 (Asia/Muscat)  
**Status:** Binding for Phase-4 **scaffold only**  
**Product:** مرصد ظفار الزراعي البيئي | Dhofar Agro & Eco Observatory  
**Companions:** `docs/SCIENCE_LOCKS_v0.4_phase1_2.md`, Product Spec 1.0.1 §12

Machine-readable twin: `docs/phase4_species_scaffold.json`

---

## Honesty (read first)

1. These are **Scientist-locked short lists** for the scaffold. They implement Spec 1.0.1 (“Terminalia + 1–2 local species” for fog; سدر / سمر / غاف for Najd).
2. **Official هيئة البيئة Oman sign-off has not been received.** Field `vetting_status` = `scientist_locked_pending_ea`. Do not print “Authority-approved” or “معتمد من الهيئة” in UI.
3. **Scores stay unvalidated.** Any Site×Species number is `unvalidated` / `provisional`. Forbidden as operational truth.
4. **No campaign numbers** (hectares, seed kg, crew days).
5. **Domains never mix.** A fog-escarpment site may only see fog species. A Najd-arid site may only see Najd species. No shared picker. No “best tree for this pixel” across domains.
6. **Mountain UI remains Hold** until science re-sign-off. Scaffold may exist as offline artifacts / hidden schema — not a partner-facing mountain recommendation map.
7. *Terminalia dhofarica* is **not** the answer for every mountain cell. The three fog species occupy different niches.
8. Expert Rules first. No ML species model.

---

## Domain enum (exactly two)

| `domain` | Arabic | Where | Never |
|----------|--------|-------|-------|
| `fog_escarpment` | منحدر الضباب / غابة الخريف | Jabal Qara, Samhan, Qamar seaward escarpment and monsoon woodland | Najd farms, dry leeward plateau, frankincense wadis |
| `najd_arid` | نجد الجاف | Najd desert farms and arid belt north of the fog crest | Fog woodland, Khareef escarpment |

**Third domain not in this scaffold:** dry leeward / frankincense belt (*Boswellia sacra*). Do not add it to either list.

---

## 1. Fog-escarpment short list (n = 3)

Community basis: Terminalia cloud forest of the South Arabian fog woodlands (Kürschner et al. 2004; Ball & Ball 2020 *Phytocoenologia*; Miller & Morris 1988; Hildebrandt / Friesen fog-intercept work).

### FOG-01 — *Terminalia dhofarica*

| Field | Value |
|-------|--------|
| `species_id` | `sp-fog-tdhof` |
| accepted name | *Terminalia dhofarica* (A.J.Scott) Gere & Boatwr. (2017) |
| synonym | *Anogeissus dhofarica* A.J.Scott (1979) — historical only |
| ar_name | ميست |
| ar_name_alt | الظفارية |
| en_name | Dhofar Terminalia |
| family | Combretaceae |
| domain | `fog_escarpment` |
| role | Canopy keystone; primary fog interceptor |
| habitat | Mid-elevation monsoon woodland on seaward escarpment |
| elevation_m | 200–1200 (core often ~400–900) |
| moisture_preference | High monsoon / fog; fails beyond fog crest |
| fog_dependence | `obligate` |
| drought_tolerance | Low–moderate once leafless; not a Najd tree |
| grazing_sensitivity | High (camel browse) |
| establishment_difficulty | High |
| germination_notes | Fruit-heads persist; **seed fill often <30%**. Do not invent seed-kg rates. Test lots. |
| timing_window | `late_khareef` / `early_post_khareef` |
| iucn | Vulnerable |
| sources | Gere & Boatwright 2017; Miller & Morris 1988; Oberprieler et al. 2009; Spec 1.0.1 |

### FOG-02 — *Olea europaea* subsp. *cuspidata*

| Field | Value |
|-------|--------|
| `species_id` | `sp-fog-oleac` |
| accepted name | *Olea europaea* L. subsp. *cuspidata* (Wall. ex G.Don) Cif. |
| synonym | *Olea africana*, *Olea chrysophylla*, *Olea cuspidata* |
| ar_name | ميتان |
| ar_name_alt | عتم (northern Oman); موتين / Motin (Jibbali) |
| en_name | Wild olive / brown olive |
| family | Oleaceae |
| domain | `fog_escarpment` |
| role | Evergreen associate; higher / rockier fog forest |
| habitat | *Cadia purpurea–Olea europaea* variant of Terminalia forest; escarpment |
| elevation_m | Prefer mid–upper escarpment (often above Terminalia core) |
| moisture_preference | Fog-rich; not Najd irrigation |
| fog_dependence | `high` |
| drought_tolerance | Moderate (evergreen) |
| grazing_sensitivity | High on accessible suckers; historically over-harvested for hardwood |
| establishment_difficulty | **Very high** — adults persist, juveniles rare in surveys |
| germination_notes | Fruit ~August in Oman literature. Prefer local wildings / protected regeneration over broadcast seed. |
| timing_window | `late_khareef` / `early_post_khareef` |
| sources | Miller & Morris 1988; Ghazanfar 2015; Ball & Ball 2020; Al-Hinai et al. wild-olive review |

### FOG-03 — *Ficus sycomorus*

| Field | Value |
|-------|--------|
| `species_id` | `sp-fog-fsyco` |
| accepted name | *Ficus sycomorus* L. |
| ar_name | جميز |
| ar_name_alt | تين سيكومور |
| en_name | Sycamore fig |
| family | Moraceae |
| domain | `fog_escarpment` |
| role | Wetter woodland / wadi-bed niche (not the dry plateau isolate) |
| habitat | *Gymnosporia dhofarensis–Ficus sycomorus* woodland variant; wadi and lower woodland |
| elevation_m | Lower–mid woodland / wadi (often ~400–700) |
| moisture_preference | High; accumulation / deep soil |
| fog_dependence | `moderate` (moisture + fog woodland, not a desert fig) |
| drought_tolerance | Low |
| grazing_sensitivity | Moderate–high on seedlings |
| establishment_difficulty | High from seed; **prefer wildings / cuttings** |
| germination_notes | Broadcast seed is a poor default. Flag `establishment_mode=vegetative_preferred`. |
| timing_window | `late_khareef` / `early_post_khareef` |
| sources | Ball & Ball 2020; Kürschner et al. 2004; Miller & Morris 1988 |

**Why these three, not more:** Spec 1.0.1 said start with *T. dhofarica* + one or two confirmed locals. These three split the fog domain (canopy / upper evergreen / wet wadi) so the matrix is not “Terminalia everywhere.”

### Fog watch list (schema only — `scaffold_include: false`)

Do **not** score or show until EA / field add:

- *Dodonaea viscosa* subsp. *angustifolia* (pioneer / disturbance shrubland)
- *Cadia purpurea*
- *Gymnosporia dhofarensis* (syn. *Maytenus dhofarensis*)
- *Jatropha dhofarica*
- *Blepharispermum hirtum*
- *Euclea racemosa*
- *Ficus vasta* (plateau isolates — different zone than escarpment woodland)

---

## 2. Najd arid short list (n = 3)

Already named in Spec 1.0.1 §12 and Science Locks v0.4 global honesty §6. Confirmed.

### NAJD-01 — *Ziziphus spina-christi*

| Field | Value |
|-------|--------|
| `species_id` | `sp-najd-zsc` |
| accepted name | *Ziziphus spina-christi* (L.) Desf. |
| ar_name | سدر |
| en_name | Christ's thorn jujube |
| family | Rhamnaceae |
| domain | `najd_arid` |
| role | Farm-adjacent / wadi-edge / silvopasture tree |
| habitat | Arid belt, irrigated farms, drainage lines |
| moisture_preference | Low–moderate; irrigation or winter rain |
| fog_dependence | `none` |
| drought_tolerance | High |
| grazing_sensitivity | Moderate (browse, but established trees persist) |
| establishment_difficulty | Moderate |
| timing_window | `winter_spring_rain` or `irrigated` — **not** Khareef-escarpment timing |
| sources | Spec 1.0.1; Ghazanfar; Miller & Morris |

### NAJD-02 — *Vachellia tortilis*

| Field | Value |
|-------|--------|
| `species_id` | `sp-najd-vtor` |
| accepted name | *Vachellia tortilis* (Forssk.) Galasso & Banfi |
| synonym | *Acacia tortilis* (Forssk.) Hayne |
| ar_name | سمر |
| en_name | Umbrella thorn |
| family | Fabaceae |
| domain | `najd_arid` |
| role | Open arid woodland / farm windbreak |
| habitat | Najd and arid Dhofar; never auto-assigned to fog woodland |
| moisture_preference | Low |
| fog_dependence | `none` |
| drought_tolerance | Very high |
| grazing_sensitivity | High on seedlings; adults browse-tolerant |
| establishment_difficulty | Moderate |
| timing_window | `winter_spring_rain` or `irrigated` |
| ui_note | Never label as generic “Acacia”. Always *Vachellia tortilis* (syn. *Acacia tortilis*). |
| sources | Spec 1.0.1 §12 naming lock |

### NAJD-03 — *Prosopis cineraria*

| Field | Value |
|-------|--------|
| `species_id` | `sp-najd-pcin` |
| accepted name | *Prosopis cineraria* (L.) Druce |
| ar_name | غاف |
| en_name | Ghaf |
| family | Fabaceae |
| domain | `najd_arid` |
| role | Deep-rooted arid native; farm and rangeland |
| habitat | Najd / arid Oman |
| moisture_preference | Very low (phreatophyte) |
| fog_dependence | `none` |
| drought_tolerance | Very high |
| grazing_sensitivity | Moderate |
| establishment_difficulty | Moderate |
| timing_window | `winter_spring_rain` or `irrigated` |
| **hard forbid** | *Prosopis juliflora* (الغاف الأمريكي / الميزكيت) is **invasive** and **never** in this product. `pcin` ≠ juliflora. |
| sources | Spec 1.0.1 |

### Najd watch list (`scaffold_include: false`)

*Senegalia senegal*, *Vachellia etbaica*, *Boscia* / *Maerua*, *Ficus salicifolia* — appear in Nejd desert literature; not MVP.

---

## 3. Timing rules

### Fog-escarpment

| Rule | Lock |
|------|------|
| Default window | `late_khareef` → `early_post_khareef` |
| Not allowed | “ازرع في الخريف” as a blanket date |
| Required inputs (later, not scaffold scores) | Khareef stage, MPI class, moisture-confidence — when mountain path is unblocked |
| If MPI class is `insufficient` or T0 is fallback | Timing stays `deferred`; no species card as a go-ahead |
| Terminalia | Sow / plant only while moisture persists; leafless dry-season planting is a fail |
| Olea | Same seasonal window; prefer protection of existing adults + rare juveniles over mass seeding |
| Ficus | Same window; vegetative preferred |

Khareef calendar is **dynamic** (Spec). Do not hard-code 21 June / 21 September as biological truth.

### Najd arid

| Rule | Lock |
|------|------|
| Default window | `winter_spring_rain` **or** `irrigated` (AOU / farm context) |
| Never | Assign Najd species a Khareef-escarpment seeding window |
| Never | Drive Najd farm species cards from mountain MPI |

---

## 4. Provenance rules

| ID | Rule |
|----|------|
| P1 | **Local Dhofar provenance only.** No imported forestry mix. No UAE/India/Pakistan “ghaf” or “sidr” lots without review. |
| P2 | **Same domain.** Fog seed stays on fog-escarpment. Najd seed stays in Najd. Cross-domain transfer forbidden. |
| P3 | **Same jabal preferred** for fog (Qara→Qara, Qamar→Qamar, Samhan→Samhan). Cross-jabal = `provenance_class=regional_dhofar` and must be flagged. |
| P4 | Record: `collector`, `gps`, `elevation_m`, `date`, `mother_tree_note`, `seed_lot_id` when a real lot exists. |
| P5 | `provenance_unknown` → do not treat lot as validated; scaffold may store the flag only. |
| P6 | Terminalia lots need a **seed-fill / viability note** (literature: often <30% filled). Missing note → no kg advice, ever. |
| P7 | Unknown or commercial exotic lot → `blocked_for_recommendation`. |

`provenance_class` enum: `local_same_jabal` · `regional_dhofar` · `oman_other` · `unknown` · `blocked_exotic`

Only `local_same_jabal` and (flagged) `regional_dhofar` are even *discussable* later. Scaffold stores the enum; it does not auto-approve.

---

## 5. Scaffold schema (what Programmer may build)

Per species row: fields above + `scaffold_include: true` + `vetting_status: scientist_locked_pending_ea` + `score_status: unvalidated`.

Per Site×Species cell (when a site exists):

- `site_id`, `species_id`, `domain` (must match)
- `suitability_stub` — allowed as **null** or a clearly labelled unvalidated stub
- `confidence` — **separate**, never merged
- `timing_window`
- `provenance_class` (default `unknown` until a lot is logged)
- `establishment_mode` (`seed` / `vegetative_preferred` / `protect_regeneration`)
- **No** hectares, **no** seed kg, **no** crew days, **no** “plant this week” push

UI copy if a cell is ever shown internally:

- EN: “Unvalidated expert stub — not an Environment Authority approval, not a field-tested score.”
- AR: «مسودة خبير غير مُحققة — ليست اعتماداً من هيئة البيئة وليست درجة ميدانية.»

---

## 6. Forbidden (Phase 4)

- Mixing fog and Najd species on one site or in one picker
- Adding *Boswellia sacra* to either short list
- Adding *Prosopis juliflora* anywhere
- Using “Acacia / Senegalia” as a single species row
- Printing *Anogeissus dhofarica* as the accepted name (synonym only)
- Claiming هيئة البيئة vetting
- Publishing suitability scores as truth
- Campaign planner numbers
- Wiring this scaffold into partner mountain UI (Hold remains)
- Treating *Ficus vasta* plateau trees as escarpment woodland (watch list only)
- Auto-picking Terminalia for every mountain cell

---

## Sign-off

**Agrofostery Scientist — 2026-09-12 (Asia/Muscat)**  
Phase-4 short lists + timing + provenance **locked for scaffold**.  
EA / field expansion = new science lock, not a silent JSON edit.
