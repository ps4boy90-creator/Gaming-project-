type Handler<T> = (payload: T) => void;

/** Tiny pub/sub so systems can react to each other without direct references. */
export class EventBus {
  private map = new Map<string, Set<Handler<any>>>();

  on<T = unknown>(event: string, handler: Handler<T>): () => void {
    let set = this.map.get(event);
    if (!set) {
      set = new Set();
      this.map.set(event, set);
    }
    set.add(handler);
    return () => set!.delete(handler);
  }

  emit<T = unknown>(event: string, payload?: T): void {
    this.map.get(event)?.forEach((h) => h(payload));
  }
}

export const bus = new EventBus();
