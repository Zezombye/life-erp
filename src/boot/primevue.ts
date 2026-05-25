import {defineBoot} from '#q-app/wrappers'
import PrimeVue from 'primevue/config';
import {definePreset} from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
import ToastService from 'primevue/toastservice';
import Tooltip from "primevue/tooltip";

const MyPreset = definePreset(Aura);

export default defineBoot(({app}) => {
    document.documentElement.classList.add('app-dark')
    app.use(PrimeVue, {
        theme: {
            preset: MyPreset,
            options: {
                darkModeSelector: '.app-dark'
            }
        }
    });
    app.use(ToastService);
    app.directive('tooltip', Tooltip);
})
