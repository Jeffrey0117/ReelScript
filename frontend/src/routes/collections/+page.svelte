<script lang="ts">
	import { onMount } from 'svelte';
	import {
		listCollections,
		createCollection,
		deleteCollection,
		getCollection,
		removeFromCollection,
		type Collection,
		type CollectionDetail,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let collections = $state<Collection[]>([]);
	let newName = $state('');
	let creating = $state(false);
	let selectedDetail = $state<CollectionDetail | null>(null);

	onMount(async () => {
		collections = await listCollections();
	});

	async function handleCreate() {
		if (!newName.trim()) return;
		creating = true;
		try {
			await createCollection(newName.trim());
			newName = '';
			collections = await listCollections();
		} finally {
			creating = false;
		}
	}

	async function handleDelete(id: string) {
		if (!confirm('Delete this collection?')) return;
		await deleteCollection(id);
		collections = await listCollections();
		if (selectedDetail?.id === id) {
			selectedDetail = null;
		}
	}

	async function openCollection(id: string) {
		selectedDetail = await getCollection(id);
	}

	async function handleRemoveVideo(videoId: string) {
		if (!selectedDetail) return;
		await removeFromCollection(selectedDetail.id, videoId);
		selectedDetail = await getCollection(selectedDetail.id);
		collections = await listCollections();
	}
</script>

<svelte:head>
	<title>{t('collections')} — ReelScript</title>
</svelte:head>

<div class="collections-layout">
	<div class="sidebar">
		<h2>{t('myCollections')}</h2>

		<form class="create-form" onsubmit={(e) => { e.preventDefault(); handleCreate(); }}>
			<input
				type="text"
				bind:value={newName}
				placeholder={t('collectionName')}
				disabled={creating}
			/>
			<button class="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
				{t('create')}
			</button>
		</form>

		<div class="collection-list">
			{#each collections as col (col.id)}
				<div class="collection-row" class:active={selectedDetail?.id === col.id}>
					<button class="collection-btn" onclick={() => openCollection(col.id)}>
						<span class="col-name">{col.name}</span>
						<span class="col-count-badge">{col.video_count}</span>
					</button>
					<button class="btn btn-danger btn-sm" onclick={() => handleDelete(col.id)}>
						x
					</button>
				</div>
			{/each}

			{#if collections.length === 0}
				<p class="empty">{t('noCollections')}</p>
			{/if}
		</div>
	</div>

	<div class="detail-panel">
		{#if selectedDetail}
			<h2>{selectedDetail.name}</h2>
			{#if selectedDetail.description}
				<p class="description">{selectedDetail.description}</p>
			{/if}

			{#if selectedDetail.videos.length === 0}
				<p class="empty">{t('noCollectionsYet')}</p>
			{:else}
				<div class="video-grid">
					{#each selectedDetail.videos as item (item.item_id)}
						<div class="video-item card">
							<div class="video-item-header">
								<a href="/watch/{item.video_id}" class="video-item-title">
									{item.title || t('untitled')}
								</a>
								<button class="btn btn-danger btn-sm" onclick={() => handleRemoveVideo(item.video_id)}>
									x
								</button>
							</div>
							<div class="video-item-meta">
								{#if item.channel}
									<span>{item.channel}</span>
								{/if}
								<span class="badge {item.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
									{item.source === 'ig' ? 'IG' : 'YT'}
								</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		{:else}
			<div class="empty-detail">
				<p>{t('myCollections')}</p>
			</div>
		{/if}
	</div>
</div>

<style>
	.collections-layout {
		display: grid;
		grid-template-columns: 300px 1fr;
		gap: 32px;
		min-height: 60vh;
	}

	@media (max-width: 768px) {
		.collections-layout {
			grid-template-columns: 1fr;
			gap: 24px;
		}
	}

	@media (max-width: 640px) {
		.sidebar h2 {
			font-size: 16px;
		}

		.create-form input {
			font-size: 13px;
		}

		.detail-panel h2 {
			font-size: 17px;
		}

		.video-item {
			padding: 12px;
		}

		.video-item-title {
			font-size: 14px;
		}
	}

	.sidebar h2 {
		font-size: 18px;
		font-weight: 600;
		margin-bottom: 16px;
	}

	.create-form {
		display: flex;
		gap: 8px;
		margin-bottom: 20px;
	}

	.create-form input {
		flex: 1;
		padding: 8px 12px;
		font-size: 14px;
	}

	.create-form .btn {
		padding: 8px 14px;
		font-size: 13px;
	}

	.collection-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.collection-row {
		display: flex;
		align-items: center;
		gap: 4px;
		border-radius: var(--radius-sm);
	}

	.collection-row.active {
		background: var(--bg-hover);
	}

	.collection-btn {
		flex: 1;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 12px;
		border-radius: var(--radius-sm);
		text-align: left;
	}

	.collection-btn:hover {
		background: var(--bg-hover);
	}

	.col-name {
		font-weight: 500;
	}

	.col-count-badge {
		background: var(--bg-hover);
		color: var(--text-dim);
		font-size: 12px;
		padding: 2px 8px;
		border-radius: 10px;
		min-width: 24px;
		text-align: center;
	}

	.btn-sm {
		padding: 4px 8px;
		font-size: 12px;
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 16px 0;
	}

	/* Detail Panel */
	.detail-panel h2 {
		font-size: 20px;
		font-weight: 600;
		margin-bottom: 8px;
	}

	.description {
		color: var(--text-dim);
		margin-bottom: 20px;
	}

	.video-grid {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.video-item {
		padding: 16px;
	}

	.video-item-header {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: 12px;
	}

	.video-item-title {
		font-weight: 600;
		font-size: 15px;
	}

	.video-item-meta {
		display: flex;
		gap: 12px;
		margin-top: 8px;
		font-size: 13px;
		color: var(--text-dim);
	}

	.empty-detail {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 40vh;
		color: var(--text-dim);
	}
</style>
