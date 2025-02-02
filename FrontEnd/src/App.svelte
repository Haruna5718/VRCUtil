<script lang="ts">
	import Box from './lib/Box.svelte';
    import Button from './lib/Button.svelte';
	import Component from './lib/Component.svelte';
    import Horizontal from './lib/Horizontal.svelte';
    import Input from './lib/Input.svelte';
    import Line from './lib/Line.svelte';
	import NavMenu from './lib/NavMenu.svelte';
    import Space from './lib/Space.svelte';
    import Switch from './lib/Switch.svelte';
    import Vertical from './lib/Vertical.svelte';

	let PageReady = false
	let NavOpen = true
	let OnTop = false
	let ModuleInfo = false

	let LayoutData:{[key: string]:any} = {};
	let WidgetData:{[key: string]:any} = {};
	let LayoutValue:{[key: string]:any} = {};
	let ModuleData:{[key: string]:any} = {};

	let ModuleStatus:{[key: string]:number} = {}
	let notices:[number, string][] = []

	let hash = "";

	let ReverseDatas = {}

	const ValueRegex = /^\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}$/;
	window.GetValue = (ModuleName:string, Name: string, Value:any=null) => {
		if(!LayoutValue[ModuleName]) LayoutValue[ModuleName] = {}
		if(!ReverseDatas[ModuleName]) ReverseDatas[ModuleName] = []
		let match = Name.match(ValueRegex);
		if(match) {
			if(match[1].startsWith("!")) ReverseDatas[ModuleName].push(match[1].replace("!",""))
			if(!LayoutValue[ModuleName][Name]||Value!=null) window.pywebview.api.GetValue(ModuleName,match[1].replace("!",""),Value)
		}
		else LayoutValue[ModuleName][Name] = Name
	}

	window.SetValue = (ModuleName: string, Name: string, Value:any=null) => {
		if(!LayoutValue[ModuleName]) LayoutValue[ModuleName] = {}
		if(!ReverseDatas[ModuleName]) ReverseDatas[ModuleName] = []
		if(ReverseDatas[ModuleName].includes(Name)) LayoutValue[ModuleName][`{!${Name}}`] = !Value;
		LayoutValue[ModuleName][`{${Name}}`] = Value;
	}

	window.ModuleState = (ModuleName:string, state:number) => {
		ModuleStatus[ModuleName]=state
	}

	window.Notice = (Message:string,Level:number=0) => {
		notices=[...notices, [Level, Message]]
	}

	let RecentPages = 0;
	const hashChange = () => {
		if(location.hash==`#${hash}`) return
		hash = location.hash.replace("#","")
		if(history.state==null) history.replaceState({i:RecentPages+1}, "");
		RecentPages = history.state.i;
		ModuleInfo = false
	}

	(async () => {
		while (!window.hasOwnProperty("pywebview")) await new Promise(resolve => setTimeout(resolve, 500));
		let LoadedData = await window.pywebview.api.LoadModule()
		LayoutData = LoadedData.LayoutData
		WidgetData = LoadedData.WidgetData
		ModuleData = LoadedData.ModuleData
		window.pywebview.api.GetValue("Settings","AutoStart")
		window.pywebview.api.GetValue("Settings","OSCHost")
		window.pywebview.api.GetValue("Settings","OSCIn")
		window.pywebview.api.GetValue("Settings","OSCOut")
		window.pywebview.api.GetValue("Settings","AutoUpdate")
		window.pywebview.api.GetValue("Settings","version")
		window.pywebview.api.GetValue("Settings","newversion")
		PageReady = true
		await window.pywebview.api.InitModule()
	})();
	history.replaceState({i:0},"");
</script>
<svelte:window on:hashchange={hashChange}></svelte:window>
<main style="grid-template-columns: 50px {PageReady&&NavOpen?180:0}px 1fr;">
	<NavMenu Icon="" onclick={()=>history.back()} Disabled={!RecentPages}/>
	<header class="pywebview-drag-region">
		<div>
			<img src="./favicon.ico" alt="" style="width: 20px; margin-right: 5px;">
			<p>VRCUtil</p>
		</div>
		<div class="HeaderButtons">
			<button on:click={()=>window.pywebview.api.ontop(!OnTop).then(v=>OnTop=v)}>{#if OnTop}<span style="position:absolute;left:8px;"></span>{/if}</button>
			<button on:click={()=>window.pywebview.api.minimize()}></button> <!--  -->
			<button on:click={()=>window.pywebview.api.destroy()}></button> <!--  -->
		</div>
	</header>
	<NavMenu Icon="" onclick={()=>NavOpen=!NavOpen} style="grid-row: 2; grid-column: 1;"/>
	<nav>
		<NavMenu Icon="" Text="DashBoard" Select={hash==""} onclick={()=>location.hash=""}/>
		{#each Object.entries(ModuleData) as val}
			<NavMenu Icon={val[1].DisplayIcon} Text={val[1].DisplayName} Select={hash==val[0]} onclick={()=>location.hash=val[0]} Status={ModuleStatus[val[0]]} />
		{/each}
	</nav>
	<NavMenu Icon="" Text="Settings" Select={hash=="Settings"} onclick={()=>location.hash="Settings"} style="grid-row: 4; grid-column: 1 / 3;"/>
	{#key hash}
		<div class="container" on:load={(e)=>e.currentTarget.scrollTo(0,0)}>
			{#if PageReady}
				<div class="Title">{hash==""?"Dashboard":(ModuleData[hash]?.DisplayName??hash)}</div>
				<div class="page">
					{#if ModuleData[hash]}
						<Component LayoutValue={LayoutValue[hash]} LayoutData={LayoutData[hash]} ModuleName={hash}/>
					{:else if hash=="Settings"}
						<Vertical>
							<Box>
								<Horizontal>
									<p>Auto Start VRCUtil With SteamVR</p>
									<Space />
									<Switch Attr={{value:"{AutoStart}"}} LayoutValue={LayoutValue[hash]} ModuleName={"Settings"}/>
								</Horizontal>
							</Box>
							<Box>
								<Horizontal>
									<p>Auto Update VRCUtil After Exit</p>
									<Space />
									<p style="color:#888c90;">Latest {LayoutValue[hash]["{newversion}"]}</p>
									<Switch Attr={{value:"{AutoUpdate}"}} LayoutValue={LayoutValue[hash]} ModuleName={"Settings"}/>
								</Horizontal>
							</Box>
							<Box>
								<Horizontal>
									<p>VRChat OSC</p>
									<Space />
									<Vertical>
										<Horizontal>
											<p class="tinytext">IP Address</p>
											<Space />
										</Horizontal>
										<Input Attr={{value:"{OSCHost}", width:"width"}} LayoutValue={{...LayoutValue[hash], width:"150px"}} ModuleName={"Settings"}/>
									</Vertical>
									<Vertical>
										<Horizontal>
											<p class="tinytext">Send Port</p>
											<Space />
										</Horizontal>
										<Input Attr={{value:"{OSCIn}", width:"width"}} LayoutValue={{...LayoutValue[hash], width:"80px"}} ModuleName={"Settings"}/>
									</Vertical>
									<Vertical>
										<Horizontal>
											<p class="tinytext">Receive Port</p>
											<Space />
										</Horizontal>
										<Input Attr={{value:"{OSCOut}", width:"width"}} LayoutValue={{...LayoutValue[hash], width:"80px"}} ModuleName={"Settings"}/>
									</Vertical>
								</Horizontal>
							</Box>
							<Box>
								<Horizontal>
									<img src="./favicon.ico" alt="" width="27px" height="27px" style="margin: 3px;">
									<Vertical>
										<Horizontal>
											<p>VRCUtil</p>
											<p style="color:#888c90;">{LayoutValue[hash]["{version}"]}</p>
											<Space />
										</Horizontal>
										<p class="minitext">© 2025. Haruna5718. All rights reserved.</p>
									</Vertical>
									<Space />
									<Button Attr={{type:"type", value:"url"}} Text="Booth" LayoutValue={{"url":"https://haruna5718.booth.pm/items/6516021", type:"link"}}/>
									<Button Attr={{type:"type", value:"url"}} Text="Github" LayoutValue={{"url":"https://github.com/Haruna5718/VRCUtil", type:"link"}}/>
								</Horizontal>
							</Box>
							<Box>
								<Horizontal>
									<img src="https://avatars.githubusercontent.com/u/179698659" alt="" width="34px" height="34px" style="border-radius: 17px;">
									<Vertical>
										<Horizontal>
											<p>Haruna5718</p>
											<Space />
										</Horizontal>
										<p class="minitext">contact@haruna5718.dev</p>
									</Vertical>
									<Space />
									<Button Attr={{type:"type", value:"url"}} Text="Booth" LayoutValue={{"url":"https://haruna5718.booth.pm", type:"link"}}/>
									<Button Attr={{type:"type", value:"url"}} Text="Github" LayoutValue={{"url":"https://github.com/Haruna5718", type:"link"}}/>
								</Horizontal>
							</Box>
						</Vertical>
					{:else}
						<Vertical>
							{#each Object.keys(WidgetData) as ModuleName}
								<Component LayoutValue={LayoutValue[ModuleName]} LayoutData={WidgetData[ModuleName]} {ModuleName}/>
							{/each}
						</Vertical>
					{/if}
				</div>
			{:else}
				<p class="WaitInit">Starting...</p>
			{/if}
		</div>
	{/key}
	{#if ModuleData[hash]}
		{#key hash}
			<div class="ModuleMenu" style="transform: translateY({ModuleInfo?0:100}%)">
				<p class="button" on:click={()=>ModuleInfo=!ModuleInfo}>Module Info <span style="top: 2px;">{ModuleInfo?"":""}</span></p>
				<div class="content">
					<Vertical>
						<Horizontal>
							<p>{ModuleData[hash]?.DisplayName} <span style="color:#888c90;">{ModuleData[hash]?.Version}</span></p>
							<Space />
						</Horizontal>
						<Horizontal>
							<p class="minitext">{ModuleData[hash]?.Author}</p>
							<Space />
						</Horizontal>
					</Vertical>
					<Space />
					{#each ModuleData[hash]?.Url as val}
						{@const data = Object.entries(val)[0]}
						<Button Attr={{type:"type", value:"url"}} Text="{data[0]}" LayoutValue={{"url":data[1], type:"link"}}/>
					{/each}
					<Line />
					<p>{ModuleData[hash]?.Description}</p>
					<Space />
					<Button Attr={{value:"Remove", background:"background"}} Text="Remove" LayoutValue={{background:"#bb3434"}}/>
				</div>
			</div>
		{/key}
	{/if}
</main>
<div class="notice">
	{#each notices as val,ind}
		<div style="background-color:{["#1c5fb8","#3ba000","#f0a000","#bb3434"][val[0]]};">
			<p style="top: 2px; margin-bottom:auto;">{["","","",""][val[0]]}</p>
			<p>{val[1]}</p>
			<p class="icon" on:click={() => { notices = notices.filter((_, i) => i !== ind); }}></p>
		</div>
	{/each}
</div>
<style lang="scss">
	.notice{
		position: absolute;
		top: 50px;
		right: 0px;
		overflow: hidden;
		display: flex;
		flex-direction: column-reverse;
		gap: 5px;
		padding: 20px;
		&>div{
			overflow: hidden;
			width: fit-content;
			margin-left: auto;
			display: flex;
			gap: 5px;
			padding: 10px;
			border-radius: 5px;
			.icon{
				cursor: pointer;
				top: 2px;
			}
			&>p:nth-child(2){
				font-size: 13px;
				line-height: 15px;
				margin-right: 5px;
				word-break: break-word;
				white-space: pre-wrap;
				max-width: 300px;
			}
		}
	}
	.ModuleMenu{
		grid-row: 4;
		grid-column: 3;
		width: calc(100% - 40px);
		margin: 0px 20px;
		height: 145px;
		border-top-left-radius: 5px;
		background-color: #2f2f2f;
		border: 1px solid #00000050;
		position: absolute;
		bottom: -1px;
		right: 0;
		transition: transform 0.2s ease-in-out;
		box-shadow: 0px 0px 5px #00000050;
		.button{
			cursor: pointer;
			background-color: inherit;
			border: inherit;
			border-bottom: none;
			border-radius: 5px 5px 0px 0px;
			padding: 10px 10px 10px 10px;
			position: absolute;
			right: -1px;
			box-shadow: inherit;
			transform: translateY(-100%);
		}
		.content{
			background-color: inherit;
			border-top-left-radius: 10px;
			width: 100%;
			height: 100%;
			padding: 20px;
			gap: 5px;
			flex-wrap: wrap;
			display: flex;
			align-items: center;
			flex-direction: row;
			align-self: stretch;
		}
	}
	.minitext{
		font-size:12px;
		color:#888c90;
	}
	.tinytext{
		font-size:10px;
		color:#888c90;
	}
	p{
		align-self: center;
	}
	.page{
		gap: 10px;
		animation : PageLoadAnim 0.1s ease-in-out forwards alternate;
	}
	@keyframes PageLoadAnim {
		0%{
			transform: translateY(80px);
		}
    }
	.Title{
		font-size: 25px;
		margin-bottom: 10px;
	}
	nav{
		display: flex;
		flex-direction: column;
		grid-row: 3;
		grid-column: 1 / 3;
		overflow-y: scroll;
		overflow-x: hidden;
		:global(button){
			margin: 3px 1px 3px 5px !important;
		}
	}
	.WaitInit{
		height: 100%;
		color: #888c90;
		display: grid;
		align-items: center;
		justify-items: center;
	}
	main{
		transition: grid-template-columns 0.1s ease-in-out;
		display: grid;
		grid-template-rows: 50px 50px 1fr 50px;
		overflow-y: hidden;
	}
	header{
		grid-row: 1;
		grid-column: 2 / 4;
		display: flex;
		font-size: 13px;
		align-items: center;
		justify-content: space-between;
		&>div{
			display: flex;
			align-items: center;
			&.HeaderButtons>button{
				transition: background-color 0.1s ease-in-out, color 0.1s ease-in-out;
				background-color: transparent;
				color: #888c90;
				width: 30px;
				height: 30px;
				font-size: 15px;
				padding-top: 3px;
				margin-right: 10px;
				border-radius: 5px;
				&:not(:last-child):hover{
					background-color: #ffffff10;
				}
				&:last-child:hover{
					background-color: #bb343430;
					color: #ffffff60;
				}
			}
		}
	}
	.container{
		grid-row: 2 / 5;
		grid-column: 3;
		border: 1px solid #1d1d1d;
		border-bottom: none;
		border-right: none;
		background-color: #272727;
		border-top-left-radius: 10px;
		padding: 30px 26px 30px 30px;
		overflow-y: scroll;
		overflow-x: hidden;
	}
</style>