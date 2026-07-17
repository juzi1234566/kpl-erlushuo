-- 0002：二路解说观点聚合
-- 注意：文件末尾的 alter type job_kind 语句需在 SQL Editor 中【单独逐条】执行
--（Postgres 不允许在同一事务中新增并使用枚举值）

-- ============ UP主配置表 ============
create table if not exists up_profiles (
  mid bigint primary key,                -- B站 uid
  name text not null,
  face_url text,
  enabled boolean not null default true,
  scan_keyword text,                     -- 可选：仅匹配含关键词的投稿（过滤杂谈视频）
  speaker_hint jsonb,                    -- 可选：说话人归属人工覆盖 {"strategy":"manual","spk":"spk0"}
  last_scan_at timestamptz,
  note text,
  created_at timestamptz not null default now()
);

-- ============ vod_sources 扩展 ============
alter table vod_sources
  add column if not exists mid bigint references up_profiles(mid),
  add column if not exists aid bigint,
  add column if not exists cid bigint,
  add column if not exists pubdate timestamptz,
  add column if not exists duration_s int,
  add column if not exists cover_url text,
  add column if not exists audio_status text not null default 'pending',      -- pending/done/failed/skipped
  add column if not exists audio_ref text,                                     -- 本地 wav 相对路径
  add column if not exists transcript_status text not null default 'pending',
  add column if not exists transcript_ref text,
  add column if not exists analysis_status text not null default 'pending',
  add column if not exists match_confidence numeric,                           -- 0-1
  add column if not exists match_method text,                                  -- title_teams_date / manual / none
  add column if not exists needs_review boolean not null default false,        -- 待定池标记
  add column if not exists last_error text;

create index if not exists idx_vod_sources_match on vod_sources(match_id);
create index if not exists idx_vod_sources_review on vod_sources(needs_review) where needs_review;

-- ============ quotes 扩展 ============
alter table quotes
  add column if not exists speaker text,        -- 'up' | 'official' | 'other'
  add column if not exists end_ms int;

-- ============ 核心新表：AI 提取的结构化观点 ============
create table if not exists commentary_insights (
  id uuid primary key default gen_random_uuid(),
  vod_id uuid not null references vod_sources(id) on delete cascade,
  match_id text not null references matches(id),
  subject_type text not null check (subject_type in ('overall','team','player')),
  subject_id text,                         -- teams.id / 选手 id，匹配不上留 null
  subject_name text not null,              -- AI 输出的原始名字（展示兜底）
  sentiment text not null check (sentiment in ('好评','差评','中立','复杂')),
  rating smallint check (rating between 1 and 5),
  summary text not null,                   -- AI 转述的评价（1-3 句，已过滤辱骂）
  quotes jsonb not null default '[]'::jsonb, -- [{text, start_ms, end_ms, speaker}]
  ai_risk numeric,
  is_ai_generated boolean not null default true,
  model text,
  status moderation_status not null default 'pending',
  created_at timestamptz not null default now(),
  unique (vod_id, subject_type, subject_name)   -- 分析重跑幂等
);
create index if not exists idx_ci_match on commentary_insights(match_id, status);

-- ============ RLS ============
alter table commentary_insights enable row level security;
drop policy if exists ci_public_read on commentary_insights;
create policy ci_public_read on commentary_insights for select
  using (status = 'approved');

alter table up_profiles enable row level security;
drop policy if exists up_profiles_public_read on up_profiles;
create policy up_profiles_public_read on up_profiles for select using (true);

alter table vod_sources enable row level security;
drop policy if exists vod_sources_public_read on vod_sources;
create policy vod_sources_public_read on vod_sources for select using (true);

-- ============ job_kind 枚举扩展 ============
-- ！！以下四条需在 SQL Editor 中逐条单独执行（不能与上面同事务）！！
-- alter type job_kind add value if not exists 'vod_scan';
-- alter type job_kind add value if not exists 'vod_download';
-- alter type job_kind add value if not exists 'vod_transcribe';
-- alter type job_kind add value if not exists 'vod_analyze';
