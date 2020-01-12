import sys
assert sys.platform == 'win32'

from ctypes import POINTER  # noqa: E402
from ctypes import windll  # noqa: E402
from ctypes import WinError  # noqa: E402
from ctypes import WINFUNCTYPE  # noqa: E402
from ctypes.wintypes import BOOL  # noqa: E402
from ctypes.wintypes import DWORD  # noqa: E402
from ctypes.wintypes import HANDLE  # noqa: E402


STD_OUTPUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4


def bool_errcheck(result, func, args):
    if not result:
        raise WinError()
    return args


GetStdHandle = WINFUNCTYPE(HANDLE, DWORD)(
    ('GetStdHandle', windll.kernel32), ((1, 'nStdHandle'),),
)

GetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, POINTER(DWORD))(
    ('GetConsoleMode', windll.kernel32),
    ((1, 'hConsoleHandle'), (2, 'lpMode')),
)
GetConsoleMode.errcheck = bool_errcheck

SetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, DWORD)(
    ('SetConsoleMode', windll.kernel32),
    ((1, 'hConsoleHandle'), (1, 'dwMode')),
)
SetConsoleMode.errcheck = bool_errcheck


def enable_virtual_terminal_processing():
    """As of Windows 10, the Windows console supports (some) ANSI escape
    sequences, but it needs to be enabled using `SetConsoleMode` first.

    More info on the escape sequences supported:
    https://msdn.microsoft.com/en-us/library/windows/desktop/mt638032(v=vs.85).aspx
    """
    stdout = GetStdHandle(STD_OUTPUT_HANDLE)
    flags = GetConsoleMode(stdout)
    SetConsoleMode(stdout, flags | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
