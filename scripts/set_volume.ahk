#Requires AutoHotkey v2.0
#SingleInstance Force

; ==========================================
; 1. Create the Custom Windows 10-Style OSD
; ==========================================

; ADDED -DPIScale HERE to prevent 1-pixel rounding overlaps
global VolGui := Gui("-DPIScale +AlwaysOnTop -Caption +ToolWindow +E0x08000000")
VolGui.BackColor := "000000" ; Dark Win 10 Background

; RECTANGLE 1: The Dark Grey Background Track (Static)
global trackBg := VolGui.Add("Text", "w11 h79 x27 y20 Background333333")

; RECTANGLE 2: The Blue Filled Track (Dynamic height and Y position)
global trackFill := VolGui.Add("Text", "w11 h0 x27 y99 Background0078D7")

; RECTANGLE 3: The White Square Thumb (Dynamic Y position)
global thumb := VolGui.Add("Text", "w11 h11 x27 y88 BackgroundWhite")

; Add the decimal text at the bottom
VolGui.SetFont("s10 cWhite q5", "Segoe UI")
global txtVol := VolGui.Add("Text", "Center w65 x0 y107", "100.00")

; ==========================================
; 2. Bind the Hotkeys
; ==========================================

$Volume_Up:: ChangeVolume("Up")
$Volume_Down:: ChangeVolume("Down")

; ==========================================
; 3. Volume Logic and Math
; ==========================================

ChangeVolume(Direction) {
    current := SoundGetVolume()
    increment := 1.10 ; 10% increment for geometric scaling

    if (Direction = "Up") {
        new_vol := current * increment
        if (new_vol < 0.1)
            new_vol := 0.1
    }
    else {
        new_vol := current / increment
    }

    if (new_vol > 100.0)
        new_vol := 100.0
    else if (new_vol < 0.01)
        new_vol := 0.0

    SoundSetVolume(new_vol)
    ShowOSD(new_vol)
}

; ==========================================
; 4. Graphical Display Functions
; ==========================================

ShowOSD(vol) {
    txtVol.Value := Format("{:.2f}", vol)

    ; --- Calculate the 3 Rectangles ---
    barHeight := 79
    barY := 20
    thumbHeight := 11

    ; 1. Move the White Thumb
    travelArea := barHeight - thumbHeight
    thumbY := Round(barY + travelArea * (1 - (vol / 100)))

    ; 2. Resize and Move the Blue Fill
    fillY := thumbY + thumbHeight
    fillBottom := barY + barHeight
    fillHeight := fillBottom - fillY

    ; Apply coordinates using AHK v2 object methods
    trackFill.Move(, fillY, , fillHeight)
    thumb.Move(, thumbY)

    ; Redraw ensures no visual ghosting between the two touching boundaries
    thumb.Redraw()

    ; Show the GUI
    VolGui.Show("x50 y60 w65 h140 NoActivate")
    WinSetTransparent(240, VolGui)

    ; Hide the GUI automatically after 2000 milliseconds
    SetTimer(HideOSD, -2000)
}

HideOSD() {
    VolGui.Hide()
}
