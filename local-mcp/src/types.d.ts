declare module "eventsource" {
    export default class EventSource {
        constructor(url: string, eventSourceInitDict?: any);
        
        static CONNECTING: number;
        static OPEN: number;
        static CLOSED: number;
        
        readonly CONNECTING: number;
        readonly OPEN: number;
        readonly CLOSED: number;
        readonly url: string;
        readonly readyState: number;
        readonly withCredentials: boolean;
        
        onopen: (evt: any) => void;
        onmessage: (evt: any) => void;
        onerror: (evt: any) => void;
        
        addEventListener(type: string, listener: (evt: any) => void): void;
        removeEventListener(type: string, listener: (evt: any) => void): void;
        dispatchEvent(evt: any): boolean;
        close(): void;
    }
} 