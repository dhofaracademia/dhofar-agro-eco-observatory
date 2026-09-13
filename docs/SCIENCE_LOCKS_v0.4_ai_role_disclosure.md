# Science locks — AI-role disclosure (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner (pipeline role):** Agrofostery Scientist  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-13 (Asia/Muscat)  
**Status:** Binding honesty lock (does **not** change ecology)  
**Verdict: Go**  
**Companions:** every `docs/SCIENCE_LOCKS_*.md`  
**Machine twin:** `docs/phase_ai_role_disclosure_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B). Ecological locks, n_clear honesty, species lists, satellite-first, and Phase 4–6 remain as written.

Evaluator note (accepted): multi-agent role names are fine **as engineering**. A public “Sign-off: Agrofostery Scientist” **without** disclosure misleads researchers and government readers.

---

## 1. What this does / does not do

| Does | Does not |
|------|----------|
| Disclose that named roles are an AI pipeline | Weaken or reopen any ecological lock |
| Relabel Sign-off so it is not read as a certified human | Claim هيئة البيئة / ministry / licensed expert |
| Keep role names for engineering routing | Make field visits a prerequisite |
| Keep human review **pending** until a named human stamps | Lift mountain 3.B seeding-rec Hold |

---

## 2. Required banner (EN + AR) — top of every `SCIENCE_LOCKS_*.md`

Paste the block below **immediately after the title / metadata header**, before the first scientific section. Bilingual, both languages required. Do not EN-only.

```markdown
> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.
```

Required on **all** of:

- `SCIENCE_LOCKS_v0.4_phase1_2.md`
- `SCIENCE_LOCKS_v0.4_phase4_species.md`
- `SCIENCE_LOCKS_v0.4_phase5_field_loop.md`
- `SCIENCE_LOCKS_v0.4_phase6_learning.md`
- `SCIENCE_LOCKS_v0.4_satellite_first.md`
- `SCIENCE_LOCKS_v0.4_evaluator_endorsement.md`
- **this file**
- any **future** `SCIENCE_LOCKS_*.md`

Scaffold JSON twins may add `"ai_pipeline_role": true` and `"human_review": "pending"`. Not a substitute for the markdown banner.

---

## 3. Sign-off relabel (binding)

**Forbidden as a standalone closer:** `## Sign-off` followed by `**Agrofostery Scientist — DATE**` with no disclosure.

**Required closer:**

```markdown
## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — DATE (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.
```

Keep the verdict line under that heading (Go / Go-with-fixes / Hold).  
`Owner:` in the header may stay as a **pipeline role label** only if the §2 banner is present.

Internal engineering phrases (“Agrofostery SHA”, “science Approve”, “Questions → Agrofostery Scientist”) may remain as **routing**. They do not become a public certified-expert claim. If they appear in partner UI without the provisional / disclosure chrome, add one short disclosure line there too. This lock’s **must-fix** is the SCIENCE_LOCKS files.

---

## 4. Forbidden

| Item | Status |
|------|--------|
| “Sign-off: Agrofostery Scientist” without disclosure | **Forbidden** |
| Implying licensed / independent human expert / «معتمد من الهيئة» | **Forbidden** |
| Softening n_clear, species, MPI, satellite-first, or mountain Hold “because AI” | **Forbidden** |
| Dropping the AR half of the banner | **Forbidden** |
| Claiming human review is complete | **Forbidden** until a named human writes it |

---

## 5. Mountain

**Unchanged.** 3.B seeding-rec Hold until post-khareef MPI (`2026-09-15`–`2026-10-31`) + pipeline Approve on that run. Disclosure does not unlock seeding.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-13 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go.** Apply the banner + relabel to every `SCIENCE_LOCKS_*.md`. Ecological locks stand.
