interface Env {
  SIMA_PROXY_SECRET: string;
}

interface PagesContext {
  request: Request;
  env: Env;
  params: { path?: string | string[] };
}

export const onRequest = async ({ request, env, params }: PagesContext): Promise<Response> => {
  const path = Array.isArray(params.path) ? params.path.join('/') : (params.path ?? '');
  const incomingUrl = new URL(request.url);
  const isProduction =
    incomingUrl.hostname === 'sima.gonor.me' || incomingUrl.hostname === 'sima-7xu.pages.dev';
  const apiOrigin = isProduction
    ? 'https://sima-451451662791.us-central1.run.app'
    : 'https://sima-dev-451451662791.us-central1.run.app';
  const upstreamUrl = new URL(`/api/${path}${incomingUrl.search}`, apiOrigin);
  const headers = new Headers(request.headers);

  headers.set('X-SIMA-Proxy-Secret', env.SIMA_PROXY_SECRET);
  headers.delete('host');
  headers.delete('cf-connecting-ip');
  headers.delete('cf-ipcountry');
  headers.delete('cf-ray');
  headers.delete('x-forwarded-for');
  headers.delete('x-forwarded-proto');

  return fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body,
    redirect: 'manual',
  });
};
