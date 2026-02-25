"""
PyGitUp Token Management Module
================================
Advanced token rotation, expiration tracking, and secure credential management.
"""

import os
import json
import time
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import base64

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

from ..utils.ui import print_success, print_error, print_info, print_warning, print_header, console, Panel
from ..github.api import github_request


# =============================================================================
# TOKEN STATUS ENUMS
# =============================================================================

class TokenStatus(Enum):
    """Token validity and expiration status."""
    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"  # Less than 7 days
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class TokenType(Enum):
    """Types of GitHub tokens."""
    PERSONAL_CLASSIC = "personal_classic"
    PERSONAL_FINE_GRAINED = "personal_fine_grained"
    OAUTH = "oauth"
    APP_INSTALLATION = "app_installation"
    APP_USER = "app_user"
    REFRESH = "refresh"
    UNKNOWN = "unknown"


@dataclass
class TokenMetadata:
    """Metadata about a GitHub token."""
    token_id: str
    token_type: TokenType
    status: TokenStatus
    created_at: Optional[datetime]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    scopes: List[str] = field(default_factory=list)
    repository_access: str = "all"  # all, selected, none
    organization: Optional[str] = None
    user_agent: Optional[str] = None
    fingerprint: str = ""
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
        }


@dataclass
class TokenRotationRecord:
    """Record of a token rotation event."""
    timestamp: str
    old_token_fingerprint: str
    new_token_fingerprint: str
    reason: str
    user: str
    success: bool
    error_message: Optional[str] = None


# =============================================================================
# TOKEN FINGERPRINTING
# =============================================================================

def generate_token_fingerprint(token: str) -> str:
    """
    Generate a unique fingerprint for a token without storing the actual token.
    Uses SHA-256 hash of the first and last 4 characters + length.
    """
    if not token or len(token) < 8:
        return "invalid"
    
    # Create fingerprint from partial token + length
    partial = f"{token[:4]}:{len(token)}:{token[-4:]}"
    return hashlib.sha256(partial.encode()).hexdigest()[:16]


def identify_token_type(token: str) -> TokenType:
    """Identify the type of GitHub token based on prefix patterns."""
    if not token:
        return TokenType.UNKNOWN
    
    prefixes = {
        'ghp_': TokenType.PERSONAL_CLASSIC,
        'github_pat_': TokenType.PERSONAL_FINE_GRAINED,
        'gho_': TokenType.OAUTH,
        'ghu_': TokenType.APP_USER,
        'ghs_': TokenType.APP_INSTALLATION,
        'ghr_': TokenType.REFRESH,
    }
    
    for prefix, token_type in prefixes.items():
        if token.startswith(prefix):
            return token_type
    
    # Check for old-style tokens (40 character hex)
    if len(token) == 40 and all(c in '0123456789abcdef' for c in token.lower()):
        return TokenType.PERSONAL_CLASSIC
    
    return TokenType.UNKNOWN


# =============================================================================
# TOKEN EXPIRATION TRACKING
# =============================================================================

class TokenExpirationTracker:
    """Tracks token expiration and provides rotation reminders."""
    
    # Fine-grained PATs expire after 1 year (365 days)
    # Classic PATs don't expire unless revoked
    FINE_GRAINED_EXPIRY_DAYS = 365
    EXPIRY_WARNING_DAYS = 30
    EXPIRY_CRITICAL_DAYS = 7
    
    def __init__(self, storage_path: str = "~/.pygitup_config/token_tracking.json"):
        self.storage_path = os.path.expanduser(storage_path)
        self.tracking_data: Dict[str, Dict] = {}
        self._load_tracking_data()
    
    def _load_tracking_data(self):
        """Load token tracking data from disk."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self.tracking_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print_warning(f"Could not load token tracking data: {e}")
            self.tracking_data = {}
    
    def _save_tracking_data(self):
        """Save token tracking data to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.tracking_data, f, indent=2)
            
            # Set restrictive permissions
            if os.name != 'nt':
                os.chmod(self.storage_path, 0o600)
        except Exception as e:
            print_error(f"Could not save token tracking data: {e}")
    
    def register_token(self, token: str, username: str, notes: str = ""):
        """
        Register a token for expiration tracking.
        
        Args:
            token: The GitHub token
            username: GitHub username
            notes: Optional notes about the token
        """
        fingerprint = generate_token_fingerprint(token)
        token_type = identify_token_type(token)
        now = datetime.now(timezone.utc)

        # Calculate expected expiration
        expires_at = None
        if token_type == TokenType.PERSONAL_FINE_GRAINED:
            expires_at = now + timedelta(days=self.FINE_GRAINED_EXPIRY_DAYS)

        self.tracking_data[fingerprint] = {
            'username': username,
            'token_type': token_type.value,
            'registered_at': now.isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'last_verified_at': now.isoformat(),
            'notes': notes,
            'rotation_count': 0,
        }

        self._save_tracking_data()

        if expires_at:
            print_info(f"📅 Token registered. Expected expiration: {expires_at.strftime('%Y-%m-%d')}")
        else:
            print_info("📅 Token registered (no expiration)")
    
    def get_token_status(self, token: str) -> TokenMetadata:
        """
        Get the current status of a token.
        
        Args:
            token: The GitHub token to check
            
        Returns:
            TokenMetadata with current status
        """
        fingerprint = generate_token_fingerprint(token)
        token_type = identify_token_type(token)
        tracking_info = self.tracking_data.get(fingerprint, {})
        
        # Get token details from GitHub API
        github_token = token
        
        # Query GitHub for token details
        token_info = self._fetch_token_info(github_token)
        
        # Determine status
        status = TokenStatus.UNKNOWN
        expires_at = None
        created_at = None
        last_used_at = None
        scopes = []
        repository_access = "all"
        organization = None
        
        if token_info:
            # TECHNICAL FIX: prioritize local registration date for accuracy
            if tracking_info.get('registered_at'):
                created_at = datetime.fromisoformat(tracking_info['registered_at'])
            else:
                # Fallback to API if not tracked locally (often account creation date)
                created_at_str = token_info.get('created_at')
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))

            expires_at_str = token_info.get('expires_at')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)

                if expires_at < now:
                    status = TokenStatus.EXPIRED
                elif expires_at < now + timedelta(days=self.EXPIRY_CRITICAL_DAYS):
                    status = TokenStatus.EXPIRING_SOON
                else:
                    status = TokenStatus.VALID
            else:
                status = TokenStatus.VALID  # Classic PATs don't expire

            last_used_str = token_info.get('last_used_at')
            if last_used_str:
                last_used_at = datetime.fromisoformat(last_used_str.replace('Z', '+00:00'))
            
            scopes = token_info.get('scopes', [])
            repository_access = token_info.get('repository_selection', 'all')
            organization = token_info.get('organization', {}).get('login') if token_info.get('organization') else None
        
        # Check if token is revoked (API returns 401)
        if not self._validate_token(github_token):
            status = TokenStatus.REVOKED
        
        return TokenMetadata(
            token_id=fingerprint,
            token_type=token_type,
            status=status,
            created_at=created_at,
            expires_at=expires_at,
            last_used_at=last_used_at,
            scopes=scopes,
            repository_access=repository_access,
            organization=organization,
            fingerprint=fingerprint
        )
    
    def _fetch_token_info(self, token: str) -> Optional[Dict]:
        """Fetch token information from GitHub API."""
        if not token:
            return None
        
        try:
            # Get current authorization and user info
            response = github_request('GET', 'https://api.github.com/user', token)
            if response.status_code == 200:
                user_data = response.json()
                
                # Safely extract scopes from header
                scopes_header = response.headers.get('X-OAuth-Scopes', '')
                scopes = [s.strip() for s in scopes_header.split(',')] if scopes_header else []
                
                return {
                    'user': user_data.get('login'),
                    'scopes': scopes,
                    'created_at': user_data.get('created_at'),
                    'last_used_at': datetime.now(timezone.utc).isoformat() # Approx
                }
        except Exception as e:
            if os.environ.get('PYGITUP_DEBUG'):
                print_warning(f"Could not fetch token info: {e}")
        
        return None
    
    def _validate_token(self, token: str) -> bool:
        """Validate if a token is still active."""
        if not token:
            return False
        
        try:
            response = github_request('GET', 'https://api.github.com/user', token)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_expiring_tokens(self, days_threshold: int = 30) -> List[Dict]:
        """Get list of tokens expiring within the threshold."""
        expiring = []
        now = datetime.now(timezone.utc)
        threshold_date = now + timedelta(days=days_threshold)

        for fingerprint, data in self.tracking_data.items():
            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'])
                # Make expires_at timezone-aware if it isn't
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at <= threshold_date:
                    days_until_expiry = (expires_at - now).days
                    expiring.append({
                        'fingerprint': fingerprint,
                        'username': data.get('username'),
                        'token_type': data.get('token_type'),
                        'expires_at': data['expires_at'],
                        'days_until_expiry': days_until_expiry,
                        'status': 'expired' if days_until_expiry < 0 else 'expiring_soon'
                    })

        return sorted(expiring, key=lambda x: x['days_until_expiry'])

    def record_rotation(self, old_token: str, new_token: str, user: str, reason: str, success: bool, error: str = ""):
        """Record a token rotation event."""
        old_fingerprint = generate_token_fingerprint(old_token)
        new_fingerprint = generate_token_fingerprint(new_token)

        # Update tracking data
        if old_fingerprint in self.tracking_data:
            old_data = self.tracking_data[old_fingerprint]

            # Create new entry with incremented rotation count
            self.tracking_data[new_fingerprint] = {
                **old_data,
                'registered_at': datetime.now(timezone.utc).isoformat(),
                'rotation_count': old_data.get('rotation_count', 0) + 1,
                'rotated_from': old_fingerprint,
            }

            # Remove old entry
            del self.tracking_data[old_fingerprint]

        self._save_tracking_data()
    
    def cleanup_expired_tracking(self):
        """Remove tracking data for long-expired tokens."""
        now = datetime.now(timezone.utc)
        expired_threshold = now - timedelta(days=90)  # Keep for 90 days after expiry

        to_remove = []
        for fingerprint, data in self.tracking_data.items():
            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'])
                # Make timezone-aware if needed
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < expired_threshold:
                    to_remove.append(fingerprint)

        for fingerprint in to_remove:
            del self.tracking_data[fingerprint]

        if to_remove:
            self._save_tracking_data()
            print_info(f"🧹 Cleaned up {len(to_remove)} expired token tracking records")


# =============================================================================
# TOKEN ROTATION MANAGER
# =============================================================================

class TokenRotationManager:
    """Manages automated and manual token rotation."""
    
    def __init__(self, tracker: Optional[TokenExpirationTracker] = None):
        self.tracker = tracker or TokenExpirationTracker()
        self.rotation_history: List[TokenRotationRecord] = []
    
    def check_rotation_needed(self, token: str) -> Tuple[bool, str]:
        """
        Check if a token needs rotation.

        Args:
            token: The GitHub token to check

        Returns:
            Tuple of (needs_rotation, reason)
        """
        metadata = self.tracker.get_token_status(token)

        if metadata.status == TokenStatus.EXPIRED:
            return True, "Token has expired"
        elif metadata.status == TokenStatus.EXPIRING_SOON:
            days_left = (metadata.expires_at - datetime.now(timezone.utc)).days if metadata.expires_at else 0
            return True, f"Token expires in {days_left} days"
        elif metadata.status == TokenStatus.REVOKED:
            return True, "Token has been revoked"
        elif metadata.status == TokenStatus.INVALID:
            return True, "Token is invalid"

        # Check for security best practices
        # Rotate tokens older than 6 months as a precaution
        if metadata.created_at:
            # Make created_at timezone-aware if needed
            created_at = metadata.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - created_at).days
            if age_days > 180:
                return True, f"Token is {age_days} days old (recommended rotation: 180 days)"

        return False, "Token is valid and does not need rotation"
    
    def rotate_token(self, old_token: str, username: str, reason: str = "Manual rotation") -> Tuple[bool, str]:
        """
        Guide user through token rotation process.
        
        Note: GitHub doesn't provide an API to create new PATs programmatically
        for security reasons. This method guides the user through the process.
        
        Args:
            old_token: Current GitHub token
            username: GitHub username
            reason: Reason for rotation
            
        Returns:
            Tuple of (success, message)
        """
        print_header("🔄 Token Rotation")
        
        # Step 1: Verify old token
        print_info("Step 1: Verifying current token...")
        if not self.tracker._validate_token(old_token):
            print_error("Current token is invalid or revoked.")
            confirm = input("Would you like to proceed with rotation anyway? (y/n) [y]: ").lower()
            if confirm == 'n':
                return False, "Rotation cancelled by user."
        else:
            print_success("Current token verified.")
        
        # Step 2: Generate instructions
        print_info("\nStep 2: Generate new token")
        print("\nGitHub requires manual token generation for security.")
        print("Please follow these steps:\n")
        
        instructions = [
            "1. Go to GitHub Settings → Developer settings → Personal access tokens",
            f"2. Click 'Generate new token' (or 'Fine-grained tokens')",
            "3. Select the same scopes as your current token:",
            "   - repo (Full control of private repositories)",
            "   - workflow (Update GitHub Action workflows)",
            "   - admin:org (if using organization features)",
            "   - gist (if using gist features)",
            "4. Generate the token and copy it",
        ]
        
        for instruction in instructions:
            print(f"  {instruction}")
        
        # Step 3: Get new token
        print("\n" + "="*60)
        new_token = input("\n👉 Paste your new token: ").strip()
        
        if not new_token:
            print_error("No new token provided.")
            return False, "No new token provided"
        
        # Step 4: Validate new token
        print_info("\nStep 3: Validating new token...")
        if not self.tracker._validate_token(new_token):
            print_error("New token is invalid or has insufficient permissions.")
            return False, "New token is invalid"
        else:
            print_success("New token validated.")
        
        # Step 5: Update configuration
        print_info("\nStep 4: Updating configuration...")
        try:
            from ..core.config import configuration_wizard, load_config, get_active_profile_path
            
            # Re-run wizard with new token
            profile_path = get_active_profile_path()
            profile_name = os.path.basename(profile_path).replace('.yaml', '')
            
            print_info(f"Updating profile: {profile_name}")
            
            # Load current config
            config = load_config()
            
            # Update with new token (encryption happens in wizard)
            from ..core.config import encrypt_data, derive_key, get_master_key
            import yaml
            import getpass
            
            # Get password to derive key
            password = getpass.getpass("🔐 Enter Master Password to update config: ")
            
            # Load existing salt
            with open(profile_path, 'r') as f:
                existing_config = yaml.safe_load(f)
            
            salt_hex = existing_config.get('security', {}).get('salt', '')
            if not salt_hex:
                return False, "Could not find salt in existing config"
            
            salt = bytes.fromhex(salt_hex)
            key = derive_key(password, salt)
            
            if not key:
                return False, "Invalid password"
            
            # Update config
            existing_config['github']['token'] = encrypt_data(new_token, salt)
            
            with open(profile_path, 'w') as f:
                yaml.dump(existing_config, f, default_flow_style=False)
            
            # Set restrictive permissions
            if os.name != 'nt':
                os.chmod(profile_path, 0o600)
            
            # Record rotation
            self.tracker.record_rotation(old_token, new_token, username, reason, True)
            
            print_success("\n✅ Token rotation completed successfully!")
            print_info("📝 Don't forget to revoke your old token in GitHub settings.")
            
            return True, "Token rotated successfully"
            
        except Exception as e:
            print_error(f"Failed to update configuration: {e}")
            return False, f"Failed to update configuration: {e}"
    
    def get_rotation_recommendations(self, token: str) -> List[str]:
        """Get security recommendations for a token."""
        recommendations = []
        metadata = self.tracker.get_token_status(token)

        # Expiration-based recommendations
        if metadata.status == TokenStatus.EXPIRED:
            recommendations.append("🚨 URGENT: Token has expired. Rotate immediately.")
        elif metadata.status == TokenStatus.EXPIRING_SOON:
            days_left = (metadata.expires_at - datetime.now(timezone.utc)).days if metadata.expires_at else 0
            recommendations.append(f"⚠️ Token expires in {days_left} days. Plan rotation soon.")

        # Age-based recommendations
        if metadata.created_at:
            created_at = metadata.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - created_at).days
            if age_days > 365:
                recommendations.append("📅 Token is over 1 year old. Consider rotation for security best practices.")
            elif age_days > 180:
                recommendations.append("📅 Token is over 6 months old. Consider scheduling rotation.")

        # Scope-based recommendations
        if 'repo' in metadata.scopes and metadata.repository_access == 'all':
            recommendations.append("🔐 Token has full repo access. Consider using fine-grained tokens with limited scope.")

        # Usage-based recommendations
        if metadata.last_used_at:
            last_used_at = metadata.last_used_at
            if last_used_at.tzinfo is None:
                last_used_at = last_used_at.replace(tzinfo=timezone.utc)
            days_since_use = (datetime.now(timezone.utc) - last_used_at).days
            if days_since_use > 90:
                recommendations.append("💤 Token hasn't been used in 90+ days. Consider revoking if no longer needed.")

        return recommendations


# =============================================================================
# SECURE TOKEN STORAGE
# =============================================================================

class SecureTokenStorage:
    """Secure temporary token storage for session management."""
    
    def __init__(self):
        self._session_tokens: Dict[str, str] = {}
        self._token_timestamps: Dict[str, float] = {}
        self._max_age_seconds = 3600  # 1 hour default
    
    def store_token(self, key: str, token: str, max_age: Optional[int] = None):
        """Store a token in memory for the current session."""
        self._session_tokens[key] = token
        self._token_timestamps[key] = time.time()
        
        if max_age:
            self._token_timestamps[f"{key}_max_age"] = max_age
        else:
            self._token_timestamps[f"{key}_max_age"] = self._max_age_seconds
    
    def get_token(self, key: str) -> Optional[str]:
        """Retrieve a token if it hasn't expired."""
        if key not in self._session_tokens:
            return None
        
        # Check expiration
        timestamp = self._token_timestamps.get(key, 0)
        max_age = self._token_timestamps.get(f"{key}_max_age", self._max_age_seconds)
        
        if time.time() - timestamp > max_age:
            # Expired - remove
            self.remove_token(key)
            return None
        
        return self._session_tokens.get(key)
    
    def remove_token(self, key: str):
        """Remove a token from storage."""
        self._session_tokens.pop(key, None)
        self._token_timestamps.pop(key, None)
        self._token_timestamps.pop(f"{key}_max_age", None)
    
    def clear_all(self):
        """Clear all stored tokens."""
        self._session_tokens.clear()
        self._token_timestamps.clear()
    
    def cleanup_expired(self):
        """Remove all expired tokens."""
        expired_keys = []
        
        for key in list(self._session_tokens.keys()):
            timestamp = self._token_timestamps.get(key, 0)
            max_age = self._token_timestamps.get(f"{key}_max_age", self._max_age_seconds)
            
            if time.time() - timestamp > max_age:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.remove_token(key)
        
        if expired_keys:
            print_info(f"🧹 Cleaned up {len(expired_keys)} expired session tokens")


# =============================================================================
# EXPORTED FUNCTIONS
# =============================================================================

def check_token_health(token: str, username: str) -> Dict:
    """
    Check the overall health of a GitHub token.
    
    Args:
        token: GitHub token
        username: GitHub username
        
    Returns:
        Dictionary with token health information
    """
    tracker = TokenExpirationTracker()
    rotation_manager = TokenRotationManager(tracker)
    
    # Get token metadata
    metadata = tracker.get_token_status(token)
    
    # Check if rotation needed
    needs_rotation, rotation_reason = rotation_manager.check_rotation_needed(token)
    
    # Get recommendations
    recommendations = rotation_manager.get_rotation_recommendations(token)
    
    return {
        'username': username,
        'token_type': metadata.token_type.value,
        'status': metadata.status.value,
        'created_at': metadata.created_at.isoformat() if metadata.created_at else None,
        'expires_at': metadata.expires_at.isoformat() if metadata.expires_at else None,
        'last_used_at': metadata.last_used_at.isoformat() if metadata.last_used_at else None,
        'scopes': metadata.scopes,
        'needs_rotation': needs_rotation,
        'rotation_reason': rotation_reason,
        'recommendations': recommendations,
        'fingerprint': metadata.fingerprint,
    }


def display_token_health_report(token: str, username: str):
    """Display a formatted token health report."""
    from ..utils.ui import console, Panel, Table, box
    
    health = check_token_health(token, username)
    
    print_header("🔐 Token Health Report")
    
    # Status Panel
    status_color = {
        'valid': 'green',
        'expiring_soon': 'yellow',
        'expired': 'red',
        'revoked': 'red',
        'invalid': 'red',
    }.get(health['status'], 'white')
    
    status_icon = {
        'valid': '✅',
        'expiring_soon': '⚠️',
        'expired': '❌',
        'revoked': '❌',
        'invalid': '❌',
    }.get(health['status'], '❓')
    
    console.print(Panel(
        f"[bold {status_color}]{status_icon} {health['status'].upper()}[/bold {status_color}]\n"
        f"Type: {health['token_type'].replace('_', ' ').title()}\n"
        f"Fingerprint: {health['fingerprint']}",
        title="Token Status",
        border_style=status_color
    ))
    
    # Details Table
    table = Table(title="Token Details", box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    if health['created_at']:
        table.add_row("Created", health['created_at'][:10])
    if health['expires_at']:
        table.add_row("Expires", health['expires_at'][:10])
    if health['last_used_at']:
        table.add_row("Last Used", health['last_used_at'][:10])
    
    table.add_row("Scopes", ", ".join(health['scopes']) if health['scopes'] else "N/A")
    
    console.print(table)
    
    # Recommendations
    if health['recommendations']:
        print_info("\n💡 Recommendations:")
        for rec in health['recommendations']:
            print(f"  • {rec}")
    
    # Rotation needed?
    if health['needs_rotation']:
        print_warning(f"\n🔄 Rotation Recommended: {health['rotation_reason']}")
        print_info("Run 'pygitup --rotate-token' to rotate your token")
    else:
        print_success("\n✅ Token is healthy. No action needed.")


# Global instances
_global_tracker = None
_global_rotation_manager = None


def force_update_token(new_token: str, username: str) -> Tuple[bool, str]:
    """
    Force update the token in config without verifying the old one.
    Use this when the old token is already revoked/disabled.
    
    Args:
        new_token: New GitHub token
        username: GitHub username
        
    Returns:
        Tuple of (success, message)
    """
    print_header("Force Token Update")
    print_info("Updating token without verifying old token...")
    
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        from pygitup.core.config import get_active_profile_path, encrypt_data, derive_key
        from pygitup.github.api import github_request
        import yaml
        import getpass
        
        profile_path = get_active_profile_path()
        profile_name = os.path.basename(profile_path).replace('.yaml', '')
        
        print_info(f"Updating profile: {profile_name}")
        
        # Load existing config to get salt
        with open(profile_path, 'r') as f:
            existing_config = yaml.safe_load(f)
        
        salt_hex = existing_config.get('security', {}).get('salt', '')
        if not salt_hex:
            return False, "Could not find salt in config"
        
        salt = bytes.fromhex(salt_hex)
        
        # Prompt for master password
        password = getpass.getpass("Enter Master Password: ")
        key = derive_key(password, salt)
        
        if not key:
            return False, "Invalid master password"
        
        # Update token
        existing_config['github']['token'] = encrypt_data(new_token, salt)
        
        # Validate new token
        test_resp = github_request('GET', 'https://api.github.com/user', new_token)
        if test_resp.status_code != 200:
            return False, f"New token is invalid (HTTP {test_resp.status_code})"
        
        # Save updated config
        with open(profile_path, 'w') as f:
            yaml.dump(existing_config, f, default_flow_style=False)
        
        if os.name != 'nt':
            os.chmod(profile_path, 0o600)
        
        # Clear session cache
        from pygitup.core.config import _SESSION_KEY
        _SESSION_KEY = None
        
        print_success("Token updated successfully!")
        print_info("Please restart PyGitUp for changes to take effect.")
        
        return True, "Token updated successfully"
        
    except Exception as e:
        return False, f"Failed to update token: {e}"


def get_token_tracker() -> TokenExpirationTracker:
    """Get or create the global token tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenExpirationTracker()
    return _global_tracker


def get_rotation_manager() -> TokenRotationManager:
    """Get or create the global rotation manager."""
    global _global_rotation_manager
    if _global_rotation_manager is None:
        _global_rotation_manager = TokenRotationManager(get_token_tracker())
    return _global_rotation_manager
