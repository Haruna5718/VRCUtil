<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string = "";
    export let Attr:{[key: string]: string}={};
    export let ModuleName:string = "";

    let open=false
    let main=[]
</script>
<svelte:window on:click={(e)=>{if(!main.includes(e.target))open=false}}></svelte:window>
<span bind:this={main[0]}>
    <div class="main" class:disabled={LayoutValue[Attr.disable]} bind:this={main[1]} on:click={()=>{if(!LayoutValue[Attr.disable])open=!open}} style="
        color: {LayoutValue[Attr.color] ?? '#fff'};
        background-color: {LayoutValue[Attr.background] ?? '#454545'};
        font-size: {LayoutValue[Attr.size] ?? '16px'};
        width: {LayoutValue[Attr.width] ?? 'auto'};
        height: {LayoutValue[Attr.height] ?? 'auto'};
        padding: {LayoutValue[Attr.padding] ?? '0'};
        margin: {LayoutValue[Attr.margin] ?? '0'};
        border-radius: {LayoutValue[Attr.round] ?? '5px'};
    ">
        <p  bind:this={main[2]}>{LayoutValue[Attr.value]} <span style="top: 2px;" bind:this={main[3]}></span></p>
    </div>
    {#if open}
        <div class="menu" bind:this={main[4]} style="
            color: {LayoutValue[Attr.color] ?? '#fff'};
            background-color: {LayoutValue[Attr.background] ?? '#454545'};
            font-size: {LayoutValue[Attr.size] ?? '16px'};
            border-radius: {LayoutValue[Attr.round] ?? '5px'};
        ">
            {#each LayoutValue[Attr.options] as val}
                <div class="item" on:click={()=>window.GetValue(ModuleName, Attr.value,!LayoutValue[Attr.value])} style="
                    color: {LayoutValue[Attr.color] ?? '#fff'};
                    background-color: {LayoutValue[Attr.background] ?? '#454545'};
                    font-size: {LayoutValue[Attr.size] ?? '16px'};
                    border-radius: {LayoutValue[Attr.round] ?? '5px'};
                ">
                    {val}
                </div>
            {/each}
        </div>
    {/if}
</span>

<style lang="scss">
    .main{
        filter: brightness(100%);
		border: 1px solid #00000020;
        transition: filter 0.1s ease-out, border 0.1s ease-out;
        &:not(.disabled){
            cursor: pointer;
            &:hover{
                border: 1px solid #ffffff20;
            }
            &:active{
                filter: brightness(90%);
                border: 1px solid #ffffff20;
                p{
                    span{
                        top: 5px !important;
                    }
                }
            }
        }
        &.disabled{
            filter: brightness(70%);
            cursor: not-allowed;
        }
        p{
            margin: 8px;
            span{
                user-select: none;
                transition: top 0.1s ease-in;
            }
        }
	}
    @keyframes OnAnim {
        0%{
            transform: translateY(0px);
        }
        100%{
            transform: translateY(10px);
        }
    }
    .menu{
        animation : OnAnim 0.2s ease-out forwards alternate;
        z-index: 100;
        padding: 6px;
        position: absolute;
        max-width: none;
        width: fit-content;
        .item{
            padding: 6px;
            cursor: pointer;
            width: 100%;
            &:hover{
                filter: brightness(115%);
            }
            &:active{
                filter: brightness(90%);
            }
        }
    }
</style>