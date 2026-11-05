type ApiClientOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
  accessTokenProvider?: () => Promise<string | null>;
};

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;
  private readonly accessTokenProvider: () => Promise<string | null>;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    this.fetcher = options.fetcher ?? getBoundFetch();
    this.accessTokenProvider = options.accessTokenProvider ?? getSupabaseAccessToken;
  }

  async request<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
    if (!this.baseUrl) {
      throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured.");
    }

    const headers = new Headers(init?.headers);
    if (!(init?.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    const accessToken = await this.accessTokenProvider();
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    const response = await this.fetcher(new URL(path, this.baseUrl), {
      ...init,
      headers,
    });

    if (!response.ok) {
      const message = await getErrorMessage(response);
      throw new Error(message ?? `API request failed with status ${response.status}.`);
    }

    return (await response.json()) as TResponse;
  }
}

function getBoundFetch(): typeof fetch {
  if (typeof window !== "undefined") {
    return window.fetch.bind(window);
  }

  return globalThis.fetch.bind(globalThis);
}

async function getErrorMessage(response: Response): Promise<string | null> {
  try {
    const payload = (await response.json()) as unknown;
    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      return payload.detail;
    }
  } catch {
    return null;
  }

  return null;
}

async function getSupabaseAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  const { getSupabaseBrowserClient } = await import("./supabase");
  const supabase = getSupabaseBrowserClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return session?.access_token ?? null;
}

export const apiClient = new ApiClient();
