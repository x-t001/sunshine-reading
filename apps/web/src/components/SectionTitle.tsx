import Link from "next/link";

export function SectionTitle({ title, actionText, actionHref }: { title: string; actionText?: string; actionHref?: string }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
      {actionText && actionHref ? (
        <Link href={actionHref} className="text-xs font-medium text-emerald-600 hover:text-emerald-700">
          {actionText}
        </Link>
      ) : null}
    </div>
  );
}
