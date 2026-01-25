
import subprocess

def run_audit():
    """Run a security audit on the project dependencies."""
    print("Running security audit on project dependencies...")
    try:
        result = subprocess.run(["pip-audit"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Audit Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\nAudit complete: No known vulnerabilities found.")
        elif result.returncode == 1:
            print("\nAudit complete: Vulnerabilities were found (listed above).")
        else:
            print(f"\nAn unexpected error occurred during the audit. Exit code: {result.returncode}")

    except FileNotFoundError:
        print("Error: 'pip-audit' is not installed. Please install it by running 'pip install pip-audit'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
