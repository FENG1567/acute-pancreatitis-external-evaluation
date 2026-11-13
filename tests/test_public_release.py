"""Self-contained public-release checks; no private inputs are read."""
from pathlib import Path
import sys,unittest,csv,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_public_snapshot import validate
class PublicReleaseTests(unittest.TestCase):
 def test_release_hashes_and_roles(self):self.assertEqual(validate()['status'],'PASS')
 def test_frozen_models_unchanged_and_private_outputs_excluded(self):
  m=json.loads((ROOT/'provenance/external_evaluation_manifest.json').read_text())
  self.assertFalse(m['assertions']['model_refit']);self.assertEqual(m['assertions']['only_corrected_feature'],'sex_male')
  self.assertFalse(any(ROOT.rglob('*.joblib')));self.assertFalse(any(ROOT.rglob('*.parquet')))
 def test_all_calibration_replicates_valid(self):
  with (ROOT/'source_data/recomputed_external/performance_metrics.csv').open() as f:r=list(csv.DictReader(f))
  self.assertTrue(all(int(x['patient_bootstrap_valid'])==2000 and int(x['cluster_bootstrap_valid'])==2000 for x in r))
if __name__=='__main__':unittest.main()
