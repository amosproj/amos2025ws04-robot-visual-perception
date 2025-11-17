#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

"""
SBOM Generator for robot-visual-perception project.

Generates:
- SBOM in SPDX JSON format (sbom.json)
- CSV with first-order dependencies (sbom-dependencies.csv)
- Optional: Updates planning-documents.xlsx in Deliverables/sprint-XX/
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def parse_requirements_file(file_path: Path) -> List[Dict[str, str]]:
    """Parse requirements.txt and extract package info."""
    packages = []
    if not file_path.exists():
        return packages

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse package==version
            match = re.match(r"^([a-zA-Z0-9\-_.]+)\s*==\s*([0-9.]+)", line)
            if match:
                name, version = match.groups()
                packages.append(
                    {
                        "name": name,
                        "version": version,
                        "ecosystem": "pypi",
                        "purl": f"pkg:pypi/{name}@{version}",
                    }
                )

    return packages


def get_npm_dependencies(package_json_path: Path) -> List[Dict[str, str]]:
    """Extract npm dependencies from package.json."""
    packages = []
    if not package_json_path.exists():
        return packages

    with open(package_json_path, "r") as f:
        data = json.load(f)

    # Production dependencies
    for name, version in data.get("dependencies", {}).items():
        version_clean = version.lstrip("^~>=<")
        packages.append(
            {
                "name": name,
                "version": version_clean,
                "ecosystem": "npm",
                "purl": f"pkg:npm/{name}@{version_clean}",
                "is_dev": False,
            }
        )

    # Dev dependencies
    for name, version in data.get("devDependencies", {}).items():
        version_clean = version.lstrip("^~>=<")
        packages.append(
            {
                "name": name,
                "version": version_clean,
                "ecosystem": "npm",
                "purl": f"pkg:npm/{name}@{version_clean}",
                "is_dev": True,
            }
        )

    return packages


def enrich_packages_with_license(packages: List[Dict[str, str]], ecosystem: str) -> None:
    """Populate license metadata for each package in-place."""
    for pkg in packages:
        pkg["license"] = get_license_info(pkg["name"], pkg["version"], ecosystem)


LicenseCacheKey = Tuple[str, str, str]
LICENSE_CACHE: Dict[LicenseCacheKey, str] = {}


def get_license_info(name: str, version: str, ecosystem: str) -> str:
    """Fetch license information for a given package from its registry."""
    cache_key: LicenseCacheKey = (ecosystem, name.lower(), version)
    if cache_key in LICENSE_CACHE:
        return LICENSE_CACHE[cache_key]

    if ecosystem == "pypi":
        license_value = fetch_license_from_pypi(name, version)
    elif ecosystem == "npm":
        license_value = fetch_license_from_npm(name, version)
    else:
        license_value = "NOASSERTION"

    LICENSE_CACHE[cache_key] = license_value
    return license_value


def extract_license_from_classifiers(classifiers: List[str]) -> Optional[str]:
    """Extract a readable license string from PyPI classifiers."""
    for classifier in reversed(classifiers):
        if classifier.startswith("License ::"):
            parts = [part.strip() for part in classifier.split("::") if part.strip()]
            if parts:
                return parts[-1]
    return None


def fetch_license_from_pypi(name: str, version: str) -> str:
    """Retrieve license metadata for a PyPI package/version."""
    encoded_name = quote(name)
    url = f"https://pypi.org/pypi/{encoded_name}/{version}/json"
    try:
        with urlopen(url, timeout=10) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return "NOASSERTION"

    info = data.get("info", {})
    license_value = (info.get("license") or "").strip()
    if not license_value or license_value.upper() == "UNKNOWN":
        license_value = extract_license_from_classifiers(info.get("classifiers", [])) or ""

    license_value = license_value.strip()
    return license_value or "NOASSERTION"


def parse_npm_license_field(raw_license: Any) -> Optional[str]:
    """Normalize possible npm license structures."""
    if isinstance(raw_license, str):
        return raw_license.strip()
    if isinstance(raw_license, dict):
        return str(raw_license.get("type", "")).strip() or None
    if isinstance(raw_license, list):
        licenses = []
        for entry in raw_license:
            normalized = parse_npm_license_field(entry)
            if normalized:
                licenses.append(normalized)
        return ", ".join(licenses) if licenses else None
    return None


def fetch_license_from_npm(name: str, version: str) -> str:
    """Retrieve license metadata for an npm package/version."""
    encoded_name = quote(name, safe="@/")
    url = f"https://registry.npmjs.org/{encoded_name}"
    try:
        with urlopen(url, timeout=10) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return "NOASSERTION"

    version_data = {}
    versions = data.get("versions", {})
    if isinstance(versions, dict):
        version_data = versions.get(version, {})

    license_value = parse_npm_license_field(version_data.get("license"))
    if not license_value:
        license_value = parse_npm_license_field(version_data.get("licenses"))
    if not license_value:
        license_value = parse_npm_license_field(data.get("license"))

    return license_value or "NOASSERTION"


PYTHON_CONTEXT_OVERRIDES: Dict[str, str] = {
    "aiortc": "WebRTC Signaling",
    "av": "WebRTC Signaling",
    "opencv-python": "Image Analysis (Python)",
    "numpy": "Image Analysis (Python)",
    "ultralytics": "Image Analysis (Python)",
    "timm": "Image Analysis (Python)",
}

def apply_context_overrides(
    packages: List[Dict[str, str]],
    context_overrides: Optional[Dict[str, str]] = None,
) -> None:
    """Inject human-readable context overrides."""
    for pkg in packages:
        name = pkg.get("name")
        if not name:
            continue
        if context_overrides:
            context_value = context_overrides.get(name)
            if context_value:
                pkg["context"] = context_value


def generate_spdx_sbom(
    python_packages: List[Dict[str, str]], npm_packages: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Generate SBOM in SPDX 2.3 JSON format."""
    timestamp = datetime.utcnow().isoformat() + "Z"

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "robot-visual-perception-sbom",
        "documentNamespace": f"https://github.com/amosproj/amos2025ws04-robot-visual-perception/sbom-{timestamp}",
        "creationInfo": {
            "created": timestamp,
            "creators": ["Tool: robot-visual-perception-sbom-generator"],
            "licenseListVersion": "3.21",
        },
        "packages": [],
    }

    # Add root package
    sbom["packages"].append(
        {
            "SPDXID": "SPDXRef-Package-root",
            "name": "robot-visual-perception",
            "versionInfo": "0.1.0",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "MIT",
            "copyrightText": "NOASSERTION",
        }
    )

    # Add Python packages
    for idx, pkg in enumerate(python_packages):
        sbom["packages"].append(
            {
                "SPDXID": f"SPDXRef-Package-pypi-{idx}",
                "name": pkg["name"],
                "versionInfo": pkg["version"],
                "downloadLocation": f"https://pypi.org/project/{pkg['name']}/{pkg['version']}",
                "filesAnalyzed": False,
                "licenseConcluded": pkg.get("license", "NOASSERTION"),
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": pkg["purl"],
                    }
                ],
            }
        )

    # Add npm packages
    for idx, pkg in enumerate(npm_packages):
        sbom["packages"].append(
            {
                "SPDXID": f"SPDXRef-Package-npm-{idx}",
                "name": pkg["name"],
                "versionInfo": pkg["version"],
                "downloadLocation": f"https://www.npmjs.com/package/{pkg['name']}/v/{pkg['version']}",
                "filesAnalyzed": False,
                "licenseConcluded": pkg.get("license", "NOASSERTION"),
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": pkg["purl"],
                    }
                ],
            }
        )

    return sbom


def generate_csv(sections: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Generate CSV data for the Bill of Materials from all dependency sections."""
    csv_data: List[Dict[str, str]] = []
    counter = 1

    for section in sections:
        context = section["context"]
        packages = section.get("packages") or []
        prefix = section.get("name_prefix", "")
        status = section.get("status", "In Use")
        for pkg in packages:
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            license_value = pkg.get("license", "NOASSERTION")
            pkg_context = pkg.get("context", context)
            pkg_status = pkg.get("status", status)
            formatted_name = (
                f"{prefix}:{name}" if prefix and name else name
            )

            csv_data.append(
                {
                    "#": str(counter),
                    "Context": pkg_context,
                    "Name": formatted_name,
                    "Version": version,
                    "License": license_value,
                    "Status": pkg_status,
                }
            )
            counter += 1

    return csv_data


def write_csv(csv_data: List[Dict[str, str]], output_path: Path) -> None:
    """Write CSV file."""
    fieldnames = [
        "#",
        "Context",
        "Name",
        "Version",
        "License",
        "Status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)


def get_latest_sprint_number() -> Optional[int]:
    """Get the latest sprint number from Git tags."""
    try:
        # Get latest tag
        tag = run_command(["git", "describe", "--tags", "--abbrev=0"])
        # Extract sprint number (e.g., v1.0.0-sprint-04 -> 4)
        match = re.search(r"sprint-(\d+)", tag)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    # Fallback: Find highest sprint folder
    root = get_project_root()
    deliverables = root / "Deliverables"
    if not deliverables.exists():
        return None

    sprint_folders = [
        int(f.name.replace("sprint-", ""))
        for f in deliverables.iterdir()
        if f.is_dir() and f.name.startswith("sprint-")
    ]
    return max(sprint_folders) if sprint_folders else None


def prepare_sprint_folder(current_sprint: int) -> Path:
    """Ensure next sprint folder exists and has planning-documents.xlsx."""
    root = get_project_root()
    deliverables = root / "Deliverables"
    next_sprint = current_sprint + 1

    next_sprint_folder = deliverables / f"sprint-{next_sprint:02d}"
    current_sprint_folder = deliverables / f"sprint-{current_sprint:02d}"

    if not next_sprint_folder.exists():
        print(f"Creating new sprint folder: {next_sprint_folder.name}")
        next_sprint_folder.mkdir(parents=True)

    import shutil

    def copy_if_missing(source: Path, target: Path, label: str) -> None:
        if target.exists():
            return
        if source.exists():
            shutil.copy2(source, target)
            print(f"Copied {label} from sprint-{current_sprint:02d}")
        else:
            print(
                f"Warning: {source} not found, cannot copy to new sprint",
                file=sys.stderr,
            )

    copy_if_missing(
        current_sprint_folder / "planning-documents.xlsx",
        next_sprint_folder / "planning-documents.xlsx",
        "planning-documents.xlsx",
    )
    copy_if_missing(
        current_sprint_folder / "planning-documents.xlsx.license",
        next_sprint_folder / "planning-documents.xlsx.license",
        "planning-documents.xlsx.license",
    )

    return next_sprint_folder


def update_excel(csv_data: List[Dict[str, str]], sprint_folder: Path) -> None:
    """Update planning-documents.xlsx with new BOM data."""
    try:
        from openpyxl import load_workbook
        from openpyxl.styles import PatternFill
    except ImportError:
        print(
            "Error: openpyxl not installed. Run: pip install openpyxl",
            file=sys.stderr,
        )
        sys.exit(1)

    excel_path = sprint_folder / "planning-documents.xlsx"
    if not excel_path.exists():
        print(f"Error: {excel_path} not found", file=sys.stderr)
        sys.exit(1)

    wb = load_workbook(excel_path)

    # Find or create 'Bill of Materials' sheet
    sheet_name = "Bill of Materials"
    if sheet_name in wb.sheetnames:
        # Clear existing sheet
        ws = wb[sheet_name]
        wb.remove(ws)

    ws = wb.create_sheet(sheet_name)

    # Write headers
    headers = list(csv_data[0].keys())
    ws.append(headers)

    header_fill = PatternFill(
        fill_type="solid",
        start_color="FFD9D9D9",
        end_color="FFD9D9D9",
    )
    for cell in ws[1]:
        cell.fill = header_fill

    # Write data
    for row in csv_data:
        ws.append(list(row.values()))

    # Save
    wb.save(excel_path)
    print(f"Updated {excel_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate SBOM for the project")
    parser.add_argument(
        "--update-excel",
        action="store_true",
        help="Update planning-documents.xlsx in Deliverables folder",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if SBOM files are up-to-date (exit 1 if not)",
    )
    args = parser.parse_args()

    root = get_project_root()

    # Parse dependencies
    print("Parsing dependencies...")
    backend_dir = root / "src" / "backend"
    frontend_dir = root / "src" / "frontend"
    scripts_dir = root / "scripts"

    python_prod = parse_requirements_file(backend_dir / "requirements.txt")
    python_dev = parse_requirements_file(backend_dir / "requirements-dev.txt")
    scripts_python = parse_requirements_file(scripts_dir / "requirements.txt")
    npm_packages = get_npm_dependencies(frontend_dir / "package.json")

    # Enrich with license info (best-effort via registry lookups)
    for package_group in (python_prod, python_dev, scripts_python):
        enrich_packages_with_license(package_group, "pypi")
    enrich_packages_with_license(npm_packages, "npm")

    # Apply context overrides for nicer BOM output
    apply_context_overrides(python_prod, PYTHON_CONTEXT_OVERRIDES)

    all_python = python_prod + python_dev + scripts_python

    print(f"Found {len(python_prod)} Python production packages")
    print(f"Found {len(python_dev)} Python dev packages")
    print(f"Found {len(scripts_python)} Python script packages")
    print(f"Found {len(npm_packages)} npm packages (prod + dev)")

    # Check mode
    if args.check:
        sbom_path = root / "sbom.json"
        csv_path = root / "sbom-dependencies.csv"

        if not sbom_path.exists() or not csv_path.exists():
            print("Error: SBOM files missing. Run 'make sbom' to generate.")
            sys.exit(1)

        # Simple check: compare modification times
        dependency_files = [
            backend_dir / "requirements.txt",
            backend_dir / "requirements-dev.txt",
            frontend_dir / "package.json",
            scripts_dir / "requirements.txt",
        ]

        existing_mtimes = [
            path.stat().st_mtime for path in dependency_files if path.exists()
        ]
        if not existing_mtimes:
            print("Error: No dependency files found to compare timestamps.", file=sys.stderr)
            sys.exit(1)

        req_time = max(existing_mtimes)

        sbom_time = min(sbom_path.stat().st_mtime, csv_path.stat().st_mtime)

        if req_time > sbom_time:
            print(
                "Error: Dependencies changed but SBOM not updated. Run 'make sbom'."
            )
            sys.exit(1)

        print("SBOM is up-to-date.")
        return

    # Generate SBOM
    print("Generating SBOM...")
    sbom = generate_spdx_sbom(all_python, npm_packages)

    sbom_path = root / "sbom.json"
    with open(sbom_path, "w") as f:
        json.dump(sbom, f, indent=2)
    print(f"Generated: {sbom_path}")

    # Generate CSV (all dependencies for BOM/Excel)
    print("Generating CSV...")
    csv_sections = [
        {
            "context": "Frontend (React UI)",
            "packages": [p for p in npm_packages if not p.get("is_dev", False)],
            "name_prefix": "npm",
        },
        {
            "context": "Frontend Dev Tooling",
            "packages": [p for p in npm_packages if p.get("is_dev", False)],
            "name_prefix": "npm",
            "status": "Development",
        },
        {
            "context": "Backend (FastAPI API)",
            "packages": python_prod,
            "name_prefix": "pypi",
        },
        {
            "context": "Backend Dev Dependencies",
            "packages": python_dev,
            "name_prefix": "pypi",
            "status": "Development",
        },
        {
            "context": "Automation Scripts",
            "packages": scripts_python,
            "name_prefix": "pypi",
        },
    ]

    csv_data = generate_csv([section for section in csv_sections if section["packages"]])

    csv_path = root / "sbom-dependencies.csv"
    write_csv(csv_data, csv_path)
    print(f"Generated: {csv_path}")

    # Update Excel if requested
    if args.update_excel:
        print("\nUpdating Excel...")
        sprint_num = get_latest_sprint_number()

        if sprint_num is None:
            print("Error: Cannot determine current sprint number", file=sys.stderr)
            sys.exit(1)

        sprint_folder = prepare_sprint_folder(sprint_num)
        update_excel(csv_data, sprint_folder)

    print("\nDone!")


if __name__ == "__main__":
    main()

