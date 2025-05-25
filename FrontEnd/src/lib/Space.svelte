<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string = "";
    export let Attr:{[key: string]: string}={};
    export let ModuleName:string = "";
</script>
<span style="
    width: {LayoutValue[Attr.size] ?? "auto"};
    height: {LayoutValue[Attr.size] ?? "auto"};
    {LayoutValue[Attr.size] ? '':"flex-grow: 1;"}
"/>
<slot />
<style lang="scss">
</style>