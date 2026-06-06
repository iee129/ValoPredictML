export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red/40 bg-red/10 text-[#ffe4e8] px-4 py-3 text-sm font-semibold">
      {message}
    </div>
  );
}
