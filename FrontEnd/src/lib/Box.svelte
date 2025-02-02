<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    // export let Text:string;
    export let Attr:{[key: string]: string}={};
</script>
<div style="
    background-color: {LayoutValue[Attr.background] ?? '#ffffff0a'};
    height: {LayoutValue[Attr.height] ?? 'auto'};
    width: {LayoutValue[Attr.width] ?? 'auto'};
    margin: {LayoutValue[Attr.margin] ?? '0'};
    padding: {LayoutValue[Attr.padding] ?? '20px'};
    border-radius: {LayoutValue[Attr.round] ?? '5px'};
    gap: {LayoutValue[Attr.gap] ?? '5px'};
">
    <slot />
</div>
<style lang="scss">
    div{
        flex-grow: 1;
        flex-wrap: wrap;
        display: flex;
        align-items: center;
        flex-direction: column;
        align-self: stretch;
    }
</style>