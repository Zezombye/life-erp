#Requires AutoHotkey v2.0
#SingleInstance Force

global API_BASE := "http://localhost:8000"
global currentTimerId := ""
global currentActivity := ""
global currentState := "idle" ; idle | running | paused

; ── GUI ──
MyGui := Gui("-Caption +ToolWindow +LastFound +AlwaysOnTop")
MyGui.BackColor := "333333"
MyGui.SetFont("cWhite s11", "Consolas")

activityText := MyGui.AddText("x5 y5 w90 BackgroundTrans", "No timer")
timeText := MyGui.AddText("x+5 y5 w50 BackgroundTrans", "")
btn := MyGui.AddButton("x+2 y2 w30 h25", "▶")
btn.OnEvent("Click", OnBtnClick)

; ── Embed in taskbar ──
taskbarHwnd := WinExist("ahk_class Shell_TrayWnd")
MyGui.Show("Hide")
DllCall("SetParent", "ptr", MyGui.Hwnd, "ptr", taskbarHwnd)
MyGui.Show("x900 y5 w190 h30 NoActivate")

; ── Poll API every 2 seconds ──
SetTimer PollTimers, 2000
PollTimers()

PollTimers(*) {
    global currentTimerId, currentActivity, currentState
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", API_BASE "/api/habits/timer", false)
        whr.Send()
        if (whr.Status != 200) {
            SetDisplay("API error", "", "idle")
            return
        }
        body := whr.ResponseText
        ; Parse JSON array of timers — find the first active one
        ; Simple parsing: look for "id":"...", "activity":"...", "started_at":..., "paused_at":..., "accumulated_ms":...
        timers := ParseTimerArray(body)
        if (timers.Length = 0) {
            SetDisplay("No timer", "", "idle")
            currentTimerId := ""
            currentActivity := ""
            currentState := "idle"
            return
        }
        ; Use the first timer
        t := timers[1]
        currentTimerId := t["id"]
        currentActivity := t["activity"]
        isPaused := t["paused_at"] != ""
        elapsedMs := t["accumulated_ms"]
        if (!isPaused && t["started_at"] != "") {
            ; Add time since started_at to accumulated_ms
            startedUtc := ISOToUnixMs(t["started_at"])
            nowUtc := DateToUnixMs(A_NowUTC)
            elapsedMs += (nowUtc - startedUtc)
        }
        elapsedMn := Floor(elapsedMs / 60000)
        state := isPaused ? "paused" : "running"
        currentState := state
        SetDisplay(currentActivity, elapsedMn "mn", state)
    } catch as e {
        SetDisplay("Offline", "", "idle")
    }
}

SetDisplay(activity, timeStr, state) {
    activityText.Value := activity
    timeText.Value := timeStr
    if (state = "running") {
        MyGui.BackColor := "15803d" ; green
        btn.Text := "⏸"
    } else if (state = "paused") {
        MyGui.BackColor := "b45309" ; orange
        btn.Text := "▶"
    } else {
        MyGui.BackColor := "333333"
        btn.Text := "▶"
    }
}

OnBtnClick(*) {
    global currentTimerId, currentState
    if (currentTimerId = "" || currentState = "idle")
        return
    try {
        action := currentState = "running" ? "pause" : "resume"
        payload := '{"action":"' action '","timer_id":"' currentTimerId '","timestamp":"' FormatTime(A_NowUTC, "yyyy-MM-ddTHH:mm:ss") 'Z"}'
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", API_BASE "/api/habits/timer", false)
        whr.SetRequestHeader("Content-Type", "application/json")
        whr.Send(payload)
        ; Immediately refresh
        PollTimers()
    } catch as e {
        ; ignore
    }
}

; ── JSON helpers ──
; Minimal JSON array-of-objects parser for the timer endpoint
ParseTimerArray(json) {
    result := []
    ; Remove outer brackets
    json := Trim(json)
    if (SubStr(json, 1, 1) != "[")
        return result
    json := SubStr(json, 2, StrLen(json) - 2)
    ; Split by },{ to get individual objects
    if (json = "")
        return result
    ; Collect objects
    depth := 0
    objStart := 1
    Loop Parse, json {
        if (A_LoopField = "{")
            depth++
        else if (A_LoopField = "}") {
            depth--
            if (depth = 0) {
                objStr := SubStr(json, objStart, A_Index - objStart + 1)
                obj := ParseTimerObj(objStr)
                result.Push(obj)
                objStart := A_Index + 2 ; skip comma
            }
        }
    }
    return result
}

ParseTimerObj(json) {
    obj := Map()
    obj["id"] := ExtractJsonStr(json, "id")
    obj["activity"] := ExtractJsonStr(json, "activity")
    obj["started_at"] := ExtractJsonStr(json, "started_at")
    obj["paused_at"] := ExtractJsonStr(json, "paused_at")
    obj["accumulated_ms"] := ExtractJsonNum(json, "accumulated_ms")
    return obj
}

ExtractJsonStr(json, key) {
    needle := '"' key '":"'
    pos := InStr(json, needle)
    if (!pos) {
        ; Check for null value
        needleNull := '"' key '":null'
        if InStr(json, needleNull)
            return ""
        return ""
    }
    start := pos + StrLen(needle)
    endPos := InStr(json, '"', , start)
    if (!endPos)
        return ""
    return SubStr(json, start, endPos - start)
}

ExtractJsonNum(json, key) {
    needle := '"' key '":'
    pos := InStr(json, needle)
    if (!pos)
        return 0
    start := pos + StrLen(needle)
    numStr := ""
    Loop Parse, SubStr(json, start) {
        if (A_LoopField = "," || A_LoopField = "}" || A_LoopField = " ")
            break
        numStr .= A_LoopField
    }
    return Number(numStr)
}

ISOToUnixMs(isoStr) {
    ; Parse "2026-05-26T14:30:00Z" or "2026-05-26T14:30:00"
    isoStr := StrReplace(isoStr, "Z", "")
    isoStr := StrReplace(isoStr, "T", "")
    isoStr := StrReplace(isoStr, "-", "")
    isoStr := StrReplace(isoStr, ":", "")
    ; Now it's like "20260526143000"
    return DateToUnixMs(isoStr)
}

DateToUnixMs(ahkDate) {
    ; AHK date difference from Unix epoch (19700101000000)
    diff := DateDiff(ahkDate, "19700101000000", "Seconds")
    return diff * 1000
}
