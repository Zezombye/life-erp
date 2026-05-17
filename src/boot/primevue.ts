import {defineBoot} from '#q-app/wrappers'
import PrimeVue from 'primevue/config';
import {definePreset} from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
import ToastService from 'primevue/toastservice';
import Tooltip from "primevue/tooltip";

// TODO update to match current KC Theme
const MyPreset = definePreset(Aura);

export default defineBoot(({app}) => {
    app.use(PrimeVue, {
        theme: {
            preset: MyPreset,
            options: {
                darkModeSelector: '.never-dark-mode'
            }
        }
    });
    app.use(ToastService);
    app.directive('tooltip', Tooltip);
    // app.component('Toast', Toast);
})
