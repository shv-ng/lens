<script lang="ts">
	import { Paperclip, Search, Check, Loader2 } from '@lucide/svelte';
  import { PUBLIC_API_BASE_URL } from '$env/static/public';

	let inputText = $state('');
	let attachedFile: File | null = $state(null);
	let isLoading = $state(false);
	let submitted = $state(false);
	let fileInput: HTMLInputElement;

	let progressEvents: Array<{node: string, message: string}> = $state([]);
	let nodeCounts: Record<string, number> = $state({});
	let finalResult: {verdict_label: string, verdict_explanation: string, framing_notes: string, top_articles: any[]} | null = $state(null);
	let errorMessage: string = $state('');

	let completedNodes = $derived(
		new Set(
			(isLoading ? progressEvents.slice(0, -1) : progressEvents)
				.map(e => e.node.split(' ')[0])
		)
	);
	let activeNode = $derived(isLoading ? progressEvents[progressEvents.length - 1]?.node.split(' ')[0] : null);
	let justCompletedNode: string | null = $state(null);
	let isBackendActive = $state(true);

	$effect(() => {
		const checkHealth = async () => {
			try {
				const res = await fetch(`/api/health`);
				isBackendActive = res.ok;
			} catch {
				isBackendActive = false;
			}
		};
		checkHealth();
		const interval = setInterval(checkHealth, 5000);
		return () => clearInterval(interval);
	});

	$effect(() => {
		if (activeNode === null && progressEvents.length > 0) {
			const last = progressEvents[progressEvents.length - 1].node.split(' ')[0];
			justCompletedNode = last;
			setTimeout(() => { if (justCompletedNode === last) justCompletedNode = null; }, 400);
		}
	});

	const nodes = {
		query: { x: 80, y: 100, label: 'Query' },
		google_news: { x: 220, y: 50, label: 'Google News' },
		news_orgs: { x: 220, y: 100, label: 'News Orgs' },
		reddit: { x: 220, y: 150, label: 'Reddit' },
		merge_rerank: { x: 360, y: 100, label: 'Merge' },
		conflict: { x: 480, y: 100, label: 'Conflict' },
		deep_dive: { x: 560, y: 155, label: 'Deep Dive' },
		verdict: { x: 600, y: 100, label: 'Verdict' }
	};

	const edges = [
		['query', 'google_news'], ['query', 'news_orgs'], ['query', 'reddit'],
		['google_news', 'merge_rerank'], ['news_orgs', 'merge_rerank'], ['reddit', 'merge_rerank'],
		['merge_rerank', 'conflict'], ['conflict', 'verdict']
	];

	async function handleSubmit() {
		isLoading = true;
		submitted = true;
		progressEvents = [];
		nodeCounts = {};
		finalResult = null;
		errorMessage = '';
		justCompletedNode = null;

		let body: BodyInit;
		let headers: HeadersInit = {};

		if (attachedFile) {
			const formData = new FormData();
			const inputType = attachedFile.type === 'application/pdf' ? 'pdf' : 'image';
			formData.append('input_type', inputType);
			formData.append('file', attachedFile);
			body = formData;
		} else {
			headers['Content-Type'] = 'application/json';
			body = JSON.stringify({ raw_input: inputText, input_type: 'text' });
		}

		try {
			const response = await fetch(`/api/verify/stream`, {
				method: 'POST',
				headers,
				body
			});

			if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();

			if (!reader) throw new Error('No body in response');

			let currentEventType = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value, { stream: true });
				const lines = chunk.split('\n');

				for (const line of lines) {
					if (line.startsWith('event: ')) {
						currentEventType = line.slice(7).trim();
					} else if (line.startsWith('data: ')) {
						try {
							const data = JSON.parse(line.slice(6));
							if (currentEventType === 'progress') {
								nodeCounts[data.node] = (nodeCounts[data.node] || 0) + 1;
								const count = nodeCounts[data.node];
								const nodeLabel = count > 1 ? `${data.node} (${count})` : data.node;

								if (count === 1) {
									progressEvents.push({ node: nodeLabel, message: data.message });
								} else {
									const existingIndex = progressEvents.findIndex(e => e.node.startsWith(data.node));
									if (existingIndex !== -1) {
										progressEvents[existingIndex].node = nodeLabel;
										progressEvents[existingIndex].message = data.message;
									}
								}
							} else if (currentEventType === 'final') {
								console.log('Final Result:', data);
								finalResult = data;
								isLoading = false;
							} else if (currentEventType === 'done') {
								isLoading = false;
							}
						} catch (e) {
							console.error('Failed to parse SSE line:', line);
						}
						currentEventType = '';
					}
				}
			}
		} catch (e) {
			errorMessage = (e as Error).message;
			isLoading = false;
		}
	}

	function handleFileChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files && target.files.length > 0) {
			attachedFile = target.files[0];
		}
	}
</script>

<style>
	@keyframes pulse-node {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.3); }
	}
	@keyframes flow {
		from { stroke-dashoffset: 24; }
		to { stroke-dashoffset: 0; }
	}
	@keyframes complete-pop {
		0% { transform: scale(1); }
		40% { transform: scale(1.4); }
		100% { transform: scale(1); }
	}
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(8px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.node-active { animation: pulse-node 1s ease-in-out infinite; }
	.complete-pop { animation: complete-pop 0.4s ease-out; }
	.edge-active { animation: flow 0.6s linear infinite; }
	circle { transition: fill 0.5s ease, stroke 0.5s ease, filter 0.5s ease; }
	line, path { transition: stroke 0.5s ease, stroke-width 0.3s ease; }
</style>

<div class="min-h-screen flex flex-col bg-zinc-950 text-zinc-100">
	<!-- Section 1: Header -->
	<header class="flex items-center px-8 py-4 bg-zinc-900 border-b border-zinc-800 shrink-0">
		<div class="flex items-center gap-3">
			<h1 class="text-xl font-bold text-white">Lens</h1>
			<span class="text-sm text-zinc-400">News Verification System</span>
		</div>
		<div class="ml-auto text-sm font-medium {isBackendActive ? 'text-emerald-400' : 'text-red-500'}">
			{isBackendActive ? 'Active' : 'Inactive'}
		</div>
	</header>

	<!-- Section 2: Input Area -->
	<main class="flex-grow flex p-4 transition-all duration-400 ease-in-out {submitted ? 'items-start justify-center pt-8' : 'items-center justify-center'}">
		<div class="w-full max-w-[680px] bg-zinc-900 border border-zinc-800 p-8 rounded-2xl shadow-lg">
			<textarea
				bind:value={inputText}
				placeholder="Paste a claim, news excerpt, or upload an image/PDF to verify..."
				rows={submitted ? 2 : 4}
				class="w-full p-4 leading-relaxed bg-zinc-950 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-zinc-500 focus:outline-none mb-6 resize-none"
			></textarea>

			<div class="flex items-center justify-between gap-6">
				<button
					type="button"
					class="flex items-center gap-2 text-zinc-400 hover:text-zinc-200 transition-colors"
					onclick={() => fileInput.click()}
				>
					<Paperclip size={20} />
					<span class="text-sm">Attach file</span>
				</button>

				<input
					type="file"
					bind:this={fileInput}
					accept="image/*, application/pdf"
					class="hidden"
					onchange={handleFileChange}
				/>

				<button
					disabled={(!inputText && !attachedFile) || isLoading}
					onclick={handleSubmit}
					class="flex items-center gap-2 px-6 py-3 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-sm font-medium transition-colors"
				>
					<Search size={20} />
					<span>Verify</span>
				</button>
			</div>

			{#if attachedFile}
				<p class="mt-6 text-sm text-zinc-400 truncate">
					Attached: {attachedFile.name}
				</p>
			{/if}
		</div>
	</main>

	<!-- Section 3: Results Area -->
	{#if submitted}
		<section class="px-4 pb-8 mt-4 max-w-[680px] mx-auto w-full">
			{#if errorMessage}
				<div class="text-red-500 bg-red-950/30 p-4 rounded-xl border border-red-900/50 mb-6">
					{errorMessage}
				</div>
			{/if}

			<svg width="100%" height="180" viewBox="0 0 680 180" class="overflow-visible">
				<defs>
					<marker id="arrow-default" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="6" markerHeight="6" orient="auto">
						<path d="M 0 0 L 10 5 L 0 10 z" fill="#3f3f46" />
					</marker>
					<marker id="arrow-complete" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="6" markerHeight="6" orient="auto">
						<path d="M 0 0 L 10 5 L 0 10 z" fill="#059669" />
					</marker>
				</defs>

				{#each edges as [src, dst]}
					{@const edgeState = completedNodes.has(src) && completedNodes.has(dst) ? 'complete' : (completedNodes.has(src) && activeNode === dst ? 'active' : 'default')}
					<line x1={nodes[src].x} y1={nodes[src].y} x2={nodes[dst].x} y2={nodes[dst].y}
						stroke={edgeState === 'complete' ? '#059669' : (edgeState === 'active' ? '#06b6d4' : '#3f3f46')}
						stroke-width={edgeState !== 'default' ? 2 : 1.5}
						stroke-dasharray={edgeState === 'active' ? '4 4' : 'none'}
						class={edgeState === 'active' ? 'edge-active' : ''}
						marker-end="url(#{edgeState === 'complete' ? 'arrow-complete' : (edgeState === 'active' ? 'arrow-active' : 'arrow-default')})"
					/>
				{/each}

				<line x1={nodes.conflict.x} y1={nodes.conflict.y + 10} x2={nodes.deep_dive.x - 5} y2={nodes.deep_dive.y - 10}
					stroke={completedNodes.has('conflict') && completedNodes.has('deep_dive') ? '#059669' : (completedNodes.has('conflict') && activeNode === 'deep_dive' ? '#06b6d4' : '#3f3f46')}
					stroke-width="1.5"
					style="opacity: {completedNodes.has('deep_dive') || activeNode === 'deep_dive' ? 1 : 0.2}"
				/>
				<path d="M {nodes.deep_dive.x} {nodes.deep_dive.y - 10} C {nodes.deep_dive.x + 30} {nodes.deep_dive.y - 25}, {nodes.deep_dive.x + 30} {nodes.conflict.y - 10}, {nodes.conflict.x} {nodes.conflict.y - 10}"
					fill="none" 
					stroke={completedNodes.has('deep_dive') && completedNodes.has('conflict') ? '#059669' : (completedNodes.has('deep_dive') && activeNode === 'conflict' ? '#06b6d4' : '#3f3f46')} 
					stroke-width="1.5"
					style="opacity: {completedNodes.has('deep_dive') ? 1 : 0.2}"
				/>

				{#each Object.entries(nodes) as [id, pos]}
					<g class="{activeNode === id ? 'node-active' : ''} {justCompletedNode === id ? 'complete-pop' : ''}" style="transform-origin: {pos.x}px {pos.y}px">
						<circle cx={pos.x} cy={pos.y} r="10"
							class="
								{activeNode === id ? 'fill-cyan-500 stroke-cyan-300' : 
								 completedNodes.has(id) ? 'fill-emerald-600 stroke-emerald-400' : 'fill-zinc-800 stroke-zinc-600'}
							"
							style="filter: {activeNode === id ? 'drop-shadow(0 0 6px #06b6d4)' : 'none'}"
						/>
						<text x={pos.x} y={pos.y + 25} text-anchor="middle" font-size="10" class="fill-zinc-500">{pos.label}</text>
					</g>
				{/each}
			</svg>

			{#if isLoading}
				<p class="text-xs text-zinc-500 text-center mt-3 h-4 transition-all duration-300">
					{progressEvents[progressEvents.length - 1]?.message ?? ''}
				</p>
			{/if}

			{#if finalResult}
				<div style="animation: fadeIn 0.5s ease forwards">
					<div class="mt-8 p-6 bg-zinc-900 border border-zinc-800 rounded-2xl">
						<div class="flex items-center">
							<span class="px-4 py-1.5 rounded-full text-sm font-semibold tracking-wide 
								{finalResult.verdict_label === 'CONSENSUS' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 
								 finalResult.verdict_label === 'PARTIAL_CONFLICT' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
								 finalResult.verdict_label === 'FACTUAL_CONFLICT' ? 'bg-red-950 text-red-400 border border-red-800' :
								 finalResult.verdict_label === 'ECHO_CLUSTER' ? 'bg-blue-950 text-blue-400 border border-blue-800' :
								 finalResult.verdict_label === 'FRAMING_DIVERGENCE' ? 'bg-purple-950 text-purple-400 border border-purple-800' :
								 'bg-zinc-800 text-zinc-400 border border-zinc-600'}">
								{finalResult.verdict_label}
							</span>
						</div>
						<p class="text-zinc-300 leading-relaxed text-base mt-4">{finalResult.verdict_explanation}</p>

						{#if finalResult.framing_notes && finalResult.framing_notes !== 'no significant framing divergence observed'}
							<div class="border-t border-zinc-800 pt-4 mt-4">
								<span class="text-zinc-500 text-sm font-medium mr-2">Framing:</span>
								<span class="text-zinc-400 text-sm">{finalResult.framing_notes}</span>
							</div>
						{/if}
					</div>

					{#if finalResult.top_articles && finalResult.top_articles.length > 0}
						<h3 class="text-zinc-400 text-sm font-medium uppercase tracking-wider mt-8 mb-4">Sources</h3>
						<div class="space-y-4">
							{#each finalResult.top_articles as article}
								<div class="bg-zinc-900/50 border border-zinc-800/50 rounded-xl p-4">
									<div class="flex items-center justify-between">
										<span class="bg-zinc-700 text-zinc-300 rounded-md px-2 py-0.5 text-xs">{article.source_name || 'Source'}</span>
										<span class="text-zinc-500 text-xs">{article.publication_date || ''}</span>
									</div>
									<a 
										href={article.link} 
										target="_blank" 
										rel="noopener noreferrer" 
										class="block text-zinc-200 font-medium text-sm mt-2 cursor-pointer hover:text-white hover:underline"
									>
										{article.title}
									</a>
									{#if article.description}
										<p class="text-zinc-500 text-xs mt-1">{article.description.slice(0, 120)}{article.description.length > 120 ? '...' : ''}</p>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</section>
	{/if}
</div>
