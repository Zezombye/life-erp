#Requires AutoHotkey v2.0

; 1. Create a borderless, tool-window GUI
MyGui := Gui("-Caption +ToolWindow +LastFound")
MyGui.BackColor := "1E1E1E" ; Dark background matching taskbar
MyGui.SetFont("cWhite s12", "Consolas")

; 2. Add Timer Text and Button
timeText := MyGui.AddText("x5 y5 w60 BackgroundTrans", "00:00")
btn := MyGui.AddButton("x+0 y2 w30 h25", "▶")
btn.OnEvent("Click", ToggleTimer)

; 3. Find the Windows Taskbar
taskbarHwnd := WinExist("ahk_class Shell_TrayWnd")

; 4. Show the GUI hidden first so we can attach it
MyGui.Show("Hide")

; 5. The Magic Trick: Parent our GUI to the Taskbar
DllCall("SetParent", "ptr", MyGui.Hwnd, "ptr", taskbarHwnd)

; 6. Position the timer at FIXED coordinates (relative to the taskbar)
; Change x1000 to move it left or right. y5 keeps it centered vertically.
MyGui.Show("x1000 y5 w100 h30 NoActivate")

; --- Timer Logic ---
global isRunning := false
global ticks := 0

ToggleTimer(*) {
    global isRunning
    if isRunning {
        SetTimer UpdateTime, 0     ; Stop timer
        btn.Text := "▶"
    } else {
        SetTimer UpdateTime, 1000  ; Start timer (1000 ms)
        btn.Text := "⏸"
    }
    isRunning := !isRunning
}

UpdateTime() {
    global ticks
    ticks++
    mins := Format("{:02}", ticks // 60)
    secs := Format("{:02}", Mod(ticks, 60))
    timeText.Value := mins ":" secs
}
