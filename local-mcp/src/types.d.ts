declare module 'eventsource' {
  interface EventSourceInitDict {
    headers?: Record<string, string>;
    https?: any;
    rejectUnauthorized?: boolean;
  }

  class EventSource {
    constructor(url: string, eventSourceInitDict?: EventSourceInitDict);
    close(): void;
    onopen: (event: any) => void;
    onmessage: (event: any) => void;
    onerror: (event: any) => void;
  }

  export default EventSource;
} 