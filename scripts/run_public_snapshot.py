#!/usr/bin/env python3
"""Check that the published files are consistent, without accessing controlled data."""
from pathlib import Path, PurePosixPath
import csv, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'PACKAGE_MANIFEST.csv','SHA256SUMS.csv'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def validate(root=ROOT):
 root=Path(root).resolve();manifest=rows(root/'PACKAGE_MANIFEST.csv');sums=rows(root/'SHA256SUMS.csv')
 indexed={}
 for row in manifest:
  rel=PurePosixPath(row['path'])
  if rel.is_absolute() or '..' in rel.parts or '\\' in row['path'] or row['path'] in indexed:raise ValueError('Unsafe or duplicate manifest path')
  p=root/rel
  if not p.is_file() or p.is_symlink() or root not in p.resolve().parents:raise ValueError('Missing or unsafe file: '+row['path'])
  if sha(p)!=row['sha256'] or p.stat().st_size!=int(row['bytes']):raise ValueError('Manifest mismatch: '+row['path'])
  indexed[row['path']]=row['sha256']
 expected={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts and '__pycache__' not in p.parts and p.name not in EXCLUDED and p.suffix!='.pyc'}
 if set(indexed)!=expected:raise ValueError('Manifest does not cover exactly the public files')
 if len(sums)!=len(indexed) or {r['path']:r['sha256'] for r in sums}!=indexed:raise ValueError('Checksum lists disagree')
 for name in ['table_1_panel_A.csv','table_1_panel_B.csv']:
  if not rows(root/'tables'/name):raise ValueError('Empty main table')
 for i in range(1,9):
  if not rows(root/f'supplementary/tables/supplemental_table_S{i}.csv'):raise ValueError('Empty supplementary table')
 for i in range(1,5):
  for ext in ['pdf','tif']:
   for rel in [f'figures/Figure_{i}.{ext}',f'supplementary/figures/Supplemental_Figure_S{i}.{ext}']:
    if not (root/rel).is_file():raise ValueError('Missing publication figure: '+rel)
 forbidden={'raw_icu_stay_id_hash','patient_key_hash','patientunitstayid','hospitalid','pred_A','pred_B'}
 for folder in ['tables','supplementary/tables','source_data','final']:
  for p in (root/folder).rglob('*.csv'):
   with p.open(encoding='utf-8-sig',newline='') as f:header=next(csv.reader(f),[])
   if set(header)&forbidden:raise ValueError('Controlled row schema in public data: '+str(p.relative_to(root)))
 status=json.loads((root/'final/release_status.json').read_text(encoding='utf-8'))
 if status['status']!='PASS' or status['model_refit'] or status['primary_n']!=359 or status['primary_events']!=21:raise ValueError('Release status is not PASS')
 values=rows(root/'final/source_of_truth_metrics.csv')
 primary=[r for r in values if r['cohort']=='eICU_primary_locked_359' and r['metric']=='auroc']
 if len(primary)!=2 or {round(float(r['estimate']),4) for r in primary}!={.8605,.8525}:raise ValueError('Primary estimates differ from current submitted values')
 return {'status':'PASS','files_verified':len(indexed),'main_figures':4,'supplemental_figures':4,'supplemental_tables':8,'controlled_data_read':False}
if __name__=='__main__':print(json.dumps(validate(),sort_keys=True))
