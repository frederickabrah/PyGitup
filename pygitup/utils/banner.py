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
    f"""{CYAN}{BOLD}
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
    f"""{MAGENTA}{BOLD}
██████╗ ██╗   ██╗ ██████╗ ██╗████████╗██╗   ██╗██████╗ 
██╔══██╗╚██╗ ██╔╝██╔════╝ ██║╚══██╔══╝██║   ██║██╔══██╗
██████╔╝ ╚████╔╝ ██║  ███╗██║   ██║   ██║   ██║██████╔╝
██╔═══╝   ╚██╔╝  ██║   ██║██║   ██║   ██║   ██║██╔═══╝ 
██║        ██║   ╚██████╔╝██║   ██║   ╚██████╔╝██║     
╚═╝        ╚═╝    ╚═════╝ ╚═╝   ╚═╝    ╚═════╝ ╚═╝     
{RESET}""",

    # 3. Slant Block
    f"""{BLUE}{BOLD}
    ____        ______(_) /  / /  / /___
   / __ \__  __/ ____/ / __/ / / / / __ \
  / /_/ / / / / / __/ / /_/ /_/ / / /_/ /
 / .___/\__, /_/___/_/\__/_/\____/_/ .___/ 
/_/    /____/                   /_/      
{RESET}""",

    # 4. 3D Diagonal
    f"""{GREEN}{BOLD}
    ____             __________ __  __  __   
   / __ \__  __     / ____/(_)_/ /_/ / / /___
  / /_/ / / / /    / / __/ / __/ __/ / / / __ \
 / ____/ /_/ /    / /_/ / / /_/ /_/ /_/ / /_/ /
/_/    \__, /     \____/_/\__/_/\____/ .___/ 
      /____/                          /_/      
{RESET}""",

    # 5. Rounded Block
    f"""{YELLOW}{BOLD}
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
    f"""{RED}{BOLD}
PYGITUP  >>>  SYSTEM READY
[ P Y G I T U P ]
{RESET}""",

    # 7. Iso Block
    f"""{WHITE}{BOLD}
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
    f"""{CYAN}{BOLD}
P Y G I T U P
#############
# CORE INIT #
#############
{RESET}""",

    # 9. DOS Style
    f"""{MAGENTA}{BOLD}
C:\> RUN PYGITUP.EXE
[████████████████] 100%
{RESET}""",

    # 10. Star Wars Style
    f"""{YELLOW}{BOLD}
PyGitUp
The Force of Git Automation
___________________________
{RESET}""",

    # 11. Bubble
    f"""{BLUE}{BOLD}
  _   _   _   _   _   _   _  
 / \ / \ / \ / \ / \ / \ / \
( P | y | G | i | t | U | p )
 \_/ \_/ \_/ \_/ \_/ \_/ \_/ 
{RESET}""",

    # 12. Digital
    f"""{GREEN}{BOLD}
 +-+-+-+-+-+-+-+
 |P|y|G|i|t|U|p|
 +-+-+-+-+-+-+-+
{RESET}""",

    # 13. Blocks & Lines
    f"""{RED}{BOLD}
||||| PYGITUP |||||
\\\ AUTOMATION /////
{RESET}""",

    # 14. Retro Computer
    f"""{WHITE}{BOLD}
***********************
*  P Y G I T U P  1.0 *
***********************
{RESET}""",

    # 15. Slash
    f"""{CYAN}{BOLD}
   / // / // / // / // / // / /
  / // / // / // / // / // / /
 / // / // / // / // / // / /
/ // / // / // / // / // / /
PYGITUP - GIT AUTOMATION
{RESET}""",

    # 16. Thick
    f"""{MAGENTA}{BOLD}
=========================
 P  Y  G  I  T  U  P
=========================
{RESET}""",

    # 17. Stencil
    f"""{YELLOW}{BOLD}
  P  Y  G  I  T  U  P  
 [=][=][=][=][=][=][=] 
{RESET}""",

    # 18. Minimal Block
    f"""{BLUE}{BOLD}
█▀█ █▄█ █▀▀ █ ▀█▀ █ █ █▀█
█▀▀  █  █▄█ █  █  █▄█ █▀▀
{RESET}""",

    # 19. Arrows
    f"""{GREEN}{BOLD}
>>>>> PYGITUP >>>>>
<<<<< AUTOMATION <<<<<
{RESET}""",

    # 20. Double Border
    f"""{RED}{BOLD}
╔═════════════════════╗
║      PYGITUP        ║
╚═════════════════════╝
{RESET}""",

    # 21. Gothic
    f"""{WHITE}{BOLD}
 ___        ____ _ _   _   _       
|  _ \ _   / ___(_) |_| | | |_ __  
| |_) | | | |  _| | __| | | | '_ \ 
|  __/| |_| | |_| | |_| |_| | |_) |
|_|    \__, |\____|_|\__|_\___/| .__/
       |___/                  |_|    
{RESET}""",

    # 22. Small Block
    f"""{CYAN}{BOLD}
┌─┐┬ ┬┌─┐┬┌┬┐┬ ┬┌─┐
├─┘└┬┘│ ┬│ │ │ │├─┘
┴   ┴ └─┘┴ ┴ └─┘┴  
{RESET}""",

    # 23. Isometric 3
    f"""{MAGENTA}{BOLD}
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
    f"""{BLUE}{BOLD}
01010000 01011001 01000111
01001001 01010100 01010101
01010000 [PYGITUP] 1.0
{RESET}""",

    # 25. Slant (Lean)
    f"""{GREEN}{BOLD}
   __ _ _ _   _   _       
  / _(_) |_| | | |_ __  
 | | | | __| | | | '_ \ 
 | |_| | |_| |_| | |_) |
  \__,_|\__|_\___/| .__/
                 |_|    
{RESET}""",

    # 26. Blocky 2
    f"""{YELLOW}{BOLD}
.---.       .-. .---. . . .-. .-. 
|   )      (   )|---  | |  |  |-' 
|---  '     `--''     `-'  '  '   
|                                 
{RESET}""",

    # 27. Ghost Style
    f"""{RED}{BOLD}
.-. .-. .-. .-. .-. .-. .-. 
| | | | | | | | | | | | | | 
|-' `-' `-' `-' `-' `-' |-' 
|                       '   
{RESET}""",

    # 28. Standard Sans
    f"""{WHITE}{BOLD}
 ___  _ _  ___  _  ___  _ _  ___
| . \| | ||  _>| ||_ _|| | || . \
|  _/`_. || <_ | | | | | | ||  _/
|_|  <___|`___/|_| |_| `___/|_|  
{RESET}""",

    # 29. Bold Script
    f"""{CYAN}{BOLD}
  _ __ _ _  __ _ _ _  _ _ __ 
 | '_ \ | |/ _` | | | | | '_ \
 | |_) | | | (_| | | |_| | |_) |
 | .__/|_|_|\__, |_|\__,_| .__/
 |_|        |___/        |_|    
{RESET}""",

    # 30. Dot Matrix
    f"""{MAGENTA}{BOLD}
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