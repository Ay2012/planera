import { promptSuggestions } from "@/lib/constants";

interface PromptChipsProps {
  onPick: (prompt: string) => void;
}

export function PromptChips({ onPick }: PromptChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {promptSuggestions.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onPick(prompt)}
          className="rounded-full border border-line bg-panel px-4 py-2 text-sm text-muted transition hover:border-ink/10 hover:text-ink"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
