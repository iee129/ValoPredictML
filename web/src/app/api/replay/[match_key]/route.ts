import { proxyBackend } from "@/lib/serverApi";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ match_key: string }> },
) {
  const { match_key } = await params;
  return proxyBackend(`/replay/${encodeURIComponent(match_key)}`);
}
