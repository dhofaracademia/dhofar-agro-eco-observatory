import csv
import json
import tempfile
import unittest
from pathlib import Path
from review import score, FIELDS

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.baseline=self.root/'baseline.json';self.reviews=self.root/'reviews.csv'
        self.baseline.write_text(json.dumps({'release_id':'fixture','predictions':{'a':{'class':'likely'},'b':{'class':'possible'}}}))
    def write(self,rows):
        with self.reviews.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    def row(self,**kw):
        # Synthetic unit-test-only reference. Never shipped as real review evidence.
        return dict(case_id='a',release_id='fixture',agricultural_presence='yes',reviewer='test-fixture',reference_kind='independent_sensor',reference_date='2026-09-19',reference_uri='https://example.org/test-only',independent_of_model='yes',notes='Synthetic test fixture',**kw)
    def test_empty_does_not_claim_validation(self):
        self.write([{'case_id':'a','release_id':'fixture'}]);r=score(self.baseline,self.reviews)
        self.assertIsNone(r['sample_agreement']);self.assertFalse(r['model_validated']);self.assertEqual(r['review_records'],0)
    def test_duplicate_and_wrong_release_rejected(self):
        row=self.row();self.write([row,row])
        with self.assertRaises(ValueError):score(self.baseline,self.reviews)
        row['release_id']='other';self.write([row])
        with self.assertRaises(ValueError):score(self.baseline,self.reviews)
    def test_model_derived_or_undocumented_reference_rejected(self):
        for key,value in [('reference_kind','model_output'),('independent_of_model','no'),('reviewer',''),('reference_uri','javascript:alert(1)')]:
            row=self.row();row[key]=value;self.write([row])
            with self.assertRaises(ValueError):score(self.baseline,self.reviews)
    def test_sample_agreement_is_not_model_validation(self):
        row=self.row();other=dict(row,case_id='b');self.write([row,other]);r=score(self.baseline,self.reviews)
        self.assertEqual(r['sample_agreement'],1);self.assertEqual(r['model_abstentions'],1);self.assertFalse(r['model_validated'])
if __name__=='__main__':unittest.main()
