#!/usr/bin/env python3
"""Create PNG previews of the submitted figures, leaving TIFF/PDF unchanged.

This compatibility entrypoint does not regenerate the earlier five-figure
layouts. Numerical plot inputs are separately available under source_data/.
"""
from pathlib import Path
import argparse
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--figure',default='all',choices=['all','1','2','3','4','S1','S2','S3','S4'])
 args=parser.parse_args()
 keys=['1','2','3','4','S1','S2','S3','S4'] if args.figure=='all' else [args.figure]
 for key in keys:
  path=ROOT/(f'supplementary/figures/Supplemental_Figure_{key}.tif' if key.startswith('S') else f'figures/Figure_{key}.tif')
  with Image.open(path) as im:im.convert('RGB').save(path.with_suffix('.png'),optimize=True)
 print(f'Created {len(keys)} preview(s); submitted TIFF/PDF files were not modified.')
if __name__=='__main__':main()
