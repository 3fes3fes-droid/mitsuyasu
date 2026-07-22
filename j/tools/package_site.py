from pathlib import Path
import zipfile, hashlib
ROOT=Path(__file__).resolve().parents[1]
zip_path=ROOT.parent/(ROOT.name+'.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted(ROOT.rglob('*')):
        if path.is_file(): z.write(path,Path(ROOT.name)/path.relative_to(ROOT))
hashv=hashlib.sha256(zip_path.read_bytes()).hexdigest()
zip_path.with_suffix(zip_path.suffix+'.sha256').write_text(f'{hashv}  {zip_path.name}\n',encoding='utf-8')
print(zip_path);print(hashv)
