# scraper/reddit.py
#
# TODO: Scraper for r/factorio using PRAW.
#
# Source characteristics:
# - Rate limit: 60 requests/minute (PRAW handles this automatically, but stay aware).
# - Blueprint strings appear in post bodies and comments — both must be searched.
# - Use PRAW's subreddit search to find posts containing blueprint strings.
#
# Implementation notes:
# - Extend BaseScraper.
# - Authenticate via config.REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT.
# - Search r/factorio for posts likely to contain blueprints (keyword + flair filters).
# - For each post: run the base class string extraction regex over the post body.
# - Also iterate top-level comments and their replies; apply the same regex.
# - Author identifier: use praw Redditor.name (stored raw; anonymised in storage layer).
# - source_url: direct link to the post or comment.
# - Pass candidates to self._process_string(raw, source_url, author).
# - Record progress by post/comment ID in the resumability DB to allow incremental runs.
# - PRAW enforces its own rate limiting — don't add extra sleep beyond what PRAW requires
#   unless the base class delay is longer.


from scraper.base import BaseScraper


class RedditScraper(BaseScraper):
    pass  # TODO: implement
