export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-vred/40 bg-vred/10 text-[#ffe4e8] px-4 py-3 text-sm font-semibold">
      {message}
    </div>
  );
}
