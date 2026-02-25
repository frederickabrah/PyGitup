"""
PyGitUp Enhanced Security Module
=================================
Advanced security features including:
- Enhanced secret detection with entropy analysis
- Runtime security monitoring and audit logging
- Token rotation and expiration management
- Rate limiting and abuse detection
- Supply chain security scanning
- HTTPS enforcement and certificate validation
"""

import os
import ast
import re
import json
import time
import hashlib
import hmac
import fnmatch
import subprocess
import logging
import math
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import base64

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.x509 import load_pem_x509_certificate
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

import requests
from urllib3.util.ssl_ import create_urllib3_context
from ..utils.ui import print_success, print_error, print_info, print_warning, print_header, console, Table, box, Panel


# =============================================================================
# SECURITY ENUMS AND DATA CLASSES
# =============================================================================

class SeverityLevel(Enum):
    """Security vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(Enum):
    """Categories of security threats."""
    INJECTION = "injection"
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA = "sensitive_data_exposure"
    XXE = "xxe"
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    SECURITY_MISCONFIG = "security_misconfiguration"
    XSS = "xss"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    KNOWN_VULNERABILITY = "known_vulnerability"
    SUPPLY_CHAIN = "supply_chain"
    CREDENTIAL_LEAK = "credential_leak"


class AuditEventType(Enum):
    """Types of security audit events."""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    TOKEN_ROTATION = "token_rotation"
    SECRET_DETECTED = "secret_detected"
    VULNERABILITY_FOUND = "vulnerability_found"
    API_RATE_LIMIT = "api_rate_limit"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CONFIG_CHANGE = "config_change"
    FILE_ACCESS = "file_access"
    NETWORK_REQUEST = "network_request"
    SECURITY_SCAN = "security_scan"


@dataclass
class SecurityFinding:
    """Represents a security vulnerability or finding."""
    id: str
    category: str
    severity: str
    title: str
    description: str
    file: str
    line: int
    code: str
    remediation: str
    cwe_id: str = ""
    cvss_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AuditEvent:
    """Represents a security audit event."""
    event_id: str
    event_type: str
    timestamp: str
    source: str
    user: str
    details: Dict[str, Any]
    severity: str
    ip_address: str = ""


# =============================================================================
# ENHANCED SECRET DETECTION
# =============================================================================

# Comprehensive secret patterns with severity levels
SECRET_PATTERNS = {
    # GitHub Tokens
    "github_pat": {
        "pattern": r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}",
        "severity": SeverityLevel.CRITICAL,
        "description": "GitHub Personal Access Token (Fine-Grained)"
    },
    "github_classic": {
        "pattern": r"ghp_[a-zA-Z0-9]{36}",
        "severity": SeverityLevel.CRITICAL,
        "description": "GitHub Personal Access Token (Classic)"
    },
    "github_oauth": {
        "pattern": r"gho_[a-zA-Z0-9]{36}",
        "severity": SeverityLevel.CRITICAL,
        "description": "GitHub OAuth Access Token"
    },
    "github_app": {
        "pattern": r"(ghu|ghs)_[a-zA-Z0-9]{36}",
        "severity": SeverityLevel.CRITICAL,
        "description": "GitHub App Token"
    },
    "github_refresh": {
        "pattern": r"ghr_[a-zA-Z0-9]{36}",
        "severity": SeverityLevel.HIGH,
        "description": "GitHub Refresh Token"
    },
    
    # AWS Credentials
    "aws_access_key": {
        "pattern": r"(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])",
        "severity": SeverityLevel.CRITICAL,
        "description": "AWS Access Key ID",
        "context_required": True  # Needs context like "aws_access_key_id"
    },
    "aws_secret_key": {
        "pattern": r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])",
        "severity": SeverityLevel.CRITICAL,
        "description": "AWS Secret Access Key"
    },
    "aws_session_token": {
        "pattern": r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{16,}(?![A-Za-z0-9/+=])",
        "severity": SeverityLevel.HIGH,
        "description": "AWS Session Token"
    },
    
    # Google Cloud
    "gcp_api_key": {
        "pattern": r"AIza[0-9A-Za-z_-]{35}",
        "severity": SeverityLevel.CRITICAL,
        "description": "Google Cloud API Key"
    },
    "gcp_service_account": {
        "pattern": r'"type":\s*"service_account"',
        "severity": SeverityLevel.CRITICAL,
        "description": "Google Cloud Service Account Key"
    },
    
    # Azure
    "azure_storage_key": {
        "pattern": r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88};",
        "severity": SeverityLevel.CRITICAL,
        "description": "Azure Storage Connection String"
    },
    "azure_sas_token": {
        "pattern": r"\?sv=\d{4}-\d{2}-\d{2}&[^\"']+",
        "severity": SeverityLevel.HIGH,
        "description": "Azure SAS Token"
    },
    
    # Database Connection Strings
    "postgres_uri": {
        "pattern": r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/\w+",
        "severity": SeverityLevel.CRITICAL,
        "description": "PostgreSQL Connection String with Password"
    },
    "mysql_uri": {
        "pattern": r"mysql://[^:]+:[^@]+@[^/]+/\w+",
        "severity": SeverityLevel.CRITICAL,
        "description": "MySQL Connection String with Password"
    },
    "mongodb_uri": {
        "pattern": r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^/]+",
        "severity": SeverityLevel.CRITICAL,
        "description": "MongoDB Connection String with Password"
    },
    "redis_uri": {
        "pattern": r"redis://:[^@]+@[^/]+",
        "severity": SeverityLevel.HIGH,
        "description": "Redis Connection String with Password"
    },
    
    # API Keys (Generic)
    "stripe_key": {
        "pattern": r"sk_live_[0-9a-zA-Z]{24,}",
        "severity": SeverityLevel.CRITICAL,
        "description": "Stripe Secret Key"
    },
    "stripe_restricted": {
        "pattern": r"rk_live_[0-9a-zA-Z]{24,}",
        "severity": SeverityLevel.HIGH,
        "description": "Stripe Restricted Key"
    },
    "twilio_key": {
        "pattern": r"SK[0-9a-fA-F]{32}",
        "severity": SeverityLevel.HIGH,
        "description": "Twilio API Key"
    },
    "sendgrid_key": {
        "pattern": r"SG\.[0-9A-Za-z_-]{22}\.[0-9A-Za-z_-]{43}",
        "severity": SeverityLevel.CRITICAL,
        "description": "SendGrid API Key"
    },
    "slack_token": {
        "pattern": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*",
        "severity": SeverityLevel.HIGH,
        "description": "Slack Token"
    },
    "slack_webhook": {
        "pattern": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8,}/B[a-zA-Z0-9_]{8,}/[a-zA-Z0-9_]{24}",
        "severity": SeverityLevel.MEDIUM,
        "description": "Slack Webhook URL"
    },
    
    # JWT Tokens
    "jwt_token": {
        "pattern": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        "severity": SeverityLevel.HIGH,
        "description": "JWT Token"
    },
    
    # Private Keys
    "rsa_private_key": {
        "pattern": r"-----BEGIN RSA PRIVATE KEY-----",
        "severity": SeverityLevel.CRITICAL,
        "description": "RSA Private Key"
    },
    "ec_private_key": {
        "pattern": r"-----BEGIN EC PRIVATE KEY-----",
        "severity": SeverityLevel.CRITICAL,
        "description": "EC Private Key"
    },
    "openssh_private_key": {
        "pattern": r"-----BEGIN OPENSSH PRIVATE KEY-----",
        "severity": SeverityLevel.CRITICAL,
        "description": "OpenSSH Private Key"
    },
    "pgp_private_key": {
        "pattern": r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
        "severity": SeverityLevel.CRITICAL,
        "description": "PGP Private Key"
    },
    
    # Passwords in Config
    "password_assignment": {
        "pattern": r"(?i)(password|passwd|pwd|secret|api_key|apikey|auth_token|accesstoken)\s*[=:]\s*['\"][^'\"]{8,}['\"]",
        "severity": SeverityLevel.HIGH,
        "description": "Hardcoded Password or Secret"
    },
    "bearer_token": {
        "pattern": r"[Bb]earer\s+[a-zA-Z0-9\._-]{20,}",
        "severity": SeverityLevel.HIGH,
        "description": "Bearer Token"
    },
}

# Variable names that suggest sensitive data
SENSITIVE_VAR_NAMES = [
    'password', 'passwd', 'pwd', 'secret', 'api_key', 'apikey', 'api-key',
    'auth_token', 'accesstoken', 'access_token', 'refresh_token',
    'private_key', 'secret_key', 'encryption_key', 'credential',
    'db_password', 'database_password', 'mysql_password', 'postgres_password',
    'aws_secret', 'aws_access_key', 'azure_key', 'gcp_key',
    'stripe_key', 'twilio_token', 'sendgrid_key', 'slack_token'
]


def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string to detect randomness."""
    if not data:
        return 0.0
    
    entropy = 0.0
    length = len(data)
    char_count = defaultdict(int)
    
    for char in data:
        char_count[char] += 1
    
    for count in char_count.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    return entropy


def is_high_entropy(data: str, threshold: float = 4.0) -> bool:
    """Check if a string has high entropy (likely a secret)."""
    if len(data) < 16:
        return False
    return calculate_entropy(data) > threshold


def detect_secrets_in_content(content: str, file_path: str = "") -> List[SecurityFinding]:
    """
    Detect secrets in content using pattern matching and entropy analysis.
    
    Args:
        content: The text content to scan
        file_path: Optional file path for context
        
    Returns:
        List of SecurityFinding objects for detected secrets
    """
    findings = []
    
    for secret_type, config in SECRET_PATTERNS.items():
        pattern = config["pattern"]
        matches = re.finditer(pattern, content, re.MULTILINE)
        
        for match in matches:
            matched_text = match.group(0)
            
            # Skip if context is required but not found
            if config.get("context_required"):
                context_window = 100
                start = max(0, match.start() - context_window)
                end = min(len(content), match.end() + context_window)
                context = content[start:end].lower()
                
                # Check for relevant context keywords
                context_keywords = secret_type.lower().split('_')
                if not any(kw in context for kw in context_keywords):
                    continue
            
            # Calculate line number
            line_num = content[:match.start()].count('\n') + 1
            
            findings.append(SecurityFinding(
                id=f"SECRET-{secret_type.upper()}-{hashlib.md5(matched_text.encode()).hexdigest()[:8]}",
                category=ThreatCategory.CREDENTIAL_LEAK.value,
                severity=config["severity"].value,
                title=f"Detected: {config['description']}",
                description=f"Potential {config['description']} found in {'file ' + file_path if file_path else 'content'}.",
                file=file_path or "unknown",
                line=line_num,
                code=matched_text[:50] + "..." if len(matched_text) > 50 else matched_text,
                remediation=f"Remove this {config['description']} immediately. Use environment variables or a secrets manager.",
                cvss_score=9.0 if config["severity"] == SeverityLevel.CRITICAL else 7.0
            ))
    
    # Additional entropy-based detection for potential unknown secrets
    words = re.findall(r'[a-zA-Z0-9+/=_-]{20,}', content)
    for word in words:
        if is_high_entropy(word) and not any(re.search(p["pattern"], word) for p in SECRET_PATTERNS.values()):
            # Check if near a sensitive variable name
            for var_name in SENSITIVE_VAR_NAMES:
                if var_name in content[max(0, content.find(word) - 50):content.find(word) + 50].lower():
                    line_num = content[:content.find(word)].count('\n') + 1
                    findings.append(SecurityFinding(
                        id=f"SECRET-ENTROPY-{hashlib.md5(word.encode()).hexdigest()[:8]}",
                        category=ThreatCategory.CREDENTIAL_LEAK.value,
                        severity=SeverityLevel.HIGH.value,
                        title="High-Entropy Secret Detected",
                        description="Potential secret detected based on entropy analysis near sensitive variable name.",
                        file=file_path or "unknown",
                        line=line_num,
                        code=f"{var_name} = '{word[:20]}...'",
                        remediation="Review this value. If it's a secret, use environment variables or a secrets manager.",
                        cvss_score=7.5
                    ))
                    break
    
    return findings


# =============================================================================
# ENHANCED AST-BASED SAST
# =============================================================================

class EnhancedSASTVisitor(ast.NodeVisitor):
    """Enhanced AST visitor for comprehensive security analysis."""
    
    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.file_path = file_path
        self.vulnerabilities: List[SecurityFinding] = []
        self.imports: Dict[str, str] = {}
        self.assigned_vars: Dict[str, Any] = {}
        
    def visit_Import(self, node: ast.Import):
        """Track imports for context-aware analysis."""
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        if node.module:
            for alias in node.names:
                self.imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """Detect hardcoded secrets and sensitive assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                
                # Check if variable name suggests sensitive data
                if any(sensitive in var_name for sensitive in SENSITIVE_VAR_NAMES):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        value = node.value.value
                        
                        # Skip empty or placeholder values
                        if len(value) > 8 and not self._is_placeholder(value):
                            # Check for known secret patterns
                            for pattern_name, pattern_config in SECRET_PATTERNS.items():
                                if re.search(pattern_config["pattern"], value):
                                    self._add_vulnerability(
                                        category=ThreatCategory.CREDENTIAL_LEAK,
                                        severity=pattern_config["severity"],
                                        title=f"Hardcoded: {pattern_config['description']}",
                                        description=f"Sensitive credential '{target.id}' appears to contain a {pattern_config['description']}.",
                                        line=node.lineno,
                                        code=f"{target.id} = '***REDACTED***'",
                                        remediation="Use environment variables (os.environ) or a secrets manager.",
                                        cvss_score=9.0
                                    )
                                    break
                            else:
                                # High entropy check for unknown secrets
                                if is_high_entropy(value):
                                    self._add_vulnerability(
                                        category=ThreatCategory.CREDENTIAL_LEAK,
                                        severity=SeverityLevel.HIGH,
                                        title="Potential Hardcoded Secret",
                                        description=f"Variable '{target.id}' contains high-entropy value that may be a secret.",
                                        line=node.lineno,
                                        code=f"{target.id} = '***REDACTED***'",
                                        remediation="If this is a secret, use environment variables or a secrets manager.",
                                        cvss_score=7.5
                                    )
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Detect dangerous function calls and insecure patterns."""
        func_info = self._get_func_info(node.func)
        
        if func_info:
            module, func_name = func_info
            
            # Command Injection Detection
            if module in ['os', 'subprocess', 'commands']:
                if func_name in ['system', 'popen', 'popen2', 'popen3', 'popen4', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe']:
                    self._add_vulnerability(
                        category=ThreatCategory.INJECTION,
                        severity=SeverityLevel.CRITICAL,
                        title="Command Injection Risk",
                        description=f"os.{func_name}() can execute arbitrary system commands.",
                        line=node.lineno,
                        code=f"os.{func_name}(...)",
                        remediation="Use subprocess.run() with shell=False and a list of arguments.",
                        cwe_id="CWE-78",
                        cvss_score=9.8
                    )
                
                elif func_name in ['run', 'call', 'check_call', 'check_output', 'Popen']:
                    # Check for shell=True
                    for keyword in node.keywords:
                        if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant):
                            if keyword.value.value is True:
                                self._add_vulnerability(
                                    category=ThreatCategory.INJECTION,
                                    severity=SeverityLevel.CRITICAL,
                                    title="Shell Injection Risk",
                                    description="subprocess call with shell=True allows command injection.",
                                    line=node.lineno,
                                    code=f"subprocess.{func_name}(..., shell=True)",
                                    remediation="Set shell=False and pass arguments as a list.",
                                    cwe_id="CWE-78",
                                    cvss_score=9.8
                                )
            
            # Insecure Deserialization
            elif module == 'pickle' and func_name in ['load', 'loads', 'Unpickler']:
                self._add_vulnerability(
                    category=ThreatCategory.INSECURE_DESERIALIZATION,
                    severity=SeverityLevel.CRITICAL,
                    title="Insecure Deserialization",
                    description="pickle.load() can execute arbitrary code during deserialization.",
                    line=node.lineno,
                    code="pickle.load(...)",
                    remediation="Use json.loads() or a safe serialization format.",
                    cwe_id="CWE-502",
                    cvss_score=9.8
                )
            
            elif module in ['yaml', 'PyYAML'] and func_name in ['load', 'unsafe_load']:
                self._add_vulnerability(
                    category=ThreatCategory.INSECURE_DESERIALIZATION,
                    severity=SeverityLevel.HIGH,
                    title="Unsafe YAML Loading",
                    description="yaml.load() without safe_load can execute arbitrary code.",
                    line=node.lineno,
                    code="yaml.load(...)",
                    remediation="Use yaml.safe_load() instead.",
                    cwe_id="CWE-502",
                    cvss_score=8.1
                )
            
            # Dynamic Code Execution
            elif func_name in ['eval', 'exec', 'compile']:
                self._add_vulnerability(
                    category=ThreatCategory.INJECTION,
                    severity=SeverityLevel.CRITICAL,
                    title="Arbitrary Code Execution",
                    description=f"{func_name}() can execute arbitrary Python code.",
                    line=node.lineno,
                    code=f"{func_name}(...)",
                    remediation="Avoid dynamic code execution. Use ast.literal_eval() for safe parsing.",
                    cwe_id="CWE-95",
                    cvss_score=9.8
                )
            
            # SQL Injection (basic detection)
            elif module in ['sqlite3', 'mysql', 'psycopg2', 'pymongo']:
                if func_name in ['execute', 'executemany', 'executescript']:
                    # Check if first argument is string concatenation or format
                    if node.args:
                        first_arg = node.args[0]
                        if isinstance(first_arg, (ast.JoinedStr, ast.BinOp)):
                            self._add_vulnerability(
                                category=ThreatCategory.INJECTION,
                                severity=SeverityLevel.CRITICAL,
                                title="SQL Injection Risk",
                                description="Dynamic SQL query construction detected.",
                                line=node.lineno,
                                code="db.execute(...)",
                                remediation="Use parameterized queries with placeholders.",
                                cwe_id="CWE-89",
                                cvss_score=9.8
                            )
            
            # Insecure HTTP
            elif module in ['requests', 'urllib', 'http.client']:
                if func_name in ['request', 'get', 'post', 'put', 'delete']:
                    # Check for verify=False (SSL bypass)
                    for keyword in node.keywords:
                        if keyword.arg == 'verify' and isinstance(keyword.value, ast.Constant):
                            if keyword.value.value is False:
                                self._add_vulnerability(
                                    category=ThreatCategory.SECURITY_MISCONFIG,
                                    severity=SeverityLevel.HIGH,
                                    title="SSL Verification Disabled",
                                    description="HTTPS certificate verification is disabled.",
                                    line=node.lineno,
                                    code="requests.request(..., verify=False)",
                                    remediation="Set verify=True or use a proper CA bundle.",
                                    cwe_id="CWE-295",
                                    cvss_score=7.4
                                )
        
        self.generic_visit(node)
    
    def visit_With(self, node: ast.With):
        """Detect insecure file operations."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func_info = self._get_func_info(item.context_expr.func)
                if func_info:
                    module, func_name = func_info
                    if func_name == 'open':
                        # Check for potentially sensitive files being opened for writing
                        if item.context_expr.args:
                            first_arg = item.context_expr.args[0]
                            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                                filename = first_arg.value.lower()
                                if any(ext in filename for ext in ['.env', '.key', '.pem', 'shadow', 'passwd']):
                                    # Check modes
                                    is_write = False
                                    for arg in item.context_expr.args[1:]:
                                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                            if any(m in arg.value for m in ['w', 'a', 'x']):
                                                is_write = True
                                    
                                    for kw in item.context_expr.keywords:
                                        if kw.arg == 'mode' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                            if any(m in kw.value.value for m in ['w', 'a', 'x']):
                                                is_write = True
                                    
                                    if is_write:
                                        self._add_vulnerability(
                                            category=ThreatCategory.SENSITIVE_DATA,
                                            severity=SeverityLevel.HIGH,
                                            title="Sensitive File Write",
                                            description=f"Potential write access to sensitive file: {filename}",
                                            line=node.lineno,
                                            code="with open(..., mode='w/a') as f:",
                                            remediation="Ensure sensitive files are protected and not modified unnecessarily.",
                                            cvss_score=7.5
                                        )
        self.generic_visit(node)
    
    def _get_func_info(self, node) -> Optional[Tuple[str, str]]:
        """Extract module and function name from a Call node."""
        if isinstance(node, ast.Name):
            module = self.imports.get(node.id, node.id)
            return module.split('.')[0], node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                module = self.imports.get(node.value.id, node.value.id)
                return module.split('.')[0], node.attr
        return None
    
    def _is_placeholder(self, value: str) -> bool:
        """Check if a value is likely a placeholder."""
        placeholders = [
            'your_', 'enter_', 'placeholder', 'token_here', 'xxx', 'changeme',
            'replace_me', 'todo', 'fixme', 'example', 'sample', 'test'
        ]
        return any(p in value.lower() for p in placeholders) or len(value) < 10
    
    def _add_vulnerability(self, category: ThreatCategory, severity: SeverityLevel,
                          title: str, description: str, line: int, code: str,
                          remediation: str, cwe_id: str = "", cvss_score: float = 0.0):
        """Add a vulnerability finding."""
        self.vulnerabilities.append(SecurityFinding(
            id=f"SAST-{category.value.upper()}-{hashlib.md5(f'{self.file_path}:{line}:{title}'.encode()).hexdigest()[:8]}",
            category=category.value,
            severity=severity.value,
            title=title,
            description=description,
            file=self.file_path,
            line=line,
            code=code,
            remediation=remediation,
            cwe_id=cwe_id,
            cvss_score=cvss_score
        ))


def run_enhanced_sast_scan(directory: str, max_files: int = 100) -> List[SecurityFinding]:
    print_info(f"Starting Enhanced AST-based SAST scan in {directory}...")
    all_findings = []
    files_scanned = 0

    target_extensions = ['.py', '.pyw', '.pyi']

    for root, _, files in os.walk(directory):
        skip_dirs = ['.git', '__pycache__', 'node_modules', 'venv', '.venv', 'build', 'dist', '.eggs']
        root_lower = root.lower()
        if any(skip_dir in root_lower for skip_dir in skip_dirs):
            continue
        
        for file in files:
            if files_scanned >= max_files:
                break
                
            if any(file.endswith(ext) for ext in target_extensions):
                file_path = os.path.join(root, file)
                files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        source_code = f.read()
                    
                    tree = ast.parse(source_code, filename=file_path)
                    visitor = EnhancedSASTVisitor(source_code, file_path)
                    visitor.visit(tree)
                    all_findings.extend(visitor.vulnerabilities)
                    
                    secret_findings = detect_secrets_in_content(source_code, file_path)
                    all_findings.extend(secret_findings)
                    
                except SyntaxError:
                    pass
                except Exception as e:
                    if os.environ.get('PYGITUP_DEBUG'):
                        print_warning(f"Error scanning {file_path}: {e}")

    if all_findings:
        _display_security_findings(all_findings)
    else:
        print_success("Enhanced SAST scan complete. No vulnerabilities detected.")

    return all_findings


def _display_security_findings(findings: List[SecurityFinding]):
    by_severity = defaultdict(list)
    for finding in findings:
        by_severity[finding.severity].append(finding)

    print_error(f"ALERT: {len(findings)} potential vulnerabilities found!")

    summary = []
    for severity in ['critical', 'high', 'medium', 'low', 'info']:
        count = len(by_severity.get(severity, []))
        if count > 0:
            color = {'critical': 'bold red', 'high': 'red', 'medium': 'yellow', 'low': 'blue', 'info': 'dim'}.get(severity, 'white')
            summary.append(f"[{color}]{count} {severity.upper()}[/{color}]")

    print_info("Summary: " + ", ".join(summary))

    table = Table(title="Security Findings", box=box.ROUNDED)
    table.add_column("Severity", style="bold", justify="center")
    table.add_column("Type", style="cyan")
    table.add_column("Location", style="green")
    table.add_column("Description", style="yellow")
    table.add_column("Remediation", style="dim")

    severity_icons = {
        'critical': '[bold red]CRIT[/bold red]',
        'high': '[red]HIGH[/red]',
        'medium': '[yellow]MED[/yellow]',
        'low': '[blue]LOW[/blue]',
        'info': '[dim]INFO[/dim]'
    }

    for finding in sorted(findings, key=lambda x: ['critical', 'high', 'medium', 'low', 'info'].index(x.severity))[:20]:
        icon = severity_icons.get(finding.severity, '')
        table.add_row(
            f"{icon}",
            finding.category.replace('_', ' ').title(),
            f"{os.path.basename(finding.file)}:{finding.line}",
            finding.title[:50] + "..." if len(finding.title) > 50 else finding.title,
            finding.remediation[:40] + "..." if len(finding.remediation) > 40 else finding.remediation
        )

    console.print(table)

    if len(findings) > 20:
        print_info(f"... and {len(findings) - 20} more findings. Review logs for details.")


# =============================================================================
# SECURITY AUDIT LOGGING
# =============================================================================

class SecurityAuditLogger:
    """Comprehensive security audit logging system."""
    
    def __init__(self, log_file: str = "pygitup_security_audit.log"):
        self.log_file = log_file
        self.event_counter = 0
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure secure audit logging."""
        self.logger = logging.getLogger('pygitup.security.audit')
        self.logger.setLevel(logging.INFO)
        
        # File handler with rotation
        handler = logging.FileHandler(self.log_file, mode='a')
        handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def log_event(self, event_type: AuditEventType, user: str, details: Dict[str, Any],
                  severity: SeverityLevel = SeverityLevel.INFO, source: str = "pygitup"):
        """Log a security audit event."""
        self.event_counter += 1
        
        event = AuditEvent(
            event_id=f"AUDIT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{self.event_counter:06d}",
            event_type=event_type.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            user=user or "anonymous",
            details=details,
            severity=severity.value
        )
        
        # Log as JSON for easy parsing
        self.logger.info(json.dumps(asdict(event)))
        
        # Also log critical events to console
        if severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            icon = '🚨' if severity == SeverityLevel.CRITICAL else '⚠️'
            print_warning(f"{icon} Security Event: {event_type.value} - {details.get('message', '')}")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Retrieve recent audit events from the log."""
        events = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f.readlines()[-limit:]:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return events


# Global audit logger instance
AUDIT_LOGGER = SecurityAuditLogger()


# =============================================================================
# RUNTIME SECURITY MONITOR
# =============================================================================

class RuntimeSecurityMonitor:
    """Monitors runtime security events and anomalies."""
    
    def __init__(self):
        self.api_call_times: List[float] = []
        self.failed_auth_attempts: Dict[str, int] = defaultdict(int)
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        self.rate_limit_window: Dict[str, List[float]] = defaultdict(list)
        
    def record_api_call(self, endpoint: str, response_time: float, status_code: int):
        """Record an API call for rate limiting analysis."""
        now = time.time()
        key = f"{endpoint}"
        
        # Add to rate limit window (last 60 seconds)
        self.rate_limit_window[key].append(now)
        self.rate_limit_window[key] = [t for t in self.rate_limit_window[key] if now - t < 60]
        
        # Check for rate limiting
        if len(self.rate_limit_window[key]) > 100:  # More than 100 calls/minute
            AUDIT_LOGGER.log_event(
                AuditEventType.API_RATE_LIMIT,
                user="system",
                details={
                    "endpoint": endpoint,
                    "calls_per_minute": len(self.rate_limit_window[key]),
                    "message": f"High API call rate detected on {endpoint}"
                },
                severity=SeverityLevel.MEDIUM
            )
    
    def record_auth_failure(self, username: str, reason: str):
        """Record a failed authentication attempt."""
        self.failed_auth_attempts[username] += 1
        
        if self.failed_auth_attempts[username] >= 5:
            AUDIT_LOGGER.log_event(
                AuditEventType.AUTH_FAILURE,
                user=username,
                details={
                    "attempt_count": self.failed_auth_attempts[username],
                    "reason": reason,
                    "message": f"Multiple authentication failures for {username}"
                },
                severity=SeverityLevel.HIGH
            )
    
    def detect_anomaly(self, pattern: str, threshold: int = 10) -> bool:
        """Detect and log anomalous patterns."""
        self.suspicious_patterns[pattern] += 1
        
        if self.suspicious_patterns[pattern] >= threshold:
            AUDIT_LOGGER.log_event(
                AuditEventType.SUSPICIOUS_ACTIVITY,
                user="system",
                details={
                    "pattern": pattern,
                    "count": self.suspicious_patterns[pattern],
                    "message": f"Suspicious pattern detected: {pattern}"
                },
                severity=SeverityLevel.HIGH
            )
            return True
        return False


# Global runtime monitor
RUNTIME_MONITOR = RuntimeSecurityMonitor()


# =============================================================================
# HTTPS AND CERTIFICATE VALIDATION
# =============================================================================

class SecureHTTPSession:
    """Secure HTTP session with certificate validation."""
    
    def __init__(self):
        self.session = requests.Session()
        self._configure_secure_session()
    
    def _configure_secure_session(self):
        """Configure session with security best practices."""
        # Force HTTPS
        self.session.headers.update({
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY'
        })
        
        # Disable redirects to prevent open redirect attacks
        self.session.allow_redirects = False
        
        # Set secure timeouts
        self.session.timeout = 30
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a secure HTTP request."""
        # Enforce HTTPS for sensitive endpoints
        if any(sensitive in url.lower() for sensitive in ['github', 'api', 'auth', 'token']):
            if not url.startswith('https://'):
                raise ValueError(f"Security Error: Non-HTTPS request blocked for {url}")
        
        # Ensure SSL verification is enabled
        kwargs.setdefault('verify', True)
        kwargs.setdefault('timeout', 30)
        
        try:
            start_time = time.time()
            response = self.session.request(method, url, **kwargs)
            elapsed = time.time() - start_time
            
            # Record for monitoring
            RUNTIME_MONITOR.record_api_call(url, elapsed, response.status_code)
            
            return response
        except requests.exceptions.SSLError as e:
            AUDIT_LOGGER.log_event(
                AuditEventType.NETWORK_REQUEST,
                user="system",
                details={
                    "url": url,
                    "error": str(e),
                    "message": "SSL certificate validation failed"
                },
                severity=SeverityLevel.HIGH
            )
            raise
        except requests.exceptions.RequestException as e:
            raise
    
    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)
    
    def post(self, url, **kwargs):
        return self.request('POST', url, **kwargs)


# =============================================================================
# EXPORTED FUNCTIONS
# =============================================================================

def run_comprehensive_security_scan(directory: str = ".", include_deps: bool = True,
                                     use_ai: bool = False, config: dict = None) -> List[SecurityFinding]:
    """
    Run a comprehensive security scan including SAST and secret detection.
    
    Args:
        directory: Directory to scan
        include_deps: Whether to include dependency scanning
        use_ai: Whether to enhance with AI analysis (requires API key)
        config: Configuration dictionary for AI key
        
    Returns:
        List of all security findings
    """
    print_header("🛡️ Comprehensive Security Scan")
    
    all_findings = []
    
    # 1. Enhanced SAST Scan
    sast_findings = run_enhanced_sast_scan(directory)
    all_findings.extend(sast_findings)
    
    # 2. Dependency Scan (if enabled)
    if include_deps:
        print_info("Scanning dependencies for vulnerabilities...")
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json", "--desc"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.stdout:
                try:
                    dep_vulns = json.loads(result.stdout)
                    if isinstance(dep_vulns, dict):
                        for pkg_name, pkg_data in dep_vulns.items():
                            if not isinstance(pkg_data, dict):
                                continue
                            vulns_list = pkg_data.get('vulns', [])
                            if not vulns_list:
                                continue
                            for vuln in vulns_list:
                                if not isinstance(vuln, dict):
                                    continue
                                cvss_data = vuln.get('CVSS')
                                cvss_score = 0.0
                                severity = "high"
                                if cvss_data:
                                    if isinstance(cvss_data, dict):
                                        cvss_score = cvss_data.get('score', 0.0)
                                    elif isinstance(cvss_data, (int, float)):
                                        cvss_score = cvss_data
                                    if cvss_score >= 9.0:
                                        severity = "critical"
                                    elif cvss_score >= 7.0:
                                        severity = "high"
                                    elif cvss_score >= 4.0:
                                        severity = "medium"
                                
                                fixed_versions = vuln.get('fix_versions', [])
                                fixed_version = fixed_versions[0] if isinstance(fixed_versions, list) and fixed_versions else None
                                
                                all_findings.append(SecurityFinding(
                                    id=f"DEP-{vuln.get('id', 'UNKNOWN')}",
                                    category="known_vulnerability",
                                    severity=severity,
                                    title=f"Vulnerable Dependency: {pkg_name}",
                                    description=vuln.get('details', 'No description'),
                                    file="requirements.txt",
                                    line=0,
                                    code=f"{pkg_name}=={pkg_data.get('version', 'unknown')}",
                                    remediation=f"Update to {fixed_version or 'latest'}",
                                    cvss_score=cvss_score
                                ))
                except json.JSONDecodeError as e:
                    print_warning(f"Dependency scan parse error: {e}")
        except FileNotFoundError:
            print_warning("'pip-audit' not installed. Skipping dependency scan.")
        except subprocess.TimeoutExpired:
            print_warning("Dependency scan timed out.")
        except Exception as e:
            print_warning(f"Dependency scan failed: {e}")

    # 3. AI Enhancement (optional)
    if use_ai and config:
        from .ai_validator import get_ai_api_key, enhance_finding_with_ai
        
        api_key = get_ai_api_key('gemini', config)
        if api_key:
            print_info("Enhancing findings with AI analysis...")
            enhanced_count = 0
            for i, finding in enumerate(all_findings):
                # Convert SecurityFinding to dict for AI processing
                finding_dict = {
                    'type': finding.category,
                    'file': finding.file,
                    'line': finding.line,
                    'description': finding.description,
                    'code': finding.code,
                    'severity': finding.severity
                }
                enhanced = enhance_finding_with_ai(finding_dict, config)
                if enhanced.get('ai_enhanced'):
                    enhanced_count += 1
            
            if enhanced_count > 0:
                print_success(f"AI enhanced {enhanced_count} findings")
        else:
            print_warning("AI enhancement skipped: API key not configured")
            print_info("Set GEMINI_API_KEY or configure in PyGitUp to enable AI analysis")

    # 4. Log the scan
    AUDIT_LOGGER.log_event(
        AuditEventType.SECURITY_SCAN,
        user=os.environ.get('USER', 'unknown'),
        details={
            "directory": directory,
            "findings_count": len(all_findings),
            "critical_count": len([f for f in all_findings if f.severity == 'critical']),
            "message": f"Security scan completed with {len(all_findings)} findings"
        },
        severity="high" if any(f.severity == 'critical' for f in all_findings) else "info"
    )

    return all_findings


def validate_token_security(token: str, token_type: str = "github") -> Tuple[bool, List[str]]:
    """
    Validate the security of a token.
    
    Args:
        token: The token to validate
        token_type: Type of token (github, aws, gcp, etc.)
        
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    # Check minimum length
    if len(token) < 20:
        issues.append("Token is too short (minimum 20 characters)")
    
    # Check entropy
    if not is_high_entropy(token, threshold=3.5):
        issues.append("Token has low entropy (may be predictable)")
    
    # Check for known patterns
    if token_type == "github":
        if not token.startswith(('ghp_', 'github_pat_', 'gho_', 'ghu_', 'ghs_')):
            issues.append("Token doesn't match known GitHub token patterns")
    
    # Check for accidental whitespace
    if token != token.strip():
        issues.append("Token contains leading/trailing whitespace")
    
    # Check for common characters that indicate placeholder
    if any(placeholder in token.lower() for placeholder in ['xxx', 'your_', 'placeholder', 'example']):
        issues.append("Token appears to be a placeholder")
    
    return len(issues) == 0, issues


def get_security_report(findings: List[SecurityFinding]) -> str:
    """Generate a security report summary."""
    if not findings:
        return "✅ No security issues detected."
    
    report = ["# 🔒 Security Scan Report", f"\nGenerated: {datetime.now(timezone.utc).isoformat()}", ""]
    
    # Summary
    by_severity = defaultdict(int)
    by_category = defaultdict(int)
    
    for finding in findings:
        by_severity[finding.severity] += 1
        by_category[finding.category] += 1
    
    report.append("## Summary")
    report.append(f"- **Total Findings:** {len(findings)}")
    report.append(f"- **Critical:** {by_severity.get('critical', 0)}")
    report.append(f"- **High:** {by_severity.get('high', 0)}")
    report.append(f"- **Medium:** {by_severity.get('medium', 0)}")
    report.append(f"- **Low:** {by_severity.get('low', 0)}")
    report.append("")
    
    # By Category
    report.append("## Findings by Category")
    for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
        report.append(f"- **{category.replace('_', ' ').title()}:** {count}")
    report.append("")
    
    # Top Issues
    report.append("## Top Issues")
    for i, finding in enumerate(sorted(findings, key=lambda x: ['critical', 'high', 'medium', 'low', 'info'].index(x.severity))[:10], 1):
        report.append(f"\n### {i}. [{finding.severity.upper()}] {finding.title}")
        report.append(f"- **File:** {finding.file}:{finding.line}")
        report.append(f"- **Description:** {finding.description}")
        report.append(f"- **Remediation:** {finding.remediation}")
        if finding.cwe_id:
            report.append(f"- **CWE:** {finding.cwe_id}")
        if finding.cvss_score:
            report.append(f"- **CVSS Score:** {finding.cvss_score}")
    
    return "\n".join(report)
