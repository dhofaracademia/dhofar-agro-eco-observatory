#!/usr/bin/env python3
"""Separate reference-review workflow. Never invokes the prediction pipeline."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ['case_id', 'release_id', 'agricultural_presence', 'reviewer', 'reference_kind', 'reference_date', 'reference_uri', 'independent_of_model', 'notes']
KINDS = {'independent_sensor', 'field_observation', 'external_record'}

def prepare(data: Path, public: Path, private: Path):
    manifest = json.loads((data / 'latest_release.json').read_text())
    rid = manifest['release_id']
    source = data / manifest['path'] / 'aou/aou_registry.geojson'
    raw = source.read_bytes()
    registry = json.loads(raw)
    if registry.get('release_id') != rid:
        raise ValueError('Registry does not match pinned release')
    public.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    cases, predictions = [], {}
    for feature in registry['features']:
        p = feature['properties']
        case = hashlib.sha256(f"{rid}/{p['aou_id']}".encode()).hexdigest()[:16]
        cases.append({'type':'Feature', 'geometry':feature['geometry'], 'properties':{
            'case_id':case, 'release_id':rid, 'observation_date':p.get('date'),
            'instructions':'Independently assess agricultural land use; do not consult model scores. Use uncertain when evidence is insufficient.'}})
        predictions[case] = {'class': p.get('ag_class'), 'aou_id':p['aou_id'], 'observation_date':p.get('date')}
    (public/'cases.geojson').write_text(json.dumps({'type':'FeatureCollection','features':cases},indent=2)+'\n')
    with (public/'reviews.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
        writer.writerows({'case_id':c['properties']['case_id'],'release_id':rid} for c in cases)
    (private/'predictions.json').write_text(json.dumps({'release_id':rid,'registry_sha256':hashlib.sha256(raw).hexdigest(),'predictions':predictions},indent=2)+'\n')
    return rid, len(cases)

def score(baseline: Path, reviews: Path):
    frozen=json.loads(baseline.read_text());predictions=frozen['predictions'];seen=set();counts={};n=0;uncertain=0;abstained=0
    with reviews.open(newline='') as f:
        reader=csv.DictReader(f)
        if set(reader.fieldnames or []) != set(FIELDS):raise ValueError('Unexpected review columns')
        for row in reader:
            case=row['case_id']
            if case not in predictions or row['release_id'] != frozen['release_id']:raise ValueError('Unknown case or mismatched release')
            if case in seen:raise ValueError('Duplicate case')
            seen.add(case)
            label=row['agricultural_presence'].strip()
            if not label:continue
            if label not in {'yes','no','uncertain'}:raise ValueError('Invalid reference label')
            if row['reference_kind'] not in KINDS or row['independent_of_model'] != 'yes':raise ValueError('Independent reference declaration required')
            if not row['reviewer'].strip() or not row['notes'].strip():raise ValueError('Reviewer and evidence notes required')
            from datetime import date
            date.fromisoformat(row['reference_date'])
            source=urlparse(row['reference_uri'])
            if source.scheme != 'https' or not source.netloc:raise ValueError('An auditable HTTPS evidence reference is required')
            n+=1
            if label=='uncertain':uncertain+=1;continue
            pred=predictions[case]['class']
            predicted='yes' if pred in {'likely','very_likely'} else 'no' if pred=='unlikely' else 'abstain'
            if predicted=='abstain':abstained+=1;continue
            key=f'reference_{label}__predicted_{predicted}';counts[key]=counts.get(key,0)+1
    compared=sum(counts.values());matches=sum(v for k,v in counts.items() if k in {'reference_yes__predicted_yes','reference_no__predicted_no'})
    return {'release_id':frozen['release_id'],'review_records':n,'uncertain_references':uncertain,'model_abstentions':abstained,
            'compared':compared,'confusion_counts':counts,'sample_agreement':matches/compared if compared else None,
            'evidence_status':'submitted_references_not_independently_verified' if n else 'awaiting_independent_references',
            'model_validated':False,'scope':'Agricultural presence only; not irrigation, pests, yield or mountain seeding. Selected pilot units are not a representative accuracy sample.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--data',type=Path,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    p=sub.add_parser('score');p.add_argument('--baseline',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':print(prepare(args.data,args.public,args.baseline))
    else: args.out.write_text(json.dumps(score(args.baseline,args.reviews),indent=2)+'\n')
