export type WebSocketTopic = 'jobs' | 'runtime.artifacts';
export type RealtimeStatus = 'connecting' | 'open' | 'closed' | 'error';

export interface TopicMessage<T = unknown> {
  topic: WebSocketTopic | 'connection';
  event: 'ready' | 'changed' | 'error';
  version?: string;
  payload: T;
}

type TopicHandler = (message: TopicMessage) => void;
type StatusHandler = (status: RealtimeStatus) => void;

class RealtimeClient {
  private socket: WebSocket | null = null;
  private socketTopics = '';
  private reconnectTimer = 0;
  private handlers = new Map<WebSocketTopic, Set<TopicHandler>>();
  private statusHandlers = new Set<StatusHandler>();
  private status: RealtimeStatus = 'closed';

  subscribe(topic: WebSocketTopic, handler: TopicHandler) {
    const handlers = this.handlers.get(topic) ?? new Set<TopicHandler>();
    handlers.add(handler);
    this.handlers.set(topic, handlers);
    if (this.socket && this.currentTopicKey() !== this.socketTopics) {
      this.reconnect();
      return () => this.unsubscribe(topic, handler);
    }
    this.ensureSocket();
    return () => this.unsubscribe(topic, handler);
  }

  onStatus(handler: StatusHandler) {
    this.statusHandlers.add(handler);
    handler(this.status);
    this.ensureSocket();
    return () => {
      this.statusHandlers.delete(handler);
    };
  }

  private ensureSocket() {
    if (this.socket || this.handlers.size === 0) {
      return;
    }
    this.setStatus('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.socketTopics = this.currentTopicKey();
    const topics = encodeURIComponent(this.socketTopics);
    this.socket = new WebSocket(`${protocol}//${window.location.host}/api/ws?topics=${topics}`);

    this.socket.onopen = () => this.setStatus('open');
    this.socket.onclose = () => {
      this.socket = null;
      this.setStatus('closed');
      if (this.handlers.size > 0) {
        window.clearTimeout(this.reconnectTimer);
        this.reconnectTimer = window.setTimeout(() => this.ensureSocket(), 2000);
      }
    };
    this.socket.onerror = () => this.setStatus('error');
    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data as string) as TopicMessage;
      if (message.topic === 'connection') {
        return;
      }
      this.handlers.get(message.topic)?.forEach((handler) => handler(message));
    };
  }

  private reconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    if (this.handlers.size > 0) {
      this.ensureSocket();
    } else {
      this.setStatus('closed');
    }
  }

  private unsubscribe(topic: WebSocketTopic, handler: TopicHandler) {
    const handlers = this.handlers.get(topic);
    handlers?.delete(handler);
    if (handlers?.size === 0) {
      this.handlers.delete(topic);
      this.reconnect();
    }
  }

  private currentTopicKey() {
    return [...this.handlers.keys()].sort().join(',');
  }

  private setStatus(status: RealtimeStatus) {
    this.status = status;
    this.statusHandlers.forEach((handler) => handler(status));
  }
}

export const realtimeClient = new RealtimeClient();
