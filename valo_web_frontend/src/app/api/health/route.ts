import { mockHealth } from "@/lib/mock";

export async function GET() {
  return Response.json(mockHealth());
}
