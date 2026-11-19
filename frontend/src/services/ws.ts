"Centralized WebSocket client for the PIMS market feed (websocket-spec §4–§7).";

export type ConnectionState =
  | "CONNECTING"
  | "CONNECTED"
  | "READY"
  | "RECONNECTING"
  | "DISCONNECTED"
  | "ERROR";

export interface WsMessage {
  protocol_version: string;
  event: string;
  event_id: string;
  timestamp: string;
  data: { [key: string]: unknown };
}

export type SubscribeParams = { symbol?: string; asset_id?: string; timeframe?: string };
type MessageCallback = (msg: WsMessage) => void;
type StatusCallback = (status: ConnectionState) => void;

interface Subscription {
  channel: string;
  params: SubscribeParams;
  callback: MessageCallback;
  subscriptionId?: string;
}

const WS_PATH = "/api/v1/ws/market";
const PING_INTERVAL_MS = 25000;
const MAX_BACKOFF_MS = 30000;

function resolveUrl(): string {
  if (process.env.NEXT_PUBLIC_PIMS_WS_URL) return process.env.NEXT_PUBLIC_PIMS_WS_URL;
  if (typeof window === "undefined") return `ws://localhost:8000${WS_PATH}`;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
  return `${proto}//${host}${WS_PATH}`;
}

function requestId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/**
 * One connection per tab, shared by every component. Reconnects with
 * exponential backoff + jitter (§16.1) and restores active subscriptions.
 */
class MarketWebSocketClient {
  private socket: WebSocket | null = null;
  private status: ConnectionState = "DISCONNECTED";
  private readonly statusListeners = new Set<StatusCallback>();
  private readonly subscriptions = new Map<string, Subscription>();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private closedByUser = false;

  getStatus(): ConnectionState {
    return this.status;
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  private setStatus(next: ConnectionState): void {
    if (this.status === next) return;
    this.status = next;
    for (const listener of this.statusListeners) {
      try {
        listener(next);
      } catch {
        // a broken listener must not break the connection
      }
    }
  }

  connect(): void {
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    this.closedByUser = false;
    this.setStatus("CONNECTING");

    let socket: WebSocket;
    try {
      socket = new WebSocket(resolveUrl());
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus("CONNECTED");
      if (this.pingTimer) clearInterval(this.pingTimer);
      this.pingTimer = setInterval(() => {
        this.send({ action: "ping", request_id: requestId() });
      }, PING_INTERVAL_MS);
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      let message: WsMessage;
      try {
        message = JSON.parse(event.data) as WsMessage;
      } catch {
        return;
      }

      if (message.event === "connection.accepted") {
        this.setStatus("READY");
        for (const [key, subscription] of this.subscriptions) {
          this.sendSubscribe(key, subscription);
        }
        return;
      }

      if (message.event === "subscription.confirmed") {
        const confirmedFor = message.data.request_id;
        const subscription = this.subscriptions.get(String(confirmedFor));
        if (subscription) subscription.subscriptionId = String(message.data.subscription_id);
        return;
      }

      for (const subscription of this.subscriptions.values()) {
        if (subscription.channel !== message.event) continue;
        const symbol = message.data.symbol;
        if (subscription.params.symbol && symbol !== subscription.params.symbol) continue;
        try {
          subscription.callback(message);
        } catch {
          // subscriber errors stay local
        }
      }
    };

    socket.onerror = () => this.setStatus("ERROR");

    socket.onclose = () => {
      if (this.pingTimer) clearInterval(this.pingTimer);
      if (this.closedByUser) {
        this.setStatus("DISCONNECTED");
      } else {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    this.setStatus("RECONNECTING");
    const backoff = Math.min(1000 * 2 ** this.reconnectAttempts, MAX_BACKOFF_MS);
    const delay = backoff + Math.random() * 1000;
    this.reconnectAttempts += 1;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private send(payload: Record<string, unknown>): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  private sendSubscribe(key: string, subscription: Subscription): void {
    this.send({
      action: "subscribe",
      request_id: key,
      channel: subscription.channel,
      params: subscription.params,
    });
  }

  /** Returns a function that unsubscribes on the server and forgets the listener. */
  subscribe(channel: string, params: SubscribeParams, callback: MessageCallback): () => void {
    const key = requestId();
    this.subscriptions.set(key, { channel, params, callback });

    if (this.status === "READY") {
      this.sendSubscribe(key, this.subscriptions.get(key) as Subscription);
    } else if (this.status === "DISCONNECTED" || this.status === "ERROR") {
      this.connect();
    }

    return () => {
      const subscription = this.subscriptions.get(key);
      if (subscription?.subscriptionId) {
        this.send({
          action: "unsubscribe",
          request_id: requestId(),
          subscription_id: subscription.subscriptionId,
        });
      }
      this.subscriptions.delete(key);
    };
  }

  /** Manual reconnect, used by the DISCONNECTED banner on the instrument page. */
  reconnect(): void {
    this.closedByUser = false;
    this.reconnectAttempts = 0;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const previous = this.socket;
    this.socket = null;
    if (previous) {
      try {
        previous.close();
      } catch {
        // already closed
      }
    }
    this.connect();
  }

  disconnect(): void {
    this.closedByUser = true;
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.socket) {
      try {
        this.socket.close();
      } catch {
        // already closed
      }
    }
    this.socket = null;
    this.setStatus("DISCONNECTED");
  }
}

export const marketWs = new MarketWebSocketClient();
