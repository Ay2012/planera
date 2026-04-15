import { classNames } from "@/lib/classNames";

export interface TabDefinition<T extends string> {
  id: T;
  label: string;
}

interface TabsProps<T extends string> {
  tabs: TabDefinition<T>[];
  activeTab: T;
  onChange: (tab: T) => void;
}

export function Tabs<T extends string>({ tabs, activeTab, onChange }: TabsProps<T>) {
  return (
    <div className="inline-flex flex-wrap gap-2 rounded-full border border-line bg-surface p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={classNames(
            "rounded-full px-4 py-2 text-sm font-medium transition",
            activeTab === tab.id
              ? "bg-contrast text-contrast-foreground shadow-card"
              : "text-muted hover:bg-panel hover:text-ink",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
