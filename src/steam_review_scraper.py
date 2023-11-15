import datetime
import logging
import json
import urllib
import re
import os
import time
import sys
import argparse


cgi_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cgi-bin")
sys.path.append(cgi_path)
import common
import db_common

k_encoding = "utf-8" # Because Steam allows all sorts of crazy characters, we need to .encode() the string before printing and writing
k_csv_separator = ";"
k_csv_replacement_seperator = ":"
k_csv_header = k_csv_separator.join([
    "responded",
    "recommended",
    "user_name",
    "content",
    "hours_played",
    "review_url",
    "posted_date",
    "helpful",
    "user_profile",
    "user_reviews"
])

k_steam_review_page_sort_filters = [
    "recent",
    "updated",
    "all"
]

class SteamReview(object):
    def __init__(self,
                 id,
                 review_url,
                 steam_appid,
                 recommended = None,
                 user_name = None,
                 content = None,
                 hours_played = None,
                 date_posted = None,
                 date_updated = None,
                 helpful_amount = None,
                 helpful_total = None,
                 games_owned = None,
                 user_link = None,
                 early_access_review = None,
                 language_key = None,
                 received_compensation=False):
        self.id = id
        self.steam_appid = steam_appid
        self.recommended = recommended
        self.user_name = user_name
        self.content = content
        self.hours_played = hours_played
        self.review_url = review_url
        self.date_posted = date_posted
        self.date_updated = date_updated
        self.games_owned = games_owned
        self.user_link = user_link
        self.is_early_access_review = early_access_review
        self.helpful_amount = helpful_amount
        self.helpful_total = helpful_total
        self.language_key = language_key
        self.received_compensation = received_compensation

        self.responded_by = None
        self.responded_date = None
        self.can_be_turned = None
        self.issue_list = None

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return "{0}: '{1}' ({2})".format(self.id, self.user_name.encode(k_encoding), self.review_url)

def get_reviews_from_api(steam_appid, languages = [], num_per_page = 20, filter = 'all', cursor = '*'):
    delta = datetime.datetime.now().date() - datetime.date(1993, 1, 1)
    
    options = {
        "json":"1",
        "cursor": cursor,
        "language":"all" if len(languages) == 0 else ','.join(languages),
        "filter":filter,
        "review_type":"all",
        "purchase_type":"all",
        "num_per_page":num_per_page,
        "day_range": delta.days
    }

    reviews = []
    url = "http://store.steampowered.com/appreviews/{}?json=1&{}".format(steam_appid, urllib.urlencode(options))

    response = urllib.urlopen(url)
    response_code = response.getcode()
    response_content = response.read()

    if response_code != 200:
        logging.error("Could not contact steam api. Response code is {}".format(response_code))
    else:
        response_data = json.loads(response_content)
        reviews_data = response_data["reviews"]

        total_reviews = None

        if "query_summary" in response_data:
            total_reviews = response_data["query_summary"].get("total_reviews", None)

        for review in reviews_data:
            review_id = review["recommendationid"]

            if review["language"] not in languages:
                logging.info("Skipping review {}, {} not in language list".format(review_id, review["language"]))
                continue

            review_url = "https://steamcommunity.com/profiles/{}/recommended/{}".format(review["author"]["steamid"], steam_appid)

            output = SteamReview(
                review_id,
                review_url,
                steam_appid,
                review["voted_up"],
                None,
                None,
                review["author"]["playtime_forever"],
                None,
                None,
                review["votes_up"],
                review["votes_up"] + review["votes_funny"],
                review["author"]["num_games_owned"],
                None,
                review["written_during_early_access"],
                review["language"],
                review["received_for_free"]
            )

            output.user_name = review["author"]["steamid"] #user_data.get("personaname", "Not found")
            output.user_link = "http://steamcommunity.com/profiles/{}".format(review["author"]["steamid"]) #user_data.get("profileurl", "Not found")
            output.date_posted = datetime.datetime.fromtimestamp(review.get("timestamp_created", 0))
            output.date_updated = datetime.datetime.fromtimestamp(review.get("timestamp_updated", 0))
            output.content = review.get("review", "")
            output.responded_by = review.get("developer_response", None)
            output.responded_date = datetime.datetime.fromtimestamp(review.get("timestamp_dev_responded", None)) if review.get("timestamp_dev_responded", None) is not None else None

            if review:
                reviews.append(output)

    return (reviews, response_data["cursor"], total_reviews)


def review_parse_loop(appid, languages, sort_by, save_to_db):
    current_cursor = '*'
    seen_cursors = []
    all_reviews = set()

    language_keys = [lang.steam_key for lang in languages]
    total_reviews = "Unknown"
    num_added = 0
    percent = 0

    while True:
        reviews, current_cursor, t = get_reviews_from_api(appid, language_keys, 100, sort_by, current_cursor)
        num_added = num_added + len(reviews)

        if t is not None:
            total_reviews = t

        if total_reviews > 0:
            percent = round((float(num_added) / float(total_reviews)) * 100)

        if save_to_db:
            db_common.insert_or_update_reviews(reviews, include_user_input_columns=False)

            if num_added % 1000 == 0:
                if os.getenv("scraper_show_progressbar", '0') == '1':
                    sys.stdout.write("\n")

                logging.info("{}%: {}/{} reviews saved to db".format(percent, num_added, total_reviews))

            if os.getenv("scraper_show_progressbar", '0') == '1':
                sys.stdout.write("\r %d%% [%-100s] %d/%d reviews saved to db" % (percent, '='*int(percent), num_added, total_reviews))
                sys.stdout.flush()

        if current_cursor in seen_cursors:
            logging.info("breaking on seen cursor {}. No more reviews to add".format(current_cursor))
            break

        if current_cursor != '*':
            #logging.info("remembering cursor {}".format(current_cursor))
            seen_cursors.append(current_cursor)

        all_reviews.update(reviews)

    return all_reviews

def get_steam_game_info(appid):
    url = "http://store.steampowered.com/api/appdetails?appids={}".format(appid)

    response = urllib.urlopen(url)
    response_code = response.getcode()
    response_content = response.read()


    if response_code == 200:
        data = json.loads(response_content)

        if str(appid) in data.keys():
            return data.get(str(appid)).get("data")

    return {}

def parse_reviews_for_app(appid, options):
    appinfo = get_steam_game_info(appid)
    logging.info(appinfo.get("name"))
    app_name = appinfo["name"]

    logging.info("Retrieving and parsing reviews for '{0}' ({1}) {2}...".format(app_name, appid, k_steam_review_page_sort_filters[0]))
    db_common.insert_or_update_app(appid, app_name)

    all_reviews = set()
    languages = common.get_settings().get_tracked_languages()

    reviews = review_parse_loop(appid, languages, k_steam_review_page_sort_filters[0], True)
    all_reviews.update(reviews)

    for language in languages:
        db_common.insert_or_update_languages(language.lang_key, language.name, language.steam_key)

    logging.info("---------------------------")
    logging.info("Added in total {} reviews".format(len(all_reviews)))
    logging.info("---------------------------")

    return all_reviews

def remove_deleted_reviews(steam_appid, recent_added_reviews):
    reviews = db_common.get_reviews_for_app_and_language(steam_appid)

    added_ids = [review.id for review in recent_added_reviews]

    languages =  common.get_settings().get_tracked_languages()

    logging.info("Checking for deleted reviews (for {}). Languages: {}".format(steam_appid, ','.join([language.steam_key for language in languages])))
    num_deleted = 0
    for review in reviews:
        review_id = review[0]
        url = review[5]
        language = review[15]

        if review_id not in added_ids and language in languages:
            logging.info("Deleting review ({} for {}, language {})".format(review_id, steam_appid, language))
            db_common.delete_review(review_id)
            num_deleted = num_deleted + 1

    logging.info("Deleted {} reviews".format(num_deleted))


def main(options):
    common.get_settings() # Try to open settings to verify they are valid json

    db_common.create_database()

    apps = common.get_settings().get_tracked_apps()
    appids = [app.appid for app in apps]
    
    logging.info("Parsing reviews for: {0}".format(appids))
    for appid in appids:
        ret = parse_reviews_for_app(appid, options)

        remove_deleted_reviews(appid, ret)

        if ret != 0:
            if type(ret) is set:
                return 0
            else:
                return ret
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieves and parses Steam reviews for the tracked games set in the settings file. Can put the parsed data in the DB or in a .csv file")
    parser.add_argument("-s", "--silent", action="store_true", help="If set, only errors will be printed during the retrieve and parse process")
    options = parser.parse_args()

    log_level = "INFO"
    if options.silent:
        log_level = "ERROR"
    common.init_logging("steam-review-scraper.log", log_level)
    start_time = time.time()
    ret = main(options)
    if ret != 0:
        logging.error("main() returned {0}".format(ret))
    logging.info("Done, total time elapsed: {0}".format(common.pretty_time(time.time() - start_time)))
