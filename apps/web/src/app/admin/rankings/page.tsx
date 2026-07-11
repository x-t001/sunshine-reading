"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import {
  createAdminRankingItem,
  createAdminRankingType,
  getAdminRankingItems,
  getAdminRankingTypes,
  updateAdminRankingItem,
  updateAdminRankingType,
  updateAdminRankingTypeStatus,
} from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type {
  AdminRankingItem,
  AdminRankingItemListParams,
  AdminRankingType,
  AdminRankingTypeListParams,
  CreateAdminRankingItemPayload,
  CreateAdminRankingTypePayload,
  UpdateAdminRankingItemPayload,
  UpdateAdminRankingTypePayload,
} from "@/types/admin";

const PAGE_SIZE = 10;

type TypeFilterState = {
  keyword: string;
  is_active: "" | "true" | "false";
};

type ItemFilterState = {
  ranking_type_id: string;
  novel_id: string;
  keyword: string;
};

type RankingTypeFormState = {
  name: string;
  code: string;
  description: string;
  is_active: boolean;
};

type RankingItemFormState = {
  ranking_type_id: string;
  novel_id: string;
  score: string;
  rank: string;
  calculated_at: string;
};

const emptyTypeFilters: TypeFilterState = { keyword: "", is_active: "" };
const emptyItemFilters: ItemFilterState = { ranking_type_id: "", novel_id: "", keyword: "" };

const initialTypeForm: RankingTypeFormState = {
  name: "",
  code: "",
  description: "",
  is_active: true,
};

const initialItemForm: RankingItemFormState = {
  ranking_type_id: "",
  novel_id: "",
  score: "0.00",
  rank: "1",
  calculated_at: "",
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "暂无";
  }
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildTypeParams(page: number, filters: TypeFilterState): AdminRankingTypeListParams {
  return {
    page,
    page_size: PAGE_SIZE,
    keyword: filters.keyword,
    is_active: filters.is_active === "" ? "" : filters.is_active === "true",
  };
}

function buildItemParams(page: number, filters: ItemFilterState): AdminRankingItemListParams {
  return {
    page,
    page_size: PAGE_SIZE,
    ranking_type_id: filters.ranking_type_id,
    novel_id: filters.novel_id,
    keyword: filters.keyword,
  };
}

function validateTypeForm(form: RankingTypeFormState): string | null {
  if (!form.name.trim()) {
    return "榜单名称不能为空。";
  }
  if (!form.code.trim()) {
    return "榜单编码不能为空。";
  }
  return null;
}

function validateItemForm(form: RankingItemFormState): string | null {
  if (!form.ranking_type_id.trim()) {
    return "榜单类型 ID 不能为空。";
  }
  if (!form.novel_id.trim()) {
    return "小说 ID 不能为空。";
  }
  if (!Number.isInteger(Number(form.ranking_type_id)) || Number(form.ranking_type_id) <= 0) {
    return "榜单类型 ID 必须是正整数。";
  }
  if (!Number.isInteger(Number(form.novel_id)) || Number(form.novel_id) <= 0) {
    return "小说 ID 必须是正整数。";
  }
  if (!Number.isInteger(Number(form.rank)) || Number(form.rank) <= 0) {
    return "排名必须是正整数。";
  }
  if (!Number.isFinite(Number(form.score))) {
    return "分数必须是数字。";
  }
  return null;
}

function normalizeTypePayload(form: RankingTypeFormState): CreateAdminRankingTypePayload {
  return {
    name: form.name.trim(),
    code: form.code.trim(),
    description: form.description.trim(),
    is_active: form.is_active,
  };
}

function normalizeItemPayload(form: RankingItemFormState): CreateAdminRankingItemPayload {
  const payload: CreateAdminRankingItemPayload = {
    ranking_type_id: Number(form.ranking_type_id),
    novel_id: Number(form.novel_id),
    score: Number(form.score).toFixed(2),
    rank: Number(form.rank),
  };
  if (form.calculated_at.trim()) {
    payload.calculated_at = form.calculated_at.trim();
  }
  return payload;
}

function typeToForm(rankingType: AdminRankingType): RankingTypeFormState {
  return {
    name: rankingType.name,
    code: rankingType.code,
    description: rankingType.description || "",
    is_active: rankingType.is_active,
  };
}

function itemToForm(item: AdminRankingItem): RankingItemFormState {
  return {
    ranking_type_id: String(item.ranking_type_id),
    novel_id: String(item.novel_id),
    score: item.score,
    rank: String(item.rank),
    calculated_at: item.calculated_at,
  };
}

export default function AdminRankingsPage() {
  return (
    <AdminLayout title="榜单管理" description="维护榜单类型和榜单条目，控制前台排行榜展示。">
      <AdminRankingsContent />
    </AdminLayout>
  );
}

function AdminRankingsContent() {
  const [typeFilters, setTypeFilters] = useState<TypeFilterState>(emptyTypeFilters);
  const [typeQuery, setTypeQuery] = useState<TypeFilterState>(typeFilters);
  const [typePage, setTypePage] = useState(1);
  const [types, setTypes] = useState<AdminRankingType[]>([]);
  const [typeCount, setTypeCount] = useState(0);
  const [typeNext, setTypeNext] = useState<string | null>(null);
  const [typePrevious, setTypePrevious] = useState<string | null>(null);
  const [typeForm, setTypeForm] = useState<RankingTypeFormState>(initialTypeForm);
  const [typeEditForms, setTypeEditForms] = useState<Record<number, RankingTypeFormState>>({});
  const [editingTypeId, setEditingTypeId] = useState<number | null>(null);
  const [typeLoading, setTypeLoading] = useState(false);

  const [itemFilters, setItemFilters] = useState<ItemFilterState>(emptyItemFilters);
  const [itemQuery, setItemQuery] = useState<ItemFilterState>(itemFilters);
  const [itemPage, setItemPage] = useState(1);
  const [items, setItems] = useState<AdminRankingItem[]>([]);
  const [itemCount, setItemCount] = useState(0);
  const [itemNext, setItemNext] = useState<string | null>(null);
  const [itemPrevious, setItemPrevious] = useState<string | null>(null);
  const [itemForm, setItemForm] = useState<RankingItemFormState>(initialItemForm);
  const [itemEditForms, setItemEditForms] = useState<Record<number, RankingItemFormState>>({});
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [itemLoading, setItemLoading] = useState(false);

  const [operatingKey, setOperatingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadTypes = useCallback(async () => {
    setTypeLoading(true);
    setError(null);
    try {
      const result = await getAdminRankingTypes(buildTypeParams(typePage, typeQuery));
      setTypes(result.results);
      setTypeCount(result.count);
      setTypeNext(result.next);
      setTypePrevious(result.previous);
      setTypeEditForms(
        result.results.reduce<Record<number, RankingTypeFormState>>((forms, rankingType) => {
          forms[rankingType.id] = typeToForm(rankingType);
          return forms;
        }, {}),
      );
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setTypeLoading(false);
    }
  }, [typePage, typeQuery]);

  const loadItems = useCallback(async () => {
    setItemLoading(true);
    setError(null);
    try {
      const result = await getAdminRankingItems(buildItemParams(itemPage, itemQuery));
      setItems(result.results);
      setItemCount(result.count);
      setItemNext(result.next);
      setItemPrevious(result.previous);
      setItemEditForms(
        result.results.reduce<Record<number, RankingItemFormState>>((forms, item) => {
          forms[item.id] = itemToForm(item);
          return forms;
        }, {}),
      );
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setItemLoading(false);
    }
  }, [itemPage, itemQuery]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadTypes();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadTypes]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadItems();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadItems]);

  function handleTypeSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTypePage(1);
    setTypeQuery(typeFilters);
  }

  function handleItemSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setItemPage(1);
    setItemQuery(itemFilters);
  }

  async function handleCreateType(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateTypeForm(typeForm);
    if (validationError) {
      setError(validationError);
      return;
    }

    setOperatingKey("type:create");
    setError(null);
    setNotice(null);
    try {
      const payload = normalizeTypePayload(typeForm);
      await createAdminRankingType(payload);
      setNotice(`榜单「${payload.name}」已创建。`);
      setTypeForm(initialTypeForm);
      setTypePage(1);
      setTypeQuery(emptyTypeFilters);
      setTypeFilters(emptyTypeFilters);
      const result = await getAdminRankingTypes(buildTypeParams(1, emptyTypeFilters));
      setTypes(result.results);
      setTypeCount(result.count);
      setTypeNext(result.next);
      setTypePrevious(result.previous);
      setTypeEditForms(
        result.results.reduce<Record<number, RankingTypeFormState>>((forms, rankingType) => {
          forms[rankingType.id] = typeToForm(rankingType);
          return forms;
        }, {}),
      );
    } catch (createError) {
      setError(getApiErrorMessage(createError));
    } finally {
      setOperatingKey(null);
    }
  }

  async function handleUpdateType(rankingType: AdminRankingType) {
    const form = typeEditForms[rankingType.id];
    if (!form) {
      return;
    }
    const validationError = validateTypeForm(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setOperatingKey(`type:${rankingType.id}`);
    setError(null);
    setNotice(null);
    try {
      const payload: UpdateAdminRankingTypePayload = normalizeTypePayload(form);
      await updateAdminRankingType(rankingType.id, payload);
      setNotice(`榜单「${payload.name || rankingType.name}」已更新。`);
      setEditingTypeId(null);
      await loadTypes();
    } catch (updateError) {
      setError(getApiErrorMessage(updateError));
    } finally {
      setOperatingKey(null);
    }
  }

  async function handleTypeStatus(rankingType: AdminRankingType, isActive: boolean) {
    const actionText = isActive ? "启用" : "停用";
    if (!window.confirm(`确认${actionText}榜单「${rankingType.name}」？`)) {
      return;
    }

    setOperatingKey(`type:${rankingType.id}`);
    setError(null);
    setNotice(null);
    try {
      await updateAdminRankingTypeStatus(rankingType.id, { is_active: isActive });
      setNotice(`榜单「${rankingType.name}」已${actionText}。`);
      await loadTypes();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperatingKey(null);
    }
  }

  async function handleCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateItemForm(itemForm);
    if (validationError) {
      setError(validationError);
      return;
    }

    setOperatingKey("item:create");
    setError(null);
    setNotice(null);
    try {
      const payload = normalizeItemPayload(itemForm);
      await createAdminRankingItem(payload);
      setNotice("榜单条目已创建。");
      setItemForm(initialItemForm);
      setItemPage(1);
      setItemQuery(emptyItemFilters);
      setItemFilters(emptyItemFilters);
      const result = await getAdminRankingItems(buildItemParams(1, emptyItemFilters));
      setItems(result.results);
      setItemCount(result.count);
      setItemNext(result.next);
      setItemPrevious(result.previous);
      setItemEditForms(
        result.results.reduce<Record<number, RankingItemFormState>>((forms, item) => {
          forms[item.id] = itemToForm(item);
          return forms;
        }, {}),
      );
      await loadTypes();
    } catch (createError) {
      setError(getApiErrorMessage(createError));
    } finally {
      setOperatingKey(null);
    }
  }

  async function handleUpdateItem(item: AdminRankingItem) {
    const form = itemEditForms[item.id];
    if (!form) {
      return;
    }
    const validationError = validateItemForm(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setOperatingKey(`item:${item.id}`);
    setError(null);
    setNotice(null);
    try {
      const payload: UpdateAdminRankingItemPayload = normalizeItemPayload(form);
      await updateAdminRankingItem(item.id, payload);
      setNotice(`榜单条目 #${item.id} 已更新。`);
      setEditingItemId(null);
      await loadItems();
      await loadTypes();
    } catch (updateError) {
      setError(getApiErrorMessage(updateError));
    } finally {
      setOperatingKey(null);
    }
  }

  function updateTypeEditForm(id: number, patch: Partial<RankingTypeFormState>) {
    setTypeEditForms((current) => ({
      ...current,
      [id]: { ...current[id], ...patch },
    }));
  }

  function updateItemEditForm(id: number, patch: Partial<RankingItemFormState>) {
    setItemEditForms((current) => ({
      ...current,
      [id]: { ...current[id], ...patch },
    }));
  }

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
        <div>
          <h2 className="text-base font-semibold text-zinc-900">榜单类型</h2>
          <p className="mt-1 text-sm text-zinc-500">控制前台展示哪些榜单，以及榜单名称和说明。</p>
        </div>

        <form className="grid gap-3 md:grid-cols-4" onSubmit={handleTypeSearch}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={typeFilters.keyword}
            onChange={(event) => setTypeFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="搜索名称、编码或描述"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={typeFilters.is_active}
            onChange={(event) => setTypeFilters((current) => ({ ...current, is_active: event.target.value as TypeFilterState["is_active"] }))}
          >
            <option value="">全部状态</option>
            <option value="true">已启用</option>
            <option value="false">已停用</option>
          </select>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>

        <form className="grid gap-3 md:grid-cols-5" onSubmit={handleCreateType}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={typeForm.name}
            onChange={(event) => setTypeForm((current) => ({ ...current, name: event.target.value }))}
            placeholder="榜单名称"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={typeForm.code}
            onChange={(event) => setTypeForm((current) => ({ ...current, code: event.target.value }))}
            placeholder="榜单编码"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={typeForm.description}
            onChange={(event) => setTypeForm((current) => ({ ...current, description: event.target.value }))}
            placeholder="描述"
          />
          <label className="flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600">
            <input
              type="checkbox"
              checked={typeForm.is_active}
              onChange={(event) => setTypeForm((current) => ({ ...current, is_active: event.target.checked }))}
            />
            启用
          </label>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300" type="submit" disabled={operatingKey === "type:create"}>
            创建榜单
          </button>
        </form>

        {typeLoading ? <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500">正在加载榜单类型...</p> : null}
        {!typeLoading && types.length === 0 ? <p className="rounded-lg border border-dashed border-zinc-300 p-4 text-center text-sm text-zinc-500">暂无榜单类型</p> : null}

        {types.length > 0 ? (
          <div className="overflow-x-auto rounded-xl border border-zinc-100">
            <table className="min-w-[980px] text-left text-sm">
              <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500">
                <tr>
                  <th className="px-4 py-3">榜单</th>
                  <th className="px-4 py-3">描述</th>
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3">条目</th>
                  <th className="px-4 py-3">时间</th>
                  <th className="px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {types.map((rankingType) => {
                  const editing = editingTypeId === rankingType.id;
                  const form = typeEditForms[rankingType.id] || typeToForm(rankingType);
                  return (
                    <tr key={rankingType.id} className="align-top">
                      <td className="px-4 py-3">
                        {editing ? (
                          <div className="space-y-2">
                            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.name} onChange={(event) => updateTypeEditForm(rankingType.id, { name: event.target.value })} />
                            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.code} onChange={(event) => updateTypeEditForm(rankingType.id, { code: event.target.value })} />
                          </div>
                        ) : (
                          <>
                            <p className="font-medium text-zinc-900">{rankingType.name}</p>
                            <p className="mt-1 text-xs text-zinc-500">{rankingType.code}</p>
                          </>
                        )}
                      </td>
                      <td className="px-4 py-3 text-zinc-600">
                        {editing ? (
                          <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.description} onChange={(event) => updateTypeEditForm(rankingType.id, { description: event.target.value })} />
                        ) : (
                          rankingType.description || "暂无"
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <label className="flex items-center gap-2 text-sm text-zinc-600">
                            <input type="checkbox" checked={form.is_active} onChange={(event) => updateTypeEditForm(rankingType.id, { is_active: event.target.checked })} />
                            启用
                          </label>
                        ) : (
                          <span className={rankingType.is_active ? "text-emerald-600" : "text-red-600"}>{rankingType.is_active ? "已启用" : "已停用"}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-zinc-500">{rankingType.item_count}</td>
                      <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                        <p>创建 {formatDateTime(rankingType.created_at)}</p>
                        <p>更新 {formatDateTime(rankingType.updated_at)}</p>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          {editing ? (
                            <>
                              <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operatingKey === `type:${rankingType.id}`} onClick={() => void handleUpdateType(rankingType)}>
                                保存
                              </button>
                              <button className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700" type="button" onClick={() => setEditingTypeId(null)}>
                                取消
                              </button>
                            </>
                          ) : (
                            <>
                              <button className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700" type="button" onClick={() => setEditingTypeId(rankingType.id)}>
                                编辑
                              </button>
                              <button className={rankingType.is_active ? "rounded-lg bg-red-600 px-3 py-2 text-white" : "rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700"} type="button" onClick={() => void handleTypeStatus(rankingType, !rankingType.is_active)}>
                                {rankingType.is_active ? "停用" : "启用"}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="flex items-center justify-between rounded-lg bg-zinc-50 p-3 text-sm">
          <button className={typePrevious ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!typePrevious} onClick={() => setTypePage((current) => Math.max(1, current - 1))}>
            上一页
          </button>
          <span className="text-zinc-500">共 {typeCount} 个榜单</span>
          <button className={typeNext ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!typeNext} onClick={() => setTypePage((current) => current + 1)}>
            下一页
          </button>
        </div>
      </section>

      <section className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
        <div>
          <h2 className="text-base font-semibold text-zinc-900">榜单条目</h2>
          <p className="mt-1 text-sm text-zinc-500">手动维护榜单内小说、排名、分数和快照时间。</p>
        </div>

        <form className="grid gap-3 md:grid-cols-4" onSubmit={handleItemSearch}>
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemFilters.keyword} onChange={(event) => setItemFilters((current) => ({ ...current, keyword: event.target.value }))} placeholder="搜索小说或榜单" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemFilters.ranking_type_id} onChange={(event) => setItemFilters((current) => ({ ...current, ranking_type_id: event.target.value }))} placeholder="榜单类型 ID" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemFilters.novel_id} onChange={(event) => setItemFilters((current) => ({ ...current, novel_id: event.target.value }))} placeholder="小说 ID" />
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>

        <form className="grid gap-3 md:grid-cols-6" onSubmit={handleCreateItem}>
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemForm.ranking_type_id} onChange={(event) => setItemForm((current) => ({ ...current, ranking_type_id: event.target.value }))} placeholder="榜单类型 ID" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemForm.novel_id} onChange={(event) => setItemForm((current) => ({ ...current, novel_id: event.target.value }))} placeholder="小说 ID" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemForm.rank} onChange={(event) => setItemForm((current) => ({ ...current, rank: event.target.value }))} placeholder="排名" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemForm.score} onChange={(event) => setItemForm((current) => ({ ...current, score: event.target.value }))} placeholder="分数" />
          <input className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={itemForm.calculated_at} onChange={(event) => setItemForm((current) => ({ ...current, calculated_at: event.target.value }))} placeholder="快照时间，可留空" />
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300" type="submit" disabled={operatingKey === "item:create"}>
            创建条目
          </button>
        </form>

        {itemLoading ? <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500">正在加载榜单条目...</p> : null}
        {!itemLoading && items.length === 0 ? <p className="rounded-lg border border-dashed border-zinc-300 p-4 text-center text-sm text-zinc-500">暂无榜单条目</p> : null}

        {items.length > 0 ? (
          <div className="overflow-x-auto rounded-xl border border-zinc-100">
            <table className="min-w-[1120px] text-left text-sm">
              <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500">
                <tr>
                  <th className="px-4 py-3">榜单</th>
                  <th className="px-4 py-3">小说</th>
                  <th className="px-4 py-3">排名/分数</th>
                  <th className="px-4 py-3">快照时间</th>
                  <th className="px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {items.map((item) => {
                  const editing = editingItemId === item.id;
                  const form = itemEditForms[item.id] || itemToForm(item);
                  return (
                    <tr key={item.id} className="align-top">
                      <td className="px-4 py-3">
                        {editing ? (
                          <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.ranking_type_id} onChange={(event) => updateItemEditForm(item.id, { ranking_type_id: event.target.value })} />
                        ) : (
                          <>
                            <p className="font-medium text-zinc-900">{item.ranking_type.name}</p>
                            <p className="mt-1 text-xs text-zinc-500">ID {item.ranking_type_id}</p>
                          </>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.novel_id} onChange={(event) => updateItemEditForm(item.id, { novel_id: event.target.value })} />
                        ) : (
                          <>
                            <p className="font-medium text-zinc-900">{item.novel_title}</p>
                            <p className="mt-1 text-xs text-zinc-500">ID {item.novel_id}</p>
                          </>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <div className="space-y-2">
                            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.rank} onChange={(event) => updateItemEditForm(item.id, { rank: event.target.value })} />
                            <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.score} onChange={(event) => updateItemEditForm(item.id, { score: event.target.value })} />
                          </div>
                        ) : (
                          <>
                            <p>第 {item.rank} 名</p>
                            <p className="mt-1 text-xs text-zinc-500">分数 {item.score}</p>
                          </>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <input className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500" value={form.calculated_at} onChange={(event) => updateItemEditForm(item.id, { calculated_at: event.target.value })} />
                        ) : (
                          <span className="text-xs text-zinc-500">{formatDateTime(item.calculated_at)}</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <div className="flex flex-wrap gap-2">
                            <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operatingKey === `item:${item.id}`} onClick={() => void handleUpdateItem(item)}>
                              保存
                            </button>
                            <button className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700" type="button" onClick={() => setEditingItemId(null)}>
                              取消
                            </button>
                          </div>
                        ) : (
                          <button className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700" type="button" onClick={() => setEditingItemId(item.id)}>
                            编辑
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="flex items-center justify-between rounded-lg bg-zinc-50 p-3 text-sm">
          <button className={itemPrevious ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!itemPrevious} onClick={() => setItemPage((current) => Math.max(1, current - 1))}>
            上一页
          </button>
          <span className="text-zinc-500">共 {itemCount} 个条目</span>
          <button className={itemNext ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!itemNext} onClick={() => setItemPage((current) => current + 1)}>
            下一页
          </button>
        </div>
      </section>
    </div>
  );
}
