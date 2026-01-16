
"""Small Tkinter utility to display cursor position and RGB color at the cursor.

Implementation uses WinAPI (GDI) BitBlt + GetDIBits for robust pixel reads
under Per-Monitor V2 DPI awareness.
"""

from __future__ import annotations

import ctypes
from typing import Optional, Tuple

import ctypes.wintypes as wt
import tkinter as tk

# Refresh interval in milliseconds.
REFRESH_MS = 200

# --- Make the process DPI aware (Per-Monitor V2) to obtain physical coordinates ---
try:
    USER32 = ctypes.windll.user32
    # -4 = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    USER32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    # Fall back silently if not supported (older Windows).
    pass

# --- WinAPI / GDI handles ---
GDI32 = ctypes.windll.gdi32
USER32 = ctypes.windll.user32

# Constants
SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


# ---- Types and structures ----
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        # We do not use a palette, but the structure requires this field.
        ("bmiColors", wt.DWORD * 3),
    ]


# ---- Selected WinAPI function aliases (readability) ----
GetDC = USER32.GetDC
ReleaseDC = USER32.ReleaseDC
GetCursorPos = USER32.GetCursorPos
CreateCompatibleDC = GDI32.CreateCompatibleDC
DeleteDC = GDI32.DeleteDC
CreateCompatibleBitmap = GDI32.CreateCompatibleBitmap
SelectObject = GDI32.SelectObject
DeleteObject = GDI32.DeleteObject
BitBlt = GDI32.BitBlt
GetDIBits = GDI32.GetDIBits

# Global screen DC. Released on app exit.
HDC_SCREEN = GetDC(0)


def get_cursor_pos() -> Tuple[int, int]:
    """Return global cursor coordinates (screen space) via WinAPI.

    Raises:
        OSError: When GetCursorPos fails.
    """
    point = wt.POINT()
    if not GetCursorPos(ctypes.byref(point)):
        raise OSError("GetCursorPos failed")
    return point.x, point.y


def get_pixel_rgb_via_blit(x: int, y: int) -> Optional[Tuple[int, int, int]]:
    """Return (r, g, b) for the pixel at (x, y) using BitBlt + GetDIBits.

    This "bulletproof" approach copies a 1x1 region from the screen into a
    compatible memory DC and reads pixel data as 32-bit BGRA. It is more
    reliable than GetPixel across various DPI/compositing configurations.

    Args:
        x: Screen X coordinate.
        y: Screen Y coordinate.

    Returns:
        A tuple (r, g, b) if successful, otherwise None.
    """
    memdc = CreateCompatibleDC(HDC_SCREEN)
    if not memdc:
        return None

    hbitmap = CreateCompatibleBitmap(HDC_SCREEN, 1, 1)
    if not hbitmap:
        DeleteDC(memdc)
        return None

    old_obj = SelectObject(memdc, hbitmap)
    if not old_obj:
        DeleteObject(hbitmap)
        DeleteDC(memdc)
        return None

    try:
        # Copy a 1x1 area from the screen into the memory DC.
        ok = BitBlt(memdc, 0, 0, 1, 1, HDC_SCREEN, x, y, SRCCOPY)
        if not ok:
            return None

        # Prepare BITMAPINFO for 32-bit BGRA, top-down (negative height).
        bmi = BITMAPINFO()
        ctypes.memset(ctypes.byref(bmi), 0, ctypes.sizeof(bmi))
        header = bmi.bmiHeader
        header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        header.biWidth = 1
        header.biHeight = -1  # top-down DIB for easier reads
        header.biPlanes = 1
        header.biBitCount = 32
        header.biCompression = BI_RGB
        header.biSizeImage = 0

        # Buffer for a single pixel (BGRA: 4 bytes).
        pixel = (ctypes.c_ubyte * 4)()

        # Retrieve the raw pixel data into the buffer.
        scanlines = GetDIBits(
            HDC_SCREEN,
            hbitmap,
            0,
            1,
            ctypes.byref(pixel),
            ctypes.byref(bmi),
            DIB_RGB_COLORS,
        )
        if scanlines != 1:
            return None

        # Convert BGRA -> RGB (ignore alpha).
        b_val, g_val, r_val, _a_val = pixel[0], pixel[1], pixel[2], pixel[3]
        return int(r_val), int(g_val), int(b_val)
    finally:
        # Clean up GDI resources.
        SelectObject(memdc, old_obj)
        DeleteObject(hbitmap)
        DeleteDC(memdc)


class App(tk.Tk):
    """Tkinter UI that shows cursor position and the RGB color at the cursor."""

    def __init__(self) -> None:
        super().__init__()
        self.title("RGB + Cursor Position (GDI BitBlt, DPI-aware)")
        self.resizable(False, False)
        # Optional: keep the window always on top.
        # self.attributes("-topmost", True)

        self.x_var = tk.StringVar(value="X: —")
        self.y_var = tk.StringVar(value="Y: —")
        self.rgb_var = tk.StringVar(value="RGB: —, —, —")

        tk.Label(self, textvariable=self.x_var, font=("Segoe UI", 12)).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        tk.Label(self, textvariable=self.y_var, font=("Segoe UI", 12)).pack(
            anchor="w", padx=10, pady=4)
        tk.Label(self, textvariable=self.rgb_var, font=("Segoe UI", 12, "bold")
                 ).pack(anchor="w", padx=10, pady=4)

        self.swatch = tk.Canvas(
            self, width=60, height=28, highlightthickness=1, highlightbackground="#666"
        )
        self.swatch.pack(padx=10, pady=(8, 10))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(REFRESH_MS, self.update_loop)

    def update_loop(self) -> None:
        """Periodic UI update: cursor pos, RGB read, and swatch repaint."""
        try:
            x, y = get_cursor_pos()
            self.x_var.set(f"X: {x}")
            self.y_var.set(f"Y: {y}")

            rgb = get_pixel_rgb_via_blit(x, y)
            if rgb is None:
                self.rgb_var.set("RGB: read error")
            else:
                r_val, g_val, b_val = rgb
                self.rgb_var.set(f"RGB: {r_val}, {g_val}, {b_val}")
                hex_color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
                self.swatch.delete("all")
                self.swatch.create_rectangle(0, 0, 60, 28, fill=hex_color, outline="")
        except Exception:
            self.rgb_var.set("RGB: read error")

        self.after(REFRESH_MS, self.update_loop)

    def on_close(self) -> None:
        """Release screen DC and close the window."""
        try:
            ReleaseDC(0, HDC_SCREEN)
        finally:
            self.destroy()


def main() -> None:
    """Entry-point to start the Tkinter app."""
    App().mainloop()


if __name__ == "__main__":
    main()
