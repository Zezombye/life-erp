#Requires AutoHotkey v2.0
#SingleInstance Force

; ==========================================
; 1. Create the Custom Windows 10-Style OSD
; ==========================================

global VolGui := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x08000000")
VolGui.BackColor := "000000" ; Dark Win 10 Background
;VolGui.MarginX := 15
;VolGui.MarginY := 15

; Add the vertical progress bar above the text
global barVol := VolGui.Add("Progress", "w11 h79 x27 y+20 c0078D7 Background333333 Vertical", 100)

; Add the decimal text at the bottom
VolGui.SetFont("s10 cWhite q5", "Segoe UI")
global txtVol := VolGui.Add("Text", "Center w65 x0 y107", "100.00")

; ==========================================
; 2. Bind the Hotkeys
; ==========================================
; The "$" prevents the script from triggering itself and blocks native Windows OSD

$Volume_Up:: ChangeVolume("Up")
$Volume_Down:: ChangeVolume("Down")

; ==========================================
; 3. Volume Logic and Math
; ==========================================

ChangeVolume(Direction) {
    ; Get exact current volume
    current := SoundGetVolume()

    increment := 1.10 ; 10% increment for geometric scaling

    if (Direction = "Up") {
        new_vol := current * increment

        ; Failsafe: If volume is 0, 0 * increment is still 0. This gives it a small bump to un-stick it.
        if (new_vol < 0.1)
            new_vol := 0.1
    }
    else {
        new_vol := current / increment
    }

    ; Cap values to prevent errors
    if (new_vol > 100.0)
        new_vol := 100.0
    else if (new_vol < 0.01)
        new_vol := 0.0

    ; Apply the new volume
    SoundSetVolume(new_vol)

    ; Update and show the popup
    ShowOSD(new_vol)
}

; ==========================================
; 4. Graphical Display Functions
; ==========================================

ShowOSD(vol) {
    ; Update the Text and the Progress Bar with the exact decimal
    txtVol.Value := Format("{:.2f}", vol)
    barVol.Value := vol

    ; Show the GUI roughly where Win 10 puts it (Top-Left), without stealing focus
    VolGui.Show("x50 y60 w65 h140 NoActivate")

    ; Apply slight transparency (255 is fully solid, 0 is invisible)
    WinSetTransparent(240, VolGui)

    ; Hide the GUI automatically after 2000 milliseconds (2 seconds)
    ; A negative timer means it only runs once and then stops
    SetTimer(HideOSD, -2000)
}

HideOSD() {
    VolGui.Hide()
}
