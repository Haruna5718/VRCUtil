<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string = "";
    export let Attr:{[key: string]: string}={};
    export let ModuleName:string = "";
</script>
<span>
    <label for="switch-{Attr.value}" class:disabled={LayoutValue[Attr.disable]} style="
    order: {LayoutValue[Attr.aligin]=="Left"?2:0};
    ">
        {LayoutValue[Attr.value]?"ON":"OFF"}
    </label>
    <input id="switch-{Attr.value}" type="checkbox" checked={LayoutValue[Attr.value]} on:input={()=>window.GetValue(ModuleName, Attr.value,!LayoutValue[Attr.value])} disabled={LayoutValue[Attr.disable]} style="
        margin: {LayoutValue[Attr.margin] ?? '0'};
    " />
</span>
<slot />
<style lang="scss">
    span{
        gap: 5px;
        display: flex;
		flex-direction: row;
        align-items: center;
    }
    label{
        user-select: none;
        color: #ffffff;
        height: 24px;
        line-height: 24px;
        &:not(.disabled){
            cursor: pointer;
            &:hover{
                filter: brightness(90%);
            }
        }
        &.disabled{
            filter: brightness(70%);
            cursor: not-allowed;
        }
    }
    input{
        transition: filter 0.1s ease-out, border 0.1s ease-out;
        order: 1;
        height: 24px;
        width: 44px;
        &:not([disabled]){
            cursor: pointer;
            &:hover{
                &:not(:checked){
                    filter: brightness(120%);
                }
                &:checked{
                    filter: brightness(90%);
                }
            }
        }
        &[disabled] {
            filter: brightness(70%);
            cursor: not-allowed;
        }
        &::before{
            content: "";
            position: absolute;
            background-color: #272727;
            width: 40px;
            border-radius: 12px;
            border: 2px solid #ffffff50;
            height: 20px;
            transition: border 0.1s ease-in-out, background-color 0.1s ease-in-out;
        }
        &::after{
            content: "";
            margin: 4px;
            position: absolute;
            background-color: #ffffff;
            width: 16px;
            border-radius: 8px;
            height: 16px;
            transform: translateX(0px);
            transition: transform 0.1s ease-in-out, background-color 0.1s ease-in-out;
        }
        &:checked{
            &::before{
                background-color: #ffffff;
                border: 2px solid #ffffff;
            }
            &::after{
                background-color: #272727;
                transform: translateX(20px);
            }
        }
	}
</style>