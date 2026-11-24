export type BuiltinFlowtimeView = 'timeline' | 'combined' | 'feed';
export type FlowtimeView = BuiltinFlowtimeView | (string & {});

export interface TimelineEvent {
  id?: string | number;
  start: string | number | Date;
  end?: string | number | Date | null;
  title?: string;
  description?: string;
  group?: string;
  metadata?: Record<string, unknown>;
  source?: unknown;
}
export interface NormalizedEvent extends Omit<
  TimelineEvent,
  'id' | 'start' | 'end' | 'title' | 'description' | 'group'
> {
  id: string;
  start: number;
  end: number | null;
  title: string;
  description: string;
  group: string;
}
export interface Group {
  id: string;
  label: string;
  color?: string;
  icon?: string;
}
export interface DateRange {
  start?: string | number | Date | null;
  end?: string | number | Date | null;
}
export interface FlowtimeFilter {
  query?: string;
  groups?: string[];
  dateRange?: DateRange;
}
export interface FlowtimeActionContext {
  viewer: Flowtime;
  event: NormalizedEvent | null;
  events: NormalizedEvent[];
  visibleEvents: NormalizedEvent[];
  view: FlowtimeView;
  textScale: number;
  filter: {
    query: string;
    groups: string[];
    dateRange: { start: number | null; end: number | null };
  };
}
export interface FlowtimeEventActionContext extends FlowtimeActionContext {
  event: NormalizedEvent;
}
export interface FlowtimeAction<Context extends FlowtimeActionContext = FlowtimeActionContext> {
  id: string;
  label: string;
  icon?: string;
  title?: string;
  variant?: 'default' | 'primary' | 'danger';
  visible?: boolean | ((context: Context) => boolean);
  disabled?: boolean | ((context: Context) => boolean);
  onClick: (context: Context) => void | Promise<void>;
}
export interface FlowtimeActions {
  actions?: FlowtimeAction[];
  eventActions?: FlowtimeAction<FlowtimeEventActionContext>[];
}
export interface FlowtimeViewContext extends FlowtimeActionContext {
  container: HTMLElement;
  signal: AbortSignal;
}
export interface FlowtimeViewInstance {
  update?: (context: FlowtimeViewContext) => void | Promise<void>;
  destroy?: () => void | Promise<void>;
}
export type FlowtimeViewMountResult = void | (() => void | Promise<void>) | FlowtimeViewInstance;
export interface FlowtimeCustomView {
  id: string;
  label: string;
  icon?: string;
  filters?: boolean;
  inspector?: boolean;
  mount: (
    container: HTMLElement,
    context: FlowtimeViewContext,
  ) => FlowtimeViewMountResult | Promise<FlowtimeViewMountResult>;
}
export interface FlowtimeOptions extends FlowtimeActions {
  events?: TimelineEvent[];
  groups?: Group[];
  view?: FlowtimeView;
  customViews?: FlowtimeCustomView[];
  theme?: 'light' | 'dark';
  locale?: string;
  timeZone?: string;
  label?: string;
  animationDuration?: number;
  /** Timeline/combined text size multiplier from 0.5 to 1.5. Default: 1. */
  textScale?: number;
  /** Display the Text size selector in timeline views beside the time zoom controls. Default: true. */
  showTextScaleControl?: boolean;
  onSelect?: (event: NormalizedEvent) => void;
  onEdit?: (event: NormalizedEvent) => void | Promise<void>;
  onDelete?: (event: NormalizedEvent) => void | Promise<void>;
}
export class Flowtime {
  constructor(container: string | HTMLElement, options?: FlowtimeOptions);
  readonly root: HTMLElement;
  readonly view: FlowtimeView;
  readonly textScale: number;
  setEvents(events: TimelineEvent[]): void;
  setActions(actions?: FlowtimeActions): void;
  setView(view: FlowtimeView): void;
  setTextScale(scale: number): void;
  setFilter(filter?: FlowtimeFilter): void;
  setDateRange(dateRange?: DateRange): void;
  select(id: string | number, options?: { reveal?: boolean }): void;
  clearSelection(): void;
  fit(): void;
  zoom(factor: number): void;
  pan(fraction: number): void;
  getEvents(): NormalizedEvent[];
  destroy(): void;
}
export default Flowtime;

export function timestamp(value: unknown): number;
