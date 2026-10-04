"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { useListShuffle } from "../../../lib/use-list-shuffle";
import {
  CalendarDays,
  Eye,
  EyeOff,
  Play,
  RefreshCw,
  Shield,
  ShieldCheck,
  Trophy,
} from "lucide-react";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ageOn, seasonYear } from "./records.mjs";
import { githubPhoto } from "./github-photos";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type LeagueKey = "laliga" | "premier" | "bundesliga" | "ligue1";
type LoadState = "idle" | "loading" | "ready" | "error";
type ViewMode = "matches" | "table" | "teams";

type Team = {
  id: string;
  name: string;
  abbreviation: string;
  logo: string;
  score: string;
  statistics: Array<{ name: string; displayValue: string }>;
};

type MatchEvent = {
  id: string;
  leagueKey: LeagueKey;
  date: string;
  seasonYear: number;
  timeConfirmed: boolean;
  statusDescription: string;
  officialDecision?: { text: string; sourceUrl: string };
  statusState: "pre" | "in" | "post";
  venue: string;
  home: Team;
  away: Team;
  details: Array<{
    type: string;
    clock: string;
    teamId: string;
    athlete: string;
    goal: boolean;
    yellow: boolean;
    red: boolean;
    ownGoal: boolean;
    penalty: boolean;
  }>;
};

type Standing = {
  rank: number;
  teamId: string;
  teamName: string;
  abbreviation: string;
  logo: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalDifference: string;
  points: number;
};

type Club = {
  id: string;
  name: string;
  abbreviation: string;
  logo: string;
  color: string;
  alternateColor: string;
};

type Player = {
  id: string;
  name: string;
  originalName: string;
  jersey: string;
  position: string;
  age: number | null;
  headshot: string;
  headshotPosition: string;
  flag: string;
  country: string;
  teamId: string;
  teamName: string;
  previousClubs: Array<{ name: string; sourceUrl: string }>;
  characteristics: Array<{ text: string; sourceUrl: string }>;
};

type LeagueData = {
  status: LoadState;
  season: string;
  matches: MatchEvent[];
  standings: Standing[];
  clubs: Club[];
  players: Player[];
  playersStatus: LoadState;
  error?: string;
};

type InitialLeaguePayload = {
  scorePayload?: any;
  tablePayload?: any;
  clubsPayload?: any;
  rosters?: Array<{ teamId: string; payload: any }>;
  error?: string;
  updatedAt?: string;
  checkedAt?: string;
  refreshState?: "current" | "partial" | "saved";
  dataDates?: { scores?: string; standings?: string; squads?: string };
  seasons?: Record<string, { label: string; tablePayload: any; updatedAt: string; sourceUrl: string; completedMatches: number; expectedMatches: number; notes?: Array<{ text: string; sourceUrl: string }> }>;
};

export type InitialPayloads = Record<LeagueKey, InitialLeaguePayload>;

const LEAGUES: Record<
  LeagueKey,
  { name: string; accent: string; tint: string; logo: string }
> = {
  laliga: { name: "ラ・リーガ", accent: "#ff5a4f", tint: "#351917", logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png" },
  premier: { name: "プレミアリーグ", accent: "#c8ff3d", tint: "#23300d", logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png" },
  bundesliga: { name: "ブンデスリーガ", accent: "#ff3f56", tint: "#351117", logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png" },
  ligue1: { name: "リーグ・アン", accent: "#55e8ff", tint: "#0d3038", logo: "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png" },
};

const TEAM_NAMES_JA: Record<string, string> = {
  "84": "マジョルカ",
  "92": "レアル・オビエド",
  "9812": "ジローナ",
  "371": "ウェストハム・ユナイテッド",
  "379": "バーンリー",
  "380": "ウォルヴァーハンプトン",
  "6418": "ハイデンハイム",
  "138": "ヴォルフスブルク",
  "270": "ザンクト・パウリ",
  "177": "メス",
  "165": "ナント",
  "83": "バルセロナ",
  "85": "セルタ・デ・ビーゴ",
  "86": "レアル・マドリード",
  "87": "ラシン・サンタンデール",
  "88": "エスパニョール",
  "89": "レアル・ソシエダ",
  "90": "デポルティーボ・ラ・コルーニャ",
  "93": "アスレティック・ビルバオ",
  "94": "バレンシア",
  "96": "アラベス",
  "97": "オサスナ",
  "99": "マラガ",
  "101": "ラージョ・バジェカーノ",
  "102": "ビジャレアル",
  "1068": "アトレティコ・マドリード",
  "1538": "レバンテ",
  "243": "セビージャ",
  "244": "レアル・ベティス",
  "2922": "ヘタフェ",
  "3751": "エルチェ",
  "306": "ハル・シティ",
  "331": "ブライトン",
  "337": "ブレントフォード",
  "349": "ボーンマス",
  "357": "リーズ・ユナイテッド",
  "359": "アーセナル",
  "360": "マンチェスター・ユナイテッド",
  "361": "ニューカッスル・ユナイテッド",
  "362": "アストン・ヴィラ",
  "363": "チェルシー",
  "364": "リヴァプール",
  "366": "サンダーランド",
  "367": "トッテナム",
  "368": "エヴァートン",
  "370": "フラム",
  "373": "イプスウィッチ・タウン",
  "382": "マンチェスター・シティ",
  "384": "クリスタル・パレス",
  "388": "コヴェントリー・シティ",
  "393": "ノッティンガム・フォレスト",
  "122": "ケルン",
  "124": "ボルシア・ドルトムント",
  "125": "アイントラハト・フランクフルト",
  "126": "フライブルク",
  "127": "ハンブルガーSV",
  "131": "バイエル・レヴァークーゼン",
  "132": "バイエルン・ミュンヘン",
  "133": "シャルケ04",
  "134": "シュトゥットガルト",
  "137": "ヴェルダー・ブレーメン",
  "268": "ボルシア・メンヒェングラートバッハ",
  "598": "ウニオン・ベルリン",
  "2950": "マインツ05",
  "3307": "パーダーボルン07",
  "3841": "アウクスブルク",
  "7911": "ホッフェンハイム",
  "10388": "エルフェアスベルク",
  "11420": "RBライプツィヒ",
  "160": "パリ・サンジェルマン",
  "166": "リール",
  "167": "リヨン",
  "169": "レンヌ",
  "170": "トロワ",
  "172": "オセール",
  "174": "モナコ",
  "175": "ランス",
  "176": "マルセイユ",
  "179": "トゥールーズ",
  "180": "ストラスブール",
  "273": "ロリアン",
  "2502": "ニース",
  "2697": "ル・マン",
  "3236": "ル・アーヴル",
  "6851": "パリFC",
  "6997": "ブレスト",
  "7868": "アンジェ",
};

const POSITION_NAMES_JA: Record<string, string> = {
  G: "ゴールキーパー",
  D: "ディフェンダー",
  M: "ミッドフィールダー",
  F: "フォワード",
};

const EMPTY_DATA: Record<LeagueKey, LeagueData> = {
  laliga: { status: "idle", season: "", matches: [], standings: [], clubs: [], players: [], playersStatus: "idle" },
  premier: { status: "idle", season: "", matches: [], standings: [], clubs: [], players: [], playersStatus: "idle" },
  bundesliga: { status: "idle", season: "", matches: [], standings: [], clubs: [], players: [], playersStatus: "idle" },
  ligue1: { status: "idle", season: "", matches: [], standings: [], clubs: [], players: [], playersStatus: "idle" },
};

function parseTeam(raw: any): Team {
  return {
    id: String(raw?.team?.id ?? ""),
    name: raw?.team?.displayName ?? "—",
    abbreviation: raw?.team?.abbreviation ?? "—",
    logo: raw?.team?.logo ?? "",
    score: String(raw?.score ?? "0"),
    statistics: Array.isArray(raw?.statistics)
      ? raw.statistics.map((stat: any) => ({
          name: String(stat?.name ?? ""),
          displayValue: String(stat?.displayValue ?? "0"),
        }))
      : [],
  };
}

function parseScoreboard(payload: any, leagueKey: LeagueKey): MatchEvent[] {
  if (!Array.isArray(payload?.events)) return [];
  return payload.events
    .map((event: any) => {
      const competition = event?.competitions?.[0];
      const competitors = competition?.competitors ?? [];
      const homeRaw = competitors.find((team: any) => team.homeAway === "home");
      const awayRaw = competitors.find((team: any) => team.homeAway === "away");
      if (!homeRaw || !awayRaw) return null;

      return {
        id: String(event.id),
        leagueKey,
        date: event.date,
        seasonYear: event.seasonYear ?? seasonYear(event.date),
        timeConfirmed: competition?.timeValid !== false,
        statusDescription: /postpon|suspend/i.test(event?.status?.type?.description ?? "") ? "延期・中断" : "",
        officialDecision: event.officialDecision,
        statusState: event?.status?.type?.state ?? "pre",
        venue: competition?.venue?.fullName ?? event?.venue?.displayName ?? "",
        home: parseTeam(homeRaw),
        away: parseTeam(awayRaw),
        details: (competition?.details ?? []).map((detail: any) => ({
          type: detail?.type?.text ?? "Event",
          clock: detail?.clock?.displayValue ?? "",
          teamId: String(detail?.team?.id ?? ""),
          athlete: detail?.athletesInvolved?.[0]?.displayName ?? "",
          goal: Boolean(detail?.scoringPlay),
          yellow: Boolean(detail?.yellowCard),
          red: Boolean(detail?.redCard),
          ownGoal: Boolean(detail?.ownGoal),
          penalty: Boolean(detail?.penaltyKick),
        })),
      } satisfies MatchEvent;
    })
    .filter(Boolean)
    .sort((left: MatchEvent, right: MatchEvent) => {
      const now = Date.now();
      return Math.abs(new Date(left.date).getTime() - now) - Math.abs(new Date(right.date).getTime() - now);
    }) as MatchEvent[];
}

function parseStandings(payload: any): Standing[] {
  const entries = payload?.children?.[0]?.standings?.entries;
  if (!Array.isArray(entries)) return [];

  return entries.map((entry: any, index: number) => {
    const stats = Object.fromEntries(
      (entry?.stats ?? []).map((stat: any) => [stat?.name, stat?.displayValue]),
    );
    return {
      rank: Number(stats.rank ?? index + 1),
      teamId: String(entry?.team?.id ?? ""),
      teamName: entry?.team?.displayName ?? "—",
      abbreviation: entry?.team?.abbreviation ?? "—",
      logo: entry?.team?.logos?.[0]?.href ?? "",
      played: Number(stats.gamesPlayed ?? 0),
      wins: Number(stats.wins ?? 0),
      draws: Number(stats.ties ?? 0),
      losses: Number(stats.losses ?? 0),
      goalDifference: String(stats.pointDifferential ?? "0"),
      points: Number(stats.points ?? 0),
    };
  });
}

function parseClubs(payload: any): Club[] {
  const entries = payload?.sports?.[0]?.leagues?.[0]?.teams;
  if (!Array.isArray(entries)) return [];

  return entries.map((entry: any) => {
    const team = entry?.team ?? {};
    return {
      id: String(team?.id ?? ""),
      name: team?.displayName ?? team?.name ?? "—",
      abbreviation: team?.abbreviation ?? "—",
      logo: team?.logos?.[0]?.href ?? "",
      color: team?.color ? `#${team.color}` : "#2a312c",
      alternateColor: team?.alternateColor ? `#${team.alternateColor}` : "#121714",
    };
  });
}

function parseRoster(payload: any, standing: Standing): Player[] {
  if (!Array.isArray(payload?.athletes)) return [];
  return payload.athletes
    .filter((athlete: any) => athlete?.status?.type !== "inactive")
    .map((athlete: any) => {
      const id = String(athlete?.id ?? "");
      const originalName = athlete?.fullName ?? athlete?.displayName ?? "—";
      return {
        id,
        name: athlete?.nameJa ?? originalName,
        originalName,
        jersey: String(athlete?.jersey ?? "—"),
        position: athlete?.position?.abbreviation ?? "—",
        age: ageOn(athlete?.dateOfBirth) ?? (athlete?.age != null && Number.isFinite(Number(athlete.age)) ? Number(athlete.age) : null),
        headshot: athlete?.headshot?.href ?? "",
        headshotPosition: athlete?.headshot?.objectPosition ?? "center top",
        flag: athlete?.flag?.href ?? "",
        country: athlete?.citizenship ?? athlete?.flag?.alt ?? "",
        teamId: standing.teamId,
        teamName: TEAM_NAMES_JA[standing.teamId] ?? standing.teamName,
        previousClubs: athlete?.profile?.previousClubs ?? [],
        characteristics: athlete?.profile?.characteristics ?? [],
      };
    });
}

function createInitialDatasets(payloads: InitialPayloads): Record<LeagueKey, LeagueData> {
  const result = { ...EMPTY_DATA };

  for (const key of Object.keys(LEAGUES) as LeagueKey[]) {
    const payload = payloads[key];
    if (!payload || payload.error || !payload.scorePayload || !payload.tablePayload) {
      result[key] = {
        ...EMPTY_DATA[key],
        status: "error",
        playersStatus: "error",
        error: "試合データを取得できませんでした",
      };
      continue;
    }

    const standings = parseStandings(payload.tablePayload);
    const standingById = new Map(standings.map((standing) => [standing.teamId, standing]));
    const rankByTeam = new Map(standings.map((standing) => [standing.teamId, standing.rank]));
    const players = (payload.rosters ?? []).flatMap(({ teamId, payload: rosterPayload }) => {
      const standing = standingById.get(String(teamId));
      return standing ? parseRoster(rosterPayload, standing) : [];
    }).filter((player, index, all) =>
      all.findIndex((candidate) => candidate.teamId === player.teamId && candidate.id === player.id) === index,
    ).sort((left, right) => {
      const teamOrder = (rankByTeam.get(left.teamId) ?? 999) - (rankByTeam.get(right.teamId) ?? 999);
      if (teamOrder) return teamOrder;
      const positions: Record<string, number> = { G: 0, D: 1, M: 2, F: 3 };
      const positionOrder = (positions[left.position] ?? 9) - (positions[right.position] ?? 9);
      if (positionOrder) return positionOrder;
      return Number(left.jersey || 999) - Number(right.jersey || 999);
    });

    result[key] = {
      status: "ready",
      season: payload.scorePayload?.leagues?.[0]?.season?.displayName ?? "",
      matches: parseScoreboard(payload.scorePayload, key),
      standings,
      clubs: parseClubs(payload.clubsPayload),
      players,
      playersStatus: players.length ? "ready" : "error",
    };
  }

  return result;
}

function statValue(team: Team, name: string) {
  const value = team.statistics.find((stat) => stat.name === name)?.displayValue;
  return Number.parseFloat(value ?? "0") || 0;
}

function formatMatchDate(date: string) {
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    weekday: "short",
  }).format(new Date(date));
}

function formatMatchTime(date: string) {
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(date));
}

function tokyoDateKey(date: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(date));
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function youtubeUrl(match: MatchEvent) {
  const year = new Date(match.date).getFullYear();
  const query = `${match.home.name} ${match.away.name} ${year} highlights`;
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
}

function TeamMark({ team }: { team: Team }) {
  return (
    <div className="team-mark">
      {team.logo ? <img src={team.logo} alt="" className="team-logo" /> : <span>{team.abbreviation.slice(0, 2)}</span>}
    </div>
  );
}

function StatLine({ label, home, away, suffix = "" }: { label: string; home: number; away: number; suffix?: string }) {
  const total = home + away;
  const ratio = total ? Math.max(5, Math.min(95, (home / total) * 100)) : 50;
  return (
    <div className="stat-line">
      <div className="stat-values"><b>{home}{suffix}</b><span>{label}</span><b>{away}{suffix}</b></div>
      <div className="stat-track"><span style={{ width: `${ratio}%` }} /></div>
    </div>
  );
}

function MatchCard({ match, revealed, onToggle }: { match: MatchEvent; revealed: boolean; onToggle: () => void }) {
  const hasResult = match.statusState !== "pre";
  const showResult = !hasResult || revealed;
  const keyEvents = match.details.filter((detail) => detail.goal || detail.yellow || detail.red);
  const statsAvailable = match.home.statistics.length > 0;
  const matchLeague = LEAGUES[match.leagueKey];

  return (
    <article className={`match-card ${revealed ? "is-revealed" : ""}`} style={{ "--league-accent": matchLeague.accent } as CSSProperties}>
      <header className="match-head">
        <time dateTime={match.date} className="match-time"><strong>{match.timeConfirmed ? formatMatchTime(match.date) : "時刻未定"}</strong></time>
        <span className="match-league" aria-label={matchLeague.name}><img src={matchLeague.logo} alt="" /></span>
        <a className="youtube-link" href={youtubeUrl(match)} target="_blank" rel="noreferrer" aria-label={`${match.home.name}対${match.away.name}をYouTubeで検索`}>
          <Play size={18} fill="currentColor" />
        </a>
      </header>

      <div className="scoreboard">
        <div className="team"><TeamMark team={match.home} /></div>
        <div className="score-center">
          {showResult ? (
            <>
              <div className="score">
                <strong>{hasResult ? match.home.score : ""}</strong>
                <span>{hasResult ? "—" : "VS"}</span>
                <strong>{hasResult ? match.away.score : ""}</strong>
              </div>
              {hasResult && <small className={match.statusState === "in" ? "live" : ""}>{match.statusState === "in" ? "LIVE" : match.officialDecision ? "確定" : "FT"}</small>}
            </>
          ) : (
            <button className="reveal-button" type="button" onClick={onToggle} aria-label="結果を見る"><Eye size={25} /></button>
          )}
        </div>
        <div className="team"><TeamMark team={match.away} /></div>
      </div>

      {match.venue && <div className="venue">{match.venue}</div>}
      {match.statusDescription && <div className="venue">{match.statusDescription}</div>}

      {hasResult && revealed && (
        <div className="revealed-panel">
          <button className="hide-one" type="button" onClick={onToggle} aria-label="この試合の結果を隠す"><EyeOff size={18} /></button>
          {match.officialDecision && <p className="football-decision"><a href={match.officialDecision.sourceUrl} target="_blank" rel="noreferrer">{match.officialDecision.text}</a></p>}
          {keyEvents.length > 0 && (
            <div className="timeline" aria-label="試合の流れ">
              {keyEvents.slice(0, 8).map((event, index) => (
                <div className={`timeline-event ${event.teamId === match.home.id ? "event-home" : "event-away"}`} key={`${event.clock}-${event.athlete}-${index}`}>
                  <span className="event-minute">{event.clock}</span>
                  <span className={`event-icon ${event.red ? "red-card" : event.yellow ? "yellow-card" : "goal"}`} />
                  <span className="event-name">{event.athlete || event.type}{event.ownGoal ? " OG" : event.penalty ? " PK" : ""}</span>
                </div>
              ))}
            </div>
          )}
          {statsAvailable && (
            <div className="match-stats" aria-label="試合スタッツ">
              <StatLine label="支配率" home={statValue(match.home, "possessionPct")} away={statValue(match.away, "possessionPct")} suffix="%" />
              <StatLine label="シュート" home={statValue(match.home, "totalShots")} away={statValue(match.away, "totalShots")} />
              <StatLine label="枠内" home={statValue(match.home, "shotsOnTarget")} away={statValue(match.away, "shotsOnTarget")} />
              <StatLine label="CK" home={statValue(match.home, "wonCorners")} away={statValue(match.away, "wonCorners")} />
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function MatchesByDate({ matches, revealedIds, onToggle }: { matches: MatchEvent[]; revealedIds: Set<string>; onToggle: (id: string) => void }) {
  const { shuffle } = useListShuffle();
  const byDate = new Map<string, { key: string; label: string; matches: MatchEvent[] }>();
  for (const match of matches) {
    const key = tokyoDateKey(match.date);
    if (!byDate.has(key)) byDate.set(key, { key, label: formatMatchDate(match.date), matches: [] });
    byDate.get(key)!.matches.push(match);
  }
  const groups = shuffle([...byDate.values()], "days");

  return (
    <div className="schedule-days">
      {groups.map((group) => (
        <section className="schedule-day" key={group.key}>
          <header className="date-heading"><time dateTime={group.key}>{group.label}</time><span>{group.matches.length}試合</span></header>
          <div className="matches-grid">
            {shuffle(group.matches, group.key).map((match) => (
              <MatchCard key={match.id} match={match} revealed={revealedIds.has(match.id)} onToggle={() => onToggle(match.id)} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function StandingsView({ standings }: { standings: Standing[] }) {
  const { shuffle } = useListShuffle();
  return (
    <div className="standings-card">
      <Table className="standings-table">
        <TableHeader>
          <TableRow>
            <TableHead className="rank-cell">#</TableHead>
            <TableHead>CLUB</TableHead>
            <TableHead className="numeric-cell">P</TableHead>
            <TableHead className="numeric-cell wide-stat">W</TableHead>
            <TableHead className="numeric-cell wide-stat">D</TableHead>
            <TableHead className="numeric-cell wide-stat">L</TableHead>
            <TableHead className="numeric-cell wide-stat">GD</TableHead>
            <TableHead className="numeric-cell points-cell">PTS</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {shuffle(standings).map((entry) => (
            <TableRow key={entry.teamId} data-rank={entry.rank}>
              <TableCell className="rank-cell"><span>{entry.rank}</span></TableCell>
              <TableCell>
                <div className="standing-team">
                  {entry.logo ? <img src={entry.logo} alt="" /> : <span>{entry.abbreviation.slice(0, 2)}</span>}
                  <b>{entry.teamName}</b>
                  <small>{entry.abbreviation}</small>
                </div>
              </TableCell>
              <TableCell className="numeric-cell">{entry.played}</TableCell>
              <TableCell className="numeric-cell wide-stat">{entry.wins}</TableCell>
              <TableCell className="numeric-cell wide-stat">{entry.draws}</TableCell>
              <TableCell className="numeric-cell wide-stat">{entry.losses}</TableCell>
              <TableCell className="numeric-cell wide-stat">{entry.goalDifference}</TableCell>
              <TableCell className="numeric-cell points-cell"><b>{entry.points}</b></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function PlayerPhoto({ player }: { player: Player }) {
  const [failed, setFailed] = useState(false);
  const [source, setSource] = useState("");

  useEffect(() => {
    let disposed = false;
    setSource("");
    setFailed(false);
    if (player.headshot) {
      void githubPhoto(player.headshot).then(url => {
        if (!disposed) setSource(url);
      }).catch(() => { if (!disposed) setFailed(true); });
    }
    return () => { disposed = true; };
  }, [player.headshot]);

  if (!player.headshot || failed) {
    return <span aria-label={`${player.name}の写真なし`}>{player.name.slice(0, 1)}</span>;
  }

  if (!source) return <span className="skeleton" aria-label={`${player.name}の写真を読み込み中`} />;

  return (
    <img
      src={source}
      alt={player.name}
      loading="lazy"
      decoding="async"
      style={{ objectPosition: player.headshotPosition }}
      onError={() => setFailed(true)}
    />
  );
}

function playerGoogleUrl(player: Player) {
  return `https://www.google.com/search?q=${encodeURIComponent(`${player.originalName} footballer`)}`;
}

function playerYoutubeUrl(player: Player) {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(`${player.originalName} football`)}`;
}

function PlayerRow({ player }: { player: Player }) {
  return (
    <article className="squad-player">
      <span className="squad-number">{player.jersey}</span>
      <a
        className="squad-photo"
        href={playerGoogleUrl(player)}
        target="_blank"
        rel="noreferrer"
        aria-label={`${player.name}をGoogleで検索`}
        title="Googleで検索"
      >
        <PlayerPhoto player={player} />
      </a>
      <div className="squad-player-copy">
        <a
          className="player-name-link"
          href={playerYoutubeUrl(player)}
          target="_blank"
          rel="noreferrer"
          aria-label={`${player.name}をYouTubeで検索`}
          title="YouTubeで検索"
        >
          {player.name}
        </a>
        {player.name !== player.originalName && <span className="player-original-name">{player.originalName}</span>}
        <dl className="player-profile">
          <div><dt>年齢</dt><dd>{player.age == null ? "—" : `${player.age}歳`}</dd></div>
          <div>
            <dt>国籍</dt>
            <dd>{player.flag && <img src={player.flag} alt="" />}{player.country || "—"}</dd>
          </div>
          {player.previousClubs.length > 0 && (
            <div className="player-history">
              <dt>過去のチーム</dt>
              <dd>{player.previousClubs.map((club, index) => (
                <span key={`${club.name}-${index}`}>
                  {index > 0 && "、"}<a href={club.sourceUrl} target="_blank" rel="noreferrer">{club.name}</a>
                </span>
              ))}</dd>
            </div>
          )}
          {player.characteristics.length > 0 && (
            <div className="player-characteristics">
              <dt>特徴</dt>
              <dd>{player.characteristics.map((fact, index) => (
                <a key={index} href={fact.sourceUrl} target="_blank" rel="noreferrer">{fact.text}</a>
              ))}</dd>
            </div>
          )}
        </dl>
      </div>
    </article>
  );
}

function TeamSquadView({ clubs, standings, players }: { clubs: Club[]; standings: Standing[]; players: Player[] }) {
  const { shuffle: shuffleClubs } = useListShuffle();
  const cards = shuffleClubs(clubs.length ? clubs : standings.map((entry) => ({
    id: entry.teamId,
    name: entry.teamName,
    abbreviation: entry.abbreviation,
    logo: entry.logo,
    color: "#2a312c",
    alternateColor: "#121714",
  })), "clubs");
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const activeTeamId = cards.some((club) => club.id === selectedTeamId) ? selectedTeamId : cards[0]?.id ?? "";
  const activeClub = cards.find((club) => club.id === activeTeamId);
  const { shuffle: shuffleSquad, reshuffle: reshuffleSquad } = useListShuffle(activeTeamId);
  const squad = shuffleSquad(players, "players").filter((player) => player.teamId === activeTeamId);
  const knownPositions = new Set(["G", "D", "M", "F"]);
  const groups = shuffleSquad([
    { key: "G", label: "GK", players: squad.filter((player) => player.position === "G") },
    { key: "D", label: "DF", players: squad.filter((player) => player.position === "D") },
    { key: "M", label: "MF", players: squad.filter((player) => player.position === "M") },
    { key: "F", label: "FW", players: squad.filter((player) => player.position === "F") },
    { key: "O", label: "OTHER", players: squad.filter((player) => !knownPositions.has(player.position)) },
  ], "positions").filter((group) => group.players.length > 0);

  return (
    <div className="teams-surface" style={{ "--club-accent": activeClub?.color ?? "var(--accent)", "--club-alt": activeClub?.alternateColor ?? "#121714" } as CSSProperties}>
      <div className="club-selector" aria-label="チームを選択">
        {cards.map((club) => (
          <button
            type="button"
            className="club-button"
            key={club.id}
            aria-label={`${club.name}の所属選手を見る`}
            aria-pressed={club.id === activeTeamId}
            onClick={() => { if (club.id === activeTeamId) reshuffleSquad(); setSelectedTeamId(club.id); }}
            style={{ "--team-color": club.color, "--team-alt": club.alternateColor } as CSSProperties}
          >
            {club.logo ? <img src={club.logo} alt="" /> : <b>{club.abbreviation.slice(0, 2)}</b>}
          </button>
        ))}
      </div>

      {squad.length > 0 ? (
        <section className="squad-panel" aria-label={`${activeClub?.name ?? "チーム"}の所属選手`}>
          {groups.map((group) => (
            <section className="position-group" key={group.key}>
              <header><b>{group.label}</b><span>{group.players.length}</span></header>
              <div className="squad-players">
                {group.players.map((player) => <PlayerRow key={`${player.teamId}-${player.id}`} player={player} />)}
              </div>
            </section>
          ))}
        </section>
      ) : (
        <div className="empty-state">選手データがありません</div>
      )}
    </div>
  );
}

function MatchSkeleton() {
  return <article className="match-card skeleton-card" aria-hidden="true"><div className="skeleton line-skeleton" /><div className="skeleton score-skeleton" /></article>;
}

export default function Dashboard({ initialPayloads, onRefresh, refreshing = false, refreshError = false }: { initialPayloads: InitialPayloads; onRefresh?: () => void; refreshing?: boolean; refreshError?: boolean }) {
  const [activeLeague, setActiveLeague] = useState<LeagueKey>("premier");
  const [viewMode, setViewMode] = useState<ViewMode>("matches");
  const datasets = useMemo(() => createInitialDatasets(initialPayloads), [initialPayloads]);
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());
  const [storageReady, setStorageReady] = useState(false);
  const [pastResultsCount, setPastResultsCount] = useState(40);
  const [upcomingCount, setUpcomingCount] = useState(40);
  const [selectedSeason, setSelectedSeason] = useState("all");
  const league = LEAGUES[activeLeague];
  const current = datasets[activeLeague];
  const currentYear = String(initialPayloads[activeLeague]?.scorePayload?.leagues?.[0]?.season?.year ?? seasonYear(new Date().toISOString()));
  const seasonOptions = useMemo(() => [...new Set(Object.values(initialPayloads).flatMap((payload) => [
    ...Object.keys(payload.seasons ?? {}), String(payload.scorePayload?.leagues?.[0]?.season?.year ?? ""),
  ]))].filter(Boolean).sort((a, b) => Number(b) - Number(a)), [initialPayloads]);
  const tableYear = selectedSeason === "all" ? currentYear : selectedSeason;
  const seasonTable = tableYear === currentYear ? current.standings : parseStandings(initialPayloads[activeLeague]?.seasons?.[tableYear]?.tablePayload);
  const activePayloads = viewMode === "matches" ? Object.values(initialPayloads) : [initialPayloads[activeLeague]];
  const latestDates = activePayloads.flatMap((payload) => [payload.dataDates?.scores ?? payload.updatedAt, payload.dataDates?.standings ?? payload.updatedAt]).filter(Boolean) as string[];
  const updatedAt = latestDates.sort()[0];
  const savedData = refreshError || activePayloads.some((payload) => payload.refreshState !== "current");
  const formatUpdate = (date?: string) => date ? new Intl.DateTimeFormat("ja-JP", { timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(date)) : "未取得";
  const allMatches = useMemo(
    () => Object.values(datasets)
      .flatMap((dataset) => dataset.matches)
      .sort((left, right) => new Date(left.date).getTime() - new Date(right.date).getTime()),
    [datasets],
  );
  const { pastResults, upcomingMatches, pendingMatches } = useMemo(() => {
    const now = Date.now();
    const matches = allMatches.filter((match) => selectedSeason === "all" || String(match.seasonYear) === selectedSeason);
    return {
      pastResults: matches.filter((match) => match.statusState !== "pre")
        .sort((left, right) => new Date(right.date).getTime() - new Date(left.date).getTime()),
      upcomingMatches: matches.filter((match) => match.statusState === "pre" && new Date(match.date).getTime() >= now),
      pendingMatches: matches.filter((match) => match.statusState === "pre" && new Date(match.date).getTime() < now),
    };
  }, [allMatches, selectedSeason]);
  const matchesReady = Object.values(datasets).some((dataset) => dataset.status === "ready");

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("nsf-revealed-matches") ?? "[]");
      if (Array.isArray(stored)) setRevealedIds(new Set(stored));
    } catch { /* Ignore a malformed local preference. */ }
    setStorageReady(true);
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    localStorage.setItem("nsf-revealed-matches", JSON.stringify([...revealedIds]));
  }, [revealedIds, storageReady]);

  function toggleReveal(id: string) {
    setRevealedIds((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  return (
    <TooltipProvider delayDuration={150}>
      <div className="site-shell" style={{ "--accent": league.accent, "--accent-tint": league.tint } as CSSProperties}>
        <header className="topbar">
          <span className="brand-mark" aria-label="NO SPOILER FOOTBALL"><ShieldCheck size={23} /></span>
          <div className="football-update" aria-live="polite">
            <span>{refreshing ? "最新情報を確認中…" : savedData ? "保存データを表示" : "試合・順位を更新済み"}</span>
            <time dateTime={updatedAt}>{formatUpdate(updatedAt)} 日本時間</time>
          </div>
          <button className="hide-all" type="button" onClick={onRefresh} disabled={refreshing} aria-label="最新情報に更新"><RefreshCw size={20} /></button>
          <button className="hide-all" type="button" onClick={() => setRevealedIds(new Set())} aria-label="すべての試合結果を隠す" disabled={revealedIds.size === 0}>
            <EyeOff size={20} />
          </button>
        </header>

        {viewMode !== "matches" && (
          <Tabs value={activeLeague} onValueChange={(value) => setActiveLeague(value as LeagueKey)} className="league-tabs">
            <TabsList className="league-tab-list" aria-label="リーグ切り替え">
              {(Object.keys(LEAGUES) as LeagueKey[]).map((key) => {
                const item = LEAGUES[key];
                return (
                  <Tooltip key={key}>
                    <TooltipTrigger asChild>
                      <TabsTrigger className="league-tab" value={key} aria-label={item.name}><img src={item.logo} alt="" /></TabsTrigger>
                    </TooltipTrigger>
                    <TooltipContent className="football-tooltip" sideOffset={8}>{item.name}</TooltipContent>
                  </Tooltip>
                );
              })}
            </TabsList>
          </Tabs>
        )}

        <section className="content-wrap">
          <div className="content-toolbar">
            <Tabs value={viewMode} onValueChange={(value) => setViewMode(value as ViewMode)} className="view-tabs-wrap">
              <TabsList className="view-tabs" aria-label="表示内容">
                {[
                  { value: "matches", label: "試合", icon: CalendarDays },
                  { value: "table", label: "順位", icon: Trophy },
                  { value: "teams", label: "チーム", icon: Shield },
                ].map(({ value, label, icon: Icon }) => (
                  <Tooltip key={value}>
                    <TooltipTrigger asChild>
                      <TabsTrigger value={value} aria-label={label}><Icon /></TabsTrigger>
                    </TooltipTrigger>
                    <TooltipContent className="football-tooltip" sideOffset={8}>{label}</TooltipContent>
                  </Tooltip>
                ))}
              </TabsList>
            </Tabs>
            {viewMode === "teams" ? <div className="period">{current.season || "—"}</div> : (
              <Select value={viewMode === "table" ? tableYear : selectedSeason} onValueChange={(value) => { setSelectedSeason(value); setPastResultsCount(40); setUpcomingCount(40); }}>
                <SelectTrigger className="football-season-select" aria-label="シーズンを選択"><SelectValue /></SelectTrigger>
                <SelectContent className="football-season-menu" position="popper">
                  {viewMode === "matches" && <SelectItem value="all">全シーズン</SelectItem>}
                  {seasonOptions.map((year) => <SelectItem key={year} value={year}>{year}–{String(Number(year) + 1).slice(-2)}{year === currentYear ? "（今季）" : ""}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
          </div>
          <details className="football-data-details">
            <summary>更新日時・情報元</summary>
            {activePayloads.map((payload) => {
              const key = (Object.keys(initialPayloads) as LeagueKey[]).find((key) => initialPayloads[key] === payload)!;
              const apis = { premier: "eng.1", laliga: "esp.1", bundesliga: "ger.1", ligue1: "fra.1" };
              return <div key={key}><b>{LEAGUES[key].name}</b><span>試合 {formatUpdate(payload.dataDates?.scores ?? payload.updatedAt)} ／ 順位 {formatUpdate(payload.dataDates?.standings ?? payload.updatedAt)} ／ 選手 {formatUpdate(payload.dataDates?.squads ?? payload.updatedAt)}</span><a href={`https://www.espn.com/soccer/standings/_/league/${apis[key]}/season/${viewMode === "table" ? tableYear : currentYear}`} target="_blank" rel="noreferrer">順位・記録の情報元</a></div>;
            })}
            {savedData && !refreshing && <p>取得できなかった情報は、表示日時の保存データを使用しています。</p>}
          </details>
          {viewMode === "table" && initialPayloads[activeLeague]?.seasons?.[tableYear]?.notes?.map((note) => <p className="football-decision" key={note.sourceUrl}><a href={note.sourceUrl} target="_blank" rel="noreferrer">{note.text}</a></p>)}

          {viewMode === "matches" ? (
            !matchesReady ? (
              <div className="matches-grid" aria-label="試合を読み込み中"><MatchSkeleton /><MatchSkeleton /><MatchSkeleton /></div>
            ) : (
              <div className="schedule-sections">
                <section className="schedule-section" aria-labelledby="past-results-title">
                  <header className="schedule-section-head"><div><span>RESULTS</span><h1 id="past-results-title">過去の結果</h1></div><b>{pastResults.length}試合</b></header>
                  {pastResults.length
                    ? <MatchesByDate matches={pastResults.slice(0, pastResultsCount)} revealedIds={revealedIds} onToggle={toggleReveal} />
                    : <div className="empty-state compact-empty">結果はまだありません</div>}
                  {pastResultsCount < pastResults.length && (
                    <button className="football-load-more" type="button" onClick={() => setPastResultsCount((count) => count + 80)}>
                      以前の結果を表示
                    </button>
                  )}
                </section>
                <section className="schedule-section" aria-labelledby="upcoming-title">
                  <header className="schedule-section-head"><div><span>SCHEDULE</span><h2 id="upcoming-title">今後の予定</h2></div><b>{upcomingMatches.length}試合</b></header>
                  {upcomingMatches.length
                    ? <MatchesByDate matches={upcomingMatches.slice(0, upcomingCount)} revealedIds={revealedIds} onToggle={toggleReveal} />
                    : <div className="empty-state compact-empty">予定されている試合はありません</div>}
                  {upcomingCount < upcomingMatches.length && <button className="football-load-more" type="button" onClick={() => setUpcomingCount((count) => count + 80)}>先の予定を表示</button>}
                </section>
                {pendingMatches.length > 0 && <section className="schedule-section" aria-label="日時・結果の確認待ち"><header className="schedule-section-head"><h2>日時・結果の確認待ち</h2><b>{pendingMatches.length}試合</b></header><MatchesByDate matches={pendingMatches} revealedIds={revealedIds} onToggle={toggleReveal} /></section>}
              </div>
            )
          ) : current.status === "loading" || current.status === "idle" ? (
            <div className="matches-grid" aria-label="試合を読み込み中"><MatchSkeleton /><MatchSkeleton /><MatchSkeleton /></div>
          ) : current.status === "error" ? (
            <div className="data-error"><span>{current.error}</span><button type="button" onClick={() => window.location.reload()}><RefreshCw size={18} />再読込</button></div>
          ) : viewMode === "table" ? (
            seasonTable.length ? <StandingsView key={`${activeLeague}:${tableYear}`} standings={seasonTable} /> : <div className="empty-state">順位データがありません</div>
          ) : viewMode === "teams" ? (
            current.clubs.length || current.standings.length
              ? <TeamSquadView key={activeLeague} clubs={current.clubs} standings={current.standings} players={current.players} />
              : <div className="empty-state">チームデータがありません</div>
          ) : null}
        </section>
      </div>
    </TooltipProvider>
  );
}
