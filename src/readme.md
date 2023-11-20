# Funcom python tool test

This test is for you to improve this simple worker that gathers reviews from steam (this could take a long time if steam is slow). First run will generate the database file, then every run after that will also check for deleted reviews and try to clean them up. Your objectives:

1. Run the worker and look at the code for ways it could be improved.
2. Improve the worker to the best of your ability.
3. Dockerify the worker and be mindful about deployment.

Good luck and have fun :)

## Requirements
python 2.7 and docker

## Usage
python steam_review_scraper.py

# Gorm Rønning Sørbye

## My Changes

1. Switched from list to set for o(1) lookup where relevant
2. Uses urllib3 for http pooling, avoid making new connections when fetching reviews
3. Batches querys to sqlite database, reduces number of writes to disk making it faster
4. Uses docker and docker compose to create a container for each of the steam apps in requirements.txt

## My assumption

Stay on python 2.7
Focus on performance upgrades not features
By being "mindful" about deployment i can change the code ot take a single app argument and run it in a docker container

Thank you for the opportunity to work on this, it was fun!