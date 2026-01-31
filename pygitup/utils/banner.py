import sys
import time
import os
import random

# ANSI color codes
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Collection of 30 Block/Mixed Style Banners
BANNERS = [
    # 1. Heavy Block Standard
    rf"""{CYAN}{BOLD}
  _____       _____ _ _   _   _       
 |  __ \     / ____(_) | | | | |      
 | |__) |   | |  __ _| |_| | | |_ __  
 |  ___/    | | |_ | | __| | | | '_ \ 
 | |     _  | |__| | | |_| |_| | |_) |
 |_|    (_)  \_____|_|\__|_|\___/| .__/
                               | |    
                               |_|    
{RESET}""",

    # 2. ANSI Shadow
    rf"""{MAGENTA}{BOLD}
██████╗ ██╗   ██╗ ██████╗ ██╗████████╗██╗   ██╗██████╗ 
██╔══██╗╚██╗ ██╔╝██╔════╝ ██║╚══██╔══╝██║   ██║██╔══██╗
██████╔╝ ╚████╔╝ ██║  ███╗██║   ██║   ██║   ██║██████╔╝
██╔═══╝   ╚██╔╝  ██║   ██║██║   ██║   ██║   ██║██╔═══╝ 
██║        ██║   ╚██████╔╝██║   ██║   ╚██████╔╝██║     
╚═╝        ╚═╝    ╚═════╝ ╚═╝   ╚═╝    ╚═════╝ ╚═╝     
{RESET}""",

    # 3. Slant Block
    rf"""{BLUE}{BOLD}
    ____        ______(_) /  / /  / /___
   / __ \__  __/ ____/ / __/ / / / / __ \
  / /_/ / / / / / __/ / /_/ /_/ / / /_/ /
 / .___/\__, /_/___/_/\__/_/\____/_/ .___/ 
/_/    /____/                   /_/      
{RESET}""",

    # 4. 3D Diagonal
    rf"""{GREEN}{BOLD}
    ____             __________ __  __  __   
   / __ \__  __     / ____/(_)_/ /_/ / / /___
  / /_/ / / / /    / / __/ / __/ __/ / / / __ \
 / ____/ /_/ /    / /_/ / / /_/ /_/ /_/ / /_/ /
/_/    \__, /     \____/_/\__/_/\____/ .___/ 
      /____/                          /_/      
{RESET}""",

    # 5. Rounded Block
    rf"""{YELLOW}{BOLD}
 _____       _____ _ _   _   _       
|  __ \     / ____(_) | | | | |      
| |__) |   | |  __ _| |_| | | |_ __  
|  ___/    | | |_ | | __| | | | '_ \ 
| |     _  | |__| | | |_| |_| | |_) |
|_|    (_)  \_____|_|\__|_|\___/| .__/
                              | |    
                              |_|    
{RESET}""",

    # 6. Futuristic
    rf"""{RED}{BOLD}
PYGITUP  >>>  SYSTEM READY
[ P Y G I T U P ]
{RESET}""",

    # 7. Iso Block
    rf"""{WHITE}{BOLD}
      ___           ___           ___           ___           ___           ___           ___     
     /\  \         |\__\         /::\  \       _\:\  \        \:\  \       /:/  /        /::\  \   
    /::\  \        |:|  |       /::\  \     /\ \:\  \        \:\  \     /:/  /  ___   /:/\:\__\  
   /:/\:\__\       |:|  |      /:/\:\__\    /\ \:\  \       /::\  \   /:/  /  ___   /:/  \/___/  
  /:/  \/__/       |:|__|__   /:/  \/__/    _\:\ \:\  \     /:/\:\__\ /:/__/  /\__\ /:/  /       
 /:/  /            /::::\__\ /:/  /  ___   /\ \:\ \:\__\    /:/\:\__\ /:/__/  /\__\ /:/  /       
 \/__/            /:/~~/~    \/__/  /\__\  \:\ \:\ \/__/    /:/  \/ / \:\  \ /:/  / \/__/        
                 /:/  /            /:/  /   \:\ \:\__\     /:/  /       \:\  /:/  /               
                 \/__/             \/__/     \:\/:/  /     \/__/         \:\/:/  /                
                                              \::/  /                     \::/  /                 
                                               \/__/                       \/__/                  
{RESET}""",

    # 8. Cyber Large
    rf"""{CYAN}{BOLD}
P Y G I T U P
#############
# CORE INIT #
#############
{RESET}""",

    # 9. DOS Style
    rf"""{MAGENTA}{BOLD}
C:\> RUN PYGITUP.EXE
[████████████████] 100%
{RESET}""",

    # 10. Star Wars Style
    rf"""{YELLOW}{BOLD}
PyGitUp
The Force of Git Automation
___________________________
{RESET}""",

    # 11. Bubble
    rf"""{BLUE}{BOLD}
  _   _   _   _   _   _   _  
 / \ / \ / \ / \ / \ / \ / \
( P | y | G | i | t | U | p )
 \_/ \_/ \_/ \_/ \_/ \_/ \_/ 
{RESET}""",

    # 12. Digital
    rf"""{GREEN}{BOLD}
 +-+-+-+-+-+-+-+
 |P|y|G|i|t|U|p|
 +-+-+-+-+-+-+-+
{RESET}""",

    # 13. Blocks & Lines
    rf"""{RED}{BOLD}
||||| PYGITUP |||||
\\\ AUTOMATION /////
{RESET}""",

    # 14. Retro Computer
    rf"""{WHITE}{BOLD}
***********************
*  P Y G I T U P  1.0 *
***********************
{RESET}""",

    # 15. Slash
    rf"""{CYAN}{BOLD}
   / // / // / // / // / // / /
  / // / // / // / // / // / /
 / // / // / // / // / // / /
/ // / // / // / // / // / /
PYGITUP - GIT AUTOMATION
{RESET}""",

    # 16. Thick
    rf"""{MAGENTA}{BOLD}
=========================
 P  Y  G  I  T  U  P
=========================
{RESET}""",

    # 17. Stencil
    rf"""{YELLOW}{BOLD}
  P  Y  G  I  T  U  P  
 [=][=][=][=][=][=][=] 
{RESET}""",

    # 18. Minimal Block
    rf"""{BLUE}{BOLD}
█▀█ █▄█ █▀▀ █ ▀█▀ █ █ █▀█
█▀▀  █  █▄█ █  █  █▄█ █▀▀
{RESET}""",

    # 19. Arrows
    rf"""{GREEN}{BOLD}
>>>>> PYGITUP >>>>>
<<<<< AUTOMATION <<<<<
{RESET}""",

    # 20. Double Border
    rf"""{RED}{BOLD}
╔═════════════════════╗
║      PYGITUP        ║
╚═════════════════════╝
{RESET}""",

    # 21. Gothic
    rf"""{WHITE}{BOLD}
 ___        ____ _ _   _   _       
|  _ \ _   / ___(_) |_| | | |_ __  
| |_) | | | |  _| | __| | | | '_ \ 
|  __/| |_| | |_| | |_| |_| | |_) |
|_|    \__, |\____|_|\__|_\___/| .__/
       |___/                  |_|    
{RESET}""",

    # 22. Small Block
    rf"""{CYAN}{BOLD}
┌─┐┬ ┬┌─┐┬┌┬┐┬ ┬┌─┐
├─┘└┬┘│ ┬│ │ │ │├─┘
┴   ┴ └─┘┴ ┴ └─┘┴  
{RESET}""",

    # 23. Isometric 3
    rf"""{MAGENTA}{BOLD}
      ___           ___           ___     
     /  /\         /  /\         /  /\    
    /  /:/:\       /  /:/:\       /  /:/_   
   /  /:/\:\     /  /:/  \:\   /  /:/ /::\ 
  /  /:/~/:/    /  /:/ \__\:\ /__/:/ /:/:/
 /__/:/ /:/___ /__/:/ \__\:\ /__/:/ /:/:/\:\
 \  \:\/:::::/ \  \:\ /  /:/ \  \:\/:/~/:/
  \  \::/~~~~   \  \:\  /:/   \  \::/ /:/
   \  \:\        \  \::/:/     \__\/ /:/
    \  \:\        \  \::/        /__/:/   
     \__\/         \__\/         \__\/    
{RESET}""",

    # 24. Binary Style
    rf"""{BLUE}{BOLD}
01010000 01011001 01000111
01001001 01010100 01010101
01010000 [PYGITUP] 1.0
{RESET}""",

    # 25. Slant (Lean)
    rf"""{GREEN}{BOLD}
   __ _ _ _   _   _       
  / _(_) |_| | | |_ __  
 | | | | __| | | | '_ \ 
 | |_| | |_| |_| | |_) |
  \__,_|\__|_\___/| .__/
                 |_|    
{RESET}""",

    # 26. Blocky 2
    rf"""{YELLOW}{BOLD}
.---.       .-. .---. . . .-. .-. 
|   )      (   )|---  | |  |  |-' 
|---  '     `--''     `-'  '  '   
|                                 
{RESET}""",

    # 27. Ghost Style
    rf"""{RED}{BOLD}
.-. .-. .-. .-. .-. .-. .-. 
| | | | | | | | | | | | | | 
|-' `-' `-' `-' `-' `-' |-' 
|                       '   
{RESET}""",

    # 28. Standard Sans
    rf"""{WHITE}{BOLD}
 ___  _ _  ___  _  ___  _ _  ___
| . \| | ||  _>| ||_ _|| | || . \
|  _/`_. || <_ | | | | | | ||  _/
|_|  <___|`___/|_| |_| `___/|_|  
{RESET}""",

    # 29. Bold Script
    rf"""{CYAN}{BOLD}
  _ __ _ _  __ _ _ _  _ _ __ 
 | '_ \ | |/ _` | | | | | '_ \
 | |_) | | | (_| | | |_| | |_) |
 | .__/|_|_|\__, |_|\__,_| .__/
 |_|        |___/        |_|    
{RESET}""",

    # 30. Dot Matrix
    rf"""{MAGENTA}{BOLD}
::: ::: :::::: ::: ::: ::: ::: ::: :::
::: ::: ::     :::  ::  :: ::: ::: :::
::::::  :::::  :::  ::  :: ::: ::: :::::
   :::  ::     :::  ::  :: ::: ::: :::
   :::  :::::: :::  ::  :: ::::::  :::
{RESET}"""
]

def show_banner():
    """Displays a random animated banner from the collection."""
    # Clear screen based on OS
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Pick a random banner
    banner = random.choice(BANNERS)
    
    # Print the ASCII art directly
    print(banner)
    
    # Typewriter effect for the subtitle
    subtitle = f"{WHITE}>>> Effortless GitHub Workflow Automation <<<{RESET}\n"
    for char in subtitle:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.01) # Slightly faster for variety
    
    print("-" * 50)