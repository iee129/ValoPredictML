import { proxyPost } from "@/lib/serverApi";

export async function POST(request: Request) {
  return proxyPost(request, "/predict");
}
