<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    // export let Text:string;
    export let Attr:{[key: string]: string}={};
</script>
<input type={LayoutValue[Attr.type]} value={LayoutValue[Attr.value]} on:change={()=>window.GetValue(Attr.value,LayoutValue[Attr.value])} disabled={LayoutValue[Attr.disable]} style="
    color: {LayoutValue[Attr.color] ?? '#fff'};
    background-color: {LayoutValue[Attr.background] ?? '#272727'};
    font-size: {LayoutValue[Attr.size] ?? '16px'};
    width: {LayoutValue[Attr.width] ?? 'auto'};
    height: {LayoutValue[Attr.height] ?? 'auto'};
    padding: {LayoutValue[Attr.padding] ?? '8px'};
    margin: {LayoutValue[Attr.margin] ?? '0'};
    border-radius: {LayoutValue[Attr.round] ?? '5px'};
"/>
<style lang="scss">
    input{
		border: 1px solid #00000020;
        border-bottom: 2px solid #ffffff30;
		outline: none;
        transition: border 0.1s ease-in-out;
		&::-webkit-inner-spin-button,&::-webkit-outer-spin-button{
			appearance: none;
			margin: 0;
		}
        &:hover{
            border-bottom: 2px solid #ffffff70;
        }
        &:focus{
            border-bottom: 2px solid #ffffff;
        }
    }
</style>