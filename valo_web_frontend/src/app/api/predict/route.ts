import { mockPredict } from "@/lib/mock";
import type { PredictRequest } from "@/types/api";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as PredictRequest;
  return Response.json(mockPredict(body));
}
