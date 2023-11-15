#!/usr/bin/env python
import os
import sys
import time
import logging
import sqlite3
import datetime

from common import pretty_time
import common
import db_definition

g_debug_mode = False

def set_debug(debug_on):
    global g_debug_mode
    g_debug_mode = debug_on

def insert_or_update_app(appid, name):
    all_columns = [
        "steam_appid",
        "display_name"
    ]
    insert_column_str = ", ".join(all_columns)
    insert_values_str = ", ".join(["?"] * len(all_columns))
    upsert_query = "INSERT OR REPLACE INTO stats_steam_games ({0}) VALUES ({1});".format(insert_column_str, insert_values_str)
    data = (appid, name)
    run_db_query(upsert_query, data)

def insert_or_update_languages(lang_key, name, steam_key):
    all_columns = [
        "lang_key",
        "name",
        "steam_key"
    ]
    insert_column_str = ", ".join(all_columns)
    insert_values_str = ", ".join(["?"] * len(all_columns))
    upsert_query = "INSERT OR REPLACE INTO stats_steam_languages ({0}) VALUES ({1});".format(insert_column_str, insert_values_str)
    data = (lang_key, name, steam_key)
    run_db_query(upsert_query, data)

def delete_review(review_id):
    run_db_query("DELETE FROM stats_steam_reviews WHERE id = ?;", (review_id,))

def insert_or_update_reviews(reviews, include_user_input_columns=False):
    ''' Inserts (or updates if the ID already exists) the given reviews into the DB.
    - reviews: list of SteamReview
    - include_user_input_columns: If true, the issue_list and can_be_turned columns will also be set, else we don't update those.
    '''
    all_columns = [
        "id",
        "steam_appid",
        "recommended",
        "user_name",
        "review_text",
        "hours_played",
        "review_url",
        "date_posted",
        "date_updated",
        "helpful_amount",
        "helpful_total",
        "owned_games_amount",
        "responded_by",
        "responded_timestamp",
        "lang_key",
        "received_compensation"
    ]
    if include_user_input_columns:
        all_columns = all_columns + [
            "can_be_turned",
            "issue_list"
        ]

    insert_column_str = ", ".join(all_columns)
    insert_values_str = ", ".join(["?"] * len(all_columns))

    upsert_query = "INSERT OR REPLACE INTO stats_steam_reviews ({0}) VALUES ({1});".format(insert_column_str, insert_values_str)

    for review in reviews:
        if not review.date_posted:
            logging.info("ReviewMissingDate,{0},{1}".format(review.review_url,review.id))
            continue

        data = (
            review.id,
            review.steam_appid,
            review.recommended,
            review.user_name,
            review.content,
            review.hours_played,
            review.review_url,
            review.date_posted,
            review.date_updated,
            review.helpful_amount,
            review.helpful_total,
            review.games_owned,
            review.responded_by,
            review.responded_date,
            review.language_key,
            review.received_compensation
        )
        if include_user_input_columns:
            data = data + (
                review.can_be_turned,
                review.issue_list
            )

        data = (data)
        if g_debug_mode:
            logging.info("Query: {0} ({1})".format(upsert_query, data))
        run_db_query(upsert_query, data)

k_columns = [
    "id",
    "recommended",
    "user_name",
    "review_text",
    "hours_played",
    "review_url",
    "date_posted",
    "date_updated",
    "helpful_amount",
    "helpful_total",
    "responded_by",
    "can_be_turned",
    "issue_list",
    "responded_timestamp"
]
k_columns = ["re." + col for col in k_columns]
k_order_modes = [
    "desc",
    "asc"
]

def get_reviews(steam_appid, page_number, reviews_per_page, sort_by, sort_order, can_be_turned, vote, hide_never_updated, has_response, only_resolved_issues, only_updated_after_response, response_by, lang_key, issue_list, from_date, until_date):
    column_str = ", ".join(k_columns)

    sort_by_column = "re." + sort_by
    sort_by_col = sort_by_column if sort_by_column in k_columns else "re.date_posted"
    sort_by_order = sort_order if sort_order in k_order_modes else k_order_modes[0]
    order_by_str = "ORDER BY {col} {order}".format(col=sort_by_col, order=sort_by_order)

    variables = (steam_appid, lang_key) if lang_key else (steam_appid,)

    where_clauses = []
    where_clauses.append("re.steam_appid = ?")

    if lang_key:
        where_clauses.append("re.lang_key = ?")

    if from_date:
        where_clauses.append("re.date_posted >= '{0}'".format(from_date))

    if until_date:
        where_clauses.append("re.date_posted <= '{0}'".format(until_date))

    if hide_never_updated:
        where_clauses.append("re.date_updated IS NOT NULL")

    if only_resolved_issues:
        where_clauses.append("0 < (select min(resolved_status) from unnest(re.issue_list) as rel(id) left join stats_steam_review_issues as ri on ri.id = rel.id)")
    elif issue_list:
        id_array = ",".join(issue_list)
        where_clauses.append("exists (select rel.id from unnest(re.issue_list) as rel(id) intersect select ri.id from unnest(array[{0}]) as ri(id))".format(id_array))

    if only_updated_after_response:
        where_clauses.append("re.date_updated > re.responded_timestamp")

    if can_be_turned and can_be_turned != "both":
        value = "true" if can_be_turned == "only" else "false"
        where_clauses.append("re.can_be_turned = {0}".format(value))

    if vote and vote != "both":
        value = "true" if vote == "yes" else "false"
        where_clauses.append("re.recommended = {0}".format(value))

    if has_response and has_response != "both":
        value = "NOT" if has_response == "only" else ""
        where_clauses.append("re.responded_by IS {0} NULL".format(value))

    if response_by != 0:
        where_clauses.append("re.responded_by = ?")
        variables = variables + (response_by,)

    where_str = " AND ".join(where_clauses)
    if where_str:
        where_str = "WHERE " + where_str + " "

    # Paging
    total_row_count = get_total_review_count(steam_appid)
    start_count = page_number * reviews_per_page
    if start_count < total_row_count:
        pagination_str = " LIMIT ? OFFSET ?"
        pagination_variables = (reviews_per_page, start_count)
    else:
        pagination_variables = ()
        pagination_str = ""

    select_reviews_query = get_reviews_select_query(column_str, where_str, order_by_str, pagination_str)
    count_reviews_query = get_reviews_select_query("count(id)", where_str, "", "")
    count_positive_reviews_query = get_reviews_select_query("sum(cast(re.recommended as integer))", where_str, "", "")

    reviews = run_db_query(select_reviews_query, variables + pagination_variables)
    query_result_count = run_db_query(count_reviews_query, variables)[0][0]
    positive_review_count = run_db_query(count_positive_reviews_query, variables)[0][0] or 0

    return reviews, query_result_count, positive_review_count

def get_reviews_for_app_and_language(steam_appid, lang_key=None, day_limit=None):
    columns = ", ".join([
        "id",
        "recommended",
        "user_name",
        "review_text",
        "hours_played",
        "review_url",
        "date_posted",
        "date_updated",
        "helpful_amount",
        "helpful_total",
        "owned_games_amount",
        "responded_by",
        "responded_timestamp",
        "can_be_turned",
        "steam_appid",
        "lang_key",
        "received_compensation"
    ])
    data = (steam_appid,)
    query = "SELECT {0} FROM stats_steam_reviews WHERE steam_appid = ?".format(columns)

    if lang_key is not None:
        query += " AND lang_key = ?"
        data = data + (lang_key,)

    if day_limit is not None:
        query += " AND date_updated > utc_now() - interval '? days'"
        data = data + (day_limit,)

    return run_db_query(query, data)
    #return run_db_query("SELECT " + columns + " FROM stats_steam_reviews WHERE steam_appid = %s AND lang_key = %s", (steam_appid, lang_key))

def get_reviews_select_query(select, where, order, pagination):
    query = "SELECT {select} FROM stats_steam_reviews as re {where}{order}{pagination};".format(select=select, where=where, order=order, pagination=pagination)
    return query

def get_total_review_count(steam_appid, language=None):
    if language:
        q_lang_count = run_db_query("SELECT count(id) FROM stats_steam_reviews WHERE steam_appid = ? AND lang_key = ?;", (steam_appid, language))
        if q_lang_count:
            return q_lang_count[0][0]
    q_review_count = run_db_query("SELECT count(id) FROM stats_steam_reviews WHERE steam_appid = ?;", (steam_appid,))
    if q_review_count:
        return q_review_count[0][0]
    return 0

def create_database():
    db_file = "steam.db"

    if os.path.isfile(db_file):
        logging.info("Database file already existed, skipping database creation")
        return

    conn = sqlite3.connect(db_file)
    conn.text_factory = str
    c = conn.cursor()

    c.execute(db_definition.STATS_EVENTS)
    c.execute(db_definition.STATS_STEAM_GAMES)
    c.execute(db_definition.STATS_STEAM_LANGUAGES)
    c.execute(db_definition.STATS_STEAM_PLAYER_COUNT)
    c.execute(db_definition.STATS_STEAM_REVIEWS)
    c.execute(db_definition.STAT_STEAM_REVIEW_ISSUES)
    c.execute(db_definition.STAT_USERS)

    conn.commit()

def run_db_query(query, data=None):
    db_file = "steam.db"
    if not db_file:
        raise Exception("Database file is not set.")

    # Check if database file exists:
    if os.path.isfile(db_file) == False:
        raise Exception("Sqlite database file does not exists, did you run the import script? If this is a new docker spin up, set the environment variable import_database_on_startup=1")

    conn = sqlite3.connect(db_file)
    conn.text_factory = str
    c = conn.cursor()
    if data:
        c.execute(query, data)
    else:
        c.execute(query)

    conn.commit()

    try:
        return c.fetchall()
    except Exception:
        return None