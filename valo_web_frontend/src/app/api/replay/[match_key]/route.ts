import { mockReplayOne } from "@/lib/mock";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ match_key: string }> },
) {
  const { match_key } = await params;
  const result = mockReplayOne(match_key);
  if (!result) {
    return Response.json({ detail: `경기 키를 찾지 못했습니다: ${match_key}` }, { status: 404 });
  }
  return Response.json(result);
}
