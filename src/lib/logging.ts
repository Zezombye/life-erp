import type {useToast} from 'primevue/usetoast'

export const success = (msg: string) => {
    console.log(msg);
    const toast = (window as any).toast as ReturnType<typeof useToast>
    toast.add({severity: 'success', summary: 'Succès', detail: msg, life: 5000});
}
export const warn = (...args: any[]) => {
    ; (console as any)._warn(...args);
    if (args.length > 1 && typeof args[0] === 'string' && args[0].startsWith("[Vue warn]:")) {
        args = args.slice(0, 1); //remove custom Vue stacktrace
    }
    const msg = args.map(a => a instanceof Error ? a.message : a instanceof ErrorEvent ? a.message : a instanceof PromiseRejectionEvent ? a.reason : String(a)).map(x => ("" + x).replace(/^(Error|Erreur) ?: */, '')).join(' ');
    const toast = (window as any).toast as ReturnType<typeof useToast>
    toast.add({severity: 'warn', summary: 'Attention', detail: msg, life: 8000});
}
export const error = (...args: any[]) => {
    if (args.length > 1 && typeof args[0] === 'string' && !args[0].trim().endsWith(':')) {
        args[0] += ' :';
    }
    ; (console as any)._error(...args);
    const toast = (window as any).toast as ReturnType<typeof useToast>
    const msg = args.map(a => a instanceof Error ? a.message : a instanceof ErrorEvent ? a.message : a instanceof PromiseRejectionEvent ? a.reason : String(a)).map(x => ("" + x).replace(/^(Error|Erreur) ?: */, '')).join(' ');
    toast.add({severity: 'error', summary: 'Erreur', detail: msg, life: 10000});
}
