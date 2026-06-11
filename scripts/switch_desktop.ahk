#Requires AutoHotkey v2.0
#SingleInstance Force
#NoTrayIcon
;#Include VD.ahk
#WinActivateForce
SetWinDelay -1
SetControlDelay -1

accentKey := "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"

desktopColors := Map(
    "Desktop1", Map(
        "TaskbarAppBarColor", [40, 170, 255, 255],
        "TaskbarHighlightColor", [120, 255, 180, 255],
        "TaskbarColor", [0X00, 0x20, 0x38, 0x80], ;target: 10, 35, 55
        "AccentColorMenu", 0xFFB16300,
    ),
    "Desktop2", Map(
        "TaskbarAppBarColor", [255, 96, 32, 255],
        "TaskbarHighlightColor", [255, 210, 64, 255],
        "TaskbarColor", [0x47, 0x00, 0x06, 0x80], ;target: 64, 11, 18
        "AccentColorMenu", 0xFFB16301,
    )
)

if (A_Args[1] = "right") {
    HandleDesktopSwitch("right")
} else if (A_Args[1] = "left") {
    HandleDesktopSwitch("left")
} else {
    ToolTip("Invalid argument: " . A_Args[1])
}

HandleDesktopSwitch(direction) {
    global desktopColors

    profilePrefix := direction = "right" ? "Desktop2" : direction = "left" ? "Desktop1" : ""
    if (profilePrefix = "") {
        throw Error("Unknown desktop switch direction: " . direction)
    }

    if !desktopColors.Has(profilePrefix) {
        throw Error("Unknown desktop profile: " . profilePrefix)
    }

    profile := desktopColors[profilePrefix]
    SetTimer(() => TaskBar_SetColor(RgbaToAbgr(profile["TaskbarColor"])), -1)

    SwitchDesktop(direction)
    ;UpdateAccentPalette(profilePrefix)

    ;Sleep 1000
    ;ToolTip("Updated accent palette to " . profilePrefix)
    ;RefreshAccentColorMenu(profilePrefix)
}

RgbaToAbgr(rgbaBytes) {
    if (rgbaBytes.Length != 4) {
        throw Error("RGBA color must contain 4 bytes.")
    }

    r := rgbaBytes[1]
    g := rgbaBytes[2]
    b := rgbaBytes[3]
    a := rgbaBytes[4]

    for value in [r, g, b, a] {
        if (value < 0 || value > 255) {
            throw Error("RGBA byte out of range: " . value)
        }
    }

    return (a << 24) | (b << 16) | (g << 8) | r
}

TaskBar_SetColor(color_ABGR) {
    WCA_ACCENT_POLICY := 19

    ACCENT_POLICY := Buffer(16, 0)
    NumPut("int", 2, ACCENT_POLICY, 0)          ; AccentState = ACCENT_ENABLE_TRANSPARENTGRADIENT
    NumPut("int", color_ABGR, ACCENT_POLICY, 8) ; GradientColor

    WINCOMPATTRDATA := Buffer(A_PtrSize = 8 ? 24 : 12, 0)
    NumPut("int", WCA_ACCENT_POLICY, WINCOMPATTRDATA, 0)
    NumPut("ptr", ACCENT_POLICY.Ptr, WINCOMPATTRDATA, A_PtrSize = 8 ? 8 : 4)
    NumPut("uint", 16, WINCOMPATTRDATA, A_PtrSize = 8 ? 16 : 8)

    if (hTrayWnd := DllCall("user32\FindWindow", "str", "Shell_TrayWnd", "ptr", 0, "ptr"))
        DllCall("user32\SetWindowCompositionAttribute", "ptr", hTrayWnd, "ptr", WINCOMPATTRDATA.Ptr)

    hSecTray := DllCall("user32\FindWindow", "str", "Shell_SecondaryTrayWnd", "ptr", 0, "ptr")
    while hSecTray {
        DllCall("user32\SetWindowCompositionAttribute", "ptr", hSecTray, "ptr", WINCOMPATTRDATA.Ptr)
        hSecTray := DllCall("user32\FindWindowEx", "ptr", 0, "ptr", hSecTray, "str", "Shell_SecondaryTrayWnd", "ptr", 0,
            "ptr")
    }
}

SwitchDesktop(direction) {
    if (direction = "right") {
        Send "^#{Right}"
        ;VD.goToRelativeDesktopNum(+1)
    } else {
        ;VD.goToRelativeDesktopNum(-1)
        Send "^#{Left}"
    }
    WinMinimize "ahk_class Shell_TrayWnd"
    ;fix loading cursor on firefox
    MouseMove(1, 0, 0, "R")
    MouseMove(-1, 0, 0, "R")
}

UpdateAccentPalette(profilePrefix) {
    global accentKey
    global desktopColors

    if !desktopColors.Has(profilePrefix) {
        throw Error("Unknown desktop profile: " . profilePrefix)
    }

    profile := desktopColors[profilePrefix]

    palette := RegReadBinary(accentKey, "AccentPalette")
    if (StrLen(palette) != 64) {
        throw Error("AccentPalette must be 32 bytes (8 RGBA colors).")
    }

    palette := SetPaletteColor(palette, 2, profile["TaskbarAppBarColor"])
    palette := SetPaletteColor(palette, 4, profile["TaskbarHighlightColor"])
    palette := SetPaletteColor(palette, 7, profile["TaskbarColor"])

    RegWrite palette, "REG_BINARY", accentKey, "AccentPalette"
}

RefreshAccentColorMenu(profilePrefix) {
    global accentKey
    global desktopColors

    if !desktopColors.Has(profilePrefix) {
        throw Error("Unknown desktop profile: " . profilePrefix)
    }

    profile := desktopColors[profilePrefix]
    RegWrite profile["AccentColorMenu"], "REG_DWORD", accentKey, "AccentColorMenu"
}

SetPaletteColor(palette, colorIndex, rgbaBytes) {
    if (rgbaBytes.Length != 4) {
        throw Error("RGBA color must contain 4 bytes.")
    }

    if (colorIndex < 1 || colorIndex > 8) {
        throw Error("Color index must be between 1 and 8.")
    }

    startChar := ((colorIndex - 1) * 8) + 1
    newColorHex := ""
    loop 4 {
        byte := rgbaBytes[A_Index]
        if (byte < 0 || byte > 255) {
            throw Error("RGBA byte out of range: " . byte)
        }
        newColorHex .= Format("{:02X}", byte)
    }

    return SubStr(palette, 1, startChar - 1) . newColorHex . SubStr(palette, startChar + 8)
}

RegReadBinary(regPath, valueName) {
    value := RegRead(regPath, valueName)
    if (Type(value) != "String") {
        throw Error(valueName . " must be REG_BINARY.")
    }

    if (Mod(StrLen(value), 2) != 0) {
        throw Error(valueName . " must have even number of hex characters.")
    }

    return value
}
