<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string = "";
    export let Attr:{[key: string]: string}={};
    export let ModuleName:string = "";

    let open=false
    let main=[]

    function ConvertText(source) {
		const grouped = [];
		const regex = /[\uE700-\uF800]+|[^\uE700-\uF800]+/g;
		let match;
		while ((match = regex.exec(source)) !== null) {
			const Text = match[0];
			const Type = /^[\uE700-\uF800]+$/.test(Text) ? "Icon" : "Text";
			grouped.push({Type, Text});
		}
		return grouped;
	}
</script>
<svelte:window on:click={(e)=>{if(!main.includes(e.target))open=false}}></svelte:window>
<span bind:this={main[0]} style="
    width: {LayoutValue[Attr.width] ?? 'auto'};
    height: {LayoutValue[Attr.height] ?? 'auto'};
    font-size: {LayoutValue[Attr.size] ?? '16px'};
    color: {LayoutValue[Attr.color] ?? '#fff'};
"> 

    <button class="main" class:disabled={LayoutValue[Attr.disable]} bind:this={main[1]} on:click={()=>{if(!LayoutValue[Attr.disable])open=!open}} style="
        color: {LayoutValue[Attr.color] ?? '#fff'};
        background-color: {LayoutValue[Attr.background] ?? '#454545'};
        margin: {LayoutValue[Attr.margin] ?? '0'};
        border-radius: {LayoutValue[Attr.round] ?? '5px'};
    ">
        <p style="padding: {LayoutValue[Attr.padding] ?? '0'}" bind:this={main[2]}>
            {#each ConvertText(LayoutValue[Attr.value]) as data,ind}
                <p style="top: {data.Type=='Icon'?2:0}px;" bind:this={main[5+ind]}>{data.Text}</p>
            {/each}
        </p>
        <span style="top: 2px;" bind:this={main[3]}></span>
        <slot />
    </button>
    {#if open}
        <div class="menu" bind:this={main[4]} style="
            background-color: {LayoutValue[Attr.background] ?? '#454545'};
            border-radius: {LayoutValue[Attr.round] ?? '5px'};
        ">
            {#if LayoutValue[Attr.options]?.length}
                {#each LayoutValue[Attr.options] as val}
                    <div class="item" on:click={()=>window.GetValue(ModuleName, Attr.value, val)} style="
                        border-radius: {LayoutValue[Attr.round] ?? '5px'};
                    ">
                        {val}
                    </div>
                {/each}
            {:else}
                <div style="
                    padding: 6px;
                    cursor: not-allowed;
                    width: 100%;
                    color: #ffffff50;
                    border-radius: {LayoutValue[Attr.round] ?? '5px'};
                ">
                    Nothing here
                </div>
            {/if}
        </div>
    {/if}
</span>

<style lang="scss">
    .main{
        font-size: inherit;
        display: flex;
        width: 100%;
        height: 100%;
        text-decoration: none;
        padding: 8px;
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
                }
                span{
                    top: 5px !important;
                }
            }
        }
        &.disabled{
            filter: brightness(70%);
            cursor: not-allowed;
        }
        &>p{
            line-height: 0.5em;
            flex-grow: 1;
            display: flex;
            align-items: center;
            &>p{
                display: inline-block;
                white-space: pre-wrap;
            }
        }
        span{
            margin-left: 4px;
            display: flex;
            align-items: center;
            user-select: none;
            transition: top 0.1s ease-in;
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
            background-color: inherit;
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