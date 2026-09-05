export function EmptyState({
  title,
  description,
  hint,
}: {
  title: string;
  description: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-dashed p-10 text-center">
      <h2 className="text-sm font-medium">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      {hint ? (
        <p className="mt-4 font-mono text-xs text-muted-foreground/80">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
