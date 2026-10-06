import json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
# Reuse proven RRI discovery/extraction code.
sys.path.insert(0, os.path.dirname(__file__))
from scanner_core import discover, fetch_article, ARTICLE_WORKERS

def main():
    items, discovery_errors = discover(50)
    fetched=[]; errors=discovery_errors
    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS, thread_name_prefix='article') as ex:
        fs=[ex.submit(fetch_article,x) for x in items]
        for f in as_completed(fs):
            d=f.result(); fetched.append(d)
            if d.get('error'): errors += 1
    articles=[]
    for d in fetched:
        if d.get('error'): continue
        sifa=bool(d.get('body_sifa'))
        edwi=bool(d.get('body_edwi') and d.get('author_match'))
        if sifa or edwi:
            articles.append({'url':d['url'],'title':d.get('title','-'),'category':d.get('category','-'),'author':d.get('author','-'),'published':d.get('published',''),'published_date':d.get('published_date',''),'sifa':sifa,'edwi':edwi})
    articles.sort(key=lambda x:(x.get('published_date',''),x.get('title','')), reverse=True)
    now=datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %z')
    data={'meta':{'last_scan':now,'discovered':len(items),'fetched':len(fetched),'matched':len(articles),'errors':errors,'workers':ARTICLE_WORKERS},'articles':articles}
    with open(os.path.join(os.path.dirname(__file__),'data.json'),'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps(data['meta'],ensure_ascii=False))
if __name__=='__main__': main()
