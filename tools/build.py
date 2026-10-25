"""Build a portable add-on; on macOS include universal local OCR."""

import argparse
import hashlib
import json
import platform
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(with_ocr=False):
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    extra = None
    if with_ocr:
        if platform.system() != "Darwin":
            raise SystemExit("Building OCR requires macOS with Xcode command line tools.")
        scratch = ROOT / "build"
        scratch.mkdir(exist_ok=True)
        parts = []
        for arch in ("arm64", "x86_64"):
            binary = scratch / f"ocr-{arch}"
            subprocess.run(
                [
                    "swiftc",
                    "-O",
                    "-target",
                    f"{arch}-apple-macosx13.0",
                    str(ROOT / "native/ocr.swift"),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            parts.append(str(binary))
        extra = scratch / "anki-star-ocr"
        subprocess.run(["lipo", "-create", *parts, "-output", str(extra)], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(extra)], check=True)
    name = "anki-star-0.1.0-macos.ankiaddon" if with_ocr else "anki-star-0.1.0.ankiaddon"
    archive = output / name
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for path in sorted((ROOT / "addon").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                package.write(path, path.relative_to(ROOT / "addon"))
        package.write(ROOT / "LICENSE", "LICENSE")
        package.write(ROOT / "native/ocr.swift", "native/ocr.swift")
        if extra:
            package.write(extra, "bin/anki-star-ocr")
    with zipfile.ZipFile(archive) as package:
        assert "__init__.py" in package.namelist()
        manifest = json.loads(package.read("manifest.json"))
        assert manifest["package"] == "anki_star"
        assert package.testzip() is None
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / f"{name}.sha256").write_text(f"{digest}  {name}\n")
    print(f"Built {archive} ({archive.stat().st_size:,} bytes)")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--macos-ocr", action="store_true")
    args = parser.parse_args()
    build(args.macos_ocr)
