import { mockCompMatch } from "@/lib/mock";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const map: string = body?.map ?? "Ascent";
  const agents: string[] = Array.isArray(body?.agents) ? body.agents : [];
  return Response.json(mockCompMatch(map, agents));
}
