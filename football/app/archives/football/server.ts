import type { InitialPayloads } from "./dashboard";
import { loadFootballSnapshot } from "./snapshot.mjs";
import { mergeEvents, validScoreboard } from "./records.mjs";


const LEAGUES = {
  laliga: "esp.1",
  premier: "eng.1",
  bundesliga: "ger.1",
  ligue1: "fra.1",
} as const;

const ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer";
const ESPN_V2 = "https://site.api.espn.com/apis/v2/sports/soccer";

function scoreYears() {
  const now = new Date();
  const year = now.getUTCFullYear();
  // ESPN accepts YYYY and YYYYMM; date ranges currently return HTTP 400.
  return now.getUTCMonth() >= 6 ? [year, year + 1] : [year];
}

async function fetchJson(url: string) {
  const response = await fetch(url, {
    signal: AbortSignal.timeout(8000),
    headers: {
      Accept: "application/json",
      "Accept-Language": "en-US,en;q=0.8",
      "User-Agent": "NoSpoilerFootball/2.0",
    },
  });

  if (!response.ok) {
    throw new Error(`data request failed: ${response.status}`);
  }

  return response.json();
}

function compactScoreboard(payload: any) {
  return {
    leagues: (payload?.leagues ?? []).slice(0, 1).map((league: any) => ({
      season: league?.season,
    })),
    events: (payload?.events ?? []).map((event: any) => {
      const competition = event?.competitions?.[0] ?? {};
      return {
        id: event?.id,
        date: event?.date,
        seasonYear: event?.season?.year,
        status: {
          type: {
            state: event?.status?.type?.state,
            name: event?.status?.type?.name,
            completed: event?.status?.type?.completed,
            shortDetail: event?.status?.type?.shortDetail,
            description: event?.status?.type?.description,
          },
        },
        venue: event?.venue,
        competitions: [{
          venue: competition?.venue,
          timeValid: competition?.timeValid,
          competitors: (competition?.competitors ?? []).map((competitor: any) => ({
            homeAway: competitor?.homeAway,
            score: competitor?.score,
            statistics: (competitor?.statistics ?? []).map((stat: any) => ({ name: stat?.name, displayValue: stat?.displayValue })),
            team: {
              id: competitor?.team?.id,
              displayName: competitor?.team?.displayName,
              shortDisplayName: competitor?.team?.shortDisplayName,
              abbreviation: competitor?.team?.abbreviation,
              logo: competitor?.team?.logo,
              color: competitor?.team?.color,
            },
          })),
          details: (competition?.details ?? []).map((detail: any) => ({
            type: detail?.type,
            clock: detail?.clock,
            team: detail?.team ? { id: detail.team.id } : null,
            athletesInvolved: (detail?.athletesInvolved ?? []).slice(0, 1).map((athlete: any) => ({
              displayName: athlete?.displayName,
            })),
            scoringPlay: detail?.scoringPlay,
            yellowCard: detail?.yellowCard,
            redCard: detail?.redCard,
            ownGoal: detail?.ownGoal,
            penaltyKick: detail?.penaltyKick,
          })),
        }],
      };
    }),
  };
}

function compactStandings(payload: any) {
  const entries = payload?.children?.[0]?.standings?.entries ?? [];
  return {
    children: [{
      standings: {
        entries: entries.map((entry: any) => ({
          team: {
            id: entry?.team?.id,
            displayName: entry?.team?.displayName,
            abbreviation: entry?.team?.abbreviation,
            logos: (entry?.team?.logos ?? []).slice(0, 1),
          },
          stats: entry?.stats ?? [],
        })),
      },
    }],
  };
}

function compactClubs(payload: any) {
  const teams = payload?.sports?.[0]?.leagues?.[0]?.teams ?? [];
  return {
    sports: [{
      leagues: [{
        teams: teams.map((entry: any) => ({
          team: {
            id: entry?.team?.id,
            displayName: entry?.team?.displayName,
            shortDisplayName: entry?.team?.shortDisplayName,
            nickname: entry?.team?.nickname,
            abbreviation: entry?.team?.abbreviation,
            color: entry?.team?.color,
            alternateColor: entry?.team?.alternateColor,
            logos: (entry?.team?.logos ?? []).slice(0, 1),
            links: (entry?.team?.links ?? []).filter((link: any) =>
              (link?.rel ?? []).some((rel: string) => ["clubhouse", "stats", "schedule"].includes(rel)),
            ),
          },
        })),
      }],
    }],
  };
}

async function loadLeague(api: string, fallback: InitialPayloads[keyof InitialPayloads]) {
  const [scores, table, clubs] = await Promise.allSettled([
    Promise.all(scoreYears().map(async (year) => {
      const payload = await fetchJson(`${ESPN_SITE}/${api}/scoreboard?dates=${year}&limit=1000`);
      if (!validScoreboard(payload)) throw new Error("Invalid scoreboard");
      return compactScoreboard(payload);
    })),
    fetchJson(`${ESPN_V2}/${api}/standings`),
    fetchJson(`${ESPN_SITE}/${api}/teams?limit=100`),
  ]);
  const checkedAt = new Date().toISOString();
  const latestScores = scores.status === "fulfilled" ? scores.value : null;
  const tableOk = table.status === "fulfilled" && table.value?.children?.[0]?.standings?.entries?.length > 0;
  const clubsOk = clubs.status === "fulfilled" && clubs.value?.sports?.[0]?.leagues?.[0]?.teams?.length > 0;
  const complete = !!latestScores && tableOk && clubsOk;

  return {
    ...fallback,
    scorePayload: latestScores ? {
      // Calendar responses can describe a different season; the saved current-season label is authoritative.
      ...fallback.scorePayload,
      events: mergeEvents(fallback.scorePayload?.events ?? [], latestScores.flatMap((payload) => payload.events)),
    } : fallback.scorePayload,
    tablePayload: tableOk && table.status === "fulfilled" ? compactStandings(table.value) : fallback.tablePayload,
    clubsPayload: clubsOk && clubs.status === "fulfilled" ? compactClubs(clubs.value) : fallback.clubsPayload,
    rosters: fallback.rosters ?? [],
    checkedAt,
    refreshState: complete ? "current" : latestScores || tableOk || clubsOk ? "partial" : "saved",
    updatedAt: complete ? checkedAt : fallback.updatedAt,
    dataDates: {
      ...fallback.dataDates,
      scores: latestScores ? checkedAt : fallback.dataDates?.scores ?? fallback.updatedAt,
      standings: tableOk ? checkedAt : fallback.dataDates?.standings ?? fallback.updatedAt,
      squads: fallback.dataDates?.squads ?? fallback.updatedAt,
    },
  };
}

export async function loadFootballPayloads() {
  const snapshot = await loadFootballSnapshot() as InitialPayloads;
  const entries = await Promise.all(
    (Object.entries(LEAGUES) as Array<[keyof typeof LEAGUES, string]>).map(
      async ([key, api]) => {
        try {
          return [key, await loadLeague(api, snapshot[key])] as const;
        } catch {
          return [key, { ...snapshot[key], refreshState: "saved", checkedAt: new Date().toISOString() }] as const;
        }
      },
    ),
  );

  return Object.fromEntries(entries) as InitialPayloads;
}
