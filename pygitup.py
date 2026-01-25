
import sys
from pygitup.main import main

if __name__ == "__main__":
    # Add the project root to the path to allow for relative imports
    sys.path.append('.')
    main()
