import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import { useApi } from "@hooks/useApi";

const MOCK_HISTORY = [
  {
    action_date: "2026-07-20T10:00:00Z",
    actor_name: "Jan Novák",
    action_description: "Změna stavu: APPLIED -> PRELIMINARY_APPROVED",
  },
  {
    action_date: "2026-07-18T14:30:00Z",
    actor_name: "Eva Svobodová",
    action_description: "Změna stavu: PENDING -> APPLIED",
  },
  {
    action_date: "2026-07-15T09:00:00Z",
    actor_name: "Systém",
    action_description: "Vytvoření přihlášky",
  },
];

function formatDate(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleDateString("cs-CZ", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Timeline({ studentPracticeId, currentStatus }) {
  const api = useApi();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchHistory = async () => {
      setLoading(true);
      try {
        // TODO: replace with real endpoint when backend is ready
        // const response = await api.get(`/student-practices/${studentPracticeId}/history/`);
        // if (!cancelled) setHistory(response.data?.results || response.data || []);
        if (!cancelled) setHistory(MOCK_HISTORY);
      } catch {
        if (!cancelled) setHistory(MOCK_HISTORY);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchHistory();
    return () => {
      cancelled = true;
    };
  }, [studentPracticeId, api]);

  if (loading) {
    return (
      <Container property="py-4">
        <Paragraph property="text-gray-500 text-sm">Načítání historie...</Paragraph>
      </Container>
    );
  }

  if (!history || history.length === 0) {
    return (
      <Container property="py-4">
        <Paragraph property="text-gray-500 text-sm">Historie změn není k dispozici.</Paragraph>
      </Container>
    );
  }

  return (
    <Container property="relative pl-4">
      {/* Vertikální čára */}
      <div className="absolute left-6 top-2 bottom-2 w-0.5 bg-gray-300" />

      <Container property="space-y-6">
        {history.map((item, index) => {
          const isLatest = index === 0;
          return (
            <Container key={index} property="relative flex items-start gap-4">
              {/* Bod na časové ose */}
              <div
                className={`relative z-10 mt-1.5 w-4 h-4 rounded-full border-2 shrink-0 ${
                  isLatest
                    ? "bg-blue-600 border-blue-600"
                    : "bg-white border-gray-400"
                }`}
              />

              {/* Obsah */}
              <Container property="flex-1 min-w-0">
                <Paragraph
                  property={`text-sm font-semibold ${
                    isLatest ? "text-blue-700" : "text-gray-700"
                  }`}
                >
                  {item.action_description}
                </Paragraph>
                <Paragraph property="text-xs text-gray-500 mt-0.5">
                  {formatDate(item.action_date)} • {item.actor_name}
                </Paragraph>
              </Container>
            </Container>
          );
        })}
      </Container>
    </Container>
  );
}
