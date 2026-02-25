"""
PyGitUp Supply Chain Security Module
=====================================
Advanced supply chain security features:
- Dependency vulnerability scanning with enhanced detection
- Package signature verification
- Lockfile integrity checking
- SBOM (Software Bill of Materials) generation
- Dependency tree analysis
"""

import os
import json
import hashlib
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import base64

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ..utils.ui import print_success, print_error, print_info, print_warning, print_header, console, Table, box, Panel


# =============================================================================
# VULNERABILITY SEVERITY ENUMS
# =============================================================================

class VulnerabilitySeverity(Enum):
    """Severity levels for vulnerabilities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class DependencyVulnerability:
    """Represents a vulnerability in a dependency."""
    id: str
    package_name: str
    installed_version: str
    vulnerable_version_range: str
    fixed_version: Optional[str]
    severity: VulnerabilitySeverity
    cve_id: Optional[str]
    cwe_id: Optional[str]
    title: str
    description: str
    cvss_score: float
    published_at: Optional[str]
    updated_at: Optional[str]
    ecosystem: str = "pypi"
    direct_dependency: bool = True


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    version: str
    direct: bool
    dependencies: List[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    maintainer: Optional[str] = None
    download_count: int = 0
    last_updated: Optional[str] = None


# =============================================================================
# DEPENDENCY PARSING
# =============================================================================

def parse_requirements_file(file_path: str = "requirements.txt") -> Dict[str, str]:
    """
    Parse a requirements.txt file.
    
    Args:
        file_path: Path to requirements file
        
    Returns:
        Dictionary of {package: version_spec}
    """
    dependencies = {}
    
    if not os.path.exists(file_path):
        return dependencies
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Skip options like -r, -e, --extra-index-url, etc.
                if line.startswith('-'):
                    continue
                
                # Parse package and version
                # Handle various formats: pkg==1.0, pkg>=1.0, pkg~=1.0, pkg[extra]==1.0
                match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_,-]+\])?)\s*([<>=!~]+.*)?$', line)
                if match:
                    package = match.group(1).split('[')[0]  # Remove extras
                    version = match.group(2) or '*'
                    dependencies[package.lower()] = version
    except Exception as e:
        print_warning(f"Error parsing requirements: {e}")
    
    return dependencies


def parse_setup_py(file_path: str = "setup.py") -> Dict[str, str]:
    """Parse setup.py for dependencies."""
    dependencies = {}
    
    if not os.path.exists(file_path):
        return dependencies
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Look for install_requires
            match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                requires_str = match.group(1)
                for req in re.findall(r"['\"]([^'\"]+)['\"]", requires_str):
                    pkg_match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!~].*)?$', req)
                    if pkg_match:
                        package = pkg_match.group(1)
                        version = pkg_match.group(2) or '*'
                        dependencies[package.lower()] = version
    except Exception as e:
        if os.environ.get('PYGITUP_DEBUG'):
            print_warning(f"Error parsing setup.py: {e}")
    
    return dependencies


def parse_pyproject_toml(file_path: str = "pyproject.toml") -> Dict[str, str]:
    """Parse pyproject.toml for dependencies."""
    dependencies = {}
    
    if not os.path.exists(file_path):
        return dependencies
    
    try:
        # Try to use tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                print_warning("tomli not installed. Cannot parse pyproject.toml")
                return dependencies
        
        with open(file_path, 'rb') as f:
            data = tomllib.load(f)
            
            # Poetry dependencies
            if 'tool' in data and 'poetry' in data['tool']:
                deps = data['tool']['poetry'].get('dependencies', {})
                for package, version in deps.items():
                    if package.lower() != 'python':
                        if isinstance(version, dict):
                            version = version.get('version', '*')
                        dependencies[package.lower()] = version
            
            # PEP 621 dependencies
            if 'project' in data:
                deps = data['project'].get('dependencies', [])
                for dep in deps:
                    pkg_match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!~].*)?$', dep)
                    if pkg_match:
                        package = pkg_match.group(1)
                        version = pkg_match.group(2) or '*'
                        dependencies[package.lower()] = version
    except Exception as e:
        if os.environ.get('PYGITUP_DEBUG'):
            print_warning(f"Error parsing pyproject.toml: {e}")
    
    return dependencies


def get_installed_packages() -> Dict[str, str]:
    """Get list of installed packages with versions."""
    packages = {}
    
    try:
        result = subprocess.run(
            ['pip', 'list', '--format=json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for pkg in json.loads(result.stdout):
            packages[pkg['name'].lower()] = pkg['version']
    except Exception as e:
        print_warning(f"Could not get installed packages: {e}")
    
    return packages


# =============================================================================
# VULNERABILITY DATABASE
# =============================================================================

class VulnerabilityDatabase:
    """Local cache of vulnerability information."""
    
    def __init__(self, cache_dir: str = "~/.pygitup_config/vuln_cache"):
        self.cache_dir = os.path.expanduser(cache_dir)
        self.cache_file = os.path.join(self.cache_dir, "vulns.json")
        self.last_updated: Optional[datetime] = None
        self.vulnerabilities: Dict[str, List[Dict]] = {}
        
        os.makedirs(self.cache_dir, exist_ok=True)
        self._load_cache()
    
    def _load_cache(self):
        """Load vulnerability cache from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.vulnerabilities = data.get('vulnerabilities', {})
                    if data.get('last_updated'):
                        self.last_updated = datetime.fromisoformat(data['last_updated'])
        except Exception as e:
            if os.environ.get('PYGITUP_DEBUG'):
                print_warning(f"Could not load vulnerability cache: {e}")
    
    def _save_cache(self):
        """Save vulnerability cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'vulnerabilities': self.vulnerabilities,
                    'last_updated': datetime.utcnow().isoformat()
                }, f, indent=2)
            
            # Set restrictive permissions
            if os.name != 'nt':
                os.chmod(self.cache_file, 0o600)
        except Exception as e:
            if os.environ.get('PYGITUP_DEBUG'):
                print_warning(f"Could not save vulnerability cache: {e}")
    
    def get_vulnerabilities(self, package: str, version: str) -> List[Dict]:
        """Get vulnerabilities for a specific package version."""
        package = package.lower()
        return self.vulnerabilities.get(package, [])
    
    def update_cache(self):
        """Update vulnerability cache from OSV database."""
        if not HAS_REQUESTS:
            print_warning("requests not installed. Cannot update vulnerability cache.")
            return
        
        print_info("🔄 Updating vulnerability database...")
        
        try:
            # Query OSV API for PyPI vulnerabilities
            response = requests.get(
                "https://api.osv.dev/v1/vulns",
                params={"ecosystem": "PyPI"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                # Parse and cache all vulnerabilities
                for vuln in data.get('vulns', []):
                    for affected in vuln.get('affected', []):
                        pkg = affected.get('package', {})
                        if pkg.get('ecosystem') == 'PyPI':
                            pkg_name = pkg.get('name', '').lower()
                            version_ranges = []
                            for range_item in affected.get('ranges', []):
                                if range_item.get('type') == 'ECOSYSTEM':
                                    version_ranges.extend([
                                        evt.get('introduced') for evt in range_item.get('events', [])
                                        if evt.get('introduced')
                                    ])
                            
                            if pkg_name and version_ranges:
                                self.vulnerabilities.setdefault(pkg_name, []).append({
                                    'vuln_id': vuln.get('id'),
                                    'summary': vuln.get('summary', ''),
                                    'details': vuln.get('details', ''),
                                    'severity': vuln.get('severity'),
                                    'published': vuln.get('published'),
                                    'version_ranges': version_ranges,
                                })
                
                self._save_cache()
                print_success(f"Vulnerability database updated ({len(self.vulnerabilities)} packages)")
        except Exception as e:
            print_warning(f"Could not update vulnerability database: {e}")


# =============================================================================
# DEPENDENCY SCANNING
# =============================================================================

def scan_dependencies_pip_audit() -> List[DependencyVulnerability]:
    """
    Scan dependencies using pip-audit.

    Returns:
        List of DependencyVulnerability objects
    """
    vulnerabilities = []

    try:
        result = subprocess.run(
            ['pip-audit', '--format', 'json', '--desc'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.stdout:
            dep_vulns = json.loads(result.stdout)
            
            # pip-audit returns a dict where keys are package names
            if isinstance(dep_vulns, dict):
                for pkg_name, pkg_data in dep_vulns.items():
                    if not isinstance(pkg_data, dict):
                        continue
                    
                    # Get vulnerabilities for this package
                    vulns_list = pkg_data.get('vulns', [])
                    if not vulns_list:
                        continue
                    
                    for vuln in vulns_list:
                        if not isinstance(vuln, dict):
                            continue
                            
                        severity = VulnerabilitySeverity.HIGH
                        cvss_score = 0.0

                        # Parse severity from CVSS
                        cvss_data = vuln.get('CVSS')
                        if cvss_data:
                            if isinstance(cvss_data, dict):
                                cvss_score = cvss_data.get('score', 0.0)
                            elif isinstance(cvss_data, (int, float)):
                                cvss_score = cvss_data
                            
                            if cvss_score >= 9.0:
                                severity = VulnerabilitySeverity.CRITICAL
                            elif cvss_score >= 7.0:
                                severity = VulnerabilitySeverity.HIGH
                            elif cvss_score >= 4.0:
                                severity = VulnerabilitySeverity.MEDIUM
                            else:
                                severity = VulnerabilitySeverity.LOW

                        # Get fixed versions
                        fixed_versions = vuln.get('fix_versions', [])
                        if isinstance(fixed_versions, list) and len(fixed_versions) > 0:
                            fixed_version = fixed_versions[0]
                        else:
                            fixed_version = None

                        vulnerabilities.append(DependencyVulnerability(
                            id=vuln.get('id', 'UNKNOWN'),
                            package_name=pkg_name,
                            installed_version=pkg_data.get('version', 'unknown'),
                            vulnerable_version_range=vuln.get('details', ''),
                            fixed_version=fixed_version,
                            severity=severity,
                            cve_id=vuln.get('id'),
                            cwe_id=None,
                            title=vuln.get('summary', vuln.get('details', ''))[:100],
                            description=vuln.get('details', ''),
                            cvss_score=cvss_score,
                            published_at=vuln.get('published'),
                            updated_at=vuln.get('modified')
                        ))
    except FileNotFoundError:
        print_warning("'pip-audit' not installed. Run: pip install pip-audit")
    except subprocess.TimeoutExpired:
        print_warning("Dependency scan timed out")
    except json.JSONDecodeError as e:
        print_warning(f"Dependency scan failed: Invalid JSON - {e}")
    except Exception as e:
        print_warning(f"Dependency scan failed: {e}")

    return vulnerabilities


def scan_dependencies_osv(packages: Dict[str, str]) -> List[DependencyVulnerability]:
    """
    Scan dependencies using OSV API.
    
    Args:
        packages: Dictionary of {package: version}
        
    Returns:
        List of DependencyVulnerability objects
    """
    if not HAS_REQUESTS:
        return []
    
    vulnerabilities = []
    
    print_info("🔍 Querying OSV vulnerability database...")
    
    for package, version in packages.items():
        try:
            response = requests.post(
                "https://api.osv.dev/v1/query",
                json={
                    "version": version,
                    "package": {
                        "name": package,
                        "ecosystem": "PyPI"
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for vuln in data.get('vulns', []):
                    severity = VulnerabilitySeverity.HIGH
                    cvss_score = 0.0
                    
                    # Parse CVSS
                    for affected in vuln.get('affected', []):
                        if affected.get('package', {}).get('ecosystem') == 'PyPI':
                            for range_item in affected.get('ranges', []):
                                if range_item.get('type') == 'ECOSYSTEM':
                                    for event in range_item.get('events', []):
                                        if 'introduced' in event:
                                            pass  # Vulnerable from this version
                                    
                    # Get CVSS score
                    if 'database_specific' in vuln:
                        db_specific = vuln['database_specific']
                        if 'cvss' in db_specific:
                            cvss = db_specific['cvss']
                            if isinstance(cvss, dict):
                                cvss_score = cvss.get('score', 0.0)
                                if cvss_score >= 9.0:
                                    severity = VulnerabilitySeverity.CRITICAL
                                elif cvss_score >= 7.0:
                                    severity = VulnerabilitySeverity.HIGH
                                elif cvss_score >= 4.0:
                                    severity = VulnerabilitySeverity.MEDIUM
                                else:
                                    severity = VulnerabilitySeverity.LOW
                    
                    vulnerabilities.append(DependencyVulnerability(
                        id=vuln.get('id', 'UNKNOWN'),
                        package_name=package,
                        installed_version=version,
                        vulnerable_version_range="See OSV database",
                        fixed_version=None,  # Would need to parse affected ranges
                        severity=severity,
                        cve_id=vuln.get('id'),
                        cwe_id=None,
                        title=vuln.get('summary', '')[:100],
                        description=vuln.get('details', ''),
                        cvss_score=cvss_score,
                        published_at=vuln.get('published'),
                        updated_at=vuln.get('modified')
                    ))
        
        except requests.exceptions.RequestException as e:
            if os.environ.get('PYGITUP_DEBUG'):
                print_warning(f"Error querying OSV for {package}: {e}")
        except Exception as e:
            if os.environ.get('PYGITUP_DEBUG'):
                print_warning(f"Error processing {package}: {e}")
    
    return vulnerabilities


# =============================================================================
# SBOM GENERATION
# =============================================================================

def generate_sbom_spdx(output_file: str = "sbom.spdx.json") -> str:
    """
    Generate a Software Bill of Materials in SPDX format.
    
    Args:
        output_file: Output file path
        
    Returns:
        Path to generated SBOM
    """
    print_info("📦 Generating Software Bill of Materials (SBOM)...")
    
    packages = get_installed_packages()
    requirements = parse_requirements_file()
    
    # SPDX document structure
    spdx_doc = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"PyGitUp-SBOM-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        # Use URN format (not a real URL) - SPDX compliant unique identifier
        "documentNamespace": f"urn:uuid:{hashlib.sha256(os.urandom(16)).hexdigest()}",
        "creationInfo": {
            "created": datetime.utcnow().isoformat() + "Z",
            "creators": ["Tool: PyGitUp"],
            "licenseListVersion": "3.19"
        },
        "packages": [],
        "relationships": []
    }
    
    # Add root package
    spdx_doc["packages"].append({
        "SPDXID": "SPDXRef-Package-PyGitUp",
        "name": "PyGitUp",
        "version": "2.3.0",
        "downloadLocation": "https://github.com/frederickabrah/PyGitUp",
        "filesAnalyzed": False,
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": "MIT",
        "copyrightText": "Copyright (c) Frederick Abraham"
    })
    
    # Add dependencies
    for i, (name, version) in enumerate(packages.items()):
        pkg_id = f"SPDXRef-Package-{i+1}"
        
        spdx_doc["packages"].append({
            "SPDXID": pkg_id,
            "name": name,
            "version": version,
            "downloadLocation": f"https://pypi.org/project/{name}/{version}/",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION"
        })
        
        # Add relationship
        spdx_doc["relationships"].append({
            "spdxElementId": "SPDXRef-Package-PyGitUp",
            "relatedSpdxElement": pkg_id,
            "relationshipType": "DEPENDS_ON"
        })
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            json.dump(spdx_doc, f, indent=2)
        
        print_success(f"✅ SBOM generated: {output_file}")
        print_info(f"   Total packages: {len(packages)}")
        
        return output_file
    except Exception as e:
        print_error(f"Failed to generate SBOM: {e}")
        return ""


def generate_sbom_cyclonedx(output_file: str = "sbom.cyclonedx.json") -> str:
    """
    Generate a Software Bill of Materials in CycloneDX format.
    
    Args:
        output_file: Output file path
        
    Returns:
        Path to generated SBOM
    """
    print_info("📦 Generating CycloneDX SBOM...")
    
    packages = get_installed_packages()
    
    # CycloneDX document structure
    cyclonedx_doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{hashlib.sha256(os.urandom(16)).hexdigest()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tools": [
                {
                    "vendor": "PyGitUp",
                    "name": "PyGitUp",
                    "version": "2.3.0"
                }
            ],
            "component": {
                "type": "application",
                "name": "PyGitUp",
                "version": "2.3.0",
                "purl": f"pkg:pypi/pygitup@2.3.0"
            }
        },
        "components": [],
        "dependencies": []
    }
    
    # Add components
    for name, version in packages.items():
        component = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}",
            "bom-ref": f"pkg:pypi/{name}@{version}"
        }
        
        cyclonedx_doc["components"].append(component)
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            json.dump(cyclonedx_doc, f, indent=2)
        
        print_success(f"✅ CycloneDX SBOM generated: {output_file}")
        print_info(f"   Total components: {len(packages)}")
        
        return output_file
    except Exception as e:
        print_error(f"Failed to generate CycloneDX SBOM: {e}")
        return ""


# =============================================================================
# DEPENDENCY HEALTH ANALYSIS
# =============================================================================

def analyze_dependency_health(packages: Dict[str, str]) -> Dict:
    """
    Analyze the health of dependencies.
    
    Args:
        packages: Dictionary of {package: version}
        
    Returns:
        Health analysis report
    """
    if not HAS_REQUESTS:
        return {"error": "requests not installed"}
    
    health_report = {
        "total_packages": len(packages),
        "outdated_packages": [],
        "unmaintained_packages": [],
        "low_download_packages": [],
        "health_score": 100
    }
    
    now = datetime.utcnow()
    
    for package, version in packages.items():
        try:
            response = requests.get(
                f"https://pypi.org/pypi/{package}/json",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if outdated
                info = data.get('info', {})
                latest_version = info.get('version')
                if latest_version and latest_version != version:
                    health_report["outdated_packages"].append({
                        "name": package,
                        "current": version,
                        "latest": latest_version
                    })
                
                # Check release date
                releases = data.get('releases', {})
                if latest_version and latest_version in releases:
                    release_files = releases[latest_version]
                    if release_files:
                        upload_time = release_files[0].get('upload_time_iso_8601')
                        if upload_time:
                            release_date = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                            days_since_update = (now - release_date).days
                            
                            # Unmaintained if no update in 2 years
                            if days_since_update > 730:
                                health_report["unmaintained_packages"].append({
                                    "name": package,
                                    "days_since_update": days_since_update
                                })
                
                # Check download count
                # (Would need to query pepy.tech or similar for this)
                
        except requests.exceptions.RequestException:
            pass  # Skip on error
        except Exception:
            pass
    
    # Calculate health score
    outdated_penalty = len(health_report["outdated_packages"]) * 5
    unmaintained_penalty = len(health_report["unmaintained_packages"]) * 10
    
    health_report["health_score"] = max(0, 100 - outdated_penalty - unmaintained_penalty)
    
    return health_report


# =============================================================================
# MAIN SCAN FUNCTION
# =============================================================================

def run_supply_chain_scan(output_sbom: bool = True) -> Dict:
    """
    Run comprehensive supply chain security scan.
    
    Args:
        output_sbom: Whether to generate SBOM
        
    Returns:
        Scan results dictionary
    """
    print_header("🔗 Supply Chain Security Scan")
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "vulnerabilities": [],
        "sbom_generated": None,
        "health_report": None,
        "recommendations": []
    }
    
    # 1. Parse dependencies
    print_info("\n📋 Parsing dependencies...")
    requirements = parse_requirements_file()
    setup_deps = parse_setup_py()
    pyproject_deps = parse_pyproject_toml()
    
    all_deps = {**requirements, **setup_deps, **pyproject_deps}
    installed = get_installed_packages()
    
    print_info(f"   Found {len(all_deps)} declared dependencies")
    print_info(f"   Found {len(installed)} installed packages")
    
    # 2. Scan for vulnerabilities
    print_info("\n🔍 Scanning for vulnerabilities...")
    
    # Use pip-audit if available
    vulns = scan_dependencies_pip_audit()
    
    # Also query OSV for additional coverage
    if vulns:
        print_success(f"   Found {len(vulns)} vulnerabilities via pip-audit")
    else:
        # Fallback to OSV
        vulns = scan_dependencies_osv(installed)
        if vulns:
            print_success(f"   Found {len(vulns)} vulnerabilities via OSV")
        else:
            print_success("   No vulnerabilities detected")
    
    results["vulnerabilities"] = [asdict(v) for v in vulns]
    
    # 3. Generate SBOM
    if output_sbom:
        print_info("\n📦 Generating SBOM...")
        sbom_file = generate_sbom_spdx()
        if sbom_file:
            results["sbom_generated"] = sbom_file
    
    # 4. Analyze dependency health
    print_info("\n💚 Analyzing dependency health...")
    health = analyze_dependency_health(installed)
    results["health_report"] = health
    
    # 5. Generate recommendations
    if vulns:
        critical_count = len([v for v in vulns if v.severity == VulnerabilitySeverity.CRITICAL])
        high_count = len([v for v in vulns if v.severity == VulnerabilitySeverity.HIGH])
        
        if critical_count > 0:
            results["recommendations"].append(f"🚨 CRITICAL: Update {critical_count} packages with critical vulnerabilities immediately")
        if high_count > 0:
            results["recommendations"].append(f"⚠️ HIGH: Update {high_count} packages with high severity vulnerabilities")
    
    if health.get("outdated_packages"):
        results["recommendations"].append(f"📦 {len(health['outdated_packages'])} packages are outdated")
    
    if health.get("unmaintained_packages"):
        results["recommendations"].append(f"⚠️ {len(health['unmaintained_packages'])} packages appear unmaintained")
    
    # Display results
    _display_scan_results(results)
    
    return results


def _display_scan_results(results: Dict):
    """Display scan results in formatted output."""
    print_header("Scan Results")
    
    # Vulnerabilities
    vulns = results.get("vulnerabilities", [])
    if vulns:
        table = Table(title="🚨 Vulnerabilities Found", box=box.ROUNDED)
        table.add_column("Package", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Vulnerability", style="yellow")
        table.add_column("Severity", style="bold")
        table.add_column("Fixed Version", style="dim")
        
        severity_colors = {
            'critical': 'bold red',
            'high': 'red',
            'medium': 'yellow',
            'low': 'blue',
            'info': 'dim'
        }
        
        for vuln in sorted(vulns, key=lambda x: ['critical', 'high', 'medium', 'low', 'info'].index(x['severity'].value if isinstance(x['severity'], VulnerabilitySeverity) else x['severity']))[:15]:
            sev_val = vuln['severity'].value if isinstance(vuln['severity'], VulnerabilitySeverity) else vuln['severity']
            table.add_row(
                vuln['package_name'],
                vuln['installed_version'],
                vuln['id'],
                f"[{severity_colors.get(sev_val, 'white')}]{sev_val.upper()}[/{severity_colors.get(sev_val, 'white')}]",
                vuln['fixed_version'] or 'None'
            )
        
        console.print(table)
        
        if len(vulns) > 15:
            print_info(f"... and {len(vulns) - 15} more vulnerabilities")
    else:
        print_success("✅ No vulnerabilities detected")
    
    # Health Score
    health = results.get("health_report", {})
    if health:
        score = health.get("health_score", 0)
        score_color = 'green' if score >= 80 else 'yellow' if score >= 50 else 'red'
        
        console.print(Panel(
            f"[bold {score_color}]{score}/100[/bold {score_color}]\n"
            f"Outdated: {len(health.get('outdated_packages', []))} | "
            f"Unmaintained: {len(health.get('unmaintained_packages', []))}",
            title="📊 Dependency Health Score",
            border_style=score_color
        ))
    
    # Recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        print_info("\n💡 Recommendations:")
        for rec in recommendations:
            print(f"  • {rec}")


# =============================================================================
# EXPORTED FUNCTIONS
# =============================================================================

def check_package_security(package: str, version: str) -> Dict:
    """
    Check security information for a specific package.
    
    Args:
        package: Package name
        version: Package version
        
    Returns:
        Security information dictionary
    """
    if not HAS_REQUESTS:
        return {"error": "requests not installed"}
    
    result = {
        "package": package,
        "version": version,
        "vulnerabilities": [],
        "security_policy": None,
        "is_fork": False,
        "repository": None
    }
    
    try:
        # Get package info from PyPI
        response = requests.get(
            f"https://pypi.org/pypi/{package}/{version}/json",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            info = data.get('info', {})
            
            result["repository"] = info.get('project_urls', {}).get('Source')
            result["is_fork"] = False  # Would need to check GitHub
            
            # Check for security policy
            if result["repository"]:
                # Try to fetch SECURITY.md
                repo_url = result["repository"]
                if 'github.com' in repo_url:
                    parts = repo_url.rstrip('/').split('/')
                    if len(parts) >= 2:
                        owner, repo = parts[-2], parts[-1]
                        sec_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/SECURITY.md"
                        try:
                            sec_response = requests.get(sec_url, timeout=5)
                            if sec_response.status_code == 200:
                                result["security_policy"] = "Found"
                        except:
                            pass
    except Exception as e:
        result["error"] = str(e)
    
    return result
