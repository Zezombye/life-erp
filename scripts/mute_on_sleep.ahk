#Requires AutoHotkey v2.0
Persistent() ; Keeps the script running in the background (only needed if running as a standalone script without hotkeys)

; Listen for the Windows Power Broadcast message (0x0218)
OnMessage(0x0218, OnPowerBroadcast)

; Variable to remember the mute state before sleeping
global WasMutedBeforeSleep := false

OnPowerBroadcast(wParam, lParam, msg, hwnd) {
    global WasMutedBeforeSleep

    ; PBT_APMSUSPEND = 0x0004 (System is about to sleep)
    if (wParam = 0x0004) {

        ; 1. Check and save the current mute state
        WasMutedBeforeSleep := SoundGetMute()

        ; 2. Mute the system sound
        SoundSetMute(true)
    }

    ; PBT_APMRESUMESUSPEND = 0x0007 (System manually resumed by user)
    ; PBT_APMRESUMEAUTOMATIC = 0x0012 (System woke up automatically in the background)
    else if (wParam = 0x0007 || wParam = 0x0012) {

        ; 1. Only unmute if it wasn't already muted before it went to sleep
        if (WasMutedBeforeSleep = false) {
            SoundSetMute(false)
        }
    }

    return 1 ; Acknowledge to Windows that the message was received
}
