import ctypes
import customtkinter

from pywebwinui3.type import Status
from pywebwinui3.util import AccentColorWatcher

class ColorPalette:
    TextFillColorPrimary = ['#191919', '#FFFFFF']
    TextFillColorSecondary = ['#5C5C5C', '#CCCCCC']
    TextFillColorTertiary = ['#868686', '#969696']
    TextFillColorDisabled = ['#9B9B9B', '#717171']
    TextFillColorInverse = ['#FFFFFF', '#030303']
    
    AccentTextFillColorDisabled = ['#9B9B9B', '#717171']
    
    TextOnAccentFillColorSelectedText = ['#FFFFFF', '#FFFFFF']
    
    TextOnAccentFillColorPrimary = ['#FFFFFF', '#000000']
    TextOnAccentFillColorSecondary = ['#FBFBFB', '#0F0F0F']
    TextOnAccentFillColorDisabled = ['#FFFFFF', '#969696']
    
    ControlFillColorDefault = ['#FBFBFB', '#2D2D2D']
    ControlFillColorSecondary = ['#F6F6F6', '#323232']
    ControlFillColorTertiary = ['#F4F4F4', '#262626']
    ControlFillColorDisabled = ['#F4F4F4', '#292929']
    ControlFillColorTransparent = "transparent"
    ControlFillColorInputActive = ['#FFFFFF', '#1E1E1E']
    
    ControlStrongFillColorDefault = ['#868686', '#999999']
    ControlStrongFillColorDisabled = ['#A5A5A5', '#575757']
    
    ControlSolidFillColorDefault = ['#FFFFFF', '#454545']
    
    SubtleFillColorTransparent = "transparent"
    SubtleFillColorSecondary = ['#EAEAEA', '#2D2D2D']
    SubtleFillColorTertiary = ['#EDEDED', '#282828']
    SubtleFillColorDisabled = "transparent"
    
    ControlAltFillColorTransparent = "transparent"
    ControlAltFillColorSecondary = ['#EDEDED', '#1C1C1C']
    ControlAltFillColorTertiary = ['#E4E4E4', '#292929']
    ControlAltFillColorQuarternary = ['#DCDCDC', '#2F2F2F']
    ControlAltFillColorDisabled = "transparent"
    
    ControlOnImageFillColorDefault = ['#FCFCFC', '#1D1D1D']
    ControlOnImageFillColorSecondary = ['#F3F3F3', '#1A1A1A']
    ControlOnImageFillColorTertiary = ['#EBEBEB', '#131313']
    ControlOnImageFillColorDisabled = ['transparent', '#1E1E1E']
    
    AccentFillColorDisabled = ['#BEBEBE', '#424242']
    
    ControlStrokeColorDefault = ['#E4E4E4', '#2F2F2F']
    ControlStrokeColorSecondary = ['#CBCBCB', '#343434']
    ControlStrokeColorOnAccentDefault = ['#F3F3F3', '#313131']
    ControlStrokeColorOnAccentSecondary = ['#919191', '#1B1B1B']
    ControlStrokeColorOnAccentTertiary = ['#BEBEBE', '#191919']
    ControlStrokeColorOnAccentDisabled = ['#E4E4E4', '#191919']
    
    ControlStrokeColorForStrongFillWhenOnImage = ['#F7F7F7', '#121212']
    
    CardStrokeColorDefault = ['#E4E4E4', '#1C1C1C']
    CardStrokeColorDefaultSolid = ['#EBEBEB', '#1C1C1C']
    
    ControlStrongStrokeColorDefault = ['#868686', '#999999']
    ControlStrongStrokeColorDisabled = ['#BEBEBE', '#424242']
    
    SurfaceStrokeColorDefault = ['#C0C0C0', '#424242']
    SurfaceStrokeColorFlyout = ['#E4E4E4', '#191919']
    SurfaceStrokeColorInverse = ['#F3F3F3', '#1E1E1E']
    
    DividerStrokeColorDefault = ['#E4E4E4', '#323232']
    
    FocusStrokeColorOuter = ['#191919', '#FFFFFF']
    FocusStrokeColorInner = ['#FBFBFB', '#090909']
    
    CardBackgroundFillColorDefault = ['#FBFBFB', '#2B2B2B']
    CardBackgroundFillColorSecondary = ['#F4F4F4', '#262626']
    
    SmokeFillColorDefault = ['#A9A9A9', '#161616']
    
    LayerFillColorDefault = ['#F9F9F9', '#272727']
    LayerFillColorAlt = ['#FFFFFF', '#2B2B2B']
    LayerOnAcrylicFillColorDefault = ['#F6F6F6', '#272727']
    LayerOnAccentAcrylicFillColorDefault = ['#F6F6F6', '#272727']
    
    LayerOnMicaBaseAltFillColorDefault = ['#FBFBFB', '#2B2B2B']
    LayerOnMicaBaseAltFillColorSecondary = ['#E9E9E9', '#2D2D2D']
    LayerOnMicaBaseAltFillColorTertiary = ['#F9F9F9', '#2C2C2C']
    LayerOnMicaBaseAltFillColorTransparent = "transparent"
    
    SolidBackgroundFillColorBase = ['#F3F3F3', '#202020']
    SolidBackgroundFillColorSecondary = ['#EEEEEE', '#1C1C1C']
    SolidBackgroundFillColorTertiary = ['#F9F9F9', '#282828']
    SolidBackgroundFillColorQuarternary = ['#FFFFFF', '#2C2C2C']
    SolidBackgroundFillColorTransparent = "transparent"
    SolidBackgroundFillColorBaseAlt = ['#DADADA', '#0A0A0A']
    
    SystemFillColorSuccess = ['#0F7B0F', '#6CCB5F']
    SystemFillColorCaution = ['#9D5D00', '#FCE100']
    SystemFillColorCritical = ['#C42B1C', '#FF99A4']
    SystemFillColorNeutral = ['#868686', '#999999']
    SystemFillColorSolidNeutral = ['#8A8A8A', '#9D9D9D']
    SystemFillColorAttentionBackground = ['#F4F4F4', '#262626']
    SystemFillColorSuccessBackground = ['#DFF6DD', '#393D1B']
    SystemFillColorCautionBackground = ['#FFF4CE', '#433519']
    SystemFillColorCriticalBackground = ['#FDE7E9', '#442726']
    SystemFillColorNeutralBackground = ['#EDEDED', '#262626']
    SystemFillColorSolidAttentionBackground = ['#F7F7F7', '#2E2E2E']
    SystemFillColorSolidNeutralBackground = ['#F3F3F3', '#2E2E2E']

class AccentPalette:
    def __init__(self, palette):
        self.AccentFillColorSelectedTextBackground = palette[3]
        self.SystemFillColorAttention = [palette[3], palette[1]]
        self.AccentTextFillColorPrimary = [palette[5], palette[0]]
        self.AccentTextFillColorSecondary = [palette[6], palette[0]]
        self.AccentTextFillColorTertiary = [palette[4], palette[1]]
        self.AccentFillColorDefault = [palette[5], palette[1]]
        self.AccentFillColorSecondary = [self.darken(palette[4],0.1), self.darken(palette[1],0.1)]
        self.AccentFillColorTertiary = [self.darken(palette[4],0.2), self.darken(palette[1],0.2)]

    @staticmethod
    def darken(hex:str, factor:float = 0.1) -> str:
        r = max(0, int(int(hex[1:3], 16) * (1 - factor)))
        g = max(0, int(int(hex[3:5], 16) * (1 - factor)))
        b = max(0, int(int(hex[5:7], 16) * (1 - factor)))
        return f"#{r:02X}{g:02X}{b:02X}"

class AccentColorManager(AccentColorWatcher):
    def __init__(self, root:customtkinter.CTk):
        super().__init__()
        self.accentPalette = AccentPalette(self.palette)
        self.event += self.themeBroadcast
        self.root = root
        self.elements = []

    def themeBroadcast(self, color=None):
        self.palette = color or self.palette
        self.accentPalette = AccentPalette(self.palette)
        for element in self.elements:
            self.root.after(0, element.onAccentChange)

    def append(self, element):
        self.elements.append(element)
        self.root.after(0, element.onAccentChange)

    def remove(self, element):
        self.elements.remove(element)

class Button(customtkinter.CTkButton):
    ColorSet = [
        [
            None,
            None,
            ColorPalette.TextOnAccentFillColorPrimary
        ],
        [
            ColorPalette.SystemFillColorSuccess,
            ColorPalette.SystemFillColorSuccess,
            ColorPalette.TextOnAccentFillColorPrimary
        ],
        [
            ColorPalette.SystemFillColorCaution,
            ColorPalette.SystemFillColorCaution,
            ColorPalette.TextOnAccentFillColorPrimary
        ],
        [
            ColorPalette.SystemFillColorCritical,
            ColorPalette.SystemFillColorCritical,
            ColorPalette.TextOnAccentFillColorPrimary
        ],
        [
            ColorPalette.ControlFillColorDefault,
            ColorPalette.ControlFillColorSecondary,
            ColorPalette.TextOnAccentFillColorPrimary
        ]
    ]
    def __init__(self, master:customtkinter.CTk, acm:AccentColorManager, text:str, callback=None, color:Status=Status.Neutral, **kwargs):
        self.acm = acm
        self.color = color
        self.callback = callback
        self.enable = True
        super().__init__(master, text=text, command=self.onClick, text_color=self.ColorSet[self.color][2], **kwargs)
        
        if self.color == Status.Attention:
            self.acm.append(self)
        else:
            self.configure(fg_color=self.ColorSet[self.color][0], hover_color=self.ColorSet[self.color][1])

    def onClick(self):
        if self.callback:
            self.callback(self)

    def config(self, enable:bool, text=None):
        self.enable = enable
        self.configure(text=text or self._text, state="normal" if enable else "disabled", fg_color=(self.ColorSet[self.color][0] or self.acm.accentPalette.AccentFillColorDefault) if enable else ColorPalette.ControlFillColorDisabled)

    def onAccentChange(self):
        if self.color == Status.Attention and self.enable:
            self.configure(fg_color=self.acm.accentPalette.AccentFillColorDefault, hover_color=self.acm.accentPalette.AccentFillColorSecondary)

class ProgressBar(customtkinter.CTkProgressBar):
    ColorSet = [
        None,
        ColorPalette.SystemFillColorSuccess,
        ColorPalette.SystemFillColorCaution,
        ColorPalette.SystemFillColorCritical,
        None
    ]
    def __init__(self, master:customtkinter.CTk, acm:AccentColorManager, state:Status=Status.Attention, **kwargs):
        self.acm = acm
        super().__init__(master, **kwargs)
        self.config(state)
        self.set(0)

    def config(self, state:Status):
        self.state = state
        if self.state == Status.Attention:
            self.acm.append(self)
        else:
            self.configure(progress_color=self.ColorSet[self.state])

    def onAccentChange(self):
        if self.state==Status.Attention:
            self.configure(progress_color=self.acm.accentPalette.AccentFillColorDefault)

class CheckBox(customtkinter.CTkCheckBox):
    def __init__(self, master:customtkinter.CTk, acm:AccentColorManager, text:str, callback=None, **kwargs):
        self.variable=customtkinter.IntVar(value=0)
        super().__init__(master, text=text, variable=self.variable, command=self.onClick, checkmark_color=ColorPalette.TextOnAccentFillColorPrimary, height=24, **kwargs)
        self.callback = callback
        self.acm = acm
        self.acm.append(self)
    
    @property
    def value(self):
        return self.variable.get()

    def onClick(self, isCallback=True):
        self.configure(hover_color=self.acm.accentPalette.AccentFillColorSecondary if self.value else ColorPalette.ControlAltFillColorTertiary)
        if isCallback and self.callback:
            self.callback(self)

    def onAccentChange(self):
        self.configure(fg_color=self.acm.accentPalette.AccentFillColorDefault)
        self.onClick(isCallback=False)

class Textbox(customtkinter.CTkTextbox):
    def __init__(self, master:customtkinter.CTk, readonly=False, **kwargs):
        super().__init__(master, **kwargs)
        self.isReadonly = readonly

    def read(self, start="1.0", end="end"):
        return self.get(start, end).strip()

    def write(self, content:str, position="end"):
        if self.isReadonly:
            self.configure(state="normal")
        self.insert(position, content)
        self.see("end")
        if self.isReadonly:
            self.configure(state="disabled")

    def delete(self, start="1.0", end="end"):
        if self.isReadonly:
            self.configure(state="normal")
        super().delete(start, end)
        self.see("end")
        if self.isReadonly:
            self.configure(state="disabled")

    def readonly(self, state=True):
        self.isReadonly = state
        if self.isReadonly:
            self.configure(state="disabled")
        else:
            self.configure(state="normal")

# ========================================================

class App(customtkinter.CTk):
    def __init__(self, title:str, size:list[int], icon:str, resize:bool=True):
        super().__init__(fg_color=ColorPalette.SolidBackgroundFillColorBase)
        customtkinter.set_appearance_mode("system")
        self.acm = AccentColorManager(self)
        self.iconbitmap(icon)
        self.title(title)
        if not resize:
            self.after(0, lambda: self._setWinStyle())
            self.resizable(False, False)
        self._setCenter(*size)

    def _setWinStyle(self):
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -16)
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, -16, style & ~ 65536 & ~ 131072)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 2 | 1 | 4 | 32)

    def _setCenter(self, width, height):# fucking center
        scale = self._get_window_scaling()
        x=(self.winfo_screenwidth()*scale-width)//2#-90*scale
        y=(self.winfo_screenheight()*scale-height)//2#-90*scale
        self.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

    def start(self):
        self.acm.start()
        super().mainloop()

class Page(customtkinter.CTkFrame):
    def __init__(self, master, acm:AccentColorManager, round=0):
        super().__init__(master, fg_color=ColorPalette.SolidBackgroundFillColorQuarternary, corner_radius=round)
        self.master = master
        self.acm = acm