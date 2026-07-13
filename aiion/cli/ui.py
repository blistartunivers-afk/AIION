"""aiion/cli/ui.py — Paleta Drácula/Neón y helpers de formato de terminal."""
from aiion.config import VERSION

R       = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
ITALIC  = "\033[3m"

# Drácula exacto
D_BG      = "\033[48;2;40;42;54m"       # #282A36 fondo
D_FG      = "\033[38;2;248;248;242m"    # #F8F8F2 texto
D_CYAN    = "\033[38;2;139;233;253m"    # #8BE9FD
D_GREEN   = "\033[38;2;80;250;123m"     # #50FA7B
D_YELLOW  = "\033[38;2;241;250;140m"    # #F1FA8C
D_ORANGE  = "\033[38;2;255;184;108m"    # #FFB86C
D_RED     = "\033[38;2;255;85;85m"      # #FF5555
D_PINK    = "\033[38;2;255;121;198m"    # #FF79C6
D_PURPLE  = "\033[38;2;189;147;249m"    # #BD93F9
D_COMMENT = "\033[38;2;98;114;164m"     # #6272A4

def c(col, txt):  return f"{col}{txt}{R}"
def bold(txt):    return f"{BOLD}{txt}{R}"
def dim(txt):     return f"{DIM}{txt}{R}"

# Aliases cortos para uso frecuente
CY = D_CYAN; GR = D_GREEN; YL = D_YELLOW
OR = D_ORANGE; RE = D_RED; PK = D_PINK
PU = D_PURPLE; CO = D_COMMENT


# Paleta Neón Degradado (Azul a Amarillo)
N_BORDER = "\033[38;2;0;180;255m"   # Azul neón eléctrico
N_L1     = "\033[38;2;0;120;255m"   # Azul neón
N_L2     = "\033[38;2;0;180;255m"   # Azul claro neón
N_L3     = "\033[38;2;0;240;255m"   # Cyan neón
N_L4     = "\033[38;2;0;255;150m"   # Verde-cyan neón
N_L5     = "\033[38;2;150;255;0m"   # Amarillo-verde neón
N_L6     = "\033[38;2;255;230;0m"   # Amarillo neón

BANNER = f"""
{c(N_BORDER+BOLD,'╔══════════════════════════════════════════════════╗')}
{c(N_BORDER+BOLD,'║')}  {c(N_L1+BOLD,' █████╗ ██╗██╗ ██████╗ ███╗   ██╗')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L2+BOLD,'██╔══██╗██║██║██╔═══██╗████╗  ██║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L3+BOLD,'███████║██║██║██║   ██║██╔██╗ ██║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L4+BOLD,'██╔══██║██║██║██║   ██║██║╚██╗██║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L5+BOLD,'██║  ██║██║██║╚██████╔╝██║ ╚████║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L6+BOLD,'╚═╝  ╚═╝╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}        {c(N_L6+BOLD, f'Agente Autónomo v{VERSION} — Android/Termux/PC')}     {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'╚══════════════════════════════════════════════════╝')}
"""

def hr(char='─', col=CO): return c(col, char * 52)

def badge(label, col=PU):
    return f"{c(col+BOLD, f'[{label}]')}"

