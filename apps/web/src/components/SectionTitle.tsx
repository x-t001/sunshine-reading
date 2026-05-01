export function SectionTitle({ title, actionText }: { title: string; actionText?: string }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
      {actionText ? <span className="text-xs text-emerald-600">{actionText}</span> : null}
    </div>
  );
}
