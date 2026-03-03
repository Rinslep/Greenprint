# pipeline/__init__.py
#
# TODO: Export the pipeline's public interface.
# - Expose a top-level `process(raw_string, source_url, source_site, author)` function
#   that runs the full pipeline: decode → validate → version filter → broken detection
#   → recipe inference → crafting graph → ratio analysis → throughput analysis → storage.
# - Also expose individual stage functions so each can be tested in isolation.
# - Keep this file thin — orchestration logic belongs in a separate orchestrator module
#   (add pipeline/orchestrator.py when building step 15 in the build order).
