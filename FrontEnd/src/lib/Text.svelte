<script lang="ts">
    export let LayoutValue:{[key: string]: any}={};
    export let Text:string;
    export let Attr:{[key: string]: string}={};

    function ConvertText(source):{Type: string, Text:String}[] {
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
<span class:disabled={LayoutValue[Attr.disable]} style="color: {LayoutValue[Attr.color] ?? '#fff'}; font-size: {LayoutValue[Attr.size] ?? '16px'}; margin: {LayoutValue[Attr.margin] ?? '0'};">
    {#each ConvertText(Text) as data}
        <p style="top: {data.Type=='Icon'?2.5:0}px;">{data.Text}</p>
    {/each}
</span>
<style lang="scss">
    span{
        align-self: center;
        white-space: pre-wrap;
        &.disabled{
            filter: brightness(70%);
        }
    }
</style>