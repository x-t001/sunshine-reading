import { formatDateLabel } from "@/lib/utils/format";
import type { AuthorAuditLog } from "@/types/author";

type AuthorAuditHistoryProps = {
  logs: AuthorAuditLog[];
  currentStatus: string;
};

const actionLabels: Record<AuthorAuditLog["action"], string> = {
  submit: "提交审核",
  claim: "领取审核",
  approve: "审核通过",
  reject: "审核驳回",
};

const statusLabels: Record<string, string> = {
  draft: "草稿",
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已驳回",
};

function getStatusLabel(status: string): string {
  return statusLabels[status] || status || "未设置";
}

export function AuthorAuditHistory({ logs, currentStatus }: AuthorAuditHistoryProps) {
  const latestRejection = currentStatus === "rejected" ? logs.find((log) => log.action === "reject") : null;

  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold">审核历史</h2>

      {latestRejection?.reason ? (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">
          <p className="font-medium">最近驳回原因</p>
          <p className="mt-1 whitespace-pre-wrap leading-6">{latestRejection.reason}</p>
        </div>
      ) : null}

      {logs.length === 0 ? (
        <p className="mt-3 rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500">暂无审核记录。</p>
      ) : (
        <ol className="mt-3 divide-y divide-zinc-200 border-y border-zinc-200">
          {logs.map((log) => (
            <li key={log.id} className="py-3 text-sm">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <p className="font-medium text-zinc-800">{actionLabels[log.action]}</p>
                <time className="text-xs text-zinc-500" dateTime={log.created_at}>
                  {formatDateLabel(log.created_at)}
                </time>
              </div>
              <p className="mt-1 text-zinc-600">
                {getStatusLabel(log.from_status)} → {getStatusLabel(log.to_status)}
                {log.reviewer ? ` · ${log.reviewer.nickname || log.reviewer.username}` : " · 作者提交"}
              </p>
              {log.reason ? <p className="mt-2 whitespace-pre-wrap rounded-lg bg-zinc-50 px-3 py-2 leading-6 text-zinc-700">{log.reason}</p> : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
