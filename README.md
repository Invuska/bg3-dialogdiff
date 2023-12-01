# bg3-dialogdiff

A simple tool that allows you to see what dialog has been changed/added from patch to patch. Built in Python & Streamlit. Basically most code is in `main.py` (yes I know but it's very much in dev right now), though the creation of cache files used extensively for the online tool is in `create_cache_files.ipynb`.

Development of the tool was done in haste - as such many parts may seem missing, messy, or suboptimal. Optimizations will come in the future.

This tool is heavily reliant on work done by roksik-dnd et al. on Tumblr. It also checks differences from the HTMLs derived from their parser tool.
