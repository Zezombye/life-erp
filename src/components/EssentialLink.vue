<template>
    <a :href="props.link" target="_blank" class="flex items-center gap-2 p-2 hover:bg-zinc-800 rounded">
        <i v-if="props.icon" :class="'pi pi-' + props.icon" />
        <div>
            <div>{{ props.title }}</div>
            <div class="text-sm opacity-60">{{ props.caption }}</div>
        </div>
    </a>
</template>

<script setup lang="ts">
const props = defineProps({
    title: {
        type: String,
        required: true
    },

    caption: {
        type: String,
        default: ''
    },

    link: {
        type: String,
        default: '#'
    },

    icon: {
        type: String,
        default: ''
    }
})
</script>
