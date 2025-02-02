<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    // export let Text:string;
    export let Attr:{[key: string]: string}={};
</script>
<span style="gap: {LayoutValue[Attr.gap] ?? 'inherit'};">
    <slot />
</span>
<style lang="scss">
    span{
        align-self: stretch;
        display: flex;
		flex-direction: row;
    }
</style>