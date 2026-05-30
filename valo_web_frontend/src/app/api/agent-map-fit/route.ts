import { mockAgentMapFit } from "@/lib/mock";

export async function GET(request: Request) {
  const map = new URL(request.url).searchParams.get("map") ?? "Ascent";
  return Response.json(mockAgentMapFit(map));
}
