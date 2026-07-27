-- 梗局 kpl-meme · 核心 schema + RLS
-- 在 Supabase SQL Editor 执行，或 supabase db push

create extension if not exists "pgcrypto";

-- ========== 枚举 ==========
do $$ begin
  create type moderation_status as enum ('pending','approved','rejected','removed');
exception when duplicate_object then null; end $$;

do $$ begin
  create type post_type as enum ('discussion','meme_card','quote_card','ai_recap');
exception when duplicate_object then null; end $$;

do $$ begin
  create type job_status as enum ('pending','running','done','failed','cancelled');
exception when duplicate_object then null; end $$;

do $$ begin
  create type job_kind as enum ('match_recap','meme_card','quote_extract','hupu_score');
exception when duplicate_object then null; end $$;

-- ========== 赛事域 ==========
create table if not exists leagues (
  id text primary key,
  name text not null,
  year int,
  season int,
  status int,
  start_time timestamptz,
  end_time timestamptz,
  icon_url text,
  raw jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists teams (
  id text primary key,
  name text not null,
  abbreviation text,
  icon_url text,
  style_tags jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists players (
  id text primary key,
  name text not null,
  display_name text,
  team_id text references teams(id),
  icon_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists heroes (
  id text primary key,
  name text not null,
  icon_url text,
  created_at timestamptz not null default now()
);

create table if not exists matches (
  id text primary key,
  league_id text references leagues(id),
  team1_id text references teams(id),
  team2_id text references teams(id),
  score1 int,
  score2 int,
  bo int,
  win_camp int,
  status int,
  start_time timestamptz,
  end_time timestamptz,
  stage_name text,
  stage_desc text,
  venue text,
  raw_ref text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists match_games (
  id text primary key,
  match_id text not null references matches(id) on delete cascade,
  battle_seq int,
  win_camp int,
  game_duration_ms bigint,
  status int,
  raw_ref text,
  created_at timestamptz not null default now()
);

create table if not exists bp_records (
  id bigserial primary key,
  game_id text not null references match_games(id) on delete cascade,
  seq int not null,
  camp int,
  is_ban boolean not null,
  hero_id text references heroes(id),
  hero_name text
);

create table if not exists game_player_stats (
  id bigserial primary key,
  game_id text not null references match_games(id) on delete cascade,
  team_id text references teams(id),
  player_name text,
  actual_player_name text,
  hero_id text references heroes(id),
  camp int,
  kills int,
  deaths int,
  assists int,
  gold int,
  kda numeric,
  participation_rate numeric,
  hurt_rate numeric,
  be_hurt_rate numeric,
  mvp_score numeric,
  is_mvp boolean default false,
  equip jsonb,
  raw jsonb
);

create index if not exists idx_matches_league on matches(league_id);
create index if not exists idx_match_games_match on match_games(match_id);
create index if not exists idx_gps_player on game_player_stats(actual_player_name);
create index if not exists idx_gps_hero on game_player_stats(hero_id);

-- 英雄池：物化视图（可刷新）
create materialized view if not exists player_hero_pool as
select
  actual_player_name as player_name,
  hero_id,
  count(*) as games,
  avg(mvp_score) as avg_mvp,
  sum(kills) as kills,
  sum(deaths) as deaths,
  sum(assists) as assists
from game_player_stats
where actual_player_name is not null
group by actual_player_name, hero_id;

-- ========== 梗域 ==========
create table if not exists memes (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  title text not null,
  definition text not null,
  origin_story text,
  category text,
  hotness int not null default 0,
  is_ai_assisted boolean not null default false,
  moderation_status moderation_status not null default 'approved',
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  occurred_at timestamptz,
  match_id text references matches(id),
  created_at timestamptz not null default now()
);

create table if not exists meme_links (
  id bigserial primary key,
  meme_id uuid not null references memes(id) on delete cascade,
  target_type text not null check (target_type in ('player','team','match','event')),
  target_id text not null,
  unique (meme_id, target_type, target_id)
);

create index if not exists idx_memes_fts on memes
  using gin (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(definition,'') || ' ' || coalesce(origin_story,'')));

-- ========== 社区域 ==========
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  display_name text,
  avatar_url text,
  is_bot boolean not null default false,
  bot_disclosure text,
  created_at timestamptz not null default now()
);

create table if not exists posts (
  id uuid primary key default gen_random_uuid(),
  author_id uuid references profiles(id),
  type post_type not null default 'discussion',
  title text,
  body text not null,
  is_ai_generated boolean not null default false,
  poll jsonb,
  match_id text references matches(id),
  meme_id uuid references memes(id),
  moderation_status moderation_status not null default 'pending',
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references posts(id) on delete cascade,
  author_id uuid references profiles(id),
  parent_id uuid references comments(id) on delete cascade,
  body text not null,
  is_ai_generated boolean not null default false,
  moderation_status moderation_status not null default 'pending',
  deleted_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists reactions (
  id bigserial primary key,
  user_id uuid not null references profiles(id) on delete cascade,
  target_type text not null check (target_type in ('post','comment','meme')),
  target_id uuid not null,
  kind text not null default 'light',
  created_at timestamptz not null default now(),
  unique (user_id, target_type, target_id, kind)
);

create table if not exists poll_votes (
  id bigserial primary key,
  post_id uuid not null references posts(id) on delete cascade,
  user_id uuid not null references profiles(id) on delete cascade,
  option_key text not null,
  created_at timestamptz not null default now(),
  unique (post_id, user_id)
);

create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid references profiles(id),
  target_type text not null,
  target_id text not null,
  reason text,
  status text not null default 'open',
  created_at timestamptz not null default now()
);

-- ========== 语录域 ==========
create table if not exists vod_sources (
  id uuid primary key default gen_random_uuid(),
  bvid text unique not null,
  title text,
  up_name text,
  subtitle_status text not null default 'pending',
  subtitle_ref text,
  match_id text references matches(id),
  created_at timestamptz not null default now()
);

create table if not exists quotes (
  id uuid primary key default gen_random_uuid(),
  vod_id uuid references vod_sources(id) on delete set null,
  text text not null,
  tag text check (tag in ('金句','打脸','毒奶','整活')),
  start_ms int,
  ai_score numeric,
  status moderation_status not null default 'pending',
  deleted_at timestamptz,
  created_at timestamptz not null default now()
);

-- ========== 管线与审计 ==========
create table if not exists raw_crawls (
  id bigserial primary key,
  source text not null,
  content_hash text not null,
  payload_ref text,
  meta jsonb,
  created_at timestamptz not null default now(),
  unique (source, content_hash)
);

create table if not exists generation_jobs (
  id uuid primary key default gen_random_uuid(),
  kind job_kind not null,
  status job_status not null default 'pending',
  payload jsonb not null default '{}'::jsonb,
  attempts int not null default 0,
  run_after timestamptz not null default now(),
  last_error text,
  result jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_jobs_poll on generation_jobs(status, run_after);

create table if not exists ai_generations (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references generation_jobs(id),
  model text,
  prompt text,
  response text,
  prompt_tokens int,
  completion_tokens int,
  cost_cny numeric,
  self_score jsonb,
  human_review text,
  publish_target text,
  created_at timestamptz not null default now()
);

create table if not exists moderation_logs (
  id bigserial primary key,
  target_type text not null,
  target_id text not null,
  provider text,
  decision text,
  detail jsonb,
  created_at timestamptz not null default now()
);

create table if not exists hupu_items (
  id bigserial primary key,
  url text unique not null,
  title text,
  score numeric,
  heat int,
  raw jsonb,
  created_at timestamptz not null default now()
);

-- ========== RLS ==========
alter table memes enable row level security;
alter table posts enable row level security;
alter table comments enable row level security;
alter table reactions enable row level security;
alter table profiles enable row level security;
alter table quotes enable row level security;
alter table reports enable row level security;
alter table leagues enable row level security;
alter table teams enable row level security;
alter table players enable row level security;
alter table heroes enable row level security;
alter table matches enable row level security;
alter table match_games enable row level security;
alter table game_player_stats enable row level security;

-- 公开读：已发布内容与赛事数据
create policy memes_public_read on memes for select using (
  deleted_at is null and moderation_status = 'approved'
);
create policy posts_public_read on posts for select using (
  deleted_at is null and moderation_status = 'approved'
);
create policy comments_public_read on comments for select using (
  deleted_at is null and moderation_status = 'approved'
);
create policy quotes_public_read on quotes for select using (
  deleted_at is null and status = 'approved'
);
create policy profiles_public_read on profiles for select using (true);
create policy leagues_public_read on leagues for select using (true);
create policy teams_public_read on teams for select using (true);
create policy players_public_read on players for select using (true);
create policy heroes_public_read on heroes for select using (true);
create policy matches_public_read on matches for select using (true);
create policy match_games_public_read on match_games for select using (true);
create policy gps_public_read on game_player_stats for select using (true);
create policy reactions_public_read on reactions for select using (true);

-- 登录用户写本人行
create policy posts_insert_own on posts for insert with check (auth.uid() = author_id);
create policy posts_update_own on posts for update using (auth.uid() = author_id);
create policy comments_insert_own on comments for insert with check (auth.uid() = author_id);
create policy reactions_insert_own on reactions for insert with check (auth.uid() = user_id);
create policy reactions_delete_own on reactions for delete using (auth.uid() = user_id);
create policy reports_insert_own on reports for insert with check (auth.uid() = reporter_id);
create policy profiles_update_own on profiles for update using (auth.uid() = id);

-- 任务/审计表：默认不开 public policy（仅 service_role）
alter table generation_jobs enable row level security;
alter table ai_generations enable row level security;
alter table raw_crawls enable row level security;
alter table moderation_logs enable row level security;

-- 种子：AI bot 说明（实际用户 id 在 Auth 创建 bot 后回填）
comment on column profiles.is_bot is '官方 AI 角色须 true，并填写 bot_disclosure';
comment on column posts.is_ai_generated is 'AI 标识法定留痕字段';
