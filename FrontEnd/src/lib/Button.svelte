<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string;
    export let Attr:{[key: string]: string}={};

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
{#if (LayoutValue[Attr.type]??"text")=="text"}
    <button class="button" disabled={LayoutValue[Attr.disable]} on:click={()=>window.GetValue(Attr.value,true)} style="
        color: {LayoutValue[Attr.color] ?? '#fff'};
        background-color: {LayoutValue[Attr.background] ?? '#454545'};
        font-size: {LayoutValue[Attr.size] ?? '16px'};
        width: {LayoutValue[Attr.width] ?? 'auto'};
        height: {LayoutValue[Attr.height] ?? 'auto'};
        margin: {LayoutValue[Attr.margin] ?? '0'};
        border-radius: {LayoutValue[Attr.round] ?? '5px'};
    ">
        <p style="padding: {LayoutValue[Attr.padding] ?? '0'}">
            {#each ConvertText(Text) as data}
                <p style="top: {data.Type=='Icon'?2:0}px;">{data.Text}</p>
            {/each}
        </p>
        <slot />
    </button>
{:else if LayoutValue[Attr.type]=="link"}
    <a class="button" target="_blank" href={LayoutValue[Attr.value]} style="
        color: {LayoutValue[Attr.color] ?? '#fff'};
        background-color: {LayoutValue[Attr.background] ?? '#454545'};
        font-size: {LayoutValue[Attr.size] ?? '16px'};
        width: {LayoutValue[Attr.width] ?? 'auto'};
        height: {LayoutValue[Attr.height] ?? 'auto'};
        margin: {LayoutValue[Attr.margin] ?? '0'};
        border-radius: {LayoutValue[Attr.round] ?? '5px'};
    ">
        <p style="padding: {LayoutValue[Attr.padding] ?? '0'}">
            {#each ConvertText(Text+" ") as data}
                <p style="top: {data.Type=='Icon'?2:0}px;">{data.Text}</p>
            {/each}
        </p>
        <slot />
    </a>
{:else if LayoutValue[Attr.type]=="toggle"}
    <button class="button" disabled={LayoutValue[Attr.disable]} class:active={LayoutValue[Attr.value]} on:click={()=>window.GetValue(Attr.value,!LayoutValue[Attr.value])} style="
        {LayoutValue[Attr.value]?'background-':''}color: {LayoutValue[Attr.color] ?? '#fff'};
        {LayoutValue[Attr.value]?'':'background-'}color: {LayoutValue[Attr.background] ?? '#454545'};
        font-size: {LayoutValue[Attr.size] ?? '16px'};
        width: {LayoutValue[Attr.width] ?? 'auto'};
        height: {LayoutValue[Attr.height] ?? 'auto'};
        margin: {LayoutValue[Attr.margin] ?? '0'};
        border-radius: {LayoutValue[Attr.round] ?? '5px'};
    ">
        <p style="padding: {LayoutValue[Attr.padding] ?? '0'}">
            {#each ConvertText(Text) as data}
                <p style="top: {data.Type=='Icon'?2:0}px;">{data.Text}</p>
            {/each}
        </p>
        <slot />
    </button>
{/if}
<style lang="scss">
    .button{
        text-decoration: none;
        padding: 8px;
        filter: brightness(100%);
		border: 1px solid #00000020;
        transition: filter 0.1s ease-out, border 0.1s ease-out;
        &:not([disabled]){
            cursor: pointer;
            &:hover{
                &:not(.active){
                    border: 1px solid #ffffff20;
                }
                &.active{
                    filter: brightness(90%);
                }
            }
            &:active{
                filter: brightness(90%);
                border: 1px solid #ffffff20;
            }
        }
        &[disabled] {
            filter: brightness(80%);
            border: 1px solid #00000040;
            cursor: not-allowed;
        }
        &>p>p{
            display: inline-block;
            white-space: pre-wrap;
        }
    }
</style>