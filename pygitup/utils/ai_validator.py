"""
PyGitUp AI Validation Module
=============================
Centralized AI API key validation and error handling for all AI features.
"""

import os
from typing import Optional, Tuple
from .ui import print_error, print_info, print_warning, print_success, console, Panel


# AI Provider Configuration
AI_PROVIDERS = {
    'gemini': {
        'name': 'Google Gemini',
        'env_var': 'GEMINI_API_KEY',
        'config_key': 'ai_api_key',
        'docs_url': 'https://makersuite.google.com/app/apikey',
        'models': ['gemini-3.1-pro', 'gemini-2.5-pro', 'gemini-2.0-flash']
    },
    'openai': {
        'name': 'OpenAI',
        'env_var': 'OPENAI_API_KEY',
        'config_key': 'openai_api_key',
        'docs_url': 'https://platform.openai.com/api-keys',
        'models': ['gpt-4', 'gpt-3.5-turbo']
    },
    'anthropic': {
        'name': 'Anthropic Claude',
        'env_var': 'ANTHROPIC_API_KEY',
        'config_key': 'anthropic_api_key',
        'docs_url': 'https://console.anthropic.com/settings/keys',
        'models': ['claude-3-5-sonnet', 'claude-3-opus']
    }
}


class AIValidationError(Exception):
    """Raised when AI API key is missing or invalid."""
    pass


def check_ai_api_key(provider: str = 'gemini', config: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if AI API key is configured.
    
    Args:
        provider: AI provider name ('gemini', 'openai', 'anthropic')
        config: Optional config dictionary to check
        
    Returns:
        Tuple of (is_valid, api_key or None)
    """
    if provider not in AI_PROVIDERS:
        return False, None
    
    provider_config = AI_PROVIDERS[provider]
    api_key = None
    
    # 1. Check environment variable
    env_var = provider_config['env_var']
    api_key = os.environ.get(env_var)
    
    # 2. Check config if provided
    if not api_key and config:
        api_key = config.get('github', {}).get(provider_config['config_key'])
    
    # 3. Validate key format (basic check)
    if api_key and len(api_key.strip()) < 10:
        return False, None
    
    return bool(api_key), api_key.strip() if api_key else None


def get_ai_api_key(provider: str = 'gemini', config: Optional[dict] = None) -> Optional[str]:
    """
    Get AI API key from environment or config.
    
    Args:
        provider: AI provider name
        config: Optional config dictionary
        
    Returns:
        API key or None
    """
    _, api_key = check_ai_api_key(provider, config)
    return api_key


def validate_ai_ready(provider: str = 'gemini', config: Optional[dict] = None, 
                      feature_name: str = "This feature") -> bool:
    """
    Validate AI is ready and show helpful error if not.
    
    Args:
        provider: AI provider name
        config: Optional config dictionary
        feature_name: Name of the feature requiring AI
        
    Returns:
        True if AI is configured, False otherwise
    """
    is_valid, api_key = check_ai_api_key(provider, config)
    
    if is_valid:
        return True
    
    # Show helpful error message
    provider_info = AI_PROVIDERS.get(provider, {})
    
    error_message = f"""
╭─────────────────────────────────────────────────────────────╮
│  🤖 AI API Key Required for {feature_name}                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  The {provider_info.get('name', provider).upper()} API key is not configured.           │
│                                                             │
│  To use this AI-powered feature, you need to:               │
│                                                             │
│  1. Get an API key from:                                    │
│     🔗 {provider_info.get('docs_url', 'N/A')}                          │
│                                                             │
│  2. Configure it using one of these methods:                │
│                                                             │
│     a) Environment Variable:                                │
│        export {provider_info.get('env_var', 'N/A')}=your_api_key        │
│                                                             │
│     b) PyGitUp Configuration:                               │
│        Run: pygitup → Option 14 (Configure)                 │
│                                                             │
│  3. Supported Models:                                       │
│     {', '.join(provider_info.get('models', []))}                     │
│                                                             │
│  After configuration, run this command again.               │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
"""
    print_error(error_message)
    return False


def ai_feature_wrapper(provider: str = 'gemini', config: Optional[dict] = None,
                       feature_name: str = "AI Feature"):
    """
    Decorator for AI-powered features with automatic validation.
    
    Usage:
        @ai_feature_wrapper(provider='gemini', feature_name="Commit Generation")
        def generate_commit():
            # AI code here
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not validate_ai_ready(provider, config, feature_name):
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator


def prompt_for_ai_enable() -> bool:
    """
    Prompt user to enable AI features.
    
    Returns:
        True if user wants to enable AI, False otherwise
    """
    print_info("\n🤖 AI-Powered Features Available")
    print("\nAI features can enhance your workflow with:")
    print("  • Intelligent code analysis")
    print("  • Automated security recommendations")
    print("  • Natural language explanations")
    print("  • Smart remediation suggestions")
    print("\n⚠️  Note: AI features require an API key and may incur costs.")
    
    choice = input("\nWould you like to configure AI now? (y/n): ").strip().lower()
    return choice in ['y', 'yes']


def get_hybrid_analysis(use_ai: bool = False, ai_provider: str = 'gemini',
                        config: Optional[dict] = None, **kwargs):
    """
    Perform hybrid analysis (rule-based + optional AI).
    
    Args:
        use_ai: Whether to use AI enhancement
        ai_provider: AI provider to use
        config: Configuration dictionary
        **kwargs: Additional arguments for analysis
        
    Returns:
        Analysis results dictionary
    """
    results = {
        'rule_based': True,
        'ai_enhanced': False,
        'ai_error': None,
        'findings': []
    }
    
    # Always do rule-based analysis
    # (caller should add rule-based findings)
    
    # Optionally enhance with AI
    if use_ai:
        is_valid, api_key = check_ai_api_key(ai_provider, config)
        
        if is_valid:
            results['ai_enhanced'] = True
            # AI enhancement would be called here
        else:
            results['ai_error'] = "AI API key not configured"
            # Fall back to rule-based only
    
    return results


# =============================================================================
# AI-Enhanced Security Analysis Functions
# =============================================================================

def analyze_with_ai(finding: dict, api_key: str, provider: str = 'gemini') -> Optional[dict]:
    """
    Use AI to analyze and enhance a security finding.
    
    Args:
        finding: Security finding dictionary
        api_key: AI API key
        provider: AI provider
        
    Returns:
        Enhanced finding with AI analysis
    """
    if not api_key:
        return None
    
    # Create prompt for AI analysis
    prompt = f"""
Analyze this security finding and provide:
1. Confirmation if this is a true positive or false positive
2. Risk assessment (Low/Medium/High/Critical)
3. Specific remediation steps with code examples
4. Any additional context or considerations

Security Finding:
- Type: {finding.get('type', 'Unknown')}
- File: {finding.get('file', 'Unknown')}:{finding.get('line', 0)}
- Description: {finding.get('description', '')}
- Code: {finding.get('code', '')}

Provide your analysis in JSON format with keys:
- is_true_positive (boolean)
- risk_level (string: Low/Medium/High/Critical)
- remediation (string with code example)
- additional_context (string)
"""
    
    try:
        # Use centralized caller for rotation and robustness
        from .ai import call_gemini_api
        ai_response = call_gemini_api(api_key, prompt)
        
        if ai_response:
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                ai_analysis = json_match.group()
                import json
                return json.loads(ai_analysis)
    except Exception as e:
        if os.environ.get('PYGITUP_DEBUG'):
            print_warning(f"AI analysis failed: {e}")
    
    return None


def enhance_finding_with_ai(finding: dict, config: Optional[dict] = None) -> dict:
    """
    Enhance a security finding with AI analysis if available.
    
    Args:
        finding: Security finding dictionary
        config: Configuration dictionary
        
    Returns:
        Enhanced finding (or original if AI unavailable)
    """
    api_key = get_ai_api_key('gemini', config)
    
    if not api_key:
        return finding
    
    # Try AI enhancement
    ai_analysis = analyze_with_ai(finding, api_key)
    
    if ai_analysis:
        finding['ai_enhanced'] = True
        finding['ai_analysis'] = ai_analysis
        
        # Update severity based on AI assessment
        if ai_analysis.get('risk_level') == 'Critical':
            finding['severity'] = 'critical'
        elif ai_analysis.get('risk_level') == 'High':
            finding['severity'] = 'high'
        elif ai_analysis.get('risk_level') == 'Medium':
            finding['severity'] = 'medium'
        elif ai_analysis.get('risk_level') == 'Low':
            finding['severity'] = 'low'
        
        # Add AI remediation if available
        if ai_analysis.get('remediation'):
            finding['ai_remediation'] = ai_analysis['remediation']
    
    return finding
