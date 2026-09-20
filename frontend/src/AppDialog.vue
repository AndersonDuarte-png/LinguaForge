<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({ labelledBy: String, busy: Boolean })
const emit = defineEmits(['close'])
const dialog = ref(null)
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => dialog.value?.close())
</script>

<template>
  <dialog ref="dialog" class="modal" :aria-labelledby="labelledBy" @cancel="props.busy && $event.preventDefault()" @close="emit('close')">
    <slot />
  </dialog>
</template>
