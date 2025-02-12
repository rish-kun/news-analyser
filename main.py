from news import get_sources
from sheets import update_sources, write_links, get_details
from rss import check_keywords

# sources = get_sources()
# update_sources(sources)
# ``kwds  = get_details().values()

kwds =['GST']
kw_link = check_keywords(kwds)
if not kw_link:
    kw_link={"No results found":[]}
write_links(kw_link)

