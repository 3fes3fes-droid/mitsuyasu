from pathlib import Path
import csv, hashlib
ROOT=Path(__file__).resolve().parents[1]
manifest=ROOT/'FILE_MANIFEST.tsv'
rows=[]
for path in sorted(ROOT.rglob('*')):
    if path.is_file() and path != manifest:
        rows.append((path.relative_to(ROOT).as_posix(),path.stat().st_size,hashlib.sha256(path.read_bytes()).hexdigest()))
with manifest.open('w',encoding='utf-8',newline='') as f:
    writer=csv.writer(f,delimiter='\t');writer.writerow(['path','bytes','sha256']);writer.writerows(rows)
print(f'manifest: {len(rows)} files')
