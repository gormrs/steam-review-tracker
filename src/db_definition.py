STATS_STEAM_REVIEWS = """CREATE TABLE "stats_steam_reviews" (
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "recommended"   boolean NOT NULL,
        "user_name"     character varying,
        "review_text"   character varying,
        "hours_played"  numeric,
        "review_url"    character varying NOT NULL,
        "date_posted"   timestamp without time zone NOT NULL,
        "date_updated"  timestamp without time zone,
        "helpful_amount"        integer,
        "helpful_total" integer,
        "owned_games_amount"    integer,
        "responded_by"  bigint,
        "responded_timestamp"   timestamp without time zone,
        "issue_list"    bigint [],
        "can_be_turned" boolean NOT NULL DEFAULT 0,
        "steam_appid"   bigint,
        "lang_key"      NUMERIC,
        "received_compensation" boolean,
        FOREIGN KEY("lang_key") REFERENCES "stats_steam_languages"("lang_key")
);"""

STAT_USERS = """CREATE TABLE "stats_users" (
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "user_name"     character varying NOT NULL,
        "steam_url"     character varying
);"""

STAT_STEAM_REVIEW_ISSUES = """CREATE TABLE "stats_steam_review_issues" (
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name"  character varying NOT NULL,
        "resolved_status"       bigint NOT NULL DEFAULT 0
);"""

STATS_STEAM_PLAYER_COUNT = """CREATE TABLE "stats_steam_player_count" (
        "player_count"  integer NOT NULL,
        "time_stamp"    timestamp without time zone NOT NULL,
        "steam_appid"   bigint NOT NULL
);"""

STATS_STEAM_LANGUAGES = """CREATE TABLE "stats_steam_languages" (
        "lang_key"      character varying NOT NULL,
        "name"  character varying NOT NULL,
        "steam_key"     character varying NOT NULL,
        PRIMARY KEY("lang_key")
);"""

STATS_EVENTS = """CREATE TABLE "stats_events" (
        "name"  character varying NOT NULL,
        "description"   character varying NOT NULL,
        "time_stamp"    timestamp without time zone NOT NULL,
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "type"  stats_event_type NOT NULL DEFAULT 'Patch',
        "steam_appid"   bigint NOT NULL
);"""

STATS_STEAM_GAMES = """CREATE TABLE "stats_steam_games" (
        "steam_appid"   bigint NOT NULL,
        "display_name"  character varying NOT NULL,
        PRIMARY KEY("steam_appid")
);"""