import { useEffect, useState } from 'react';
import { realtimeClient, type RealtimeStatus, type TopicMessage, type WebSocketTopic } from '../services/realtime-client';

export function useRealtimeStatus() {
  const [status, setStatus] = useState<RealtimeStatus>('closed');

  useEffect(() => realtimeClient.onStatus(setStatus), []);

  return status;
}

export function useRealtimeTopic<T>(
  topic: WebSocketTopic,
  handler: (message: TopicMessage<T>) => void,
) {
  useEffect(
    () => realtimeClient.subscribe(topic, handler as (message: TopicMessage) => void),
    [handler, topic],
  );
}
