<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    // export let Text:string;
    export let Attr:{[key: string]: string}={};
    // export let ModuleName:string = "";
</script>
<hr style="border-color: {LayoutValue[Attr.color] ?? '#ffffff9f'}; height: {LayoutValue[Attr.thin] ?? '0px'}; margin: {LayoutValue[Attr.margin] ?? '10px 0px'};">
<style lang="scss">
hr{
    width: 100%;
    flex-grow: 1;
}
</style>