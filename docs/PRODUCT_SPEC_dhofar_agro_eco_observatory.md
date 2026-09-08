# مواصفات المنتج — ظفار رصد | Dhofar Agro & Eco Observatory

| الحقل | القيمة |
|-------|--------|
| **الإصدار** | **1.0.1** (مراجعة علمية Agroforestry بعد 1.0؛ يحل محل المسودة 0.3 مفهومياً) |
| **التاريخ** | 8 سبتمبر 2026 (توقيت مسقط / Asia/Muscat) |
| **الاسم الأساسي** | **ظفار رصد \| Dhofar Agro & Eco Observatory** |
| **اسم سابق / Alias** | ظفار رصد / Dhofar Agro Monitor (يُحتفظ به كاسم قصير وواجهة تسويقية) |
| **الأساس التقني** | امتداد `najd-planting-monitor` (لا تفريع) + خط أنابيب `/workspace/najd-satellite/pipeline/run_monitor.py` |
| **ملكية علمية** | قواعد الأنواع–الموقع تبقى لمراجعة عالم الحراجة الزراعية / هيئة البيئة |

### ملاحظة ترحيل من المسودة 0.3

المسودة 0.3 ركّزت على «مزارع نجد + بذر الجبال» تحت اسم *Dhofar Agro Monitor*، مع اعتماد خلايا شبكية حتى تصل حدود المزارع. الإصدار **1.0** يعيد صياغة المنتج كـ **مرصد زراعي–بيئي متكامل** وفق مبدأ *Open Data First → Government Data Later*، ويقدّم **وحدة الرصد الزراعية (AOU)** لتعمل المنصة منذ اليوم الأول دون أسماء/حدود رسمية، ويوسّع مسار الاستعادة إلى *Restoration Intelligence* (مراحل خريف ديناميكية، MPI، سلم تجدد طبيعي vs زراعة نشطة، محرك أنواع Site×Species، حلقة تعلّم ميداني). القسم التقني يبقى متوافقاً مع المكدس المعتمد في 0.3 مع إضافة xarray وCOGs ومعالجة مجدولة. **1.0.1** يدمج ملاحظات المراجعة العلمية غير الحاجبة.

---

## 1. Executive Summary (EN)

**ظفار رصد | Dhofar Agro & Eco Observatory** is a bilingual (Arabic RTL / English LTR) decision-support platform for Dhofar Governorate, Oman. It is **not** a satellite slideshow: it turns open Earth-observation and field data into interpretable indicators, recommendations, actions, and learning.

Two observatories share maps, imagery, alerts, seasonal calendar, and infrastructure, with **clearly separated scientific rules**:

1. **Agricultural Observatory** — detect and monitor irrigated/cultivated activity across the Najd desert plain (Thumrait, Hanfit, Ash Shisr, Saih Al-Khairat, Dawkah, Al-Mazyunah and surrounds) using **Agricultural Observation Units (AOUs)** derived from Sentinel-2/1 and Landsat time series. Day-one operation does **not** require official farm names or cadastral boundaries.
2. **Restoration & Reforestation Observatory** — support vegetation recovery on Jabal Qara, Jabal Samhan, Jabal Qamar and coastal foothills (Mirbat, Mughsayl) through dynamic Khareef staging, Moisture Persistence Index, hydrological suitability (beyond slope), site suitability with a **separate** confidence score, a **Site × Species** engine (MVP-capable), seeding operations, and a field learning loop.

**Scientific honesty (non-negotiable):** no confirmed pest/disease diagnosis from space; SMAP/ESA CCI are regional context only; spectral moisture proxies ≠ field soil moisture; species rules need local calibration; accepted name *Terminalia dhofarica* (syn. *Anogeissus dhofarica*). Start with **interpretable Expert Rules**; ML only after sufficient ground truth.

**Product experience:** one map, two modes (Agricultural / Restoration), «Why This Site?» cards, bilingual alerts (in-app → push/SMS in v2). **Stack:** Vite 6 · React 19 · TypeScript · Tailwind 4 · i18next · Leaflet (+ MapLibre option); Planetary Computer STAC · pystac-client · rasterio · numpy · geopandas · xarray in `mapvenv`; MVP file/GeoJSON storage; v2 PostGIS + FastAPI + SMS. Extend `najd-planting-monitor`; do not fork.

---

## 2. الهوية والاسم والفلسفة

| | |
|--|--|
| **الاسم الأساسي** | ظفار رصد \| Dhofar Agro & Eco Observatory |
| **Alias** | ظفار رصد / Dhofar Agro Monitor |
| **الفلسفة** | **Open Data First → Government Data Later** |
| **التعريف** | منصة ذكاء زراعي وبيئي خاصة بظفار: Remote Sensing + زراعة + هيدرولوجيا + مناخ + حراجة زراعية + علم الاستعادة + بيانات ميدانية + دعم قرار + تعلّم مستمر |

المنصة **لا تنتظر** بيانات حكومية لتعمل. في النسخة الأولى لا تُسمّى المنطقة المكتشفة «مزرعة رسمية»، بل **وحدة رصد زراعية (AOU)**. عند توفر بيانات وزارة الثروة الزراعية والسمكية وموارد المياه (أو الجهات المختصة) لاحقاً:

`AOU → Official Farm → Official Parcel`

مع **الحفاظ على التاريخ** المجموع قبل الربط الرسمي.

**مبدأ القرار العلمي:** Expert Rules + Empirical Calibration أولاً (قابل للتفسير والتدقيق)، ثم Random Forest / Gradient Boosting / XGBoost أو نماذج مكانية–زمنية بعد كفاية البيانات الميدانية.

---

## 3. الهدف والمنظومتين

| | Agricultural Observatory — مرصد الزراعة | Restoration & Reforestation Observatory — مرصد الاستعادة |
|--|------------------------------------------|--------------------------------------------------------|
| **الغرض** | اكتشاف البصمة الزراعية، مراقبة الصحة والإجهاد، تنبيهات مبكرة | ذكاء استعادة: خريف ديناميكي، رطوبة مستمرة، ملاءمة مواقع/أنواع، بذر، قياس نجاح، تعلّم |
| **الجغرافيا** | سهل/نجد ظفار (مزارع مروية) | جبل القرا، سمحان، القمر؛ مرباط، المغسيل والسفوح ذات الصلة |
| **يشترك** | الخرائط، الأقمار، التحليل الزمني، التنبيهات، التقويم الموسمي، البنية، التحليلات المكانية | نفس المشتركة |
| **يفترق** | قواعد الإجهاد الزراعي وAOU | قواعد الاستعادة والتجدد والأنواع |

سلسلة القيمة للمنتج:

`Satellite Data → QA → Indicators → Ecological/Agricultural Model → Suitability → Confidence → Recommendation → Field Action → Validation → Learning`

---

## 4. وحدة الرصد الزراعية — AOU

**Agricultural Observation Unit** وحدة مكانية مكتشفة من الصور والسلاسل الزمنية: مساحة زراعية، كتلة حقول، مجموعة متجاورة، مساحة مزروعة محتملة، أو منطقة نباتية بخصائص زراعية.

| الحقل | الوصف |
|-------|--------|
| المعرّف | مثال: `AOU-NJ-000184` |
| الإحداثيات + الشكل | مضلع مشتق من الأقمار |
| المساحة التقديرية | هكتار تقديري |
| Agricultural Probability | درجة احتمالية زراعية |
| الغطاء المحتمل | تصنيف أولي |
| NDVI / NDRE / NDMI | مؤشرات نباتية/مائية |
| السجل الزمني | سلاسل ومقارنات |
| مستوى الثقة | منفصل عن الاحتمالية حيث يلزم |
| التنبيهات + التاريخ | سجل تنبيهات ومقارنات تاريخية |

الربط المستقبلي: `AOU → Official Farm → Official Parcel` دون فقد السجل.

---

## 5. اكتشاف البصمة الزراعية + Agricultural Probability Score

المسار:

`Imagery → Agricultural Footprint Detection → Probability Map → Spatial Segmentation → AOUs → Monitoring & Alerts`

**المصادر الأساسية:** Sentinel-2، Sentinel-1، Landsat 8/9. مساعدة: Dynamic World، طبقات Copernicus، DEM، طقس/أمطار متاحة.

**لا يعتمد الاكتشاف على NDVI وحده.** الخصائص تشمل: NDVI، NDMI، NDRE *(عند توفر Red Edge)*، الانعكاس الطيفي، Red Edge، SWIR، التغيّر الزمني، استمرار الغطاء، النمط الموسمي، Texture، Sentinel-1 backscatter عند الحاجة، Dynamic World كطبقة مساعدة وليست مرجعاً وحيداً. في MVP المزارع: NDVI+NDMI+SWIR/زمن كافية؛ NDRE يُضاف دون أن يكون شرطاً للتشغيل.

| Agricultural Probability Score | التفسير |
|--------------------------------|---------|
| 0–30% | غير مرجح زراعياً |
| 30–60% | محتمل |
| 60–80% | مرجح |
| 80–100% | احتمال مرتفع جداً |

---

## 6. المراقبة والتنبيهات الزراعية

### 6.1 ملف ديناميكي لكل AOU (Dynamic Profile)

المساحة، الإحداثيات، الغطاء، التغيّر الزمني، NDVI/NDRE/NDMI، مؤشرات الإجهاد، سجل التنبيهات، مقارنة الأسابيع السابقة ونفس الفترة في السنوات السابقة (مثلاً 2023–2026).

**قيد تنفيذ مسار المزارع (MVP):** المحرك الحالي يجلب B04/B08/B11 (+ SCL). **NDRE اختياري** ويتطلب نطاقات Red Edge من Sentinel-2؛ لا يُحجب مسار المزارع أو التنبيهات الأساسية إذا لم تُجلب نطاقات Red Edge بعد.

**العرض التفسيري:** Vegetation Health · Water Stress · Vegetation Change · Cultivation Persistence · Possible Biotic Stress · Drought Risk.

### 6.2 Vegetated Area ≠ Cultivated Area

لا تُستخدم عبارة «Planted Area» إذا كان الاستنتاج من NDVI وحده. تقدير المساحة الزراعية يعتمد على التحليل الزمني والخصائص الطيفية والسلوكية. مثال عرض:

- Estimated Agricultural Area: 2.8 ha  
- Agricultural Confidence: 87%  
- Change from Previous Season: +12%

(الأرقام أعلاه **أمثلة شكلية للواجهة** وليست مقاييس دقة معلنة للمنتج.)

### 6.3 Crop Stress / Health Model

مداخل: شذوذ NDVI/NDRE/NDMI، خط أساس تاريخي، مرحلة فينولوجية، سياق موسمي، معلومات حرارية اختيارية.

مخرجات تفسيرية: **Vegetation Health Score (0–100)** و **Water Stress Score (0–100)** مع أسباب نصية (مثلاً: NDMI دون المتوسط + انخفاض NDVI + استمرار أسبوعين + عدم تحسن الرطوبة).

### 6.4 أنواع التنبيهات الزراعية

1. Water Stress Alert  
2. Vegetation Decline Alert  
3. Possible Pest/Biotic Stress Alert  
4. Drought Risk Alert  
5. Sudden Cultivation Change  
6. Irrigation/Watering Anomaly  
7. Persistent Vegetation Stress  

**قيد صارم:** لا تشخيص حشرة/مرض مؤكد من القمر وحده. الصيغة: *Possible Biotic Stress* → «يُشتبه بوجود إجهاد نباتي/حيوي. يوصى بالتحقق الميداني.» الاستناد: anomaly طيفي + نمط مكاني/زمني + سياق المحصول + مقارنة المحيطات.

**توافق MVP مع المحرك الحالي:** أكواد التصنيف الأربعة في `run_monitor.py` (`bare` · `healthy` · `water_attention` · `vigor_attention` + `unclear`) تبقى طبقة التنفيذ الأولى؛ الأنواع أعلاه تُوسَّع تدريجياً فوقها دون اختراع مصنّفات غير موثّقة في اليوم الأول.

---

## 7. الجفاف والرطوبة متعددة المصادر

| المصدر | الدور | القيد |
|--------|-------|-------|
| Sentinel-2 | مؤشرات طيفية (NDVI/NDMI/…) | غيوم؛ وكيل نباتي |
| Sentinel-1 | استمرارية تحت الغيوم | تفسير رطوبة التربة محدود |
| SMAP / ESA CCI | سياق إقليمي/هيدرولوجي | **ليس** قياساً دقيقاً لمساحة صغيرة |
| CHIRPS (أو مشابه) | هطول | دقة خشنة |
| ERA5 (أو مناسب) | طقس | سياق إقليمي |

المخرج المركّب: **Regional Drought Context + Local Vegetation Stress + Moisture Anomaly** — لا يُعتبر أي مؤشر منفرد دليلاً كافياً على الجفاف الحقلي.

---

## 8. Restoration Intelligence + مراحل الخريف + MPI

مسار الاستعادة:

`Pre-Khareef → Khareef → Peak → End → Post-Khareef → Moisture Persistence → Vegetation Response → Regeneration Assessment → Site Suitability → Species/Seed → Seeding → Germination → Survival → Learning`

### 8.1 الخريف ديناميكي (ليس تاريخاً ثابتاً)

| المرحلة | الغرض التشغيلي |
|---------|----------------|
| Pre-Khareef | خط أساس جاف/ما قبل الترطيب |
| Khareef Onset | بداية تراكم الرطوبة |
| Peak Khareef | ذروة الرطوبة |
| Khareef Weakening | بدء الانخفاض |
| Khareef End | نهاية الموسم الرطب |
| Post-Khareef | نافذة البذر والاستجابة النباتية |

تحديد المراحل من بيانات الرصد البيئي والمناخي، للإجابة: متى يبدأ الترطيب؟ متى الذروة؟ متى الانخفاض؟ متى نافذة البذر؟

### 8.2 مركّبات زمنية + Moisture Persistence Index (MPI)

مركّبات: Pre-Khareef Baseline · Khareef Composite · Post-Khareef Composite — مع دراسة التغيّر. **لا تعتمد المنصة على صورة واحدة بعد الخريف.**

**Post-Khareef Moisture Persistence Index:** متابعة الموقع عند T0، +1 أسبوع، +2، +4، +6 أسابيع لمعرفة: هل احتفظ الموقع بالرطوبة؟ وليس فقط: هل كان رطباً يوم الالتقاط؟

**تشغيل عملي تحت غيوم الخريف:** مركّبات *Peak Khareef* على القرا/سمحان/قمر غالباً محدودة سحابياً. حتى يتوفر مسار Sentinel-1 موثوق، يُثقَّل **MPI التشغيلي** نوافذ **onset + post-khareef** أكثر من ذروة الخريف البصرية (انظر أيضاً قسم المخاطر).

### 8.3 تقييم الغطاء النباتي

مؤشرات: NDVI، NDMI، NDRE، Vegetation Density، Vegetation Anomaly — مقارنة بالسنوات السابقة، المواقع المجاورة، المتوسط التاريخي، الموسم السابق → حالات: Stable · Improving · Declining · Degraded · Regenerating.

---

## 9. Natural Regeneration vs Active Planting — سلم القرار

لا يُفترض أن الحل دائماً «ازرع أشجاراً جديدة».

| الترتيب | التوصية | متى |
|---------|---------|-----|
| 1 | Protect Natural Regeneration | مؤشرات تجدد طبيعي قوية → حماية وتقليل الضغط |
| 2 | Assisted Natural Regeneration | تجدد جزئي يحتاج دعماً خفيفاً |
| 3 | Enrichment Seeding | غطاء موجود ضعيف/فجوات |
| 4 | Active Planting | حاجة تدخّل نشط بعد تقييم |
| 5 | Avoid / Defer | مخاطر هيدرولوجية/انحدار/سياق غير مناسب |

---

## 10. Hydrological Suitability

DEM لا يقتصر على Elevation / Slope / Aspect. يُضاف: Flow Direction، Flow Accumulation، Relative Position، Wetness Proxy / **TWI**، Drainage، Potential Erosion Risk.

**قاعدة مرفوضة:** «منطقة منخفضة = موقع ممتاز للبذر».

**Hydrological Suitability** يعالج مخاطر: جريان شديد، انجراف، ركود مفرط، انحدار شديد، فقدان تربة، عدم استقرار الموقع. DEM المجاني كافٍ للاستبعاد التقريبي وnichés؛ غير كافٍ لتصميم هندسي تفصيلي.

---

## 11. Site Suitability Engine + Confidence Score

لكل موقع محتمل:

**Ecological Suitability Score (0–100)** من: Moisture Persistence + Vegetation Condition + Natural Regeneration + Elevation + Slope + Aspect + Hydrology + Historical Success + Degradation + Ecological Context.

**Confidence Score** منفصل تماماً (مثال شكلي: Suitability 91 / Confidence 74). لا يُدمج الاثنان في رقم واحد مضلّل.

---

## 12. Seed & Species Suitability Engine (MVP-capable)

وظيفة **أساسية وليست مؤجّلة**. ليست قائمة ثابتة فقط، بل **Site × Species Matrix**.

لكل نوع يُقيَّم: الارتفاع، المناخ المحلي، الرطوبة، الضباب/الخريف، التربة، الصرف، الانحدار، الاتجاه، تحمل الجفاف، الحساسية للرعي، متطلبات الإنبات، ملاءمة الموقع، التوقيت الموسمي، توافر البذور، الأصل/السلالات المحلية عند التوفر، اعتبارات الحفظ.

مخرج: **Species Suitability Score** (مثال شكلي: *Terminalia dhofarica* 88 · *Vachellia tortilis* 74 · مرشح آخر 61). سلة «Acacia / Senegalia» مقبولة كتصنيف عائلي عريض إذا وُضّح أنها ليست نوعاً واحداً.

**الاسم العلمي المقبول:** *Terminalia dhofarica* (syn. *Anogeissus dhofarica*) عند الحاجة للتسميات التاريخية.

**تسمية السمر:** يُفضَّل في الواجهة العربية/الإنجليزية *Vachellia tortilis* (syn. *Acacia tortilis*).

**MVP لمنطقة الضباب/المنحدر:** قائمة قصيرة ومعتمدة من الجهات المختصة — ابدأ بـ *Terminalia dhofarica* + نوع أو نوعين محليين مؤكدين؛ التوسيع فقط بعد مراجعة هيئة البيئة / التحقق الميداني.

**ملكية علمية:** قواعد الأنواع تخضع لمراجعة عالم الحراجة الزراعية والجهات البيئية المختصة (هيئة البيئة). لا تُحوَّل الدرجات إلى حقيقة علمية نهائية دون معايرة محلية. لا خلط تلقائي بين أنواع نجد الجافة (سدر *Ziziphus spina-christi*، سمر *Vachellia tortilis* (syn. *Acacia tortilis*)، غاف *Prosopis cineraria*) وأنواع منحدرات الضباب.

**Recommended Seeding Window** يستند إلى: بداية الترطيب، استقرار الرطوبة، رطوبة ما بعد الهطول، احتمال الاستمرار، مرحلة الخريف، ظروف الموقع، نوع البذور، خصائص الإنبات — وليس مجرد «ازرع في الخريف».

مثال بطاقة توصية: Site `JR-00871` · Enrichment Seeding · Species X · Late Khareef / Early Post-Khareef · Moisture Confidence High · Ecological Suitability 89%.

---

## 13. Seeding Operations + Timelines

### 13.1 تسجيل العملية

الموقع، التاريخ، نوع التدخل، النوع، مصدر البذور، الكمية، طريقة البذر، عدد المشاركين، الجهة المنفذة، GPS، الصور، ملاحظات الفريق — ثم متابعة الموقع.

### 13.2 Germination ≠ Establishment ≠ Survival

| المحطة | المعنى |
|--------|--------|
| Baseline | حالة ما قبل التدخل |
| Germination 30d | إنبات أولي |
| Survival 90d | بقاء قصير |
| Survival 180d | تأسيس متوسط |
| Survival 365d | بقاء سنوي |

مع صور وملاحظات. الهدف: أي المواقع/الأنواع/الطرق/الظروف نجحت؟

---

## 14. Field Learning Loop + Ground Truth

```
Recommendation → Action → Field Result → Validation → Model Update
```

فشل الموقع يُسجَّل مع السبب؛ نجاحه يُفسَّر. بمرور السنوات تتحول المنصة إلى **Locally Calibrated Restoration Intelligence**.

**برنامج التحقق الميداني:** عينات High / Medium / Low Suitability مقابل الواقع. مقاييس مستهدفة (تُحسب بعد بيانات كافية — **بلا أرقام ملفّقة الآن**): Accuracy، Precision، Recall، False Alert Rate، Recommendation Success Rate، Germination Accuracy، Survival Prediction Accuracy.

---

## 15. Ecological Suitability vs Operational Accessibility

| المفهوم | المعنى |
|---------|--------|
| Ecological Suitability | ملاءمة بيئية خالصة |
| Operational Accessibility | سهولة الوصول والتنفيذ الميداني |
| Campaign Priority Score | دمج تشغيلي **دون تشويه** التقييم البيئي الأساسي |

موقع ممتاز بيئياً قد يكون صعب الوصول؛ الأولوية التشغيلية لا تُعاد كتابتها كـ «ملاءمة بيئية».

---

## 16. تجربة المستخدم (UX)

- **خريطة واحدة** · وضعان واضحان: Farms / Agricultural Observation ↔ Mountains / Restoration  
- فتح AOU → **Agricultural Profile** · فتح موقع جبلي → **Restoration Profile**  
- بطاقة **Why This Site?** (Moisture Persistence، Vegetation Recovery، Slope، Hydrology، Natural Regeneration، Historical Success، Action، Species، Confidence) — المنصة ليست Black Box  
- تصميم: Modern · Professional · Scientific · Simple · Bilingual · Map-Centric — يخدم المزارع والفني والمهندس والباحث والمتطوع والجهة الحكومية والمستثمر دون واجهة مختصين فقط  

**طبقات قابلة للتشغيل/الإيقاف:** Agricultural Units · Official Farms (مستقبل) · NDVI · NDMI · NDRE · Water Stress · Drought · Vegetation Change · Khareef · Moisture Persistence · Elevation · Slope · Hydrology · Restoration Sites · Recommended Seeding Sites · Historical Success · Field Validation.

---

## 17. التنبيهات واللغة

| القناة | المرحلة |
|--------|---------|
| In-app Alert | MVP |
| Push Notification | v2 |
| SMS | v2 (تكلفة متغيرة؛ شرائح محدودة أولاً) |

رسائل بسيطة للمستخدم منخفض التقنية، مثال:

- «تنبيه: وحدة زراعية يظهر فيها إجهاد مائي مرتفع خلال الأسبوعين الماضيين. يرجى التحقق من الري.»  
- «موقع جبلي رقم JR-00871 لديه رطوبة متبقية مرتفعة وملاءمة بيئية عالية للبذر.»

**اللغة:** عربية + English · RTL + LTR منذ البداية (i18next كما في التطبيق القائم).

---

## 18. البنية التقنية — MVP → v2

### 18.1 المكدس المعتمد (لا تتعارض معه)

| الطبقة | التقنيات |
|--------|----------|
| Frontend | **Vite 6 · React 19 · TypeScript · Tailwind 4 · i18next (AR RTL) · Leaflet + react-leaflet** · MapLibre مسموح كخيار v1+ |
| Processing | Python في `/workspace/mapvenv`: **Planetary Computer STAC · pystac-client · rasterio · numpy · geopandas** + **xarray** · shapely/pyproj |
| Pipeline | `/workspace/najd-satellite/pipeline/run_monitor.py` — محرك مشترك؛ وحدات جبال جديدة بجانبه |
| App | `/workspace/najd-planting-monitor` — **امتداد لا تفريع** |
| بيانات | Sentinel-2 · Sentinel-1 · Landsat · Copernicus DEM · OSM · SMAP · CHIRPS · ERA5 · Dynamic World عند الحاجة |
| بنية تحتية | PC/STAC · **Cloud Optimized GeoTIFFs** · Object Storage · **Scheduled Processing** |

### 18.2 MVP

- ملفات / GeoJSON تحت `public/data` مع تقسيم `farm/` vs `mountain/` (+ `shared/calendar/`, `imagery_meta/`)  
- CLI/cron أسبوعي للمزارع + موسمي للجبال  
- لا بث COG حي في الواجهة — GeoJSON محسوب + PNG browse  
- نموذج تغذية راجعة يكتب ملفات  

### 18.3 v2

- **PostGIS** + **FastAPI** رقيق (وظائف، اشتراكات، CRUD ميداني)  
- Task Queue · SMS Gateway · Role-based Access · Government Data Integration  
- TiTiler اختياري لـ COG · احتياطي Landsat · دمج SMAP/CCI أوسع  

### 18.4 مبادئ توجيهية

- لوحة خريطة واحدة؛ قواعد تحليل مختلفة لكل وضع  
- إخراج AOI من التضمين الصلب في `run_monitor.py`  
- تثبيت `requirements.txt` (أو تصدير مجمّد من `mapvenv`) للـ cron/CI  

---

## 19. نموذج البيانات والحوكمة

### 19.1 كيانات أساسية

`AgriculturalObservationUnit` · `OfficialFarm` · `RestorationSite` · `SatelliteObservation` · `EnvironmentalObservation` · `Alert` · `Species` · `SeedSource` · `SeedingEvent` · `FieldObservation` · `ValidationResult` · `HistoricalRegeneration` · `KhareefSeason` · `Recommendation`

فصل دائم: **Observation Data** عن **Official / Legal Data**.

### 19.2 طبقات الحوكمة

| الطبقة | المحتوى |
|--------|---------|
| **Public** | مؤشرات مجمّعة، طبقات عامة، توصيات غير شخصية |
| **Protected** | تغذية راجعة ميدانية، حسابات جهات، تفاصيل عمليات |
| **Official** | حدود/أسماء رسمية، بيانات حساسة بعد تصريح |

في النسخة المفتوحة **لا تُعرض:** اسم المالك، الاتصال، الإنتاج، مصادر المياه الخاصة، الآبار، البيانات الزراعية الحساسة — إلا بتصريح. عند الدمج الحكومي: Data Governance · Access Control · Privacy · Security.

---

## 20. مبادئ الفصل الحاكمة

يجب الحفاظ دائماً على الفصل بين:

1. **AOU / Agricultural Observation** ↔ **Official Farm Data**  
2. **Ecological Suitability** ↔ **Operational Accessibility**  
3. **Suitability Score** ↔ **Confidence Score**  
4. **Satellite Observation** ↔ **Field Validation**  
5. **Natural Regeneration** ↔ **Active Planting**  

وجميع التوصيات **قابلة للتفسير والمراجعة والتحديث**.

---

## 21. مؤشرات نجاح المنصة

لا تقتصر على عدد المستخدمين أو سرعة النظام. مستهدفات قياس (بعد بيانات كافية):

| المجال | مؤشر |
|--------|------|
| اكتشاف | Agricultural Area Detection Accuracy |
| تنبيهات | Alert Precision · False Alert Rate · Average Alert Lead Time |
| رطوبة/جفاف | Moisture Prediction Accuracy (مقابل تحقق ميداني/إقليمي معلن) |
| استعادة | Restoration Site Prediction Accuracy |
| نتائج ميدانية | Germination Success Rate · 1-Year Survival Prediction |
| تعلّم | Field Validation Agreement · Recommendation Improvement Year-over-Year |

**مقاييس مرحلة MVP قابلة للتحقق فوراً:** نشر طبقة نجد أسبوعياً عند المشهد الصافي · وجود مبدّل Agricultural/Restoration في نفس التطبيق · مسودة توصية بذر GeoJSON لموسم تجريبي بمصادر مفتوحة · غياب ادعاءات تشخيص آفات أو رطوبة تربة حقلية دقيقة في النصوص.

---

## 22. سيناريوهات المستخدم

### 22.1 زراعي

يدخل → خريطة ظفار → وحدات AOU مكتشفة تلقائياً → يفتح `AOU-NJ-000184` → يرى المساحة، الحالة النباتية، المؤشرات، الإجهاد المائي، التاريخ، التنبيهات، الثقة → «Water Stress: High» → توصية: «تحقق من نظام الري.»

### 22.2 بيئي

Restoration Observatory → Jabal Qara → Post-Khareef Analysis → طبقات MPI / Vegetation Recovery / Degradation / Natural Regeneration / Slope / Hydrology → Recommended Sites → `JR-00871`: Suitability 89% · Confidence 78% · Regeneration Low · MPI High · Enrichment Seeding · *Terminalia dhofarica* · Late Khareef / Early Post-Khareef.

### 22.3 بعد التنفيذ

تسجيل البذر → Germination 30d · Survival 90d · Survival 365d → ربط النتائج بخصائص الموقع → اكتشاف عبر المواسم: أفضل المواقع/الأنواع/الظروف/أوقات البذر/طرق التنفيذ → تحسين مستمر للمحرك.

---

## 23. خارطة طريق MVP → v2 → v3

| المرحلة | النطاق |
|---------|--------|
| **MVP** | امتداد `najd-planting-monitor`؛ AOU/خلايا شبكية + اكتشاف احتمالية زراعية أولي؛ مسار جبال (مركّبات خريف، MPI أولي، DEM+TWI أساسي، مسودة Site×Species بقواعد خبير)؛ مبدّل أوضاع؛ تقويم خريف ديناميكي مبسّط؛ تغذية راجعة ملفات؛ لماذا هذا الموقع؟ |
| **v2** | PostGIS · FastAPI · SMS/Push · حسابات بلدية · تطبيق متطوعين · سجل بذر كامل وجداول بقاء · تشغيل مفعَّل بنوافذ الخريف · TiTiler اختياري · ربط Official Farm عند التوفر |
| **v3** | تجزئة AOI · عمّال سحابة · معايرة ML بعد كفاية Ground Truth · تغطية كتل جبلية أوسع · تقارير مؤسسية · أتمتة أسبوعية شبه كاملة |

---

## 24. مخاطر وقيود صادقة

1. **الآفات/الأمراض:** لا تشخيص مؤكد من البصري وحده → Possible Biotic Stress + فحص ميداني.  
2. **proxies ≠ رطوبة تربة حقلية:** NDMI/MPI وكلاء؛ التحقق الميداني قبل حملات واسعة.  
3. **SMAP/CCI/ERA5/CHIRPS:** سياق إقليمي؛ إساءة الاستخدام على مستوى الحقل مضلّلة.  
4. **غيوم الخريف:** الساحل والجبال أشد تأثراً من نجد الداخلي.  
5. **DEM المجاني:** استبعاد منحدرات وnichés — ليس تصميماً هندسياً.  
6. **حدود المزارع الرسمية:** قد تتأخر؛ AOU يغطي الفجوة منذ اليوم الأول.  
7. **اقتراح الأنواع:** إرشادي؛ يتطلب مراجعة محلية قبل التعميم.  
8. **بيانات مجانية:** دقة محدودة مقابل التجاري — مقبول مع الإفصاح.  
9. **استدامة التشغيل:** الأتمتة ضرورية حتى لا يعتمد التحديث على جهد يدوي هش.  
10. **توقعات المستخدم:** دعم قرار ورصد — ليست بديلاً عن المهندس الزراعي أو المسح الحقلي.

---

## 25. ملحق توافق مع `najd-planting-monitor`

| العنصر الحالي | الامتداد في Observatory 1.0 |
|---------------|------------------------------|
| الاسم AR: رصد زراعة نجد | المنتج الأم: **ظفار رصد \| Dhofar Agro & Eco Observatory**؛ نجد = وضع زراعي أساسي |
| NDVI / NDMI / SAVI + أكواد `bare/healthy/water_attention/vigor_attention` | تُبقى كطبقة تنفيذ أولى؛ تُوسَّع إلى Health/Water Stress Scores وتنبيهات أوسع |
| خلايا ~500 م + hubs | أساس AOU الأولي؛ ترقية إلى مضلعات مجزّأة عند نضج الاكتشاف/الحدود |
| Vite 6 + React 19 + TS + Tailwind 4 + i18next RTL + Leaflet | نفس التطبيق؛ مبدّل Agricultural/Restoration؛ Why This Site؟ |
| PC STAC + rasterio (`mapvenv` / `run_monitor.py`) | محرك مشترك + وحدات جبال (خريف، MPI، هيدرولوجيا، Site×Species) |
| `public/data` GeoJSON | `farm/` · `mountain/` · `shared/` |
| Alias التسويقي | «Dhofar Agro Monitor» يبقى مقبولاً كنص قصير |

### أسماء أماكن مرجعية

- **نجد (hubs اليوم):** ثمريت، الشصر، سيح الخيرات، حنفِيت، المزيونة — دوكة/قطبيت عند توفر AOI.  
- **جبال:** القرا، سمحان، القمر.  
- **ساحل/سفوح:** مرباط، المغسيل؛ صلالة كسياق إداري/مناخي.

---

*نهاية مواصفات المنتج 1.0.1 — ظفار رصد | Dhofar Agro & Eco Observatory. موافقة علمية Agroforestry على 1.0 مع ملاحظات خفيفة مُدمجة (قائمة ضباب قصيرة، تسمية *V. tortilis*، تثقيل MPI لـ onset/post-khareef، NDRE اختياري في مسار المزارع). المعمارية امتداد معتمد لمكدس najd-planting-monitor.*
