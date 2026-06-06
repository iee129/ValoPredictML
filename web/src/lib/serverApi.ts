const INTERNAL_API_URL = (
  process.env.VALO_INTERNAL_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

type ProxyInit = {
  method?: "GET" | "POST";
  body?: BodyInit | null;
  contentType?: string | null;
};

function backendUrl(path: string) {
  return `${INTERNAL_API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function proxyBackend(
  path: string,
  init: ProxyInit = {},
): Promise<Response> {
  try {
    const headers = new Headers();
    if (init.contentType) headers.set("Content-Type", init.contentType);

    const upstream = await fetch(backendUrl(path), {
      method: init.method ?? "GET",
      headers,
      body: init.body,
      cache: "no-store",
    });

    const body = await upstream.text();
    const contentType =
      upstream.headers.get("Content-Type") ?? "application/json; charset=utf-8";

    return new Response(body, {
      status: upstream.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "FastAPI backend unavailable";
    return Response.json(
      {
        detail: `FastAPI 백엔드에 연결하지 못했습니다 (${INTERNAL_API_URL}): ${message}`,
      },
      { status: 503 },
    );
  }
}

export function proxyGet(request: Request, path: string) {
  const url = new URL(request.url);
  return proxyBackend(`${path}${url.search}`, { method: "GET" });
}

export async function proxyPost(request: Request, path: string) {
  const contentType = request.headers.get("Content-Type") ?? "application/json";
  return proxyBackend(path, {
    method: "POST",
    contentType,
    body: await request.text(),
  });
}
