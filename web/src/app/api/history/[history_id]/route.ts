import { proxyBackend } from "@/lib/serverApi";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ history_id: string }> },
) {
  const { history_id } = await params;
  return proxyBackend(`/history/${encodeURIComponent(history_id)}`);
}
