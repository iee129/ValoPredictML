import { proxyGet } from "@/lib/serverApi";

export async function GET(request: Request) {
  return proxyGet(request, "/model");
}
