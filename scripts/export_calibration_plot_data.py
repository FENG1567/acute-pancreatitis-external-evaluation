#!/usr/bin/env python3
"""Export non-identifying calibration plot summaries from a private prediction lock.

Execute only in the authorized data environment. No patient identifiers are
written. These summaries support independent plots, not exact layout replay.
"""
from pathlib import Path
import argparse,sys,json,hashlib
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from external_evaluation import metric_values,expit
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--primary-lock',type=Path,required=True);p.add_argument('--sensitive-lock',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError('Output must be a new directory')
 rows=[];curves=[];hist=[];inputs={}
 for cohort,path in [('primary',a.primary_lock),('sensitive',a.sensitive_lock)]:
  inputs[cohort]=hashlib.sha256(path.read_bytes()).hexdigest();f=pd.read_parquet(path)
  for model in ['A','B']:
   y=f['outcome'].to_numpy(int);risk=f[f'pred_{model}'].to_numpy(float);m=metric_values(y,risk)
   for group in np.array_split(np.argsort(risk,kind='stable'),10):
    rows.append({'cohort':cohort,'model':model,'bin':len([r for r in rows if r['cohort']==cohort and r['model']==model])+1,'n':len(group),'mean_prediction':risk[group].mean(),'observed_proportion':y[group].mean()})
   for x in np.linspace(.001,.999,300):curves.append({'cohort':cohort,'model':model,'predicted_risk':x,'joint_logistic_calibration':float(expit(np.array([m['calibration_intercept']+m['calibration_slope']*np.log(x/(1-x))]))[0])})
   counts,edges=np.histogram(risk,bins=np.linspace(0,1,21))
   for low,high,n in zip(edges[:-1],edges[1:],counts):hist.append({'cohort':cohort,'model':model,'bin_low':low,'bin_high':high,'n':n})
 a.output.mkdir(parents=True)
 for name,data in [('calibration_bins.csv',rows),('calibration_curves.csv',curves),('prediction_distribution.csv',hist)]:pd.DataFrame(data).to_csv(a.output/name,index=False,float_format='%.17g')
 (a.output/'provenance.json').write_text(json.dumps({'inputs_sha256':inputs,'kind':'aggregate_plot_summaries','identifiers_written':False,'binning':'ten equal-size ordered groups; histogram 20 fixed bins'},indent=2))
if __name__=='__main__':main()
