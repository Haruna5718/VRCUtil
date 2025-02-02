<script lang="ts">
    export let Icon:string;
    export let Text:string = "";
    export let style:string = "";
    export let Select:boolean = false;
    export let Disabled:boolean = false;
    export let Status:number = null;
    export let onclick = ()=>{};
    let Width: number;
    
</script>

<button class:Select={Select} class:Disabled={Disabled} style="{style}" bind:clientWidth={Width} on:click={onclick}>
    <span class="Icon">{Icon}</span>
    {#if Width>=200}
        <span class="Text">{Text}</span>
    {/if}
    {#if Status!=null}
        <span class="Status" style="top: {Width>=200?15:5}px; right: {Width>=200?15:5}px;" class:Offline={Status==0} class:Online={Status==1} class:Active={Status==2} class:warning={Status==-1} class:Error={Status==-2}/>
    {/if}
</button>
<style lang="scss">
	button{
        cursor: pointer;
        outline: none;
        border: none;
        display: block;
		background-color: transparent;
        margin: 5px;
		border-radius: 5px;
        min-width: 40px;
        align-self: stretch;
		height: 40px;
		color: #ffffff;
        text-align: left;
        padding: 0px 12px 0px 12px;
        line-height: 40px;
        transition: background-color 0.1s ease-in-out;
        .Offline{
            background-color: #888888;
        }
        .Online{
            background-color: #3ba000;
        }
        .warning{
            background-color: #f0a000
        }
        .Error{
            background-color: #bb3434;
        }
        .Active{
            background-color: #208fff;
        }
        .Status{
            position: absolute;
            border-radius: 5px;
            width: 10px;
            height: 10px;
        }
        .Icon{
            font-size: 16px;
            top: 2px;
        }
        .Text{
            left: 10px;
        }
        &::before{
            transition: background-color 0.1s ease-in-out;
            position: absolute;
            left: 0;
            top: 12px;
            content: "";
            background-color: transparent;
            width: 3px;
            border-radius: 1.5px;
            height: 16px;
        }
        &:not(.Disabled){
            &.Select,&:hover{
                background-color: #ffffff10;
            }
            &.Select::before{
                background-color: #fff;
            }
            &:active{
                background-color: #ffffff0b;
            }
        }
        &.Disabled{
            color: #ffffff50;
        }
	}
</style>