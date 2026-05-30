import { mockReplayMatches } from "@/lib/mock";

export async function GET(request: Request) {
  const limit = Number(new URL(request.url).searchParams.get("limit") ?? "200");
  return Response.json(mockReplayMatches(Number.isFinite(limit) ? limit : 200));
}
