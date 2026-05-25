import {defineBoot} from '#q-app/wrappers';
import {error, warn} from "src/lib/logging";

export default defineBoot(() => {

    window.addEventListener('unhandledrejection', (e) => {
        error(e)
    })
    window.addEventListener('error', (e) => {
        error(e);
    })

        // Intercept console.warn/error to show toast notifications
        ; (console as any)._warn = console.warn
    console.warn = (...args: any[]) => {
        warn(...args)
    }
        ; (console as any)._error = console.error
    console.error = (...args: any[]) => {
        error(...args)
    }
})
