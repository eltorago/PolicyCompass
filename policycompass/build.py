"""Build the unsigned Windows browser app, portable ZIP and optional EXE installer."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from policycompass import ENGINE_VERSION

LIBRARIES = ('pypdf', 'pdfplumber', 'pdfminer.six', 'Pillow', 'pypdfium2', 'charset-normalizer',
             'cryptography', 'cffi', 'pycparser', 'pyinstaller')


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clean_directory(path, parent):
    path, parent = path.resolve(), parent.resolve()
    if path.parent != parent or path.name not in ('PolicyCompass', 'runtime') or path.is_symlink():
        raise ValueError('Build cleanup target is outside the selected output directory.')
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def build(output, iscc=None):
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Build with 64-bit Python on Windows.')
    output = output.resolve()
    if output == ROOT or output in ROOT.parents:
        raise ValueError('Choose a separate build output directory.')
    output.mkdir(parents=True, exist_ok=True)
    payload = output / 'PolicyCompass'
    runtime = output / 'runtime'
    clean_directory(payload, output)
    clean_directory(runtime, output)
    common = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--noupx',
              '--workpath', str(output / 'work'), '--specpath', str(output)]
    subprocess.run([*common, '--onedir', '--name', 'policycompass', '--paths', str(ROOT),
        '--distpath', str(runtime),
        '--add-data', str(ROOT / 'policycompass/assets') + ';policycompass/assets',
        '--add-data', str(ROOT / 'sources/permissions.json') + ';sources',
        '--add-data', str(ROOT / 'data/wa-audit-context.json') + ';data',
        '--collect-all', 'pypdf', '--hidden-import', 'cryptography.hazmat.primitives.asymmetric.ed25519',
        str(ROOT / 'policycompass/entry.py')], check=True, cwd=ROOT)
    shutil.copytree(runtime / 'policycompass', payload / 'core')
    # Keep worker stdin/stdout intact while the launcher runs without a console.
    subprocess.run([*common, '--onefile', '--windowed', '--name', 'PolicyCompass',
                    '--distpath', str(payload), str(ROOT / 'policycompass/windows_launcher.py')], check=True, cwd=ROOT)
    notices = payload / 'licenses'
    for name in LIBRARIES:
        dist = importlib.metadata.distribution(name)
        for entry in dist.files or ():
            if 'license' in str(entry).lower() or 'copying' in str(entry).lower():
                source = Path(dist.locate_file(entry))
                if source.is_file() and source.suffix.lower() not in ('.py', '.pyc'):
                    target = notices / name / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
    python_notice = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_notice.is_file():
        notices.mkdir(exist_ok=True)
        shutil.copy2(python_notice, notices / 'Python-LICENSE.txt')
    shutil.copy2(ROOT / 'packaging/README.txt', payload / 'README.txt')
    inventory = []
    for path in sorted(payload.rglob('*')):
        if path.is_file():
            relative = path.relative_to(payload).as_posix()
            if any(part.lower() in ('examples', 'tests') for part in path.relative_to(payload).parts) or path.suffix.lower() == '.policycompass':
                raise ValueError('A test, example policy or saved comparison entered the release payload: ' + relative)
            inventory.append(dict(path=relative, size=path.stat().st_size, sha256=sha256(path),
                role='executable dependency' if path.suffix.lower() in ('.exe', '.dll', '.pyd') else 'runtime asset'))
    artifacts = output / 'release'
    artifacts.mkdir(exist_ok=True)
    portable = Path(shutil.make_archive(str(artifacts / f'PolicyCompass-{ENGINE_VERSION}-windows-x64-portable'),
                                      'zip', root_dir=output, base_dir='PolicyCompass'))
    products = [portable]
    if iscc:
        subprocess.run([str(iscc), '/DAppVersion=' + ENGINE_VERSION, '/DPayloadDir=' + str(payload),
                        '/DReleaseDir=' + str(artifacts), str(ROOT / 'packaging/windows.iss')], check=True)
        products.append(artifacts / f'PolicyCompass-{ENGINE_VERSION}-windows-x64-setup.exe')
    manifest = dict(name='PolicyCompass', version=ENGINE_VERSION, platform='windows-x64', signed=False,
        repositoryRevision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        workingTreeChanges=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
        python=sys.version, files=inventory,
        excluded=['Example policies', 'Publisher documents', 'Saved comparisons', 'Tests and local development files'],
        frameworkSetup='Use Framework updates to download publisher files or import the AESCSF Core workbook.',
        artifacts=[dict(name=p.name, size=p.stat().st_size, sha256=sha256(p)) for p in products])
    manifest_path = artifacts / 'release-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    components = [dict(type='library', name=name, version=importlib.metadata.version(name),
                  purl='pkg:pypi/' + name + '@' + importlib.metadata.version(name)) for name in LIBRARIES]
    sbom = artifacts / 'sbom.cdx.json'
    sbom.write_text(json.dumps(dict(bomFormat='CycloneDX', specVersion='1.5', version=1,
        metadata={'component': {'type':'application', 'name':'PolicyCompass', 'version':ENGINE_VERSION}},
        components=components), indent=2), encoding='utf-8')
    products.extend([manifest_path, sbom])
    (artifacts / 'SHA256SUMS.txt').write_text(''.join(sha256(p) + '  ' + p.name + '\n' for p in products), encoding='utf-8')
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'data/local/browser-build'))
    parser.add_argument('--installer', action='store_true', help='Also build a per-user EXE installer with Inno Setup')
    parser.add_argument('--iscc', help='Path to the Inno Setup compiler (ISCC.exe)')
    args = parser.parse_args()
    compiler = args.iscc or shutil.which('ISCC.exe')
    if args.installer and not compiler:
        candidate = Path('C:/Program Files (x86)/Inno Setup 6/ISCC.exe')
        compiler = str(candidate) if candidate.is_file() else None
        if not compiler:
            parser.error('Install Inno Setup or provide --iscc with its ISCC.exe path.')
    print(build(Path(args.output), compiler if args.installer or args.iscc else None))


if __name__ == '__main__':
    main()
