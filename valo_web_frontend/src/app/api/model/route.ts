import { mockModel } from "@/lib/mock";

export async function GET() {
  return Response.json(mockModel());
}
