<script lang="ts">
    import Component from './Component.svelte';
    
    import Text from './Text.svelte';
    import Line from './Line.svelte';
    import Space from './Space.svelte';
    import Box from './Box.svelte';
    import Vertical from './Vertical.svelte';
    import Horizontal from './Horizontal.svelte';
    import Button from './Button.svelte';
    import Input from './Input.svelte';
    import Switch from './Switch.svelte';
    import Select from './Select.svelte';

    type LayoutDataType = {
        Type: string,
        Attr: {[key: string]: string},
        Text: string,
        Children: LayoutDataType[];
    };

    const Components = {
        Text,
        Line,
        Space,
        Box,
        Vertical,
        Horizontal,
        Button,
        Input,
        Switch,
        Select
    };

    function SetRepeatData(data: LayoutDataType, ind: number): LayoutDataType {
        Object.keys(data.Attr).forEach((key)=>{
            data.Attr[key] = data.Attr[key].replaceAll(/\{i\}/g, `${ind}`);
        })
        data.Text = data.Text.replaceAll(/\{i\}/g, `${ind}`);
        data.Children = data.Children.map((child) => SetRepeatData(child, ind));
        return data;
    }
    
    export let LayoutData:LayoutDataType;
    export let LayoutValue:{[key: string]: any} = {};
    export let ModuleName:string = "";
    

    Object.values(LayoutData.Attr).forEach((v)=>{window.GetValue(ModuleName, v)})
    window.GetValue(ModuleName, LayoutData.Text)

</script>
{#if LayoutData}
    {#if LayoutData.Type=="Repeat"}
    {@const Length=Number(LayoutValue[LayoutData.Attr.value])}
        {#each new Array(Length?Length:0) as _,ind}
            {#each LayoutData.Children as val}
                <Component {LayoutValue} LayoutData={SetRepeatData(structuredClone(val),ind)} {ModuleName}/>
            {/each}
        {/each}
    {:else if LayoutData.Type=="If"}
        {#key LayoutValue[LayoutData.Attr.value]}
            {#each (LayoutData.Children?.find(data=>data.Type==(LayoutValue[LayoutData.Attr.value]?"True":"False"))?.Children) ?? [] as val}
                <Component {LayoutValue} LayoutData={val} {ModuleName}/>
            {/each}
        {/key}
    {:else}
        <svelte:component {LayoutValue} this={Components[LayoutData.Type]} Attr={LayoutData.Attr} Text={LayoutValue[LayoutData.Text]} {ModuleName}>
            {#each LayoutData.Children as val}
                <Component {LayoutValue} LayoutData={val} {ModuleName}/>
            {/each}
        </svelte:component>
    {/if}
{/if}