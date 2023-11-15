import os
import sys
import json
import time
import logging
import logging.handlers
import datetime

k_settings_file_path = os.path.join(os.path.dirname(__file__), "settings.json")
if not os.path.isfile(k_settings_file_path):
    logging.error("Settings file doesn't exist! ({0})".format(k_settings_file_path))
    sys.exit(1)

g_settings = None

def pretty_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return "%.0fh %.0fm %.0fs" % (hours, minutes, seconds)
    elif minutes:
        return "%.0fm %.0fs" % (minutes, seconds)
    return "%.0fs" % (seconds,)

def get_settings():
    global g_settings
    if g_settings:
        return g_settings
    with open(k_settings_file_path, "r") as settings_file:
        try:
            settings_data = json.load(settings_file)
            apps = {}
            for appid in settings_data["apps"]:
                app_data = settings_data["apps"][appid]
                apps[appid] = AppConfig(appid, app_data["track"], app_data["ignore_zero_players"], app_data.get("wordcloud_stopwords", {}))
            languages = {}
            for lang_key in settings_data["languages"]:
                lang_data = settings_data["languages"][lang_key]
                languages[lang_key] = Language(lang_key, lang_data["name"], lang_data["steam_key"], lang_data["track"])
        except (ValueError, KeyError):
            logging.error("Settings file ({0}) contains invalid json!".format(k_settings_file_path))
            sys.exit(1)
        g_settings = Settings(apps, languages, settings_data)
        return g_settings

class Settings(object):
    def __init__(self, apps, languages, settings_data):
        self.apps = apps
        self.languages = languages
        self.settings_data = settings_data

    def get_tracked_apps(self):
        return [self.apps[appid] for appid in self.apps if self.apps[appid].track]

    def get_tracked_languages(self):
        return [self.languages[lang_key] for lang_key in self.languages if self.languages[lang_key].track]

    def get(self, key, default=None):
        return self.settings_data.get(key, default)

    def __getitem__(self, key):
        return self.settings_data[key]

class AppConfig(object):
    def __init__(self, appid, track, ignore_zero_players, stopwords):
        self.appid = appid
        self.track = track
        self.ignore_zero_players = ignore_zero_players
        self.stopwords = stopwords

    def get_stopwords(self, lang_key):
        if lang_key in self.stopwords:
            return self.stopwords[lang_key]
        return []

class Language(object):
    def __init__(self, lang_key, name, steam_key, track):
        self.lang_key = lang_key
        self.name = name
        self.steam_key = steam_key
        self.track = track

k_logging_format = "[%(asctime)s][%(name)s][%(module)s][%(levelname)s] %(message)s"
def init_logging(log_name, log_level_name):
    full_log_path = os.path.join(os.path.dirname(__file__), "logs", log_name)
    if not os.path.exists(os.path.dirname(full_log_path)):
        print("Creating log dir '{0}'".format(os.path.dirname(full_log_path)))
        os.makedirs(os.path.dirname(full_log_path))
    if get_settings().get("log_to_console", True):
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(logging.Formatter(k_logging_format))
        log_level_name = log_level_name or get_settings().get("log_level").upper()
        log_level = getattr(logging, log_level_name)
        if not log_level:
            raise Exception("Unknown log level specified '{0}'".format(log_level_name))
        console_handler.setLevel(log_level)
        logging.getLogger().addHandler(console_handler)
    file_handler = logging.handlers.TimedRotatingFileHandler(full_log_path, when=get_settings().get("log_when"), backupCount=get_settings().get("log_count"), utc=True)
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(logging.Formatter(k_logging_format))
    logging.getLogger().addHandler(file_handler)

    logging.getLogger().setLevel("INFO")