"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import {
  createAdminCategory,
  getAdminCategories,
  updateAdminCategory,
  updateAdminCategoryStatus,
} from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type {
  AdminCategory,
  AdminCategoryListParams,
  CreateAdminCategoryPayload,
  UpdateAdminCategoryPayload,
} from "@/types/admin";

const PAGE_SIZE = 10;

type FilterState = {
  keyword: string;
  is_active: "" | "true" | "false";
  parent_id: string;
};

type CategoryFormState = {
  name: string;
  slug: string;
  parent_id: string;
  sort_order: string;
  is_active: boolean;
};

const initialFormState: CategoryFormState = {
  name: "",
  slug: "",
  parent_id: "",
  sort_order: "0",
  is_active: true,
};
const emptyFilters: FilterState = { keyword: "", is_active: "", parent_id: "" };

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

function buildParams(page: number, filters: FilterState): AdminCategoryListParams {
  return {
    page,
    page_size: PAGE_SIZE,
    keyword: filters.keyword,
    is_active: filters.is_active === "" ? "" : filters.is_active === "true",
    parent_id: filters.parent_id,
  };
}

function normalizeFormPayload(form: CategoryFormState): CreateAdminCategoryPayload {
  return {
    name: form.name.trim(),
    slug: form.slug.trim(),
    parent_id: form.parent_id.trim() ? Number(form.parent_id) : null,
    sort_order: Number(form.sort_order) || 0,
    is_active: form.is_active,
  };
}

function validateForm(form: CategoryFormState): string | null {
  if (!form.name.trim()) {
    return "分类名称不能为空。";
  }
  if (!form.slug.trim()) {
    return "分类标识不能为空。";
  }
  if (form.parent_id.trim() && !Number.isInteger(Number(form.parent_id))) {
    return "父分类 ID 必须是整数。";
  }
  if (Number(form.sort_order) < 0) {
    return "排序值不能小于 0。";
  }
  return null;
}

function toFormState(category: AdminCategory): CategoryFormState {
  return {
    name: category.name,
    slug: category.slug,
    parent_id: category.parent_id ? String(category.parent_id) : "",
    sort_order: String(category.sort_order),
    is_active: category.is_active,
  };
}

export default function AdminCategoriesPage() {
  return (
    <AdminLayout title="分类管理" description="维护小说分类、排序、父级关系和启用状态。">
      <AdminCategoriesContent />
    </AdminLayout>
  );
}

function AdminCategoriesContent() {
  const [filters, setFilters] = useState<FilterState>({ keyword: "", is_active: "", parent_id: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AdminCategory[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<CategoryFormState>(initialFormState);
  const [editForms, setEditForms] = useState<Record<number, CategoryFormState>>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const activeCategoryOptions = useMemo(
    () => items.filter((category) => category.is_active).map((category) => ({ id: category.id, label: category.name })),
    [items],
  );

  const loadCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminCategories(buildParams(page, query));
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
      setEditForms(
        result.results.reduce<Record<number, CategoryFormState>>((forms, category) => {
          forms[category.id] = toFormState(category);
          return forms;
        }, {}),
      );
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [page, query]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadCategories();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadCategories]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(filters);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateForm(createForm);
    if (validationError) {
      setError(validationError);
      return;
    }

    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const payload = normalizeFormPayload(createForm);
      await createAdminCategory(payload);
      setNotice(`分类「${payload.name}」已创建。`);
      setCreateForm(initialFormState);
      setPage(1);
      setQuery(emptyFilters);
      setFilters(emptyFilters);
      const result = await getAdminCategories(buildParams(1, emptyFilters));
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
      setEditForms(
        result.results.reduce<Record<number, CategoryFormState>>((forms, category) => {
          forms[category.id] = toFormState(category);
          return forms;
        }, {}),
      );
    } catch (createError) {
      setError(getApiErrorMessage(createError));
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(category: AdminCategory) {
    const form = editForms[category.id];
    if (!form) {
      return;
    }
    const validationError = validateForm(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setOperatingId(category.id);
    setError(null);
    setNotice(null);
    try {
      const payload: UpdateAdminCategoryPayload = normalizeFormPayload(form);
      await updateAdminCategory(category.id, payload);
      setNotice(`分类「${payload.name || category.name}」已更新。`);
      setEditingId(null);
      await loadCategories();
    } catch (updateError) {
      setError(getApiErrorMessage(updateError));
    } finally {
      setOperatingId(null);
    }
  }

  async function handleStatus(category: AdminCategory, isActive: boolean) {
    const actionText = isActive ? "启用" : "停用";
    if (!window.confirm(`确认${actionText}分类「${category.name}」？`)) {
      return;
    }

    setOperatingId(category.id);
    setError(null);
    setNotice(null);
    try {
      await updateAdminCategoryStatus(category.id, { is_active: isActive });
      setNotice(`分类「${category.name}」已${actionText}。`);
      await loadCategories();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperatingId(null);
    }
  }

  function updateEditForm(categoryId: number, patch: Partial<CategoryFormState>) {
    setEditForms((current) => ({
      ...current,
      [categoryId]: {
        ...current[categoryId],
        ...patch,
      },
    }));
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="grid gap-3 md:grid-cols-5" onSubmit={handleSearch}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={filters.keyword}
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="搜索分类名称或 slug"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.is_active}
            onChange={(event) => setFilters((current) => ({ ...current, is_active: event.target.value as FilterState["is_active"] }))}
          >
            <option value="">全部状态</option>
            <option value="true">已启用</option>
            <option value="false">已停用</option>
          </select>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.parent_id}
            onChange={(event) => setFilters((current) => ({ ...current, parent_id: event.target.value }))}
            placeholder="父分类 ID"
          />
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900">创建分类</h2>
        <form className="mt-3 grid gap-3 md:grid-cols-6" onSubmit={handleCreate}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={createForm.name}
            onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
            placeholder="分类名称"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={createForm.slug}
            onChange={(event) => setCreateForm((current) => ({ ...current, slug: event.target.value }))}
            placeholder="分类标识 slug"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={createForm.parent_id}
            onChange={(event) => setCreateForm((current) => ({ ...current, parent_id: event.target.value }))}
          >
            <option value="">无父分类</option>
            {activeCategoryOptions.map((category) => (
              <option key={category.id} value={category.id}>
                {category.label}
              </option>
            ))}
          </select>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            type="number"
            min={0}
            value={createForm.sort_order}
            onChange={(event) => setCreateForm((current) => ({ ...current, sort_order: event.target.value }))}
            placeholder="排序值"
          />
          <label className="flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600">
            <input
              type="checkbox"
              checked={createForm.is_active}
              onChange={(event) => setCreateForm((current) => ({ ...current, is_active: event.target.checked }))}
            />
            启用
          </label>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300" type="submit" disabled={creating}>
            {creating ? "创建中..." : "创建分类"}
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载分类列表...</p> : null}

      {!loading && items.length === 0 ? <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无数据</section> : null}

      {items.length > 0 ? (
        <section className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="min-w-[1080px] text-left text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500">
              <tr>
                <th className="px-4 py-3">分类</th>
                <th className="px-4 py-3">父级</th>
                <th className="px-4 py-3">排序/状态</th>
                <th className="px-4 py-3">内容</th>
                <th className="px-4 py-3">时间</th>
                <th className="px-4 py-3">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {items.map((category) => {
                const editing = editingId === category.id;
                const form = editForms[category.id] || toFormState(category);
                return (
                  <tr key={category.id} className="align-top">
                    <td className="px-4 py-3">
                      {editing ? (
                        <div className="space-y-2">
                          <input
                            className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                            value={form.name}
                            onChange={(event) => updateEditForm(category.id, { name: event.target.value })}
                          />
                          <input
                            className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                            value={form.slug}
                            onChange={(event) => updateEditForm(category.id, { slug: event.target.value })}
                          />
                        </div>
                      ) : (
                        <>
                          <p className="font-medium text-zinc-900">{category.name}</p>
                          <p className="mt-1 text-xs text-zinc-500">{category.slug}</p>
                          <p className="mt-1 text-xs text-zinc-400">ID {category.id}</p>
                        </>
                      )}
                    </td>
                    <td className="px-4 py-3 text-zinc-600">
                      {editing ? (
                        <input
                          className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                          value={form.parent_id}
                          onChange={(event) => updateEditForm(category.id, { parent_id: event.target.value })}
                          placeholder="父分类 ID，空为无"
                        />
                      ) : (
                        category.parent_name || "无父分类"
                      )}
                    </td>
                    <td className="px-4 py-3 text-zinc-600">
                      {editing ? (
                        <div className="space-y-2">
                          <input
                            className="w-full rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                            type="number"
                            min={0}
                            value={form.sort_order}
                            onChange={(event) => updateEditForm(category.id, { sort_order: event.target.value })}
                          />
                          <label className="flex items-center gap-2 text-xs text-zinc-600">
                            <input
                              type="checkbox"
                              checked={form.is_active}
                              onChange={(event) => updateEditForm(category.id, { is_active: event.target.checked })}
                            />
                            启用
                          </label>
                        </div>
                      ) : (
                        <>
                          <p>排序 {category.sort_order}</p>
                          <p className={category.is_active ? "mt-1 text-xs text-emerald-600" : "mt-1 text-xs text-red-600"}>
                            {category.is_active ? "已启用" : "已停用"}
                          </p>
                        </>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                      <p>子分类 {category.children_count}</p>
                      <p>小说 {category.novel_count}</p>
                    </td>
                    <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                      <p>创建 {formatDateTime(category.created_at)}</p>
                      <p>更新 {formatDateTime(category.updated_at)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {editing ? (
                          <>
                            <button
                              className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
                              type="button"
                              disabled={operatingId === category.id}
                              onClick={() => void handleUpdate(category)}
                            >
                              保存
                            </button>
                            <button
                              className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700"
                              type="button"
                              disabled={operatingId === category.id}
                              onClick={() => {
                                setEditingId(null);
                                updateEditForm(category.id, toFormState(category));
                              }}
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700"
                              type="button"
                              disabled={operatingId === category.id}
                              onClick={() => setEditingId(category.id)}
                            >
                              编辑
                            </button>
                            <button
                              className={
                                category.is_active
                                  ? "rounded-lg bg-red-600 px-3 py-2 text-white disabled:bg-zinc-300"
                                  : "rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400"
                              }
                              type="button"
                              disabled={operatingId === category.id}
                              onClick={() => void handleStatus(category, !category.is_active)}
                            >
                              {category.is_active ? "停用" : "启用"}
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
        </section>
      ) : null}

      <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
        <button className={previous ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          上一页
        </button>
        <span className="text-zinc-500">共 {count} 个分类</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>
    </div>
  );
}
