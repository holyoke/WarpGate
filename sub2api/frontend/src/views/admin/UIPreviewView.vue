<template>
  <AppLayout>
    <div class="space-y-5">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="mb-2 font-mono text-xs tracking-widest wg-muted">WARPGATE / DESIGN PREVIEW</p>
          <h2 class="text-2xl font-semibold text-gray-900 dark:text-white">{{ t('uiPreview.title') }}</h2>
          <p class="mt-2 text-sm wg-muted">{{ t('uiPreview.description') }}</p>
        </div>
        <span class="badge badge-warning">{{ t('uiPreview.demoOnly') }}</span>
      </div>

      <div class="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <button v-for="item in sections" :key="item" class="wg-panel p-4 text-left transition-colors hover:border-primary-500" :class="section === item ? 'ring-1 ring-primary-500' : ''" :aria-pressed="section === item" @click="section = item">
          <span class="text-xs wg-muted">{{ t(`uiPreview.sections.${item}`) }}</span>
          <span class="mt-2 block font-mono text-2xl font-semibold text-gray-900 dark:text-white">24<span class="ml-2 text-xs font-normal wg-muted">{{ t('uiPreview.records') }}</span></span>
          <span class="mt-2 block text-xs wg-muted">{{ t(`uiPreview.summaries.${item}`) }}</span>
        </button>
      </div>

      <section class="wg-panel overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 p-4 dark:border-dark-700">
          <div class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-primary-600 dark:bg-primary-400"></span>
            <h3 class="text-sm font-semibold">{{ t(`uiPreview.sections.${section}`) }}</h3>
            <span class="badge badge-gray">{{ filtered.length }}</span>
          </div>
          <div class="flex w-full flex-wrap gap-2 sm:w-auto">
            <input v-model="search" class="input sm:w-64" type="search" :aria-label="t('uiPreview.search')" :placeholder="t('uiPreview.search')" />
            <select v-model="status" class="input w-auto" :aria-label="t('uiPreview.statusFilter')">
              <option value="all">{{ t('uiPreview.allStatuses') }}</option>
              <option v-for="value in statuses" :key="value" :value="value">{{ statusLabel(value) }}</option>
            </select>
            <button class="btn btn-secondary" @click="reset">{{ t('uiPreview.reset') }}</button>
          </div>
        </div>
        <div class="p-3">
          <DataTable :key="section" :columns="columns" :data="pageRows" row-key="id" :server-side-sort="true" :clickable-rows="true" :expandable-actions="false" @sort="sortRows" @row-click="selected = $event">
            <template #cell-name="{ row }">
              <div class="py-1"><div class="font-medium">{{ row.name }}</div><div class="mt-1 text-xs wg-muted">{{ row.description }}</div></div>
            </template>
            <template #cell-id="{ value }"><span class="font-mono text-xs wg-muted">{{ value }}</span></template>
            <template #cell-status="{ value }"><span :class="['badge', statusClass(value)]"><span class="mr-1 h-1.5 w-1.5 rounded-full bg-current"></span>{{ statusLabel(value) }}</span></template>
            <template #cell-metric="{ value }"><span class="font-mono font-medium">{{ formatMetric(value) }}</span></template>
            <template #cell-updated="{ value }"><span class="font-mono text-xs wg-muted">{{ value }}</span></template>
            <template #cell-actions="{ row }"><button class="btn btn-secondary btn-sm" @click.stop="selected = row">{{ t('uiPreview.details') }}</button></template>
          </DataTable>
        </div>
        <Pagination v-if="filtered.length" v-model:page="page" :page-size="8" :total="filtered.length" :show-page-size-selector="false" />
        <p class="px-4 py-3 text-xs wg-muted">{{ t('uiPreview.footer') }}</p>
      </section>

      <BaseDialog :show="!!selected" :title="t('uiPreview.details')" @close="selected = null">
        <dl v-if="selected" class="space-y-4">
          <div v-for="column in columns.filter(c => c.key !== 'actions')" :key="column.key" class="flex justify-between gap-4 border-b border-gray-200 pb-3 text-sm dark:border-dark-700">
            <dt class="wg-muted">{{ column.label }}</dt>
            <dd class="text-right font-medium">{{ column.key === 'status' ? statusLabel(selected.status) : column.key === 'metric' ? formatMetric(selected.metric) : selected[column.key as keyof PreviewRow] }}</dd>
          </div>
          <p class="text-xs wg-muted">{{ t('uiPreview.demoOnly') }}</p>
        </dl>
      </BaseDialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppLayout from '@/components/layout/AppLayout.vue'
import DataTable from '@/components/common/DataTable.vue'
import Pagination from '@/components/common/Pagination.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import type { Column } from '@/components/common/types'
import { sections, createPreviewRows, filterPreviewRows, type PreviewRow, type PreviewSection } from './ui-preview/fixtures'

const { t, locale } = useI18n()
const section = ref<PreviewSection>('users'), search = ref(''), status = ref('all'), page = ref(1)
const selected = ref<PreviewRow | null>(null)
const sort = ref({ key: 'id', order: 'asc' as 'asc' | 'desc' })
const statuses = ['healthy', 'pending', 'failed', 'disabled'] as const
const rows = computed(() => createPreviewRows(section.value))
const filtered = computed(() => filterPreviewRows(rows.value, search.value, status.value).sort((a, b) => {
  const key = sort.value.key as keyof PreviewRow
  const left = a[key], right = b[key]
  const result = typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right), locale.value, { numeric: true })
  return sort.value.order === 'asc' ? result : -result
}))
const pageRows = computed(() => filtered.value.slice((page.value - 1) * 8, page.value * 8))
const columns = computed<Column[]>(() => [
  { key: 'name', label: t(`uiPreview.names.${section.value}`), sortable: true },
  { key: 'id', label: 'ID', sortable: true },
  { key: 'category', label: t('uiPreview.category'), sortable: true },
  { key: 'status', label: t('uiPreview.statusFilter'), sortable: true },
  { key: 'metric', label: t(`uiPreview.metrics.${section.value}`), sortable: true },
  { key: 'updated', label: t('uiPreview.updated'), sortable: true },
  { key: 'actions', label: t('uiPreview.action') }
])
const statusLabel = (value: string) => t(`uiPreview.status.${value}`)
const statusClass = (value: string) => ({ healthy: 'badge-success', pending: 'badge-warning', failed: 'badge-danger', disabled: 'badge-gray' })[value] || 'badge-gray'
function formatMetric(value: number) {
  if (section.value === 'channels') return `${value} ms`
  if (section.value === 'requests') return value.toLocaleString(locale.value)
  return new Intl.NumberFormat(locale.value, { style: 'currency', currency: section.value === 'orders' ? 'CNY' : 'USD' }).format(value)
}
function sortRows(key: string, order: 'asc' | 'desc') { sort.value = { key, order }; page.value = 1 }
function reset() { search.value = ''; status.value = 'all'; page.value = 1; selected.value = null }
watch(section, reset)
watch([search, status], () => { page.value = 1 })
</script>
