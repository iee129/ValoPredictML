import type { Explanation } from "@/types/api";

export default function ReasonCard({
  winnerName,
  explanations,
}: {
  winnerName: string;
  explanations: Explanation[];
}) {
  if (!explanations || explanations.length === 0) return null;
  return (
    <div>
      <div className="text-xs font-bold text-muted mb-1">승부 근거</div>
      <div className="font-extrabold mb-1">{winnerName} 우세</div>
      <ul className="list-disc pl-4 flex flex-col gap-1 text-sm leading-snug">
        {explanations.map((e) => (
          <li key={e.feature}>{e.text}</li>
        ))}
      </ul>
    </div>
  );
}
