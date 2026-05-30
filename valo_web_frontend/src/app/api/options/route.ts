import { mockOptions } from "@/lib/mock";

export async function GET() {
  return Response.json(mockOptions());
}
