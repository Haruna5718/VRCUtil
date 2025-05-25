<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string = "";
    export let Attr:{[key: string]: string}={};
    export let ModuleName:string = "";
</script>
<input type={LayoutValue[Attr.type]} max={LayoutValue[Attr.max]} min={LayoutValue[Attr.min]} value={LayoutValue[Attr.value]} on:input={(e)=>window.GetValue(ModuleName, Attr.value,e.currentTarget.value)} disabled={LayoutValue[Attr.disable]} style="
    color: {LayoutValue[Attr.color] ?? '#fff'};
    background-color: {LayoutValue[Attr.background] ?? '#272727'};
    font-size: {LayoutValue[Attr.size] ?? '16px'};
    width: {LayoutValue[Attr.width] ?? 'auto'};
    height: {LayoutValue[Attr.height] ?? 'auto'};
    padding: {LayoutValue[Attr.padding] ?? '4.7px 6px'};
    margin: {LayoutValue[Attr.margin] ?? '0'};
    border-radius: {LayoutValue[Attr.round] ?? '5px'};
"/>
<slot />
<style lang="scss">
    input{
		border: 1px solid #00000040;
        border-bottom: 2px solid #ffffff30;
		outline: none;
        transition: border 0.1s ease-in-out;
        transition: filter 0.1s ease-out, border 0.1s ease-out, border-bottom 0.1s ease-out;
        line-height: 1.3em;
		&::-webkit-inner-spin-button,&::-webkit-outer-spin-button{
			appearance: none;
			margin: 0;
		}
        &:not([disabled]){
            &:hover{
                filter: brightness(90%) contrast(0.9);
                border-bottom: 2px solid #ffffff70;
            }
            &:focus{
                filter: brightness(100%) contrast(1.1);
                border-bottom: 2px solid #ffffff;
            }
        }
        &[disabled] {
            filter: brightness(80%);
            cursor: not-allowed;
        }
    }
</style>