"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/index.ts
var index_exports = {};
__export(index_exports, {
  AgentIdentityModule: () => AgentIdentityModule,
  BasisAPI: () => BasisAPI,
  BasisClient: () => BasisClient,
  FactoryModule: () => FactoryModule,
  LeverageSimulatorModule: () => LeverageSimulatorModule,
  LoansModule: () => LoansModule,
  MarketReaderModule: () => MarketReaderModule,
  MarketResolverModule: () => MarketResolverModule,
  OrderBookModule: () => OrderBookModule,
  PredictionMarketsModule: () => PredictionMarketsModule,
  PrivateMarketsModule: () => PrivateMarketsModule,
  StakingModule: () => StakingModule,
  TaxesModule: () => TaxesModule,
  TradingModule: () => TradingModule,
  VestingModule: () => VestingModule
});
module.exports = __toCommonJS(index_exports);

// src/BasisClient.ts
var import_viem5 = require("viem");
var import_accounts = require("viem/accounts");
var import_chains = require("viem/chains");
var import_siwe = require("siwe");

// src/api.ts
var import_sharp = __toESM(require("sharp"));
var BasisAPI = class {
  client;
  constructor(client) {
    this.client = client;
  }
  // -----------------------------------------------------------------------
  // Internal fetch helpers
  // -----------------------------------------------------------------------
  /**
   * Fetch helper that attaches the session cookie for endpoints requiring
   * an authenticated session (auth, metadata, comments write, images, etc.).
   */
  async fetchWithSession(endpoint, options = {}) {
    const cookie = this.client.sessionCookie;
    if (!cookie) {
      throw new Error(
        "No session cookie available. Authenticate first via BasisClient.authenticate()."
      );
    }
    const url = this.buildUrl(endpoint);
    const headers = {
      ...options.headers,
      Cookie: cookie
    };
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(
        `API request failed [${res.status}] ${res.statusText}: ${body}`
      );
    }
    return res;
  }
  /**
   * Fetch helper that attaches the X-API-Key header for /api/v1 data endpoints.
   */
  async fetchWithApiKey(endpoint, options = {}) {
    const apiKey = this.client.apiKey;
    if (!apiKey) {
      throw new Error(
        "No API key available. Provide one via BasisClientOptions.apiKey or use BasisClient.create() with a privateKey to auto-provision."
      );
    }
    const url = this.buildUrl(endpoint);
    const headers = {
      ...options.headers,
      "X-API-Key": apiKey
    };
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(
        `API request failed [${res.status}] ${res.statusText}: ${body}`
      );
    }
    return res;
  }
  buildUrl(endpoint) {
    const base = this.client.apiDomain.replace(/\/+$/, "");
    return `${base}${endpoint}`;
  }
  // -----------------------------------------------------------------------
  // Auth endpoints (session-based)
  // -----------------------------------------------------------------------
  /** GET /api/auth/me — get current session info. */
  async getSession(address) {
    const params = address ? `?address=${encodeURIComponent(address)}` : "";
    const res = await this.fetchWithSession(`/api/auth/me${params}`, {
      method: "GET"
    });
    return res.json();
  }
  /** DELETE /api/auth/me — log out a specific address. */
  async logout(address) {
    const res = await this.fetchWithSession(
      `/api/auth/me?address=${encodeURIComponent(address)}`,
      { method: "DELETE" }
    );
    return res.json();
  }
  // -----------------------------------------------------------------------
  // API key management (session-based)
  // -----------------------------------------------------------------------
  /** POST /api/v1/auth/keys — create a new API key. */
  async createApiKey(label) {
    const res = await this.fetchWithSession("/api/v1/auth/keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label })
    });
    return res.json();
  }
  /** GET /api/v1/auth/keys — list API keys for the session wallet. */
  async listApiKeys() {
    const res = await this.fetchWithSession("/api/v1/auth/keys", {
      method: "GET"
    });
    return res.json();
  }
  /** DELETE /api/v1/auth/keys/:id — revoke an API key. */
  async deleteApiKey(id) {
    const res = await this.fetchWithSession(
      `/api/v1/auth/keys/${encodeURIComponent(id)}`,
      { method: "DELETE" }
    );
    return res.json();
  }
  // -----------------------------------------------------------------------
  // Image upload (session-based)
  // -----------------------------------------------------------------------
  /**
   * POST /api/images — upload an image file.
   *
   * Accepts Blob, Buffer, or a File-like object. Returns the hosted URL string.
   */
  async uploadImage(file, filename = "image.png") {
    const formData = new FormData();
    if (Buffer.isBuffer(file)) {
      const ext = filename.split(".").pop()?.toLowerCase();
      const mimeMap = {
        webp: "image/webp",
        png: "image/png",
        jpg: "image/jpeg",
        jpeg: "image/jpeg",
        gif: "image/gif"
      };
      const mime = mimeMap[ext || ""] || "image/png";
      const blob = new Blob([new Uint8Array(file)], { type: mime });
      formData.append("file", blob, filename);
    } else {
      formData.append("file", file, filename);
    }
    const res = await this.fetchWithSession("/api/images", {
      method: "POST",
      body: formData
    });
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  /**
   * Downloads an image from a URL, resizes it to 512x512 (center-crop),
   * converts to WebP, and uploads it to IPFS via /api/images.
   *
   * Returns the hosted IPFS URL string.
   */
  async uploadImageFromUrl(imageUrl, contractAddress) {
    const response = await fetch(imageUrl);
    if (!response.ok) {
      throw new Error(`Failed to download image from ${imageUrl}: ${response.status}`);
    }
    const arrayBuffer = await response.arrayBuffer();
    const inputBuffer = Buffer.from(arrayBuffer);
    const webpBuffer = await (0, import_sharp.default)(inputBuffer).resize(512, 512, { fit: "cover", position: "centre" }).webp({ quality: 90 }).toBuffer();
    const filename = contractAddress ? `${contractAddress}.webp` : `image_${Date.now()}.webp`;
    return this.uploadImage(webpBuffer, filename);
  }
  // -----------------------------------------------------------------------
  // Metadata (session-based, must be creator)
  // -----------------------------------------------------------------------
  /**
   * POST /api/metadata — publish or update project metadata.
   * Requires session and the caller must be the token creator.
   */
  async updateMetadata(payload) {
    const res = await this.fetchWithSession("/api/metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  }
  // -----------------------------------------------------------------------
  // Project updates (session-based, must be dev)
  // -----------------------------------------------------------------------
  /**
   * POST /api/projects/:address — update project info.
   * Accepts either a plain JSON payload or a payload with an image Blob/Buffer.
   */
  async updateProject(address, payload, image, imageFilename) {
    let body;
    const headers = {};
    if (image) {
      const formData = new FormData();
      for (const [key, value] of Object.entries(payload)) {
        if (value !== void 0 && value !== null) {
          formData.append(key, String(value));
        }
      }
      if (Buffer.isBuffer(image)) {
        formData.append("image", new Blob([new Uint8Array(image)]), imageFilename || "image.png");
      } else {
        formData.append("image", image, imageFilename || "image.png");
      }
      body = formData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(payload);
    }
    const res = await this.fetchWithSession(
      `/api/projects/${encodeURIComponent(address)}`,
      { method: "POST", headers, body }
    );
    return res.json();
  }
  // -----------------------------------------------------------------------
  // Comments
  // -----------------------------------------------------------------------
  /** GET /api/comments — list comments for a project. */
  async getComments(projectId, options = {}) {
    const params = new URLSearchParams();
    params.set("projectId", String(projectId));
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const url = `${this.client.apiDomain}/api/comments?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Failed to fetch comments: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }
  /** POST /api/comments — create a comment (session required). */
  async createComment(projectId, content, authorAddress) {
    const res = await this.fetchWithSession("/api/comments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projectId, content, authorAddress })
    });
    return res.json();
  }
  /** DELETE /api/comments — soft-delete a comment (session required). */
  async deleteComment(commentId, authorAddress) {
    const params = new URLSearchParams();
    params.set("id", String(commentId));
    params.set("authorAddress", authorAddress);
    const res = await this.fetchWithSession(
      `/api/comments?${params.toString()}`,
      { method: "DELETE" }
    );
    return res.json();
  }
  // -----------------------------------------------------------------------
  // v1 Data endpoints (API-key authenticated)
  // -----------------------------------------------------------------------
  /**
   * GET /api/v1/tokens — list / search tokens.
   */
  async getTokens(options = {}) {
    const params = new URLSearchParams();
    if (options.search !== void 0) params.set("search", options.search);
    if (options.isPrediction !== void 0) params.set("isPrediction", String(options.isPrediction));
    if (options.sort !== void 0) params.set("sort", options.sort);
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/tokens${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /** GET /api/v1/tokens/:address — get a single token's details. */
  async getToken(address) {
    const res = await this.fetchWithApiKey(
      `/api/v1/tokens/${encodeURIComponent(address)}`
    );
    return res.json();
  }
  /**
   * GET /api/v1/tokens/:address/candles — OHLCV candle data.
   */
  async getCandles(address, options = {}) {
    const params = new URLSearchParams();
    if (options.interval !== void 0) params.set("interval", options.interval);
    if (options.from !== void 0) params.set("from", String(options.from));
    if (options.to !== void 0) params.set("to", String(options.to));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/tokens/${encodeURIComponent(address)}/candles${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/tokens/:address/trades — trade history for a token.
   */
  async getTrades(address, options = {}) {
    const params = new URLSearchParams();
    if (options.cursor !== void 0) params.set("cursor", options.cursor);
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    if (options.type !== void 0) params.set("type", options.type);
    const qs = params.toString();
    const endpoint = `/api/v1/tokens/${encodeURIComponent(address)}/trades${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/tokens/:address/orders — order book entries for a token.
   */
  async getOrders(address, options = {}) {
    const params = new URLSearchParams();
    if (options.status !== void 0) params.set("status", options.status);
    if (options.outcomeId !== void 0) params.set("outcomeId", options.outcomeId);
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/tokens/${encodeURIComponent(address)}/orders${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/tokens/:address/comments — comments for a token (via API key).
   */
  async getTokenComments(address, options = {}) {
    const params = new URLSearchParams();
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/tokens/${encodeURIComponent(address)}/comments${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/tokens/:address/whitelist — whitelist data for a token.
   */
  async getWhitelist(address, options = {}) {
    const params = new URLSearchParams();
    if (options.wallet !== void 0) params.set("wallet", options.wallet);
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/tokens/${encodeURIComponent(address)}/whitelist${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/wallet/:address/transactions — transaction history for a wallet.
   */
  async getWalletTransactions(address, options = {}) {
    const params = new URLSearchParams();
    if (options.cursor !== void 0) params.set("cursor", options.cursor);
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    if (options.type !== void 0) params.set("type", options.type);
    const qs = params.toString();
    const endpoint = `/api/v1/wallet/${encodeURIComponent(address)}/transactions${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/markets/:address/liquidity — liquidity events for a prediction market.
   */
  async getMarketLiquidity(address, options = {}) {
    const params = new URLSearchParams();
    if (options.cursor !== void 0) params.set("cursor", options.cursor);
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    if (options.outcomeId !== void 0) params.set("outcomeId", options.outcomeId);
    const qs = params.toString();
    const endpoint = `/api/v1/markets/${encodeURIComponent(address)}/liquidity${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithApiKey(endpoint);
    return res.json();
  }
  /**
   * POST /api/v1/orders/sync — sync an on-chain order event to the database.
   * Call after listOrder, cancelOrder, or buyOrder transactions.
   * Accepts either session cookie or API key for auth.
   */
  async syncOrder(txHash, marketType = "public") {
    const body = JSON.stringify({ txHash, marketType });
    const headers = { "Content-Type": "application/json" };
    const apiKey = this.client.apiKey;
    const cookie = this.client.sessionCookie;
    if (apiKey) {
      const url = `${this.client.apiDomain}/api/v1/orders/sync`;
      headers["X-API-Key"] = apiKey;
      const res = await fetch(url, { method: "POST", headers, body });
      if (!res.ok) {
        const errBody = await res.text().catch(() => "");
        throw new Error(`Order sync failed [${res.status}]: ${errBody}`);
      }
      return res.json();
    } else if (cookie) {
      const res = await this.fetchWithSession("/api/v1/orders/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body
      });
      return res.json();
    } else {
      throw new Error("syncOrder requires either an API key or session cookie.");
    }
  }
  // -----------------------------------------------------------------------
  // Loan & Vault sync (public, no auth required)
  // -----------------------------------------------------------------------
  /**
   * POST /api/v1/sync — sync an on-chain loan or vault event to the database.
   * Call after any loan, vault staking, or leverage transaction.
   * No authentication required (public on-chain data). Rate limited to 20 req/min.
   * Idempotent — submitting the same txHash twice is safe.
   */
  async syncLoan(txHash) {
    const url = `${this.client.apiDomain}/api/v1/sync`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ txHash })
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Loan sync failed [${res.status}]: ${body}`);
    }
    return res.json();
  }
  // -----------------------------------------------------------------------
  // Loans, Vault & Vesting read endpoints (session or API key)
  // -----------------------------------------------------------------------
  /**
   * Internal helper: fetch with API key or session cookie.
   */
  async fetchWithAuth(endpoint, options = {}) {
    const apiKey = this.client.apiKey;
    const cookie = this.client.sessionCookie;
    const headers = {
      ...options.headers
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    } else if (cookie) {
      headers["Cookie"] = cookie;
    } else {
      throw new Error("Authentication required (API key or session cookie).");
    }
    const url = this.buildUrl(endpoint);
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`API request failed [${res.status}] ${res.statusText}: ${body}`);
    }
    return res;
  }
  /**
   * GET /api/v1/loans — list loans for the authenticated wallet.
   */
  async getLoans(options = {}) {
    const params = new URLSearchParams();
    if (options.source !== void 0) params.set("source", options.source);
    if (options.active !== void 0) params.set("active", String(options.active));
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/loans${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithAuth(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/loans/events — list loan lifecycle events for the authenticated wallet.
   */
  async getLoanEvents(options = {}) {
    const params = new URLSearchParams();
    if (options.source !== void 0) params.set("source", options.source);
    if (options.action !== void 0) params.set("action", options.action);
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/loans/events${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithAuth(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/vault/events — list vault staking events for the authenticated wallet.
   */
  async getVaultEvents(options = {}) {
    const params = new URLSearchParams();
    if (options.action !== void 0) params.set("action", options.action);
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/vault/events${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithAuth(endpoint);
    return res.json();
  }
  /**
   * GET /api/v1/vesting/events — list vesting events for the authenticated wallet.
   */
  async getVestingEvents(options = {}) {
    const params = new URLSearchParams();
    if (options.action !== void 0) params.set("action", options.action);
    if (options.vestingId !== void 0) params.set("vestingId", String(options.vestingId));
    if (options.page !== void 0) params.set("page", String(options.page));
    if (options.limit !== void 0) params.set("limit", String(options.limit));
    const qs = params.toString();
    const endpoint = `/api/v1/vesting/events${qs ? `?${qs}` : ""}`;
    const res = await this.fetchWithAuth(endpoint);
    return res.json();
  }
  // -----------------------------------------------------------------------
  // Twitter / X Verification
  // -----------------------------------------------------------------------
  /**
   * POST /api/auth/twitter/challenge — request a verification code.
   * Returns a code to include in a tweet and a pre-built tweet template.
   */
  async requestTwitterChallenge() {
    const apiKey = this.client.apiKey;
    const cookie = this.client.sessionCookie;
    const headers = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    else if (cookie) headers["Cookie"] = cookie;
    else throw new Error("Twitter challenge requires authentication (API key or session).");
    const url = `${this.client.apiDomain}/api/auth/twitter/challenge`;
    const res = await fetch(url, { method: "POST", headers });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Twitter challenge failed [${res.status}]: ${body}`);
    }
    return res.json();
  }
  /**
   * POST /api/auth/twitter/verify-tweet — verify a tweet containing the challenge code.
   * Links the X account to the authenticated wallet.
   */
  async verifyTwitter(tweetUrl) {
    const apiKey = this.client.apiKey;
    const cookie = this.client.sessionCookie;
    const headers = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    else if (cookie) headers["Cookie"] = cookie;
    else throw new Error("Twitter verification requires authentication (API key or session).");
    const url = `${this.client.apiDomain}/api/auth/twitter/verify-tweet`;
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ tweetUrl })
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Twitter verification failed [${res.status}]: ${body}`);
    }
    return res.json();
  }
};

// src/abis/ATokenFactory.json
var ATokenFactory_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "swapAddress",
          type: "address"
        },
        {
          internalType: "address",
          name: "stasisAddress",
          type: "address"
        },
        {
          internalType: "address",
          name: "_usdc",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "tokenAddress",
          type: "address"
        },
        {
          indexed: false,
          internalType: "string",
          name: "name",
          type: "string"
        },
        {
          indexed: false,
          internalType: "string",
          name: "symbol",
          type: "string"
        },
        {
          indexed: false,
          internalType: "address",
          name: "creator",
          type: "address"
        }
      ],
      name: "TokenCreated",
      type: "event"
    },
    {
      inputs: [
        {
          internalType: "string",
          name: "symbol",
          type: "string"
        },
        {
          internalType: "string",
          name: "name",
          type: "string"
        },
        {
          internalType: "uint256",
          name: "hybridMultiplier",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "frozen",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "usdcForBonding",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "startLP",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "autoVest",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "autoVestDuration",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "gradualAutovest",
          type: "bool"
        }
      ],
      name: "createToken",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [],
      name: "creationCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "creatorOf",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "creatorToTokens",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "feeAmount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "feeWhitelist",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "creator",
          type: "address"
        }
      ],
      name: "getTokenCountByCreator",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "creator",
          type: "address"
        }
      ],
      name: "getTokensByCreator",
      outputs: [
        {
          internalType: "address[]",
          name: "",
          type: "address[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isEcosystemToken",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isPairToken",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "lastCreation",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "setEcosystemToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newFeeAmount",
          type: "uint256"
        }
      ],
      name: "setFeeAmount",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "bool",
          name: "enabled",
          type: "bool"
        }
      ],
      name: "setFeeEnabled",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "addr",
          type: "address"
        },
        {
          internalType: "bool",
          name: "whitelisted",
          type: "bool"
        }
      ],
      name: "setFeeWhitelist",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "addr",
          type: "address"
        }
      ],
      name: "setSWAP",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "togglePairToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "vestFeeEnabled",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/abis/FACTORYTOKEN.json
var FACTORYTOKEN_default = {
  abi: [
    {
      inputs: [
        {
          components: [
            {
              internalType: "address",
              name: "swapAddress",
              type: "address"
            },
            {
              internalType: "address",
              name: "stasisAddress",
              type: "address"
            },
            {
              internalType: "string",
              name: "name",
              type: "string"
            },
            {
              internalType: "string",
              name: "symbol",
              type: "string"
            },
            {
              internalType: "uint256",
              name: "hybridMultiplier",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "frozen",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "usdcForBondingNeeded",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "startLP",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "autoVest",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "autoVestDuration",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "gradualAutoVesting",
              type: "bool"
            },
            {
              internalType: "address",
              name: "dev",
              type: "address"
            },
            {
              internalType: "address",
              name: "usdcAddress",
              type: "address"
            }
          ],
          internalType: "struct IFactoryToken.ConstructorParams",
          name: "params",
          type: "tuple"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "x",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "y",
          type: "uint256"
        }
      ],
      name: "PRBMath_MulDiv18_Overflow",
      type: "error"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "x",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "y",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "denominator",
          type: "uint256"
        }
      ],
      name: "PRBMath_MulDiv_Overflow",
      type: "error"
    },
    {
      inputs: [
        {
          internalType: "UD60x18",
          name: "x",
          type: "uint256"
        }
      ],
      name: "PRBMath_UD60x18_Exp2_InputTooBig",
      type: "error"
    },
    {
      inputs: [
        {
          internalType: "UD60x18",
          name: "x",
          type: "uint256"
        }
      ],
      name: "PRBMath_UD60x18_Log_InputTooSmall",
      type: "error"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "owner",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "Approval",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "amountToken",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amountUSDC",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "liquidity",
          type: "uint256"
        }
      ],
      name: "LiquidityAdded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "address",
          name: "investor",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "claimableNow",
          type: "uint256"
        }
      ],
      name: "RewardsClaimed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "rewardsToBeAdded",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "rewardsPerShareToday",
          type: "uint256"
        }
      ],
      name: "RewardsDistributed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        }
      ],
      name: "Sync",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "amountToken",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amountUSDC",
          type: "uint256"
        },
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "price",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "enum FACTORYTOKEN.TradeType",
          name: "tradeType",
          type: "uint8"
        }
      ],
      name: "TokensTraded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "from",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "Transfer",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "string",
          name: "tag",
          type: "string"
        }
      ],
      name: "WhiteListedWallet",
      type: "event"
    },
    {
      inputs: [],
      name: "CEO",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "DEV",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "DisableFreeze",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokensToBurn",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "mainToBurn",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          internalType: "bool",
          name: "isLeverage",
          type: "bool"
        }
      ],
      name: "LiquidateLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "wallet",
          type: "address"
        }
      ],
      name: "RemoveWhitelist",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "SWAP",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        }
      ],
      name: "SetProjectVetted",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newSwap",
          type: "address"
        }
      ],
      name: "SetSwapWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address[]",
          name: "wallets",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "string",
          name: "tag",
          type: "string"
        }
      ],
      name: "SetWhitelistedWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "addToRewards",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "_owner",
          type: "address"
        },
        {
          internalType: "address",
          name: "spender",
          type: "address"
        }
      ],
      name: "allowance",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "approve",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "autoVest",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "autoVestDuration",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "_owner",
          type: "address"
        }
      ],
      name: "balanceOf",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "baseReserve0",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "baseReserve1",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "buyAmount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "buyer",
          type: "address"
        }
      ],
      name: "buyBondingTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "buyer",
          type: "address"
        }
      ],
      name: "buyTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "calculateFloor",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmountOut",
          type: "uint256"
        }
      ],
      name: "calculateMainForTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "calculateTokenFloor",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "mainAmount",
          type: "uint256"
        }
      ],
      name: "calculateTokensForBuy",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "mainAmountOut",
          type: "uint256"
        }
      ],
      name: "calculateTokensForMain",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        }
      ],
      name: "calculateTokensForSell",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "claimRewards",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "claimedRewards",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "creationBlock",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "creationTime",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "decimals",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "excluded",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "frozen",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getBondingTarget",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "investor",
          type: "address"
        }
      ],
      name: "getClaimableRewards",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getLiquidity",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getReserves",
      outputs: [
        {
          internalType: "uint256",
          name: "_reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "_reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "_blockTimestampLast",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getTokenPrice",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getUSDPrice",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "gradualAutoVesting",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "hasBonded",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "hybridMultiplier",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "lastDistribution",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "lastTrade",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "name",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newReserveTokens",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "newReserveStasis",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "newTokens",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "openLeverageFactory",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "projectedVetted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "seller",
          type: "address"
        }
      ],
      name: "sellBondingTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "seller",
          type: "address"
        }
      ],
      name: "sellTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "shares",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "symbol",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "token0",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "token1",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "tokenClosed",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalRewardsPerShare",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalShares",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalSupply",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalWhitelisted",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "transfer",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "from",
          type: "address"
        },
        {
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "transferFrom",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newCEO",
          type: "address"
        }
      ],
      name: "transferOwnership",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "usdcForBondingNeeded",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "whitelistBoughtByUser",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "whitelistMaxBuyForUser",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "whitelisted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/Factory.ts
var import_viem = require("viem");
var FactoryModule = class {
  client;
  factoryAddress;
  constructor(client, factoryAddress) {
    this.client = client;
    this.factoryAddress = factoryAddress;
  }
  /**
   * Internal: creates a token on-chain. Use createTokenWithMetadata() instead.
   */
  async createToken(symbol, name, hybridMultiplier, frozen, usdbForBonding, startLP, autoVest, autoVestDuration, gradualAutovest) {
    if (!this.client.walletClient) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const account = this.client.walletClient.account;
    if (!account) throw new Error("Account is required");
    const feeAmount = await this.client.publicClient.readContract({
      address: this.factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "feeAmount"
    });
    const { request } = await this.client.publicClient.simulateContract({
      account,
      address: this.factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "createToken",
      args: [
        symbol,
        name,
        hybridMultiplier,
        frozen,
        usdbForBonding,
        startLP,
        autoVest,
        autoVestDuration,
        gradualAutovest
      ],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Creates a token and registers its metadata on IPFS in one call.
   * Requires SIWE authentication (call client.authenticate() first).
   *
   * 1. Creates the token on-chain
   * 2. Parses the new token address from logs
   * 3. Downloads, resizes (512x512 WebP), and uploads the image to IPFS
   * 4. Creates metadata on IPFS (name, symbol, description auto-read from chain)
   *
   * Returns { hash, receipt, tokenAddress, imageUrl, metadata }
   */
  async createTokenWithMetadata(options) {
    const createResult = await this.createToken(
      options.symbol,
      options.name,
      options.hybridMultiplier,
      options.frozen ?? false,
      options.usdbForBonding ?? 0n,
      options.startLP,
      options.autoVest ?? false,
      options.autoVestDuration ?? 0n,
      options.gradualAutovest ?? false
    );
    if (createResult.receipt.status === "reverted") {
      throw new Error(`Token creation reverted (tx: ${createResult.hash})`);
    }
    const TOKEN_CREATED_TOPIC = (0, import_viem.keccak256)((0, import_viem.toBytes)("TokenCreated(address,string,string,address)"));
    const tokenCreatedLog = createResult.receipt.logs.find(
      (l) => l.address.toLowerCase() === this.factoryAddress.toLowerCase() && l.topics[0] === TOKEN_CREATED_TOPIC
    );
    let tokenAddress;
    if (tokenCreatedLog && tokenCreatedLog.topics[1]) {
      tokenAddress = (0, import_viem.getAddress)("0x" + tokenCreatedLog.topics[1].slice(26));
    } else {
      throw new Error("Could not extract token address from creation logs.");
    }
    let imageUrl;
    if (options.imageUrl) {
      imageUrl = await this.client.api.uploadImageFromUrl(options.imageUrl, tokenAddress);
    }
    const metadata = await this.client.api.updateMetadata({
      address: tokenAddress,
      description: options.description,
      image: imageUrl,
      website: options.website,
      telegram: options.telegram,
      twitterx: options.twitterx
    });
    return {
      hash: createResult.hash,
      receipt: createResult.receipt,
      tokenAddress,
      imageUrl,
      metadata
    };
  }
  async disableFreeze(tokenAddress) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "DisableFreeze"
    });
    const hash = await this.client.walletClient.writeContract(request);
    return this.client.publicClient.waitForTransactionReceipt({ hash });
  }
  async setWhitelistedWallet(tokenAddress, wallets, amount, tag) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "SetWhitelistedWallet",
      args: [wallets, amount, tag]
    });
    const hash = await this.client.walletClient.writeContract(request);
    return this.client.publicClient.waitForTransactionReceipt({ hash });
  }
  async getTokenState(tokenAddress) {
    const contract = (0, import_viem.getContract)({
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      client: this.client.publicClient
    });
    const [frozen, hasBonded, totalSupply, usdPrice] = await Promise.all([
      contract.read.frozen(),
      contract.read.hasBonded(),
      contract.read.totalSupply(),
      contract.read.getUSDPrice()
    ]);
    return {
      frozen,
      hasBonded,
      totalSupply: totalSupply.toString(),
      usdPrice: usdPrice.toString()
    };
  }
  /**
   * Checks if a token address belongs to the ecosystem.
   */
  async isEcosystemToken(tokenAddress) {
    return this.client.publicClient.readContract({
      address: this.factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "isEcosystemToken",
      args: [tokenAddress]
    });
  }
  /**
   * Returns all token addresses created by a given creator.
   */
  async getTokensByCreator(creator) {
    return this.client.publicClient.readContract({
      address: this.factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "getTokensByCreator",
      args: [creator]
    });
  }
  /**
   * Returns the current fee amount (in wei) required to create a token.
   */
  async getFeeAmount() {
    return this.client.publicClient.readContract({
      address: this.factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "feeAmount"
    });
  }
  /**
   * Removes a wallet from the whitelist on a FACTORYTOKEN contract.
   */
  /**
   * Claim accumulated USDB rewards from presale shares on a factory token.
   */
  async claimRewards(tokenAddress) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "claimRewards"
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Get claimable USDB rewards for an address on a factory token.
   */
  async getClaimableRewards(tokenAddress, investor) {
    return this.client.publicClient.readContract({
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "getClaimableRewards",
      args: [investor]
    });
  }
  async removeWhitelist(tokenAddress, wallet) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "RemoveWhitelist",
      args: [wallet]
    });
    const hash = await this.client.walletClient.writeContract(request);
    return this.client.publicClient.waitForTransactionReceipt({ hash });
  }
};

// src/abis/ASwap.json
var ASwap_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "_usdc",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          components: [
            {
              internalType: "string",
              name: "name",
              type: "string"
            },
            {
              internalType: "string",
              name: "symbol",
              type: "string"
            },
            {
              internalType: "uint256",
              name: "price",
              type: "uint256"
            }
          ],
          indexed: false,
          internalType: "struct ASwap.TradeInfo",
          name: "info",
          type: "tuple"
        }
      ],
      name: "Traded",
      type: "event"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minOut",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "bool",
          name: "wrapTokens",
          type: "bool"
        }
      ],
      name: "buyTokens",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "inputToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "inputAmount",
          type: "uint256"
        }
      ],
      name: "convertToNative",
      outputs: [
        {
          internalType: "uint256",
          name: "usdcOut",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        }
      ],
      name: "getAmountsOut",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "lastTradeBlock",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minOut",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        }
      ],
      name: "leverageBuy",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minOutLev",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minOut",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "percentageLeverage",
          type: "uint256"
        }
      ],
      name: "mixedBuy",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "loanId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "percentage",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isLeverage",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "minOut",
          type: "uint256"
        }
      ],
      name: "partialLoanSell",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "tokenToRescue",
          type: "address"
        }
      ],
      name: "rescueAnyToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "rescueEth",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "originalToken",
          type: "address"
        }
      ],
      name: "sellAndDistributeStasis",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minOut",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "bool",
          name: "swapToETH",
          type: "bool"
        }
      ],
      name: "sellTokens",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newFactory",
          type: "address"
        },
        {
          internalType: "address",
          name: "newLeverage",
          type: "address"
        },
        {
          internalType: "address",
          name: "newVesting",
          type: "address"
        },
        {
          internalType: "address",
          name: "newMain",
          type: "address"
        },
        {
          internalType: "address",
          name: "newTaxes",
          type: "address"
        },
        {
          internalType: "address",
          name: "newStaking",
          type: "address"
        }
      ],
      name: "setContracts",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "swapForStaking",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "totalTaxDistributed",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      stateMutability: "payable",
      type: "receive"
    }
  ]
};

// src/abis/IERC20.json
var IERC20_default = {
  _format: "hh-sol-artifact-1",
  contractName: "IERC20",
  sourceName: "contracts/LEVERAGE.sol",
  abi: [
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "owner",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "Approval",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "from",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "Transfer",
      type: "event"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "loanId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "additionalTokens",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "AddCollateralFor",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "DEV",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "InjectUSDC",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "borrowedAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "colleteralValue",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "priceBefore",
          type: "uint256"
        }
      ],
      name: "TakeLeverageFor",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "TakeLoanFor",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "addToRewards",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "_owner",
          type: "address"
        },
        {
          internalType: "address",
          name: "spender",
          type: "address"
        }
      ],
      name: "allowance",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "approve",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "autoVest",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "autoVestDuration",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "who",
          type: "address"
        }
      ],
      name: "balanceOf",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "baseReserve0",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "bondVestingDays",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "buyer",
          type: "address"
        }
      ],
      name: "buyBondingTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "buyTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "calculateTokensForBuy",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "calculateTokensForSell",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "deposit",
      outputs: [],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [],
      name: "dynamicFeePercentage",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "getColleteralValue",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        }
      ],
      name: "getDynamicFee",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getReserves",
      outputs: [
        {
          internalType: "uint256",
          name: "_reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "_reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "_blockTimestampLast",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getTokenPrice",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "getUSDPrice",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "gradualAutoVesting",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "hasBonded",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "hybridMultiplier",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "name",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "stasisToMint",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "usdcToMint",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "usdcToLP",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "stasisToReceive",
          type: "uint256"
        }
      ],
      name: "openLeverage",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "seller",
          type: "address"
        }
      ],
      name: "sellBondingTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "sellTokens",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "staticFeePercentage",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "symbol",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "token0",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "token1",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalSupply",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "transfer",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "from",
          type: "address"
        },
        {
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "transferFrom",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "withdraw",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    }
  ],
  bytecode: "0x",
  deployedBytecode: "0x",
  linkReferences: {},
  deployedLinkReferences: {}
};

// src/modules/Trading.ts
var import_viem2 = require("viem");
var leverageAbi = [
  { "inputs": [{ "name": "", "type": "address" }], "name": "leverageCount", "outputs": [{ "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" },
  { "inputs": [{ "name": "", "type": "address" }, { "name": "", "type": "uint256" }], "name": "leverages", "outputs": [{ "name": "user", "type": "address" }, { "name": "token", "type": "address" }, { "name": "collateralAmount", "type": "uint256" }, { "name": "liquidatedAmount", "type": "uint256" }, { "name": "fullAmount", "type": "uint256" }, { "name": "borrowedAmount", "type": "uint256" }, { "name": "liquidationTime", "type": "uint256" }, { "name": "liquidationClaim", "type": "uint256" }, { "name": "isLiquidated", "type": "bool" }, { "name": "active", "type": "bool" }, { "name": "creationTime", "type": "uint256" }, { "name": "timeOfClosure", "type": "uint256" }], "stateMutability": "view", "type": "function" }
];
var TradingModule = class {
  client;
  swapAddress;
  constructor(client, swapAddress) {
    this.client = client;
    this.swapAddress = swapAddress;
  }
  async _syncLoan(txHash) {
    try {
      await this.client.api.syncLoan(txHash);
    } catch (e) {
      console.warn("Loan sync warning:", e.message || e);
    }
  }
  /**
   * Automatically approves the token to be spent by the SWAP contract.
   * Internal helper function.
   */
  async approveIfNeeded(tokenAddress, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, this.swapAddress]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [this.swapAddress, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  /**
   * Buys tokens during the bonding curve phase.
   * Calls buyTokens on SWAP.sol.
   */
  async buyBondingTokens(amount, minOut, path, wrapTokens) {
    return this.buyTokens(amount, minOut, path, wrapTokens);
  }
  /**
   * Sells tokens during the bonding curve phase.
   * Calls sellTokens on SWAP.sol.
   */
  async sellBondingTokens(amount, minOut, path, swapToETH) {
    return this.sellTokens(amount, minOut, path, swapToETH);
  }
  /**
   * General buy tokens function.
   */
  async buyTokens(amount, minOut, path, wrapTokens) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const account = this.client.walletClient.account;
    if (path.length > 0) {
      await this.approveIfNeeded(path[0], amount);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account,
      address: this.swapAddress,
      abi: ASwap_default.abi,
      functionName: "buyTokens",
      args: [amount, minOut, path, wrapTokens]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * General sell tokens function.
   */
  async sellTokens(amount, minOut, path, swapToETH) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const account = this.client.walletClient.account;
    if (path.length > 0) {
      await this.approveIfNeeded(path[0], amount);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account,
      address: this.swapAddress,
      abi: ASwap_default.abi,
      functionName: "sellTokens",
      args: [amount, minOut, path, swapToETH]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Simplified buy: purchases the target token using USDB.
   * Automatically builds the correct swap path.
   */
  async buy(tokenAddress, usdbAmount, minOut = 0n, wrapTokens = false) {
    const path = this.buildBuyPath(tokenAddress);
    return this.buyTokens(usdbAmount, minOut, path, wrapTokens);
  }
  /**
   * Simplified sell: sells a token.
   * For factory tokens, set toUsdb=true to swap all the way to USDB (3-hop),
   * or false to stop at MAINTOKEN (2-hop). Ignored when selling MAINTOKEN.
   */
  async sell(tokenAddress, amount, toUsdb = false, minOut = 0n, swapToETH = false) {
    const path = this.buildSellPath(tokenAddress, toUsdb);
    return this.sellTokens(amount, minOut, path, swapToETH);
  }
  buildBuyPath(tokenAddress) {
    const usdb = (0, import_viem2.getAddress)(this.client.usdbAddress);
    const mainToken = (0, import_viem2.getAddress)(this.client.mainTokenAddress);
    const target = (0, import_viem2.getAddress)(tokenAddress);
    if (target === mainToken) {
      return [usdb, mainToken];
    }
    return [usdb, mainToken, target];
  }
  buildSellPath(tokenAddress, toUsdb) {
    const usdb = (0, import_viem2.getAddress)(this.client.usdbAddress);
    const mainToken = (0, import_viem2.getAddress)(this.client.mainTokenAddress);
    const target = (0, import_viem2.getAddress)(tokenAddress);
    if (target === mainToken) {
      return [mainToken, usdb];
    }
    if (toUsdb) {
      return [target, mainToken, usdb];
    }
    return [target, mainToken];
  }
  /**
   * Leveraged buy: purchases tokens with leverage (creates a loan position).
   */
  async leverageBuy(amount, minOut, path, numberOfDays) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const account = this.client.walletClient.account;
    if (path.length > 0) {
      await this.approveIfNeeded(path[0], amount);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account,
      address: this.swapAddress,
      abi: ASwap_default.abi,
      functionName: "leverageBuy",
      args: [amount, minOut, path, numberOfDays]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Partially sells collateral from a loan/leverage position.
   * percentage must be divisible by 10 (10-100).
   */
  async partialLoanSell(loanId, percentage, isLeverage, minOut) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.swapAddress,
      abi: ASwap_default.abi,
      functionName: "partialLoanSell",
      args: [loanId, percentage, isLeverage, minOut]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Sells a percentage of the user's token balance.
   * percentage: 1-100
   */
  async sellPercentage(tokenAddress, percentage, toUsdb = false, minOut = 0n, swapToETH = false) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    if (percentage < 1 || percentage > 100) {
      throw new Error("Percentage must be between 1 and 100.");
    }
    const account = this.client.walletClient.account;
    const balance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "balanceOf",
      args: [account.address]
    });
    if (balance === 0n) {
      throw new Error("Token balance is zero.");
    }
    const sellAmount = balance * BigInt(percentage) / 100n;
    return this.sell(tokenAddress, sellAmount, toUsdb, minOut, swapToETH);
  }
  /**
   * Gets the leverage position count for a user from MAINTOKEN.
   */
  async getLeverageCount(user) {
    const count = await this.client.publicClient.readContract({
      address: this.client.mainTokenAddress,
      abi: leverageAbi,
      functionName: "leverageCount",
      args: [user]
    });
    return count;
  }
  /**
   * Gets a specific leverage position from MAINTOKEN.
   */
  async getLeveragePosition(user, loanId) {
    return this.client.publicClient.readContract({
      address: this.client.mainTokenAddress,
      abi: leverageAbi,
      functionName: "leverages",
      args: [user, loanId]
    });
  }
  /**
   * Fetches the token price from the token's contract.
   */
  async getTokenPrice(tokenAddress) {
    const price = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "getTokenPrice"
    });
    return price.toString();
  }
  /**
   * Fetches the USD price of the token from the token's contract.
   */
  async getUSDPrice(tokenAddress) {
    const price = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: FACTORYTOKEN_default.abi,
      functionName: "getUSDPrice"
    });
    return price.toString();
  }
  /**
   * Converts a market token position to native tokens via the swap contract.
   * Auto-approves the input token.
   */
  async convertToNative(marketToken, inputToken, inputAmount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(inputToken, inputAmount);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.swapAddress,
      abi: ASwap_default.abi,
      functionName: "convertToNative",
      args: [marketToken, inputToken, inputAmount]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Returns the expected output amounts for a given input amount and swap path.
   */
  async getAmountsOut(amount, path) {
    return this.client.publicClient.readContract({
      address: this.swapAddress,
      abi: ASwap_default.abi,
      functionName: "getAmountsOut",
      args: [amount, path]
    });
  }
};

// src/abis/AMarketTrading.json
var AMarketTrading_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "_taxes",
          type: "address"
        },
        {
          internalType: "address",
          name: "_insuranceWallet",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "donor",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "BountyDonated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "swap",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "usdc",
          type: "address"
        }
      ],
      name: "EcosystemAdded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "ecosystem",
          type: "address"
        }
      ],
      name: "MarketCreated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "generalPotSentToInsurance",
          type: "uint256"
        }
      ],
      name: "MarketInvalidated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        }
      ],
      name: "OrderCancelled",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          indexed: true,
          internalType: "address",
          name: "seller",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "pricePerShare",
          type: "uint256"
        }
      ],
      name: "OrderCreated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          indexed: true,
          internalType: "address",
          name: "buyer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcSpent",
          type: "uint256"
        }
      ],
      name: "OrderFilled",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "donor",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "PotDonated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "payout",
          type: "uint256"
        }
      ],
      name: "SharesRedeemed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "buyer",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "shares",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcSpent",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "enum AMarketTrading.TradeType",
          name: "tradeType",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "newReserve",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "newTotalReserve",
          type: "uint256"
        }
      ],
      name: "SharesTraded",
      type: "event"
    },
    {
      inputs: [],
      name: "CEO",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "DisableFreeze",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "FLOOR_PER_OUTCOME",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MAX_OUTCOMES",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MAX_TOTAL_POOL",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MIN_TOTAL_POOL",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "ONE_USD",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_EARLY",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_INVALID",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_UNRESOLVED",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "wallet",
          type: "address"
        },
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "RemoveWhitelist",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address[]",
          name: "wallets",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "string",
          name: "tag",
          type: "string"
        },
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "SetWhitelistedWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "TAXES",
      outputs: [
        {
          internalType: "contract IATaxes",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          internalType: "address",
          name: "swap",
          type: "address"
        },
        {
          internalType: "address",
          name: "usdc",
          type: "address"
        }
      ],
      name: "addEcosystem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyPool",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "address",
          name: "inputToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "inputAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minUsdc",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minShares",
          type: "uint256"
        }
      ],
      name: "buy",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256[]",
          name: "orderIds",
          type: "uint256[]"
        },
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "buyMultipleOrders",
      outputs: [
        {
          internalType: "uint256",
          name: "remainingUsdc",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "fill",
          type: "uint256"
        }
      ],
      name: "buyOrder",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256[]",
          name: "orderIds",
          type: "uint256[]"
        },
        {
          internalType: "address",
          name: "inputToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "totalInput",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minShares",
          type: "uint256"
        }
      ],
      name: "buyOrdersAndContract",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        }
      ],
      name: "cancelOrder",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "string",
          name: "marketName",
          type: "string"
        },
        {
          internalType: "string",
          name: "symbol",
          type: "string"
        },
        {
          internalType: "uint256",
          name: "endTime",
          type: "uint256"
        },
        {
          internalType: "string[]",
          name: "_optionNames",
          type: "string[]"
        },
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "bool",
          name: "frozen",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "bonding",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "seedAmount",
          type: "uint256"
        }
      ],
      name: "createMarket",
      outputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isBounty",
          type: "bool"
        }
      ],
      name: "donate",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "drainBountyPool",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "ecosystems",
      outputs: [
        {
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          internalType: "address",
          name: "swap",
          type: "address"
        },
        {
          internalType: "address",
          name: "usdc",
          type: "address"
        },
        {
          internalType: "bool",
          name: "active",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getBountyPool",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "getBuyOrderAmountsOut",
      outputs: [
        {
          internalType: "uint256",
          name: "fill",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "baseUsdc",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "buyerTax",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalCostToBuyer",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "fill",
          type: "uint256"
        }
      ],
      name: "getBuyOrderCost",
      outputs: [
        {
          internalType: "uint256",
          name: "baseUsdc",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "buyerTax",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalCostToBuyer",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "netToSeller",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getGeneralPot",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "n",
          type: "uint256"
        }
      ],
      name: "getInitialReserves",
      outputs: [
        {
          internalType: "uint256",
          name: "perOutcome",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalReserve",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getMarketData",
      outputs: [
        {
          components: [
            {
              internalType: "address",
              name: "marketToken",
              type: "address"
            },
            {
              internalType: "address",
              name: "creator",
              type: "address"
            },
            {
              internalType: "address",
              name: "ecosystem",
              type: "address"
            },
            {
              internalType: "address",
              name: "usdc",
              type: "address"
            },
            {
              internalType: "string",
              name: "marketName",
              type: "string"
            },
            {
              internalType: "uint256",
              name: "creationTime",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "endTime",
              type: "uint256"
            },
            {
              internalType: "uint8",
              name: "finalOutcome",
              type: "uint8"
            },
            {
              internalType: "bool",
              name: "resolved",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "generalPot",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalVirtualReserve",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "isPrivate",
              type: "bool"
            }
          ],
          internalType: "struct AMarketTrading.MarketData",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getNumOutcomes",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getOptionNames",
      outputs: [
        {
          internalType: "string[]",
          name: "",
          type: "string[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "getOutcome",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "virtualReserve",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalCost",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "circulatingShares",
              type: "uint256"
            }
          ],
          internalType: "struct AMarketTrading.Outcome",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "getUserShares",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "hasBetted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "hasBettedOnMarket",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "insuranceWallet",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "lastTrade",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pricePerShare",
          type: "uint256"
        }
      ],
      name: "listOrder",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "marketData",
      outputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        },
        {
          internalType: "address",
          name: "usdc",
          type: "address"
        },
        {
          internalType: "string",
          name: "marketName",
          type: "string"
        },
        {
          internalType: "uint256",
          name: "creationTime",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "endTime",
          type: "uint256"
        },
        {
          internalType: "uint8",
          name: "finalOutcome",
          type: "uint8"
        },
        {
          internalType: "bool",
          name: "resolved",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "generalPot",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalVirtualReserve",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isPrivate",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "marketOrders",
      outputs: [
        {
          internalType: "address",
          name: "seller",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pricePerShare",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "active",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "minSeed",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "nextOrderId",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "optionNames",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "outcomes",
      outputs: [
        {
          internalType: "uint256",
          name: "virtualReserve",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalCost",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "circulatingShares",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "redeem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        }
      ],
      name: "rescueToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "resolver",
      outputs: [
        {
          internalType: "contract IMarketResolver",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newWallet",
          type: "address"
        }
      ],
      name: "setInsuranceWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_minSeed",
          type: "uint256"
        }
      ],
      name: "setMinSeed",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "minPool",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "maxPool",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "floor",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "maxOutcomes",
          type: "uint256"
        }
      ],
      name: "setPoolConfig",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "_resolver",
          type: "address"
        }
      ],
      name: "setPredictionResolver",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcome",
          type: "uint8"
        }
      ],
      name: "setResolved",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      name: "sharesLockedInOrders",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      name: "userShares",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      stateMutability: "payable",
      type: "receive"
    }
  ]
};

// src/modules/PredictionMarkets.ts
var import_viem3 = require("viem");
var PredictionMarketsModule = class {
  client;
  marketTradingAddress;
  constructor(client, marketTradingAddress) {
    this.client = client;
    this.marketTradingAddress = marketTradingAddress;
  }
  /**
   * Helper to approve tokens for the MarketTrading contract
   */
  async approveIfNeeded(tokenAddress, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, this.marketTradingAddress]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [this.marketTradingAddress, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  /**
   * Internal: creates a market on-chain. Use createMarketWithMetadata() instead.
   */
  async createMarket(marketName, symbol, endTime, optionNames, maintoken, frozen, bonding, seedAmount = 0n) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const ecoData = await this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "ecosystems",
      args: [maintoken]
    });
    const factoryAddress = ecoData.factory ?? ecoData[0];
    const feeAmount = await this.client.publicClient.readContract({
      address: factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "feeAmount"
    });
    if (seedAmount > 0n) {
      await this.approveIfNeeded(this.client.usdbAddress, seedAmount);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "createMarket",
      args: [marketName, symbol, endTime, optionNames, maintoken, frozen, bonding, seedAmount],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Creates a prediction market and registers its metadata on IPFS in one call.
   * Requires SIWE authentication.
   *
   * Returns { hash, receipt, marketTokenAddress, imageUrl, metadata }
   */
  async createMarketWithMetadata(options) {
    const createResult = await this.createMarket(
      options.marketName,
      options.symbol,
      options.endTime,
      options.optionNames,
      options.maintoken,
      options.frozen ?? false,
      options.bonding ?? 0n,
      options.seedAmount ?? 0n
    );
    if (createResult.receipt.status === "reverted") {
      throw new Error(`Market creation reverted (tx: ${createResult.hash})`);
    }
    const MARKET_CREATED_TOPIC = (0, import_viem3.keccak256)((0, import_viem3.toBytes)("MarketCreated(address,address,address)"));
    const marketLog = createResult.receipt.logs.find(
      (l) => l.address.toLowerCase() === this.marketTradingAddress.toLowerCase() && l.topics[0] === MARKET_CREATED_TOPIC
    );
    let marketTokenAddress;
    if (marketLog && marketLog.topics[1]) {
      marketTokenAddress = (0, import_viem3.getAddress)("0x" + marketLog.topics[1].slice(26));
    } else {
      throw new Error("Could not extract market address from creation logs.");
    }
    let imageUrl;
    if (options.imageUrl) {
      imageUrl = await this.client.api.uploadImageFromUrl(options.imageUrl, marketTokenAddress);
    }
    const metadata = await this.client.api.updateMetadata({
      address: marketTokenAddress,
      description: options.description,
      image: imageUrl,
      website: options.website,
      telegram: options.telegram,
      twitterx: options.twitterx
    });
    return {
      hash: createResult.hash,
      receipt: createResult.receipt,
      marketTokenAddress,
      imageUrl,
      metadata
    };
  }
  /**
   * Executes an AMM buy for a prediction outcome.
   */
  async buy(marketToken, outcomeId, inputToken, inputAmount, minUsdb, minShares) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(inputToken, inputAmount);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "buy",
      args: [marketToken, outcomeId, inputToken, inputAmount, minUsdb, minShares]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Claims winnings after a market resolves.
   */
  async redeem(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "redeem",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Reads the MarketData struct.
   */
  async getMarketData(marketToken) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getMarketData",
      args: [marketToken]
    });
  }
  /**
   * Reads the Outcome struct.
   */
  async getOutcome(marketToken, outcomeId) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getOutcome",
      args: [marketToken, outcomeId]
    });
  }
  /**
   * Reads user balances.
   */
  async getUserShares(marketToken, user, outcomeId) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getUserShares",
      args: [marketToken, user, outcomeId]
    });
  }
  /**
   * Returns the initial reserves required for a given number of outcomes.
   */
  async getInitialReserves(numOutcomes) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getInitialReserves",
      args: [numOutcomes]
    });
  }
  /**
   * Buys from order book and AMM in a single transaction.
   * Fills specified orders first, then routes remaining input to the AMM.
   */
  async getNumOutcomes(marketToken) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getNumOutcomes",
      args: [marketToken]
    });
  }
  async getOptionNames(marketToken) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getOptionNames",
      args: [marketToken]
    });
  }
  async hasBettedOnMarket(marketToken, user) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "hasBettedOnMarket",
      args: [marketToken, user]
    });
  }
  async getBountyPool(marketToken) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getBountyPool",
      args: [marketToken]
    });
  }
  async getGeneralPot(marketToken) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getGeneralPot",
      args: [marketToken]
    });
  }
  async getBuyOrderAmountsOut(marketToken, orderId, usdbAmount) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getBuyOrderAmountsOut",
      args: [marketToken, orderId, usdbAmount]
    });
  }
  async buyOrdersAndContract(marketToken, outcomeId, orderIds, inputToken, totalInput, minShares) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(inputToken, totalInput);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "buyOrdersAndContract",
      args: [marketToken, outcomeId, orderIds, inputToken, totalInput, minShares]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
};

// src/modules/OrderBook.ts
var OrderBookModule = class {
  client;
  marketTradingAddress;
  constructor(client, marketTradingAddress) {
    this.client = client;
    this.marketTradingAddress = marketTradingAddress;
  }
  /**
   * Creates a limit order.
   */
  async listOrder(marketToken, outcomeId, amount, pricePerShare) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "listOrder",
      args: [marketToken, outcomeId, amount, pricePerShare]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Cancels an active order.
   */
  async cancelOrder(marketToken, orderId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "cancelOrder",
      args: [marketToken, orderId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Executes against a specific order.
   */
  async buyOrder(marketToken, orderId, fill) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "buyOrder",
      args: [marketToken, orderId, fill]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Sweeps multiple orders.
   */
  async buyMultipleOrders(marketToken, orderIds, usdbAmount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "buyMultipleOrders",
      args: [marketToken, orderIds, usdbAmount]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Syncs an order transaction to the backend database.
   * Called automatically after listOrder, cancelOrder, buyOrder, buyMultipleOrders.
   */
  async syncOrder(txHash, marketType = "public") {
    try {
      await this.client.api.syncOrder(txHash, marketType);
    } catch (err) {
      console.warn("Order sync warning:", err instanceof Error ? err.message : err);
    }
  }
  /**
   * Retrieves exact cost including taxes before buying.
   */
  async getBuyOrderCost(marketToken, orderId, fill) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getBuyOrderCost",
      args: [marketToken, orderId, fill]
    });
  }
  /**
   * Preview how many shares can be bought for a given USDB amount on a P2P order.
   */
  async getBuyOrderAmountsOut(marketToken, orderId, usdbAmount) {
    return this.client.publicClient.readContract({
      address: this.marketTradingAddress,
      abi: AMarketTrading_default.abi,
      functionName: "getBuyOrderAmountsOut",
      args: [marketToken, orderId, usdbAmount]
    });
  }
};

// src/abis/ALOAN_HUB.json
var ALOAN_HUB_default = {
  abi: [
    {
      inputs: [],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "mainToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "stable",
          type: "address"
        }
      ],
      name: "EcosystemAdded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "claimed",
          type: "uint256"
        }
      ],
      name: "LiquidationClaimed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "coreId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "borrowed",
          type: "uint256"
        }
      ],
      name: "LoanCreated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "addDays",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "bool",
          name: "refinance",
          type: "bool"
        }
      ],
      name: "LoanExtended",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amountAdded",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "borrowed",
          type: "uint256"
        }
      ],
      name: "LoanIncreased",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        }
      ],
      name: "LoanRepaid",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "percentage",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "received",
          type: "uint256"
        }
      ],
      name: "PartialLoanSold",
      type: "event"
    },
    {
      inputs: [],
      name: "CEO",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "mainToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "stable",
          type: "address"
        },
        {
          internalType: "address",
          name: "swapContract",
          type: "address"
        }
      ],
      name: "addEcosystem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        }
      ],
      name: "claimLiquidation",
      outputs: [
        {
          internalType: "uint256",
          name: "claimed",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "ecosystems",
      outputs: [
        {
          internalType: "address",
          name: "mainToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "stable",
          type: "address"
        },
        {
          internalType: "address",
          name: "swapContract",
          type: "address"
        },
        {
          internalType: "bool",
          name: "active",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "addDays",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "payInStable",
          type: "bool"
        },
        {
          internalType: "bool",
          name: "refinance",
          type: "bool"
        }
      ],
      name: "extendLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "extensionWhitelisted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        }
      ],
      name: "getUserLoanDetails",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "hubId",
              type: "uint256"
            },
            {
              internalType: "address",
              name: "ecosystem",
              type: "address"
            },
            {
              internalType: "uint256",
              name: "coreLoanId",
              type: "uint256"
            },
            {
              internalType: "address",
              name: "collateralToken",
              type: "address"
            },
            {
              internalType: "address",
              name: "token",
              type: "address"
            },
            {
              internalType: "uint256",
              name: "collateralAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "liquidatedAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "fullAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "borrowedAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "liquidationTime",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "liquidationClaim",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "isLiquidated",
              type: "bool"
            },
            {
              internalType: "bool",
              name: "active",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "creationTime",
              type: "uint256"
            }
          ],
          internalType: "struct ALOAN_HUB.FullLoanDetails",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "percentage",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isLeverage",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "minOut",
          type: "uint256"
        }
      ],
      name: "hubPartialLoanSell",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "amountToAdd",
          type: "uint256"
        }
      ],
      name: "increaseLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isEcosystemRegistered",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        }
      ],
      name: "repayLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        }
      ],
      name: "rescueToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "wallet",
          type: "address"
        },
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        }
      ],
      name: "setExtensionWhitelist",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        },
        {
          internalType: "address",
          name: "collateral",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "daysCount",
          type: "uint256"
        }
      ],
      name: "takeLoan",
      outputs: [
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "mainToken",
          type: "address"
        },
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        }
      ],
      name: "toggleEcosystemStatus",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "userLoanCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "userLoans",
      outputs: [
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "coreLoanId",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "collateralToken",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/Loans.ts
var LoansModule = class {
  client;
  loanHubAddress;
  constructor(client, loanHubAddress) {
    this.client = client;
    this.loanHubAddress = loanHubAddress;
  }
  async _syncLoan(txHash) {
    try {
      await this.client.api.syncLoan(txHash);
    } catch (e) {
      console.warn("Loan sync warning:", e.message || e);
    }
  }
  async approveIfNeeded(tokenAddress, spender, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, spender]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [spender, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  /**
   * Takes a loan. Auto-approves the collateral token to the LoanHub.
   */
  async takeLoan(ecosystem, collateral, amount, daysCount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(collateral, this.loanHubAddress, amount);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "takeLoan",
      args: [ecosystem, collateral, amount, daysCount]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Repays a loan to release collateral.
   * Auto-approves the borrowed token (USDB) to the LoanHub.
   */
  async repayLoan(hubId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const loanDetails = await this.getUserLoanDetails(
      this.client.walletClient.account.address,
      hubId
    );
    const fullAmount = loanDetails.fullAmount ?? loanDetails[4] ?? 0n;
    if (fullAmount > 0n) {
      await this.approveIfNeeded(this.client.usdbAddress, this.loanHubAddress, fullAmount);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "repayLoan",
      args: [hubId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Prolongs duration of a loan.
   * When payInStable is true, auto-approves USDB to the LoanHub.
   */
  async extendLoan(hubId, addDays, payInStable, refinance) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    if (payInStable) {
      const usdbBalance = await this.client.publicClient.readContract({
        address: this.client.usdbAddress,
        abi: IERC20_default.abi,
        functionName: "balanceOf",
        args: [this.client.walletClient.account.address]
      });
      if (usdbBalance > 0n) {
        await this.approveIfNeeded(this.client.usdbAddress, this.loanHubAddress, usdbBalance);
      }
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "extendLoan",
      args: [hubId, addDays, payInStable, refinance]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Executes liquidation on a defaulted loan.
   */
  async claimLiquidation(hubId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "claimLiquidation",
      args: [hubId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Returns FullLoanDetails struct.
   */
  async getUserLoanDetails(user, hubId) {
    return this.client.publicClient.readContract({
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "getUserLoanDetails",
      args: [user, hubId]
    });
  }
  /**
   * Increases collateral on an existing loan.
   * Reads loan details to find the collateral token, then auto-approves it.
   */
  async increaseLoan(hubId, amountToAdd) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const loanDetails = await this.getUserLoanDetails(
      this.client.walletClient.account.address,
      hubId
    );
    const collateral = loanDetails.collateral ?? loanDetails[4];
    await this.approveIfNeeded(collateral, this.loanHubAddress, amountToAdd);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "increaseLoan",
      args: [hubId, amountToAdd]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Returns the number of loans a user has.
   */
  /**
   * Partially sell collateral from a hub loan position.
   */
  async hubPartialLoanSell(hubId, percentage, isLeverage, minOut) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "hubPartialLoanSell",
      args: [hubId, percentage, isLeverage, minOut]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  async getUserLoanCount(user) {
    return this.client.publicClient.readContract({
      address: this.loanHubAddress,
      abi: ALOAN_HUB_default.abi,
      functionName: "userLoanCount",
      args: [user]
    });
  }
};

// src/abis/A_VestingContract.json
var A_VestingContract_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          internalType: "address",
          name: "loan",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "address",
          name: "oldBeneficiary",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "newBeneficiary",
          type: "address"
        }
      ],
      name: "BeneficiaryChanged",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "address",
          name: "oldCreator",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "newCreator",
          type: "address"
        }
      ],
      name: "CreatorRoleTransferred",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "newFeeAmount",
          type: "uint256"
        }
      ],
      name: "FeeAmountChanged",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "address",
          name: "payer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "FeeCollected",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "bool",
          name: "enabled",
          type: "bool"
        }
      ],
      name: "FeeEnabledChanged",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "address",
          name: "addr",
          type: "address"
        },
        {
          indexed: false,
          internalType: "bool",
          name: "whitelisted",
          type: "bool"
        }
      ],
      name: "FeeWhitelistUpdated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "newBuffer",
          type: "uint256"
        }
      ],
      name: "LoanBufferUpdated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "loanId",
          type: "uint256"
        }
      ],
      name: "LoanRepaid",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "loanId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "loanDurationDays",
          type: "uint256"
        }
      ],
      name: "LoanTaken",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "TokensClaimed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "beneficiary",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        }
      ],
      name: "VestingCreated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "additionalDays",
          type: "uint256"
        }
      ],
      name: "VestingExtended",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "beneficiary",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        }
      ],
      name: "VestingUpdated",
      type: "event"
    },
    {
      inputs: [],
      name: "LOAN",
      outputs: [
        {
          internalType: "contract ILOAN",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MAX_VESTING_DURATION",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MIN_VESTING_DURATION",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "factory",
          type: "address"
        }
      ],
      name: "addEcosystem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "additionalAmount",
          type: "uint256"
        }
      ],
      name: "addTokensToVesting",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address[]",
          name: "beneficiaries",
          type: "address[]"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256[]",
          name: "totalAmounts",
          type: "uint256[]"
        },
        {
          internalType: "uint256",
          name: "unlockTime",
          type: "uint256"
        },
        {
          internalType: "string[]",
          name: "userMemos",
          type: "string[]"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        }
      ],
      name: "batchCreateCliffVesting",
      outputs: [
        {
          internalType: "uint256[]",
          name: "",
          type: "uint256[]"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address[]",
          name: "beneficiaries",
          type: "address[]"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256[]",
          name: "totalAmounts",
          type: "uint256[]"
        },
        {
          internalType: "string[]",
          name: "userMemos",
          type: "string[]"
        },
        {
          internalType: "uint256",
          name: "startTime",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "durationInDays",
          type: "uint256"
        },
        {
          internalType: "enum A_VestingContract.TimeUnit",
          name: "timeUnit",
          type: "uint8"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        }
      ],
      name: "batchCreateGradualVesting",
      outputs: [
        {
          internalType: "uint256[]",
          name: "",
          type: "uint256[]"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "beneficiaryCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "beneficiaryVestings",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "newBeneficiary",
          type: "address"
        }
      ],
      name: "changeBeneficiary",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "claimTokens",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "beneficiary",
          type: "address"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "unlockTime",
          type: "uint256"
        },
        {
          internalType: "string",
          name: "memo",
          type: "string"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        }
      ],
      name: "createCliffVesting",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "beneficiary",
          type: "address"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "startTime",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "durationInDays",
          type: "uint256"
        },
        {
          internalType: "enum A_VestingContract.TimeUnit",
          name: "timeUnit",
          type: "uint8"
        },
        {
          internalType: "string",
          name: "memo",
          type: "string"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        }
      ],
      name: "createGradualVesting",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "creatorCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "creatorVestings",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "ecosystems",
      outputs: [
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          internalType: "address",
          name: "mainpair",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "additionalDays",
          type: "uint256"
        }
      ],
      name: "extendVestingPeriod",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "feeAmount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "feeEnabled",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "feeWhitelist",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "getActiveLoan",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "getClaimableAmount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "startIndex",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "endIndex",
          type: "uint256"
        }
      ],
      name: "getTokenVestingIds",
      outputs: [
        {
          internalType: "uint256[]",
          name: "",
          type: "uint256[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "getVestedAmount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "getVestingDetails",
      outputs: [
        {
          components: [
            {
              internalType: "address",
              name: "creator",
              type: "address"
            },
            {
              internalType: "address",
              name: "beneficiary",
              type: "address"
            },
            {
              internalType: "address",
              name: "token",
              type: "address"
            },
            {
              internalType: "address",
              name: "ecosystem",
              type: "address"
            },
            {
              internalType: "uint256",
              name: "totalAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "claimedAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "startTime",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "durationInDays",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "unlockTime",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "isGradual",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "activeLoanId",
              type: "uint256"
            },
            {
              internalType: "string",
              name: "memo",
              type: "string"
            },
            {
              internalType: "enum A_VestingContract.TimeUnit",
              name: "timeUnit",
              type: "uint8"
            }
          ],
          internalType: "struct A_VestingContract.Vesting",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256[]",
          name: "vestingIds",
          type: "uint256[]"
        }
      ],
      name: "getVestingDetailsBatch",
      outputs: [
        {
          components: [
            {
              internalType: "address",
              name: "creator",
              type: "address"
            },
            {
              internalType: "address",
              name: "beneficiary",
              type: "address"
            },
            {
              internalType: "address",
              name: "token",
              type: "address"
            },
            {
              internalType: "address",
              name: "ecosystem",
              type: "address"
            },
            {
              internalType: "uint256",
              name: "totalAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "claimedAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "startTime",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "durationInDays",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "unlockTime",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "isGradual",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "activeLoanId",
              type: "uint256"
            },
            {
              internalType: "string",
              name: "memo",
              type: "string"
            },
            {
              internalType: "enum A_VestingContract.TimeUnit",
              name: "timeUnit",
              type: "uint8"
            }
          ],
          internalType: "struct A_VestingContract.Vesting[]",
          name: "",
          type: "tuple[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "beneficiary",
          type: "address"
        }
      ],
      name: "getVestingsByBeneficiary",
      outputs: [
        {
          internalType: "uint256[]",
          name: "",
          type: "uint256[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "creator",
          type: "address"
        }
      ],
      name: "getVestingsByCreator",
      outputs: [
        {
          internalType: "uint256[]",
          name: "",
          type: "uint256[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "loanBuffer",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "repayLoanOnVesting",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "tokenToRescue",
          type: "address"
        }
      ],
      name: "rescueAnyToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "rescueEth",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "factory",
          type: "address"
        }
      ],
      name: "setEcosystem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newFeeAmount",
          type: "uint256"
        }
      ],
      name: "setFeeAmount",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "bool",
          name: "enabled",
          type: "bool"
        }
      ],
      name: "setFeeEnabled",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "addr",
          type: "address"
        },
        {
          internalType: "bool",
          name: "whitelisted",
          type: "bool"
        }
      ],
      name: "setFeeWhitelist",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newBuffer",
          type: "uint256"
        }
      ],
      name: "setLoanBuffer",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newLoan",
          type: "address"
        }
      ],
      name: "setNewLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        }
      ],
      name: "takeLoanOnVesting",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "tokenVestingCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "tokenVestings",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "vestingId",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "newCreator",
          type: "address"
        }
      ],
      name: "transferCreatorRole",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "vestingCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "vestingSchedules",
      outputs: [
        {
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          internalType: "address",
          name: "beneficiary",
          type: "address"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "claimedAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "startTime",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "durationInDays",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "unlockTime",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isGradual",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "activeLoanId",
          type: "uint256"
        },
        {
          internalType: "string",
          name: "memo",
          type: "string"
        },
        {
          internalType: "enum A_VestingContract.TimeUnit",
          name: "timeUnit",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/Vesting.ts
var VestingModule = class {
  client;
  vestingAddress;
  constructor(client, vestingAddress) {
    this.client = client;
    this.vestingAddress = vestingAddress;
  }
  async _syncLoan(txHash) {
    try {
      await this.client.api.syncLoan(txHash);
    } catch (e) {
      console.warn("Loan sync warning:", e.message || e);
    }
  }
  async approveIfNeeded(tokenAddress, spender, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, spender]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [spender, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  async getFeeAmount() {
    try {
      return await this.client.publicClient.readContract({
        address: this.vestingAddress,
        abi: A_VestingContract_default.abi,
        functionName: "feeAmount"
      });
    } catch {
      return 0n;
    }
  }
  /**
   * Creates a gradual vesting schedule.
   * Auto-approves the token to the vesting contract and attaches the creation fee.
   */
  async createGradualVesting(beneficiary, token, totalAmount, startTime, durationInDays, timeUnit, memo, ecosystem) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(token, this.vestingAddress, totalAmount);
    const feeAmount = await this.getFeeAmount();
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "createGradualVesting",
      args: [beneficiary, token, totalAmount, startTime, durationInDays, timeUnit, memo, ecosystem],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Creates a cliff vesting schedule.
   */
  async createCliffVesting(beneficiary, token, totalAmount, unlockTime, memo, ecosystem) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(token, this.vestingAddress, totalAmount);
    const feeAmount = await this.getFeeAmount();
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "createCliffVesting",
      args: [beneficiary, token, totalAmount, unlockTime, memo, ecosystem],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Claims unlocked tokens.
   */
  async claimTokens(vestingId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "claimTokens",
      args: [vestingId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Leverages locked tokens for a loan.
   */
  async takeLoanOnVesting(vestingId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "takeLoanOnVesting",
      args: [vestingId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Repays a loan taken on a vesting schedule.
   * Auto-approves the borrowed token (USDB) to the vesting contract.
   */
  async repayLoanOnVesting(vestingId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const usdbBalance = await this.client.publicClient.readContract({
      address: this.client.usdbAddress,
      abi: IERC20_default.abi,
      functionName: "balanceOf",
      args: [this.client.walletClient.account.address]
    });
    if (usdbBalance > 0n) {
      await this.approveIfNeeded(this.client.usdbAddress, this.vestingAddress, usdbBalance);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "repayLoanOnVesting",
      args: [vestingId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Gets details of a specific vesting schedule.
   */
  async getVestingDetails(vestingId) {
    return this.client.publicClient.readContract({
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "getVestingDetails",
      args: [vestingId]
    });
  }
  /**
   * Gets the current claimable amount for a vesting schedule.
   */
  async getClaimableAmount(vestingId) {
    return this.client.publicClient.readContract({
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "getClaimableAmount",
      args: [vestingId]
    });
  }
  /**
   * Creates gradual vesting schedules for multiple beneficiaries in a single transaction.
   * Auto-approves the sum of all amounts and attaches the creation fee.
   */
  async batchCreateGradualVesting(beneficiaries, token, totalAmounts, userMemos, startTime, durationInDays, timeUnit, ecosystem) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const totalApproval = totalAmounts.reduce((sum, amt) => sum + amt, 0n);
    await this.approveIfNeeded(token, this.vestingAddress, totalApproval);
    const feeAmount = await this.getFeeAmount();
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "batchCreateGradualVesting",
      args: [beneficiaries, token, totalAmounts, userMemos, startTime, durationInDays, timeUnit, ecosystem],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Creates cliff vesting schedules for multiple beneficiaries in a single transaction.
   * Auto-approves the sum of all amounts and attaches the creation fee.
   */
  async batchCreateCliffVesting(beneficiaries, token, totalAmounts, unlockTime, userMemos, ecosystem) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const totalApproval = totalAmounts.reduce((sum, amt) => sum + amt, 0n);
    await this.approveIfNeeded(token, this.vestingAddress, totalApproval);
    const feeAmount = await this.getFeeAmount();
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "batchCreateCliffVesting",
      args: [beneficiaries, token, totalAmounts, unlockTime, userMemos, ecosystem],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Changes the beneficiary of a vesting schedule.
   */
  async changeBeneficiary(vestingId, newBeneficiary) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "changeBeneficiary",
      args: [vestingId, newBeneficiary]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Extends the vesting period by additional days.
   */
  async extendVestingPeriod(vestingId, additionalDays) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "extendVestingPeriod",
      args: [vestingId, additionalDays]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Adds more tokens to an existing vesting schedule.
   * Auto-approves the token to the vesting contract.
   */
  async addTokensToVesting(vestingId, additionalAmount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const details = await this.getVestingDetails(vestingId);
    const token = details.token ?? details[2];
    await this.approveIfNeeded(token, this.vestingAddress, additionalAmount);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "addTokensToVesting",
      args: [vestingId, additionalAmount]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Transfers the creator role of a vesting schedule to a new address.
   */
  async transferCreatorRole(vestingId, newCreator) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "transferCreatorRole",
      args: [vestingId, newCreator]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Returns all vesting IDs for a given beneficiary.
   */
  async getVestingsByBeneficiary(beneficiary) {
    return this.client.publicClient.readContract({
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "getVestingsByBeneficiary",
      args: [beneficiary]
    });
  }
  /**
   * Returns all vesting IDs created by a given creator.
   */
  async getVestingsByCreator(creator) {
    return this.client.publicClient.readContract({
      address: this.vestingAddress,
      abi: A_VestingContract_default.abi,
      functionName: "getVestingsByCreator",
      args: [creator]
    });
  }
};

// src/abis/AStasisVault.json
var AStasisVault_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "_stasisToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "_loanHub",
          type: "address"
        },
        {
          internalType: "address",
          name: "_swap",
          type: "address"
        },
        {
          internalType: "address",
          name: "_usdc",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "owner",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "Approval",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "stasisSpent",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "wStasisReceived",
          type: "uint256"
        }
      ],
      name: "Bought",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "wStasisBurned",
          type: "uint256"
        }
      ],
      name: "LiquidationProcessed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "additionalStasis",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcReceived",
          type: "uint256"
        }
      ],
      name: "LoanAdded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "daysAdded",
          type: "uint256"
        }
      ],
      name: "LoanExtended",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "stasisCollateralReturned",
          type: "uint256"
        }
      ],
      name: "LoanRepaid",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "stasisCollateralUsed",
          type: "uint256"
        }
      ],
      name: "LoanTaken",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "Locked",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "previousOwner",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "newOwner",
          type: "address"
        }
      ],
      name: "OwnershipTransferred",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "wStasisSold",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "stasisReceived",
          type: "uint256"
        }
      ],
      name: "Sold",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "from",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "value",
          type: "uint256"
        }
      ],
      name: "Transfer",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "Unlocked",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcReceived",
          type: "uint256"
        }
      ],
      name: "YieldClaimed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "stasisAdded",
          type: "uint256"
        }
      ],
      name: "YieldInjected",
      type: "event"
    },
    {
      inputs: [],
      name: "SWAP",
      outputs: [
        {
          internalType: "contract ISWAP",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "TAXES",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_additionalStasisToBorrow",
          type: "uint256"
        }
      ],
      name: "addToLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "owner",
          type: "address"
        },
        {
          internalType: "address",
          name: "spender",
          type: "address"
        }
      ],
      name: "allowance",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "approve",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "account",
          type: "address"
        }
      ],
      name: "balanceOf",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_stasisAmountToBorrow",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "_days",
          type: "uint256"
        }
      ],
      name: "borrow",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        }
      ],
      name: "buy",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "buyForUser",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "shares",
          type: "uint256"
        }
      ],
      name: "convertToAssets",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "assets",
          type: "uint256"
        }
      ],
      name: "convertToShares",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "decimals",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "subtractedValue",
          type: "uint256"
        }
      ],
      name: "decreaseAllowance",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_daysToAdd",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "_payInUSDC",
          type: "bool"
        },
        {
          internalType: "bool",
          name: "_refinance",
          type: "bool"
        }
      ],
      name: "extendLoan",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "getAvailableStasis",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "getUserStakeDetails",
      outputs: [
        {
          internalType: "uint256",
          name: "liquidShares",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "lockedShares",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalShares",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalAssetValue",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "spender",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "addedValue",
          type: "uint256"
        }
      ],
      name: "increaseAllowance",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        }
      ],
      name: "injectYield",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "loanHub",
      outputs: [
        {
          internalType: "contract IALOAN_HUB",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_shares",
          type: "uint256"
        }
      ],
      name: "lock",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "minBuyAmount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "name",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "owner",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "renounceOwnership",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "repay",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        }
      ],
      name: "rescueToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_shares",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "_claimUSDC",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "_minUSDC",
          type: "uint256"
        }
      ],
      name: "sell",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newTaxes",
          type: "address"
        },
        {
          internalType: "address",
          name: "newSwap",
          type: "address"
        },
        {
          internalType: "address",
          name: "newLoan",
          type: "address"
        }
      ],
      name: "setContracts",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        }
      ],
      name: "setMinBuy",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "settleLiquidation",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "stasisToken",
      outputs: [
        {
          internalType: "contract IERC20",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "symbol",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalAssets",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalStasisAvailable",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalStasisPledged",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "totalSupply",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "transfer",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "from",
          type: "address"
        },
        {
          internalType: "address",
          name: "to",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "transferFrom",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newOwner",
          type: "address"
        }
      ],
      name: "transferOwnership",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_shares",
          type: "uint256"
        }
      ],
      name: "unlock",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "userVaults",
      outputs: [
        {
          internalType: "uint256",
          name: "lockedWStasis",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pledgedStasis",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "hubId",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "hasActiveLoan",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/Staking.ts
var StakingModule = class {
  client;
  stakingAddress;
  constructor(client, stakingAddress) {
    this.client = client;
    this.stakingAddress = stakingAddress;
  }
  async _syncLoan(txHash) {
    try {
      await this.client.api.syncLoan(txHash);
    } catch (e) {
      console.warn("Loan sync warning:", e.message || e);
    }
  }
  async approveIfNeeded(tokenAddress, spender, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, spender]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [spender, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  /**
   * Wraps STASIS (MAINTOKEN) into wSTASIS.
   * Approves the staking contract to spend MAINTOKEN if needed.
   */
  async buy(amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(this.client.mainTokenAddress, this.stakingAddress, amount);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "buy",
      args: [amount]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Unwraps wSTASIS back to STASIS, optionally converting to USDB.
   */
  async sell(shares, claimUSDB = false, minUSDB = 0n) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "sell",
      args: [shares, claimUSDB, minUSDB]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Locks wSTASIS as collateral for borrowing.
   */
  async lock(shares) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(this.stakingAddress, this.stakingAddress, shares);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "lock",
      args: [shares]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Unlocks wSTASIS collateral.
   */
  async unlock(shares) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "unlock",
      args: [shares]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Pledges STASIS as collateral and borrows USDB against it.
   * The stasisAmountToBorrow parameter is the STASIS amount to pledge — USDB received is collateral value minus fees.
   */
  async borrow(stasisAmountToBorrow, days) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "borrow",
      args: [stasisAmountToBorrow, days]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Repays the active staking loan. Auto-approves USDB to the staking contract.
   */
  async repay() {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const usdbBalance = await this.client.publicClient.readContract({
      address: this.client.usdbAddress,
      abi: IERC20_default.abi,
      functionName: "balanceOf",
      args: [this.client.walletClient.account.address]
    });
    if (usdbBalance > 0n) {
      await this.approveIfNeeded(this.client.usdbAddress, this.stakingAddress, usdbBalance);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "repay"
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Extends the active staking loan.
   */
  async extendLoan(daysToAdd, payInUSDB, refinance) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "extendLoan",
      args: [daysToAdd, payInUSDB, refinance]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Gets staking details for a user.
   * Returns [wStasisBalance, lockedWStasis, pledgedStasis, availableStasis].
   */
  async getUserStakeDetails(user) {
    return this.client.publicClient.readContract({
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "getUserStakeDetails",
      args: [user]
    });
  }
  /**
   * Gets the available STASIS (collateral value minus pledged).
   */
  async getAvailableStasis(user) {
    return this.client.publicClient.readContract({
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "getAvailableStasis",
      args: [user]
    });
  }
  /**
   * Converts STASIS amount to wSTASIS shares.
   */
  async convertToShares(assets) {
    return this.client.publicClient.readContract({
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "convertToShares",
      args: [assets]
    });
  }
  /**
   * Converts wSTASIS shares to STASIS amount.
   */
  async convertToAssets(shares) {
    return this.client.publicClient.readContract({
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "convertToAssets",
      args: [shares]
    });
  }
  /**
   * Borrows additional STASIS against locked wSTASIS collateral on an existing loan.
   */
  async addToLoan(additionalStasisToBorrow) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "addToLoan",
      args: [additionalStasisToBorrow]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
  /**
   * Settles a liquidated staking loan position.
   */
  async settleLiquidation() {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.stakingAddress,
      abi: AStasisVault_default.abi,
      functionName: "settleLiquidation"
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    this._syncLoan(hash);
    return { hash, receipt };
  }
};

// src/abis/AMarketResolver.json
var AMarketResolver_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "_trading",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "winner",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        }
      ],
      name: "BondsDistributed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        }
      ],
      name: "BondsSeized",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "claimer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "BountyClaimed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "DisputeReset",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "disputer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "newOutcomeId",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "bond",
          type: "uint256"
        }
      ],
      name: "DisputeStarted",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "proposer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "Proposal",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "finalOutcome",
          type: "uint8"
        }
      ],
      name: "Resolved",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "vetoer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "proposedOutcome",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "bond",
          type: "uint256"
        }
      ],
      name: "Vetoed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "voter",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "Vote",
      type: "event"
    },
    {
      inputs: [],
      name: "CEO",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "DISPUTE_PERIOD",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MAX_QUORUM",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MIN_QUORUM",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MIN_STAKE_AMOUNT",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "ONE_USD",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_EARLY",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_INVALID",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_UNRESOLVED",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "PROPOSAL_BOND",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "PROPOSAL_PERIOD",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "VETO_PERIOD",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "VOTE_LOCK_DURATION",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "VOTING_CONSENSUS",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyClaimed",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyEarlyClaimed",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "bountyPerCorrectEarlyVoteForRound",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyPerCorrectVote",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "claimBounty",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "round",
          type: "uint256"
        }
      ],
      name: "claimEarlyBounty",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "dp",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pp",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "vp",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pb",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "mq",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "maxq",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "vc",
          type: "uint256"
        }
      ],
      name: "configResolver",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "currentRound",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "newOutcomeId",
          type: "uint8"
        }
      ],
      name: "dispute",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "disputes",
      outputs: [
        {
          internalType: "address",
          name: "proposer",
          type: "address"
        },
        {
          internalType: "address",
          name: "disputer",
          type: "address"
        },
        {
          internalType: "address",
          name: "vetoer",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "originalOutcome",
          type: "uint8"
        },
        {
          internalType: "uint8",
          name: "disputedOutcome",
          type: "uint8"
        },
        {
          internalType: "uint8",
          name: "vetoOutcome",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "proposerBond",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "disputerBond",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "vetoBond",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "disputeStartTime",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "finalOutcome",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "finalizeMarket",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "finalizeUncontested",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "inDispute",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "inVeto",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isVoter",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "lastVoteTime",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "nftHasVoted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        },
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      name: "nftVoteCount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "proposeOutcome",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        }
      ],
      name: "rescueToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "resolveByBasis",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "resolved",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "trader",
          type: "address"
        }
      ],
      name: "setPredictionTrader",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "stake",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "wallet",
          type: "address"
        }
      ],
      name: "toggleVoterWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "trading",
      outputs: [
        {
          internalType: "contract IMarketTrading",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "unstake",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "userStakedAmount",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "proposedOutcome",
          type: "uint8"
        }
      ],
      name: "veto",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "vote",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "voterChoice",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/MarketResolver.ts
var MarketResolverModule = class {
  client;
  resolverAddress;
  constructor(client, resolverAddress) {
    this.client = client;
    this.resolverAddress = resolverAddress;
  }
  async approveIfNeeded(tokenAddress, spender, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, spender]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [spender, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  // -----------------------------------------------------------------------
  // Write methods
  // -----------------------------------------------------------------------
  /**
   * Proposes an outcome for a market.
   * Auto-approves USDB to the resolver for the PROPOSAL_BOND amount.
   */
  async proposeOutcome(marketToken, outcomeId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const bond = await this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "PROPOSAL_BOND"
    });
    await this.approveIfNeeded(this.client.usdbAddress, this.resolverAddress, bond);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "proposeOutcome",
      args: [marketToken, outcomeId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Disputes a proposed outcome.
   * Auto-approves USDB to the resolver for the PROPOSAL_BOND amount.
   */
  async dispute(marketToken, newOutcomeId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const bond = await this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "PROPOSAL_BOND"
    });
    await this.approveIfNeeded(this.client.usdbAddress, this.resolverAddress, bond);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "dispute",
      args: [marketToken, newOutcomeId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Casts a vote on a disputed market outcome.
   */
  async vote(marketToken, outcomeId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "vote",
      args: [marketToken, outcomeId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Stakes tokens to become a resolver voter.
   * Auto-approves the token to the resolver for MIN_STAKE_AMOUNT.
   */
  async stake(token) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const minStake = await this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "MIN_STAKE_AMOUNT"
    });
    await this.approveIfNeeded(token, this.resolverAddress, minStake);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "stake",
      args: [token]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Unstakes tokens, removing resolver voter status.
   */
  async unstake(token) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "unstake",
      args: [token]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Finalizes an uncontested market (proposal period expired without dispute).
   */
  async finalizeUncontested(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "finalizeUncontested",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Finalizes a disputed market after the dispute period.
   */
  async finalizeMarket(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "finalizeMarket",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Vetoes a proposed outcome.
   * Auto-approves USDB to the resolver for the PROPOSAL_BOND amount.
   */
  async veto(marketToken, proposedOutcome) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const bond = await this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "PROPOSAL_BOND"
    });
    await this.approveIfNeeded(this.client.usdbAddress, this.resolverAddress, bond);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "veto",
      args: [marketToken, proposedOutcome]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Claims the bounty reward for voting correctly on a resolved market.
   */
  async claimBounty(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "claimBounty",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Claims an early bounty reward for a specific dispute round.
   */
  async claimEarlyBounty(marketToken, round) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "claimEarlyBounty",
      args: [marketToken, round]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  // -----------------------------------------------------------------------
  // Read methods
  // -----------------------------------------------------------------------
  /**
   * Returns the dispute data struct for a market.
   */
  async getDisputeData(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "disputes",
      args: [marketToken]
    });
  }
  /**
   * Returns whether a market has been resolved.
   */
  async isResolved(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "resolved",
      args: [marketToken]
    });
  }
  /**
   * Returns the final outcome of a resolved market.
   */
  async getFinalOutcome(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "finalOutcome",
      args: [marketToken]
    });
  }
  /**
   * Returns whether a market is currently in a dispute.
   */
  async isInDispute(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "inDispute",
      args: [marketToken]
    });
  }
  /**
   * Returns whether a market is currently in a veto period.
   */
  async isInVeto(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "inVeto",
      args: [marketToken]
    });
  }
  /**
   * Returns the current dispute round for a market.
   */
  async getCurrentRound(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "currentRound",
      args: [marketToken]
    });
  }
  /**
   * Returns the vote count for a specific outcome in a specific round.
   */
  async getVoteCount(marketToken, round, outcomeId) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "nftVoteCount",
      args: [marketToken, round, outcomeId]
    });
  }
  /**
   * Returns whether a voter has already voted in a specific round.
   */
  async hasVoted(marketToken, round, voter) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "nftHasVoted",
      args: [marketToken, round, voter]
    });
  }
  /**
   * Returns the outcome a voter chose in a specific round.
   */
  async getVoterChoice(marketToken, round, voter) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "voterChoice",
      args: [marketToken, round, voter]
    });
  }
  /**
   * Returns the bounty amount per correct vote for a resolved market.
   */
  async getBountyPerVote(marketToken) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "bountyPerCorrectVote",
      args: [marketToken]
    });
  }
  /**
   * Returns whether a voter has already claimed the bounty for a market.
   */
  async hasClaimed(marketToken, voter) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "bountyClaimed",
      args: [marketToken, voter]
    });
  }
  /**
   * Returns the staked amount for a voter.
   */
  async getUserStake(voter) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "userStakedAmount",
      args: [voter]
    });
  }
  /**
   * Returns whether an address is a registered voter.
   */
  async isVoter(voter) {
    return this.client.publicClient.readContract({
      address: this.resolverAddress,
      abi: AMarketResolver_default.abi,
      functionName: "isVoter",
      args: [voter]
    });
  }
  /**
   * Returns all system configuration constants.
   */
  async getConstants() {
    const [disputePeriod, proposalPeriod, proposalBond, minStakeAmount] = await Promise.all([
      this.client.publicClient.readContract({
        address: this.resolverAddress,
        abi: AMarketResolver_default.abi,
        functionName: "DISPUTE_PERIOD"
      }),
      this.client.publicClient.readContract({
        address: this.resolverAddress,
        abi: AMarketResolver_default.abi,
        functionName: "PROPOSAL_PERIOD"
      }),
      this.client.publicClient.readContract({
        address: this.resolverAddress,
        abi: AMarketResolver_default.abi,
        functionName: "PROPOSAL_BOND"
      }),
      this.client.publicClient.readContract({
        address: this.resolverAddress,
        abi: AMarketResolver_default.abi,
        functionName: "MIN_STAKE_AMOUNT"
      })
    ]);
    return { disputePeriod, proposalPeriod, proposalBond, minStakeAmount };
  }
};

// src/abis/APrivateTradingMarket.json
var APrivateTradingMarket_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "_taxes",
          type: "address"
        },
        {
          internalType: "address",
          name: "_insuranceWallet",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "claimer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "BountyClaimed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "donor",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "BountyDonated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "ecosystem",
          type: "address"
        }
      ],
      name: "MarketCreated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "totalMarketLiquidity",
          type: "uint256"
        }
      ],
      name: "MarketInvalidated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        }
      ],
      name: "OrderCancelled",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          indexed: true,
          internalType: "address",
          name: "seller",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "pricePerShare",
          type: "uint256"
        }
      ],
      name: "OrderCreated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          indexed: true,
          internalType: "address",
          name: "buyer",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcSpent",
          type: "uint256"
        }
      ],
      name: "OrderFilled",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "address",
          name: "donor",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "PotDonated",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "finalOutcome",
          type: "uint8"
        }
      ],
      name: "Resolved",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "payout",
          type: "uint256"
        }
      ],
      name: "SharesRedeemed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "buyer",
          type: "address"
        },
        {
          indexed: true,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "shares",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "usdcSpent",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "enum APrivateTradingMarket.TradeType",
          name: "tradeType",
          type: "uint8"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "newReserve",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "newTotalReserve",
          type: "uint256"
        }
      ],
      name: "SharesTraded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "voter",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "Vote",
      type: "event"
    },
    {
      inputs: [],
      name: "CEO",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "DisableFreeze",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "FLOOR_PER_OUTCOME",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MAX_OUTCOMES",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MAX_TOTAL_POOL",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "MIN_TOTAL_POOL",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "ONE_USD",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_INVALID",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "OUTCOME_UNRESOLVED",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "TAXES",
      outputs: [
        {
          internalType: "contract IATaxes",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "VOTING_WINDOW",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          internalType: "address",
          name: "swap",
          type: "address"
        },
        {
          internalType: "address",
          name: "usdc",
          type: "address"
        }
      ],
      name: "addEcosystem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyClaimed",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyPerCorrectVote",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "bountyPool",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "address",
          name: "inputToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "inputAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minUsdc",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minShares",
          type: "uint256"
        }
      ],
      name: "buy",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256[]",
          name: "orderIds",
          type: "uint256[]"
        },
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "buyMultipleOrders",
      outputs: [
        {
          internalType: "uint256",
          name: "remainingUsdc",
          type: "uint256"
        }
      ],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "fill",
          type: "uint256"
        }
      ],
      name: "buyOrder",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256[]",
          name: "orderIds",
          type: "uint256[]"
        },
        {
          internalType: "address",
          name: "inputToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "totalInput",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "minShares",
          type: "uint256"
        }
      ],
      name: "buyOrdersAndContract",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        }
      ],
      name: "cancelOrder",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "claimBounty",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "string",
          name: "marketName",
          type: "string"
        },
        {
          internalType: "string",
          name: "symbol",
          type: "string"
        },
        {
          internalType: "uint256",
          name: "endTime",
          type: "uint256"
        },
        {
          internalType: "string[]",
          name: "_optionNames",
          type: "string[]"
        },
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "bool",
          name: "privateEvent",
          type: "bool"
        },
        {
          internalType: "bool",
          name: "frozen",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "bonding",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "seedAmount",
          type: "uint256"
        }
      ],
      name: "createMarket",
      outputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      stateMutability: "payable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isBounty",
          type: "bool"
        }
      ],
      name: "donate",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "ecosystems",
      outputs: [
        {
          internalType: "address",
          name: "factory",
          type: "address"
        },
        {
          internalType: "address",
          name: "swap",
          type: "address"
        },
        {
          internalType: "address",
          name: "usdc",
          type: "address"
        },
        {
          internalType: "bool",
          name: "active",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "finalize",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "firstVoteTime",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        }
      ],
      name: "getBuyOrderAmountsOut",
      outputs: [
        {
          internalType: "uint256",
          name: "fill",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "baseUsdc",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "buyerTax",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalCostToBuyer",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "orderId",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "fill",
          type: "uint256"
        }
      ],
      name: "getBuyOrderCost",
      outputs: [
        {
          internalType: "uint256",
          name: "baseUsdc",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "buyerTax",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalCostToBuyer",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "netToSeller",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "n",
          type: "uint256"
        }
      ],
      name: "getInitialReserves",
      outputs: [
        {
          internalType: "uint256",
          name: "perOutcome",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalReserve",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getMarketData",
      outputs: [
        {
          components: [
            {
              internalType: "address",
              name: "marketToken",
              type: "address"
            },
            {
              internalType: "address",
              name: "creator",
              type: "address"
            },
            {
              internalType: "address",
              name: "ecosystem",
              type: "address"
            },
            {
              internalType: "address",
              name: "usdc",
              type: "address"
            },
            {
              internalType: "string",
              name: "marketName",
              type: "string"
            },
            {
              internalType: "uint256",
              name: "creationTime",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "endTime",
              type: "uint256"
            },
            {
              internalType: "uint8",
              name: "finalOutcome",
              type: "uint8"
            },
            {
              internalType: "bool",
              name: "resolved",
              type: "bool"
            },
            {
              internalType: "uint256",
              name: "generalPot",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalVirtualReserve",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "isPrivate",
              type: "bool"
            }
          ],
          internalType: "struct APrivateTradingMarket.MarketData",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getNumOutcomes",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "hasBetted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "insuranceWallet",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isMarketVoter",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "lastTrade",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pricePerShare",
          type: "uint256"
        }
      ],
      name: "listOrder",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "voter",
          type: "address"
        },
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        }
      ],
      name: "manageVoter",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address[]",
          name: "wallets",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "string",
          name: "tag",
          type: "string"
        },
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        }
      ],
      name: "manageWhitelist",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "marketData",
      outputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "creator",
          type: "address"
        },
        {
          internalType: "address",
          name: "ecosystem",
          type: "address"
        },
        {
          internalType: "address",
          name: "usdc",
          type: "address"
        },
        {
          internalType: "string",
          name: "marketName",
          type: "string"
        },
        {
          internalType: "uint256",
          name: "creationTime",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "endTime",
          type: "uint256"
        },
        {
          internalType: "uint8",
          name: "finalOutcome",
          type: "uint8"
        },
        {
          internalType: "bool",
          name: "resolved",
          type: "bool"
        },
        {
          internalType: "uint256",
          name: "generalPot",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalVirtualReserve",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "isPrivate",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "marketOrders",
      outputs: [
        {
          internalType: "address",
          name: "seller",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "pricePerShare",
          type: "uint256"
        },
        {
          internalType: "bool",
          name: "active",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "marketVoters",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "minSeedPrivate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "minSeedPublic",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "nextOrderId",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "optionNames",
      outputs: [
        {
          internalType: "string",
          name: "",
          type: "string"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "outcomes",
      outputs: [
        {
          internalType: "uint256",
          name: "virtualReserve",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "totalCost",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "circulatingShares",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "redeem",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        }
      ],
      name: "rescueToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newWallet",
          type: "address"
        }
      ],
      name: "setInsuranceWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_minSeedPublic",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "_minSeedPrivate",
          type: "uint256"
        }
      ],
      name: "setMinSeed",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "minPool",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "maxPool",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "floor",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "maxOutcomes",
          type: "uint256"
        }
      ],
      name: "setPoolConfig",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      name: "sharesLockedInOrders",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "address[]",
          name: "buyers",
          type: "address[]"
        },
        {
          internalType: "bool",
          name: "status",
          type: "bool"
        }
      ],
      name: "togglePrivateEventBuyers",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "userCanBuyEvent",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      name: "userShares",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        }
      ],
      name: "vote",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "voterChoice",
      outputs: [
        {
          internalType: "uint8",
          name: "",
          type: "uint8"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      stateMutability: "payable",
      type: "receive"
    }
  ]
};

// src/modules/PrivateMarkets.ts
var PrivateMarketsModule = class {
  client;
  privateMarketAddress;
  constructor(client, privateMarketAddress) {
    this.client = client;
    this.privateMarketAddress = privateMarketAddress;
  }
  async approveIfNeeded(tokenAddress, spender, amount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet account is required for approval.");
    }
    const account = this.client.walletClient.account;
    const allowance = await this.client.publicClient.readContract({
      address: tokenAddress,
      abi: IERC20_default.abi,
      functionName: "allowance",
      args: [account.address, spender]
    });
    if (allowance < amount) {
      const { request } = await this.client.publicClient.simulateContract({
        account,
        address: tokenAddress,
        abi: IERC20_default.abi,
        functionName: "approve",
        args: [spender, amount]
      });
      const hash = await this.client.walletClient.writeContract(request);
      await this.client.publicClient.waitForTransactionReceipt({ hash });
    }
  }
  async syncOrder(txHash) {
    try {
      await this.client.api.syncOrder(txHash, "private");
    } catch (err) {
      console.warn("Order sync warning:", err instanceof Error ? err.message : err);
    }
  }
  // -----------------------------------------------------------------------
  // Write methods
  // -----------------------------------------------------------------------
  /**
   * Creates a new private prediction market.
   * Fetches the ecosystem factory fee and attaches it.
   */
  async createMarket(marketName, symbol, endTime, optionNames, maintoken, privateEvent, frozen, bonding, seedAmount = 0n) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const ecoData = await this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "ecosystems",
      args: [maintoken]
    });
    const factoryAddress = ecoData.factory ?? ecoData[0];
    const feeAmount = await this.client.publicClient.readContract({
      address: factoryAddress,
      abi: ATokenFactory_default.abi,
      functionName: "feeAmount"
    });
    if (seedAmount > 0n) {
      await this.approveIfNeeded(this.client.usdbAddress, this.privateMarketAddress, seedAmount);
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "createMarket",
      args: [marketName, symbol, endTime, optionNames, maintoken, privateEvent, frozen, bonding, seedAmount],
      value: feeAmount
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Executes an AMM buy for a private market outcome.
   * Auto-approves the input token.
   */
  async buy(marketToken, outcomeId, inputToken, inputAmount, minUsdb, minShares) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(inputToken, this.privateMarketAddress, inputAmount);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "buy",
      args: [marketToken, outcomeId, inputToken, inputAmount, minUsdb, minShares]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Redeems winnings after a market resolves.
   */
  async redeem(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "redeem",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Creates a limit order on a private market.
   */
  async listOrder(marketToken, outcomeId, amount, pricePerShare) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "listOrder",
      args: [marketToken, outcomeId, amount, pricePerShare]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Cancels an active order on a private market.
   */
  async cancelOrder(marketToken, orderId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "cancelOrder",
      args: [marketToken, orderId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Fills a specific order on a private market.
   */
  async buyOrder(marketToken, orderId, fill) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "buyOrder",
      args: [marketToken, orderId, fill]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Sweeps multiple orders on a private market.
   */
  async buyMultipleOrders(marketToken, orderIds, usdbAmount) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "buyMultipleOrders",
      args: [marketToken, orderIds, usdbAmount]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Buys from order book and AMM in a single transaction.
   * Auto-approves the input token.
   */
  async buyOrdersAndContract(marketToken, outcomeId, orderIds, inputToken, totalInput, minShares) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    await this.approveIfNeeded(inputToken, this.privateMarketAddress, totalInput);
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "buyOrdersAndContract",
      args: [marketToken, outcomeId, orderIds, inputToken, totalInput, minShares]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    await this.syncOrder(hash);
    return { hash, receipt };
  }
  /**
   * Casts a vote on a private market outcome.
   */
  async vote(marketToken, outcomeId) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "vote",
      args: [marketToken, outcomeId]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Finalizes a private market after voting is complete.
   */
  async finalize(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "finalize",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Claims the bounty reward for voting correctly.
   */
  async claimBounty(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "claimBounty",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Manages voter status for a private market.
   */
  async manageVoter(marketToken, voter, status) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "manageVoter",
      args: [marketToken, voter, status]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Toggles whether specific addresses can buy in a private event market.
   */
  async togglePrivateEventBuyers(marketToken, buyers, status) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "togglePrivateEventBuyers",
      args: [marketToken, buyers, status]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Disables the freeze on a private market.
   */
  async disableFreeze(marketToken) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "DisableFreeze",
      args: [marketToken]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Manages the whitelist for a private market.
   */
  async manageWhitelist(marketToken, wallets, amount, tag, status) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required for write methods.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "manageWhitelist",
      args: [marketToken, wallets, amount, tag, status]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  // -----------------------------------------------------------------------
  // Read methods
  // -----------------------------------------------------------------------
  /**
   * Returns the MarketData struct for a private market.
   */
  async getMarketData(marketToken) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "getMarketData",
      args: [marketToken]
    });
  }
  /**
   * Returns the number of outcomes for a market.
   */
  async getNumOutcomes(marketToken) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "getNumOutcomes",
      args: [marketToken]
    });
  }
  /**
   * Returns the Outcome struct for a specific outcome.
   */
  async getOutcome(marketToken, outcomeId) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "outcomes",
      args: [marketToken, outcomeId]
    });
  }
  /**
   * Returns user shares for a specific outcome.
   */
  async getUserShares(marketToken, user, outcomeId) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "userShares",
      args: [marketToken, user, outcomeId]
    });
  }
  /**
   * Returns whether a user has bet on a market.
   */
  async hasBetted(marketToken, user) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "hasBetted",
      args: [marketToken, user]
    });
  }
  /**
   * Returns the bounty pool amount for a market.
   */
  async getBountyPool(marketToken) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "bountyPool",
      args: [marketToken]
    });
  }
  /**
   * Returns the cost to buy an order.
   */
  async getBuyOrderCost(marketToken, orderId, fill) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "getBuyOrderCost",
      args: [marketToken, orderId, fill]
    });
  }
  /**
   * Returns the amounts out when buying an order with a specific USDB amount.
   */
  async getBuyOrderAmountsOut(marketToken, orderId, usdbAmount) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "getBuyOrderAmountsOut",
      args: [marketToken, orderId, usdbAmount]
    });
  }
  /**
   * Returns an order by market and order ID.
   */
  async getMarketOrders(marketToken, orderId) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "marketOrders",
      args: [marketToken, orderId]
    });
  }
  /**
   * Returns the next order ID for a market.
   */
  async getNextOrderId(marketToken) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "nextOrderId",
      args: [marketToken]
    });
  }
  /**
   * Returns whether an address is a voter for a market.
   */
  async isMarketVoter(marketToken, voter) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "isMarketVoter",
      args: [marketToken, voter]
    });
  }
  /**
   * Returns the outcome a voter chose for a market.
   */
  async getVoterChoice(marketToken, voter) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "voterChoice",
      args: [marketToken, voter]
    });
  }
  /**
   * Returns the first vote time for a market.
   */
  async getFirstVoteTime(marketToken) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "firstVoteTime",
      args: [marketToken]
    });
  }
  /**
   * Returns whether a user can buy in a private event market.
   */
  async canUserBuy(marketToken, user) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "userCanBuyEvent",
      args: [marketToken, user]
    });
  }
  /**
   * Returns the bounty per correct vote for a market.
   */
  async getBountyPerVote(marketToken) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "bountyPerCorrectVote",
      args: [marketToken]
    });
  }
  /**
   * Returns whether a voter has claimed the bounty for a market.
   */
  async hasClaimed(marketToken, voter) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "bountyClaimed",
      args: [marketToken, voter]
    });
  }
  /**
   * Returns the initial reserves required for a given number of outcomes.
   */
  async getInitialReserves(numOutcomes) {
    return this.client.publicClient.readContract({
      address: this.privateMarketAddress,
      abi: APrivateTradingMarket_default.abi,
      functionName: "getInitialReserves",
      args: [numOutcomes]
    });
  }
};

// src/abis/AMarketReader.json
var AMarketReader_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "routerAddress",
          type: "address"
        },
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        },
        {
          internalType: "uint256[]",
          name: "orderIds",
          type: "uint256[]"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "estimateSharesOut",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "routerAddress",
          type: "address"
        },
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        }
      ],
      name: "getAllOutcomes",
      outputs: [
        {
          components: [
            {
              internalType: "uint8",
              name: "outcomeId",
              type: "uint8"
            },
            {
              internalType: "string",
              name: "name",
              type: "string"
            },
            {
              internalType: "uint256",
              name: "virtualReserve",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalCost",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "circulatingShares",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "pricePerShare",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "probability",
              type: "uint256"
            },
            {
              internalType: "bool",
              name: "hasWon",
              type: "bool"
            }
          ],
          internalType: "struct AMarketReader.OutcomeInfo[]",
          name: "infos",
          type: "tuple[]"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "routerAddress",
          type: "address"
        },
        {
          internalType: "address",
          name: "marketToken",
          type: "address"
        },
        {
          internalType: "uint8",
          name: "outcomeId",
          type: "uint8"
        },
        {
          internalType: "uint256",
          name: "sharesAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "estimatedUsdcToPool",
          type: "uint256"
        }
      ],
      name: "getPotentialPayout",
      outputs: [
        {
          internalType: "uint256",
          name: "holdPayout",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "simulatedAmmPayout",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/MarketReader.ts
var MarketReaderModule = class {
  client;
  readerAddress;
  constructor(client, readerAddress) {
    this.client = client;
    this.readerAddress = readerAddress;
  }
  /**
   * Returns outcome info for all outcomes in a market.
   */
  async getAllOutcomes(routerAddress, marketToken) {
    return this.client.publicClient.readContract({
      address: this.readerAddress,
      abi: AMarketReader_default.abi,
      functionName: "getAllOutcomes",
      args: [routerAddress, marketToken]
    });
  }
  /**
   * Estimates the number of shares received for a given USDB input,
   * considering both order book fills and AMM.
   */
  async estimateSharesOut(routerAddress, marketToken, outcomeId, usdbAmount, orderIds, user) {
    return this.client.publicClient.readContract({
      address: this.readerAddress,
      abi: AMarketReader_default.abi,
      functionName: "estimateSharesOut",
      args: [routerAddress, marketToken, outcomeId, usdbAmount, orderIds, user]
    });
  }
  /**
   * Returns potential payout for holding or selling shares.
   */
  async getPotentialPayout(routerAddress, marketToken, outcomeId, sharesAmount, estimatedUsdbToPool) {
    const result = await this.client.publicClient.readContract({
      address: this.readerAddress,
      abi: AMarketReader_default.abi,
      functionName: "getPotentialPayout",
      args: [routerAddress, marketToken, outcomeId, sharesAmount, estimatedUsdbToPool]
    });
    return {
      holdPayout: result[0],
      simulatedAmmPayout: result[1]
    };
  }
};

// src/abis/ALEVERAGE.json
var ALEVERAGE_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "taxes",
          type: "address"
        },
        {
          internalType: "address",
          name: "maintoken",
          type: "address"
        },
        {
          internalType: "address",
          name: "_usdc",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "x",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "y",
          type: "uint256"
        }
      ],
      name: "PRBMath_MulDiv18_Overflow",
      type: "error"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "x",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "y",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "denominator",
          type: "uint256"
        }
      ],
      name: "PRBMath_MulDiv_Overflow",
      type: "error"
    },
    {
      inputs: [
        {
          internalType: "UD60x18",
          name: "x",
          type: "uint256"
        }
      ],
      name: "PRBMath_UD60x18_Exp2_InputTooBig",
      type: "error"
    },
    {
      inputs: [
        {
          internalType: "UD60x18",
          name: "x",
          type: "uint256"
        }
      ],
      name: "PRBMath_UD60x18_Log_InputTooSmall",
      type: "error"
    },
    {
      inputs: [],
      name: "PRICEMULTIPLIER",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "newTaxes",
          type: "address"
        }
      ],
      name: "SetTaxWallet",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "USDCMULTIPLIER",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hybridMultiplier",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "baseReserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve1",
          type: "uint256"
        }
      ],
      name: "calculateFloor",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "hybridMultiplier",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "baseReserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve1",
          type: "uint256"
        }
      ],
      name: "calculateFloor2",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        }
      ],
      name: "calculateTokensForBuy",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "pure",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amountIn",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "multiplier",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "inputreserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "inputreserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "splitter",
          type: "uint256"
        }
      ],
      name: "calculateTokensToBurn",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "pure",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        }
      ],
      name: "getColleteralValue",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "tokenAmount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "multiplier",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "basereserve0",
          type: "uint256"
        }
      ],
      name: "getColleteralValueHybrid",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        }
      ],
      name: "getTokenPrice",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve1",
          type: "uint256"
        }
      ],
      name: "getUSDPrice",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "tokenToRescue",
          type: "address"
        }
      ],
      name: "rescueAnyToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [],
      name: "rescueEth",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "addr",
          type: "address"
        }
      ],
      name: "setMainToken",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        }
      ],
      name: "simulateDex",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "dexTax",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve0Added",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve1Added",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "boughtTokens",
              type: "uint256"
            }
          ],
          internalType: "struct ALEVERAGE.DexResult",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "multiplier",
          type: "uint256"
        }
      ],
      name: "simulateDexFactory",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "dexTax",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve0Added",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve1Added",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "boughtTokens",
              type: "uint256"
            }
          ],
          internalType: "struct ALEVERAGE.DexResult",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "pure",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        }
      ],
      name: "simulateLeverage",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "newXeReserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "newXeReserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "newReserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "newReserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalRepay",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalBorrowed",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalColleteral",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalFees",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "realLiquidity",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "xeAdded",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "usdcAdded",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "tokenAdded",
              type: "uint256"
            }
          ],
          internalType: "struct ALEVERAGE.EndResult",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "_amount",
          type: "uint256"
        },
        {
          internalType: "address[]",
          name: "path",
          type: "address[]"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        }
      ],
      name: "simulateLeverageFactory",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "newXeReserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "newXeReserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "newReserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "newReserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalRepay",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalBorrowed",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalColleteral",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalFees",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "realLiquidity",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "xeAdded",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "usdcAdded",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "tokenAdded",
              type: "uint256"
            }
          ],
          internalType: "struct ALEVERAGE.EndResult",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "boughtTokens",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        }
      ],
      name: "simulateLoan",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "colleteralValue",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalFee",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "borrowedAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "xereserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "xereserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "lpFee",
              type: "uint256"
            }
          ],
          internalType: "struct ALEVERAGE.LoanResult",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "boughtTokens",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "reserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "xereserve1",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "multiplier",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "basereserve0",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "numberOfDays",
          type: "uint256"
        }
      ],
      name: "simulateLoanHybrid",
      outputs: [
        {
          components: [
            {
              internalType: "uint256",
              name: "colleteralValue",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "totalFee",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "borrowedAmount",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "reserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "xereserve0",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "xereserve1",
              type: "uint256"
            },
            {
              internalType: "uint256",
              name: "lpFee",
              type: "uint256"
            }
          ],
          internalType: "struct ALEVERAGE.LoanResult",
          name: "",
          type: "tuple"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/LeverageSimulator.ts
var LeverageSimulatorModule = class {
  client;
  leverageAddress;
  constructor(client, leverageAddress) {
    this.client = client;
    this.leverageAddress = leverageAddress;
  }
  /**
   * Simulates a leveraged buy and returns the EndResult struct.
   */
  async simulateLeverage(amount, path, numberOfDays) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "simulateLeverage",
      args: [amount, path, numberOfDays]
    });
  }
  /**
   * Simulates a leveraged buy via factory and returns the EndResult struct.
   */
  async simulateLeverageFactory(amount, path, numberOfDays) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "simulateLeverageFactory",
      args: [amount, path, numberOfDays]
    });
  }
  /**
   * Calculates the floor price for a hybrid token.
   */
  async calculateFloor(hybridMultiplier, reserve0, reserve1, baseReserve0, xereserve0, xereserve1) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "calculateFloor",
      args: [hybridMultiplier, reserve0, reserve1, baseReserve0, xereserve0, xereserve1]
    });
  }
  /**
   * Returns the token price given reserves.
   */
  async getTokenPrice(reserve0, reserve1) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "getTokenPrice",
      args: [reserve0, reserve1]
    });
  }
  /**
   * Returns the USD price of a token given reserves.
   */
  async getUSDPrice(reserve0, reserve1, xereserve0, xereserve1) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "getUSDPrice",
      args: [reserve0, reserve1, xereserve0, xereserve1]
    });
  }
  /**
   * Returns the collateral value in USDB for a given token amount.
   */
  async getCollateralValue(tokenAmount, reserve0, reserve1) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "getColleteralValue",
      args: [tokenAmount, reserve0, reserve1]
    });
  }
  /**
   * Returns the collateral value for a hybrid token.
   */
  async getCollateralValueHybrid(tokenAmount, reserve0, reserve1, xereserve0, xereserve1, multiplier, basereserve0) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "getColleteralValueHybrid",
      args: [tokenAmount, reserve0, reserve1, xereserve0, xereserve1, multiplier, basereserve0]
    });
  }
  /**
   * Calculates how many tokens can be purchased for a given USDB amount.
   */
  async calculateTokensForBuy(usdbAmount, reserve0, reserve1) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "calculateTokensForBuy",
      args: [usdbAmount, reserve0, reserve1]
    });
  }
  /**
   * Calculates the number of tokens to burn for a given input.
   */
  async calculateTokensToBurn(amountIn, multiplier, inputreserve0, inputreserve1, splitter) {
    return this.client.publicClient.readContract({
      address: this.leverageAddress,
      abi: ALEVERAGE_default.abi,
      functionName: "calculateTokensToBurn",
      args: [amountIn, multiplier, inputreserve0, inputreserve1, splitter]
    });
  }
};

// src/abis/ATaxes.json
var ATaxes_default = {
  abi: [
    {
      inputs: [
        {
          internalType: "address",
          name: "mainToken",
          type: "address"
        },
        {
          internalType: "address",
          name: "staking",
          type: "address"
        },
        {
          internalType: "address",
          name: "_usdc",
          type: "address"
        }
      ],
      stateMutability: "nonpayable",
      type: "constructor"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          indexed: true,
          internalType: "address",
          name: "recipient",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "amount",
          type: "uint256"
        }
      ],
      name: "DevTaxDistributed",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "refundSeconds",
          type: "uint256"
        }
      ],
      name: "SurgeEnded",
      type: "event"
    },
    {
      anonymous: false,
      inputs: [
        {
          indexed: true,
          internalType: "address",
          name: "token",
          type: "address"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "startRate",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "endRate",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "duration",
          type: "uint256"
        },
        {
          indexed: false,
          internalType: "uint256",
          name: "startTime",
          type: "uint256"
        }
      ],
      name: "SurgeStarted",
      type: "event"
    },
    {
      inputs: [],
      name: "CEO",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "_taxRateDefault",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "_taxRatePrediction",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "_taxRateStable",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "_taxRateStasis",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        },
        {
          internalType: "address",
          name: "wallet",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "basisPoints",
          type: "uint256"
        }
      ],
      name: "addDevShare",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "availableSurgeQuota",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "devBasisPoints",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "devRate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "devTotalAllocated",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "devTotalEarnings",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "devWallets",
      outputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "usdcAmount",
          type: "uint256"
        },
        {
          internalType: "contract IERC20",
          name: "originalToken",
          type: "address"
        }
      ],
      name: "distributeTax",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "endSurgeTax",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "getCurrentSurgeTax",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        },
        {
          internalType: "address",
          name: "user",
          type: "address"
        }
      ],
      name: "getTaxRate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "injectRate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isPrediction",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isSurgeActive",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "isWhitelisted",
      outputs: [
        {
          internalType: "bool",
          name: "",
          type: "bool"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [],
      name: "presaleRate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "contract IERC20",
          name: "token",
          type: "address"
        },
        {
          internalType: "address",
          name: "wallet",
          type: "address"
        }
      ],
      name: "removeDevShare",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "_mainToken",
          type: "address"
        }
      ],
      name: "setMain",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "prediction",
          type: "address"
        }
      ],
      name: "setPrediction",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "_staking",
          type: "address"
        }
      ],
      name: "setStaking",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "buyback",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "presalers",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "dev",
          type: "uint256"
        }
      ],
      name: "setTaxRates",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newTaxRate",
          type: "uint256"
        }
      ],
      name: "setTaxesDefault",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newTaxRate",
          type: "uint256"
        }
      ],
      name: "setTaxesStable",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "newTaxRate",
          type: "uint256"
        }
      ],
      name: "setTaxesStasis",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "user",
          type: "address"
        },
        {
          internalType: "bool",
          name: "value",
          type: "bool"
        }
      ],
      name: "setWhitelistStatus",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "uint256",
          name: "startRate",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "endRate",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "duration",
          type: "uint256"
        },
        {
          internalType: "address",
          name: "token",
          type: "address"
        }
      ],
      name: "startSurgeTax",
      outputs: [],
      stateMutability: "nonpayable",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "surgeDuration",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "surgeEndRate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      name: "surgeHistory",
      outputs: [
        {
          internalType: "uint256",
          name: "start",
          type: "uint256"
        },
        {
          internalType: "uint256",
          name: "dur",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "surgeStartRate",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "surgeStartTime",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        },
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "tokenDevEarnings",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    },
    {
      inputs: [
        {
          internalType: "address",
          name: "",
          type: "address"
        }
      ],
      name: "totalDevTaxCollected",
      outputs: [
        {
          internalType: "uint256",
          name: "",
          type: "uint256"
        }
      ],
      stateMutability: "view",
      type: "function"
    }
  ]
};

// src/modules/Taxes.ts
var TaxesModule = class {
  client;
  taxesAddress;
  constructor(client, taxesAddress) {
    this.client = client;
    this.taxesAddress = taxesAddress;
  }
  /**
   * Returns the effective tax rate (in basis points) for a specific token and user.
   */
  async getTaxRate(token, user) {
    return this.client.publicClient.readContract({
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "getTaxRate",
      args: [token, user]
    });
  }
  /**
   * Returns the current surge tax rate (in basis points) for a token.
   */
  async getCurrentSurgeTax(token) {
    return this.client.publicClient.readContract({
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "getCurrentSurgeTax",
      args: [token]
    });
  }
  /**
   * Returns the available surge quota for a token.
   */
  async getAvailableSurgeQuota(token) {
    return this.client.publicClient.readContract({
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "availableSurgeQuota",
      args: [token]
    });
  }
  /**
   * Returns all four base tax rates.
   */
  async getBaseTaxRates() {
    const [stasis, stable, defaultRate, prediction] = await Promise.all([
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxes_default.abi,
        functionName: "_taxRateStasis"
      }),
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxes_default.abi,
        functionName: "_taxRateStable"
      }),
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxes_default.abi,
        functionName: "_taxRateDefault"
      }),
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxes_default.abi,
        functionName: "_taxRatePrediction"
      })
    ]);
    return { stasis, stable, default: defaultRate, prediction };
  }
  /**
   * Start a decaying surge tax on a factory token. Only callable by the token's DEV.
   */
  async startSurgeTax(startRate, endRate, duration, token) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "startSurgeTax",
      args: [startRate, endRate, duration, token]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * End an active surge tax early. Only callable by the token's DEV.
   */
  async endSurgeTax(token) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "endSurgeTax",
      args: [token]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Add a developer revenue share wallet for a token. Only callable by the token's DEV.
   */
  async addDevShare(token, wallet, basisPoints) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "addDevShare",
      args: [token, wallet, basisPoints]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
  /**
   * Remove a developer revenue share wallet. Only callable by the token's DEV.
   */
  async removeDevShare(token, wallet) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Stateful initialization (walletClient) is required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.taxesAddress,
      abi: ATaxes_default.abi,
      functionName: "removeDevShare",
      args: [token, wallet]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
};

// src/modules/AgentIdentity.ts
var import_viem4 = require("viem");
var IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432";
var identityRegistryAbi = [
  { "inputs": [{ "name": "agentURI", "type": "string" }], "name": "register", "outputs": [{ "name": "agentId", "type": "uint256" }], "stateMutability": "nonpayable", "type": "function" },
  { "inputs": [], "name": "register", "outputs": [{ "name": "agentId", "type": "uint256" }], "stateMutability": "nonpayable", "type": "function" },
  { "inputs": [{ "name": "owner", "type": "address" }], "name": "balanceOf", "outputs": [{ "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" },
  { "inputs": [{ "name": "tokenId", "type": "uint256" }], "name": "ownerOf", "outputs": [{ "name": "", "type": "address" }], "stateMutability": "view", "type": "function" },
  { "inputs": [{ "name": "agentId", "type": "uint256" }], "name": "getAgentWallet", "outputs": [{ "name": "", "type": "address" }], "stateMutability": "view", "type": "function" },
  { "inputs": [{ "name": "agentId", "type": "uint256" }, { "name": "metadataKey", "type": "string" }], "name": "getMetadata", "outputs": [{ "name": "", "type": "bytes" }], "stateMutability": "view", "type": "function" },
  { "inputs": [{ "name": "agentId", "type": "uint256" }, { "name": "metadataKey", "type": "string" }, { "name": "metadataValue", "type": "bytes" }], "name": "setMetadata", "outputs": [], "stateMutability": "nonpayable", "type": "function" },
  { "inputs": [{ "name": "agentId", "type": "uint256" }, { "name": "newURI", "type": "string" }], "name": "setAgentURI", "outputs": [], "stateMutability": "nonpayable", "type": "function" },
  { "inputs": [{ "name": "spender", "type": "address" }, { "name": "agentId", "type": "uint256" }], "name": "isAuthorizedOrOwner", "outputs": [{ "name": "", "type": "bool" }], "stateMutability": "view", "type": "function" },
  { "inputs": [{ "name": "agentId", "type": "uint256" }], "name": "tokenURI", "outputs": [{ "name": "", "type": "string" }], "stateMutability": "view", "type": "function" },
  { "anonymous": false, "inputs": [{ "indexed": true, "name": "agentId", "type": "uint256" }, { "indexed": false, "name": "agentURI", "type": "string" }, { "indexed": true, "name": "owner", "type": "address" }], "name": "Registered", "type": "event" }
];
var AgentIdentityModule = class {
  client;
  registryAddress;
  constructor(client) {
    this.client = client;
    this.registryAddress = IDENTITY_REGISTRY;
  }
  /**
   * Build the on-chain metadata JSON for an agent.
   */
  buildMetadataUri(wallet, config) {
    const metadata = {
      type: "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
      name: config?.name || "Basis Agent",
      description: config?.description || null,
      image: config?.image || null,
      website: "https://launchonbasis.com",
      profile: `https://launchonbasis.com/profile/${wallet}`,
      protocol: "basis",
      active: true,
      capabilities: config?.capabilities || ["trading"],
      supportedTrust: ["reputation"]
    };
    const json = JSON.stringify(metadata);
    const base64 = Buffer.from(json).toString("base64");
    return `data:application/json;base64,${base64}`;
  }
  /**
   * Check if a wallet has registered an agent on the Identity Registry.
   */
  async isRegistered(wallet) {
    const balance = await this.client.publicClient.readContract({
      address: this.registryAddress,
      abi: identityRegistryAbi,
      functionName: "balanceOf",
      args: [wallet]
    });
    return balance > 0n;
  }
  /**
   * Register the current wallet as an ERC-8004 agent.
   * Returns the agentId.
   *
   * If already registered on-chain, returns null (check via isRegistered first).
   */
  async register(config) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet required to register as agent.");
    }
    const account = this.client.walletClient.account;
    const uri = this.buildMetadataUri(account.address, config);
    const { request } = await this.client.publicClient.simulateContract({
      account,
      address: this.registryAddress,
      abi: identityRegistryAbi,
      functionName: "register",
      args: [uri]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    let agentId = 0n;
    for (const log of receipt.logs) {
      if (log.address.toLowerCase() === this.registryAddress.toLowerCase()) {
        try {
          const decoded = (0, import_viem4.decodeEventLog)({
            abi: identityRegistryAbi,
            data: log.data,
            topics: log.topics
          });
          if (decoded.eventName === "Registered") {
            agentId = decoded.args.agentId;
            break;
          }
        } catch {
        }
      }
    }
    return { hash, agentId };
  }
  /**
   * Full registration flow:
   * 1. Check if already registered on-chain
   * 2. If not, register on-chain
   * 3. Save to backend API
   *
   * Returns the agentId.
   */
  async registerAndSync(config) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet required to register as agent.");
    }
    const address = this.client.walletClient.account.address;
    const alreadyRegistered = await this.isRegistered(address);
    let agentId;
    if (alreadyRegistered) {
      try {
        const apiAgent = await this.lookupFromApi(address);
        if (apiAgent && apiAgent.isAgent) {
          return BigInt(apiAgent.agent.agentId);
        }
      } catch {
      }
      return 0n;
    }
    const result = await this.register(config);
    agentId = result.agentId;
    try {
      await this.syncToApi(address, agentId, config);
    } catch (err) {
      console.warn("Agent API sync warning:", err instanceof Error ? err.message : err);
    }
    return agentId;
  }
  /**
   * Sync agent registration to the backend API.
   */
  async syncToApi(wallet, agentId, config) {
    const cookie = this.client.sessionCookie;
    if (!cookie) return;
    const body = JSON.stringify({
      wallet,
      agentId: Number(agentId),
      name: config?.name || "Basis Agent",
      description: config?.description || null
    });
    const res = await fetch(`${this.client.apiDomain}/api/agents`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: cookie
      },
      body
    });
    if (!res.ok) {
      const errBody = await res.text().catch(() => "");
      throw new Error(`Agent sync failed [${res.status}]: ${errBody}`);
    }
  }
  /**
   * Look up an agent by wallet address via the API.
   */
  async lookupFromApi(wallet) {
    try {
      const res = await fetch(`${this.client.apiDomain}/api/agents/${wallet}`);
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  }
  /**
   * List all registered agents via the API.
   */
  async listAgents(page = 1, limit = 20) {
    const res = await fetch(`${this.client.apiDomain}/api/agents?page=${page}&limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to list agents: ${res.status}`);
    return res.json();
  }
  /**
   * Get the tokenURI for a registered agent (on-chain).
   */
  async getAgentURI(agentId) {
    return this.client.publicClient.readContract({
      address: this.registryAddress,
      abi: identityRegistryAbi,
      functionName: "tokenURI",
      args: [agentId]
    });
  }
  /**
   * Get the wallet linked to an agent ID (on-chain).
   */
  async getAgentWallet(agentId) {
    return this.client.publicClient.readContract({
      address: this.registryAddress,
      abi: identityRegistryAbi,
      functionName: "getAgentWallet",
      args: [agentId]
    });
  }
  /**
   * Get metadata for an agent by key (on-chain).
   */
  async getMetadata(agentId, key) {
    return this.client.publicClient.readContract({
      address: this.registryAddress,
      abi: identityRegistryAbi,
      functionName: "getMetadata",
      args: [agentId, key]
    });
  }
  /**
   * Update the agent's URI (on-chain). Must be the owner.
   */
  async setAgentURI(agentId, newURI) {
    if (!this.client.walletClient || !this.client.walletClient.account) {
      throw new Error("Wallet required.");
    }
    const { request } = await this.client.publicClient.simulateContract({
      account: this.client.walletClient.account,
      address: this.registryAddress,
      abi: identityRegistryAbi,
      functionName: "setAgentURI",
      args: [agentId, newURI]
    });
    const hash = await this.client.walletClient.writeContract(request);
    const receipt = await this.client.publicClient.waitForTransactionReceipt({ hash });
    return { hash, receipt };
  }
};

// src/BasisClient.ts
var BasisClient = class _BasisClient {
  publicClient;
  walletClient;
  apiDomain;
  usdbAddress;
  mainTokenAddress;
  // API wrapper
  api;
  // Modules
  factory;
  trading;
  predictionMarkets;
  orderBook;
  loans;
  vesting;
  staking;
  resolver;
  privateMarkets;
  marketReader;
  leverageSimulator;
  taxes;
  agent;
  // Auth state
  _sessionCookie = null;
  _apiKey = null;
  /** Session cookie for authenticated API requests. */
  get sessionCookie() {
    return this._sessionCookie;
  }
  /** API key for v1 data endpoints. */
  get apiKey() {
    return this._apiKey;
  }
  constructor(options = {}) {
    const rpcUrl = options.rpcUrl || "https://bsc-dataseed.binance.org/";
    this.apiDomain = options.apiDomain || "https://launchonbasis.com";
    this.publicClient = (0, import_viem5.createPublicClient)({
      chain: import_chains.bsc,
      transport: (0, import_viem5.http)(rpcUrl)
    });
    if (options.privateKey) {
      const account = (0, import_accounts.privateKeyToAccount)(options.privateKey);
      this.walletClient = (0, import_viem5.createWalletClient)({
        account,
        chain: import_chains.bsc,
        transport: (0, import_viem5.http)(rpcUrl)
      });
    }
    if (options.apiKey) {
      this._apiKey = options.apiKey;
    }
    const factoryAddr = options.factoryAddress || "0xd80850a3b712E6B9dB4d3e487c76b7c1F904E273";
    const swapAddr = options.swapAddress || "0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e";
    const marketTradingAddr = options.marketTradingAddress || "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6";
    const loanHubAddr = options.loanHubAddress || "0x504AeDa510D4cb5Fe6E29D000Dfc377f3f50cC30";
    const vestingAddr = options.vestingAddress || "0x82D1a54fd9671Cd4fE8774f0f85A0CB8A96dee3b";
    this.usdbAddress = options.usdbAddress || "0x217B82e4bAc4E4647B1F189F33554229Ce27c51A";
    this.mainTokenAddress = options.mainTokenAddress || "0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b";
    this.api = new BasisAPI(this);
    this.factory = new FactoryModule(this, factoryAddr);
    this.trading = new TradingModule(this, swapAddr);
    this.predictionMarkets = new PredictionMarketsModule(this, marketTradingAddr);
    this.orderBook = new OrderBookModule(this, marketTradingAddr);
    this.loans = new LoansModule(this, loanHubAddr);
    this.vesting = new VestingModule(this, vestingAddr);
    const stakingAddr = options.stakingAddress || "0x8E2C5267f2BA1A142A88a333C075E21719E330aC";
    this.staking = new StakingModule(this, stakingAddr);
    const resolverAddr = options.resolverAddress || "0x1AB2C2551429Bd4f9a5D8c781BEb5BC5497a42bd";
    this.resolver = new MarketResolverModule(this, resolverAddr);
    const privateMarketAddr = options.privateMarketAddress || "0x4eCDD0A082b3f523c31F61eC8bEfF69A8182C0aD";
    this.privateMarkets = new PrivateMarketsModule(this, privateMarketAddr);
    const readerAddr = options.readerAddress || "0xC8652aF90B1C2C9012ADe56B58EfA9572122d342";
    this.marketReader = new MarketReaderModule(this, readerAddr);
    const leverageAddr = options.leverageAddress || "0x0030d46D3ba98287e7D62482c14E4395FbF52904";
    this.leverageSimulator = new LeverageSimulatorModule(this, leverageAddr);
    const taxesAddr = options.taxesAddress || "0x3CE0381C6515b7771a6E47d99abf1e42054121CD";
    this.taxes = new TaxesModule(this, taxesAddr);
    this.agent = new AgentIdentityModule(this);
  }
  /**
   * Async factory method that creates a fully initialized BasisClient.
   *
   * - Validates custom RPC URL by checking chainId === 56 (BSC).
   * - If a privateKey is provided and no apiKey: authenticates via SIWE and auto-provisions an API key.
   * - If an apiKey is provided: stores it directly.
   */
  static async create(options = {}) {
    const client = new _BasisClient(options);
    if (options.rpcUrl) {
      try {
        const chainId = await client.publicClient.getChainId();
        if (chainId !== 56) {
          throw new Error(
            `RPC endpoint returned chainId ${chainId}, expected 56 (BSC Mainnet). Ensure your RPC URL points to BSC Mainnet.`
          );
        }
      } catch (err) {
        if (err.message && err.message.includes("chainId")) {
          throw err;
        }
        throw new Error(
          `Failed to validate RPC endpoint "${options.rpcUrl}": ${err.message || err}. Check that the URL is correct and the node is reachable.`
        );
      }
    }
    if (options.privateKey && !options.apiKey) {
      if (!client.walletClient?.account) {
        throw new Error("WalletClient was not initialized despite privateKey being provided.");
      }
      const address = client.walletClient.account.address;
      await client.authenticate(address);
      await client.ensureApiKey();
    }
    if (options.agent && options.privateKey) {
      const agentConfig = typeof options.agent === "object" ? options.agent : void 0;
      try {
        await client.agent.registerAndSync(agentConfig);
      } catch (err) {
        console.warn("Agent registration warning:", err instanceof Error ? err.message : err);
      }
    }
    return client;
  }
  /**
   * Authenticates with the Basis API using Sign-In with Ethereum (SIWE).
   *
   * 1. Fetches a nonce from the server
   * 2. Constructs and signs a SIWE message
   * 3. Submits the signed message for verification
   * 4. Stores the session cookie for subsequent authenticated requests
   */
  async authenticate(address) {
    if (!this.walletClient) {
      throw new Error("WalletClient must be initialized to authenticate. Provide a privateKey.");
    }
    const nonceRes = await fetch(
      `${this.apiDomain}/api/auth/nonce?address=${address}`
    );
    if (!nonceRes.ok) {
      throw new Error(`Failed to fetch nonce: ${nonceRes.status} ${nonceRes.statusText}`);
    }
    const nonceData = await nonceRes.json();
    const nonce = nonceData.nonce;
    const domain = new URL(this.apiDomain).host;
    const message = new import_siwe.SiweMessage({
      domain,
      address,
      statement: "Sign in to Basis API.",
      uri: this.apiDomain,
      version: "1",
      chainId: 56,
      nonce
    });
    const preparedMessage = message.prepareMessage();
    const signature = await this.walletClient.signMessage({
      account: this.walletClient.account,
      message: preparedMessage
    });
    const verifyRes = await fetch(`${this.apiDomain}/api/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: preparedMessage, signature })
    });
    if (!verifyRes.ok) {
      const body = await verifyRes.text().catch(() => "");
      throw new Error(
        `SIWE verification failed: ${verifyRes.status} ${verifyRes.statusText}. ${body}`
      );
    }
    const setCookie = verifyRes.headers.get("set-cookie");
    if (setCookie) {
      this._sessionCookie = setCookie;
    }
  }
  /**
   * Ensures an API key exists for the authenticated session.
   * Fetches existing keys or creates one labeled "basis-sdk-auto".
   */
  async ensureApiKey() {
    if (!this._sessionCookie) {
      throw new Error("No session cookie. Call authenticate() first.");
    }
    const listRes = await fetch(`${this.apiDomain}/api/v1/auth/keys`, {
      headers: { Cookie: this._sessionCookie }
    });
    if (!listRes.ok) {
      throw new Error(`Failed to list API keys: ${listRes.status} ${listRes.statusText}`);
    }
    const listData = await listRes.json();
    if (listData.keys && listData.keys.length > 0 && listData.keys[0].key) {
      this._apiKey = listData.keys[0].key;
      return;
    }
    if (listData.keys && listData.keys.length > 0 && !listData.keys[0].key) {
      await fetch(`${this.apiDomain}/api/v1/auth/keys/${listData.keys[0].id}`, {
        method: "DELETE",
        headers: { Cookie: this._sessionCookie }
      });
    }
    const createRes = await fetch(`${this.apiDomain}/api/v1/auth/keys`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: this._sessionCookie
      },
      body: JSON.stringify({ label: "basis-sdk-auto" })
    });
    if (!createRes.ok) {
      const body = await createRes.text().catch(() => "");
      throw new Error(
        `Failed to create API key: ${createRes.status} ${createRes.statusText}. ${body}`
      );
    }
    const createData = await createRes.json();
    this._apiKey = createData.key;
  }
  /**
   * Returns the current session status.
   * Optionally checks for a specific address.
   */
  async getSession(address) {
    const params = address ? `?address=${address}` : "";
    const headers = {};
    if (this._sessionCookie) {
      headers["Cookie"] = this._sessionCookie;
    }
    const res = await fetch(`${this.apiDomain}/api/auth/me${params}`, { headers });
    if (!res.ok) {
      throw new Error(`Failed to get session: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }
  /**
   * Logs out the specified address, removing it from the session.
   */
  async logout(address) {
    if (!this._sessionCookie) {
      throw new Error("No session cookie. Not logged in.");
    }
    const res = await fetch(`${this.apiDomain}/api/auth/me?address=${address}`, {
      method: "DELETE",
      headers: { Cookie: this._sessionCookie }
    });
    if (!res.ok) {
      throw new Error(`Logout failed: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    this._sessionCookie = null;
    this._apiKey = null;
    return data;
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  AgentIdentityModule,
  BasisAPI,
  BasisClient,
  FactoryModule,
  LeverageSimulatorModule,
  LoansModule,
  MarketReaderModule,
  MarketResolverModule,
  OrderBookModule,
  PredictionMarketsModule,
  PrivateMarketsModule,
  StakingModule,
  TaxesModule,
  TradingModule,
  VestingModule
});
