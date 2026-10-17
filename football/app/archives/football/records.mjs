export function seasonYear(date) {
  const parsed = new Date(date);
  return parsed.getUTCFullYear() - (parsed.getUTCMonth() < 6 ? 1 : 0);
}

export function validScoreboard(payload) {
  return Array.isArray(payload?.events) && Array.isArray(payload?.leagues) && payload.leagues.length > 0;
}

export function mergeEvents(saved, incoming) {
  const events = new Map(saved.map((event) => [String(event.id), event]));
  for (const event of incoming) {
    if (!event?.id || !Number.isFinite(Date.parse(event.date))) continue;
    const previous = events.get(String(event.id));
    if (previous?.officialDecision) continue;
    // A delayed schedule response must never turn a finished match back into a fixture.
    if (previous?.status?.type?.state === "post" && event?.status?.type?.state === "pre") continue;
    const oldCompetition = previous?.competitions?.[0];
    const competition = event.competitions?.[0];
    if (!competition?.competitors?.some((team) => team.homeAway === "home") ||
        !competition.competitors.some((team) => team.homeAway === "away")) continue;
    const competitors = competition.competitors.map((team) => {
      const oldTeam = oldCompetition?.competitors?.find((item) => String(item.team?.id) === String(team.team?.id));
      return { ...team, statistics: team.statistics?.length ? team.statistics : oldTeam?.statistics ?? [] };
    });
    events.set(String(event.id), {
      ...previous, ...event,
      seasonYear: event.seasonYear ?? previous?.seasonYear ?? seasonYear(event.date),
      competitions: [{
        ...oldCompetition, ...competition, competitors,
        details: competition.details?.length ? competition.details : oldCompetition?.details ?? [],
      }],
    });
  }
  return [...events.values()].sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
}

export function ageOn(dateOfBirth, now = new Date()) {
  if (!dateOfBirth) return null;
  const born = new Date(dateOfBirth);
  if (!Number.isFinite(born.getTime())) return null;
  const [year, month, day] = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(now).split("-").map(Number);
  const age = year - born.getUTCFullYear() - Number(month < born.getUTCMonth() + 1 ||
    (month === born.getUTCMonth() + 1 && day < born.getUTCDate()));
  return age >= 0 && age < 100 ? age : null;
}
