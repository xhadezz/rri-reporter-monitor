import requests, re, json, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, urlunsplit

BASE='https://rri.co.id/surakarta/'
LIST_BASE='https://rri.co.id/surakarta/terbaru/list/'
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'id-ID,id;q=0.9,en;q=0.8'}
MONTHS={'Jan':'01','Feb':'02','Mar':'03','Apr':'04','Mei':'05','Jun':'06','Jul':'07','Agu':'08','Sep':'09','Okt':'10','Nov':'11','Des':'12'}
SIFA_RE=re.compile(r'\(\s*SIFA\s*\)',re.I)
EDWI_RE=re.compile(r'\(\s*Edwi(?:\s*/\s*Rill)?\s*\)',re.I)
ARTICLE_RE=re.compile(r'^https://rri\.co\.id/surakarta/(?:[^/?#]+/)*\d+(?:/[^?#]*)?/?$',re.I)
AUTHOR_TARGET='Soufi Asegaf'
DISCOVERY_WORKERS=16
ARTICLE_WORKERS=20
REQUEST_TIMEOUT=(6,20)
_tls=threading.local()

def session():
 if not hasattr(_tls, 'session'):
  import requests.adapters
  _tls.session=requests.Session()
  adapter=requests.adapters.HTTPAdapter(pool_connections=ARTICLE_WORKERS, pool_maxsize=ARTICLE_WORKERS, max_retries=0)
  _tls.session.mount('http://', adapter); _tls.session.mount('https://', adapter)
  _tls.session.headers.update(HEADERS)
 return _tls.session


def http_get(url, **kwargs):
 return session().get(url, **kwargs)


def clean(s): return re.sub(r'\s+',' ',s or '').strip()


def normalize_url(href,base):
 u=urljoin(base,href).split('#')[0]; p=urlsplit(u); return urlunsplit((p.scheme,p.netloc,p.path.rstrip('/'),'',''))


def parse_date(text):
 m=re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Sep|Okt|Nov|Des)[a-z]*\s+(\d{4})',text or '',re.I)
 if not m:return '',''
 d,mon,y=m.groups(); return f'{int(d):02d} {mon} {y}',f'{y}-{MONTHS.get(mon[:3].title(),"01")}-{int(d):02d}'


def discover_one(url,page):
 for attempt in range(3):
  try:
   r=http_get(url,headers=HEADERS,timeout=REQUEST_TIMEOUT); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser'); out={}
   for a in soup.find_all('a',href=True):
    href=normalize_url(a['href'],url)
    if not ARTICLE_RE.match(href): continue
    parts=urlsplit(href).path.strip('/').split('/')
    if len(parts)<3: continue
    out[href]={'url':href,'title':clean(a.get_text(' ',strip=True)),'category':'/'.join(parts[1:-1])}
   return page,list(out.values()),''
  except Exception as e:
   if attempt==2:return page,[],f'{type(e).__name__}: {e}'
   time.sleep(.6*(attempt+1))


def discover(max_pages=50):
 all_items={}; errs=0
 urls=[]
 for p in range(1,max_pages+1): urls.append((LIST_BASE if p==1 else urljoin(LIST_BASE,str(p)),p))
 for p in range(1,min(max_pages,10)+1): urls.append((f'https://rri.co.id/surakarta/berita' if p==1 else f'https://rri.co.id/surakarta/berita/{p}',p))
 with ThreadPoolExecutor(max_workers=DISCOVERY_WORKERS, thread_name_prefix='discover') as ex:
  fs=[ex.submit(discover_one,u,p) for u,p in urls]
  for f in as_completed(fs):
   page,items,err=f.result()
   if err: errs+=1
   for x in items: all_items[x['url']]=x
 return list(all_items.values()),errs


def safe_text(node):
 try:return clean(node.get_text(' ',strip=True)) if node else ''
 except:return ''


def safe_attr(node,key,default=''):
 try:
  v=node.get(key,default) if node else default; return v if v is not None else default
 except:return default


def extract_body(soup):
 lead_re=re.compile(r'RRI\s*\.\s*CO\s*\.\s*ID,\s*Surakarta\s*[–—-]',re.I)
 stop_re=re.compile(r'Kata\s*Kunci\s*/\s*Tags|Kata\s*Kunci|Tags\b',re.I)
 candidates=[]
 def segment(text):
  text=clean(text); m=lead_re.search(text)
  if not m:return ''
  tail=text[m.start():]; st=stop_re.search(tail)
  if st: tail=tail[:st.start()]
  return clean(tail)
 # JSON-LD articleBody
 try:
  for sc in soup.find_all('script',type=re.compile(r'application/ld\+json',re.I)):
   raw=sc.string or sc.get_text(' ',strip=True)
   try:data=json.loads(raw)
   except:continue
   stack=data if isinstance(data,list) else [data]
   while stack:
    o=stack.pop()
    if isinstance(o,dict):
     if isinstance(o.get('articleBody'),str): candidates.append(clean(o['articleBody']))
     stack.extend(v for v in o.values() if isinstance(v,(dict,list)))
    elif isinstance(o,list): stack.extend(o)
 except: pass
 try:
  roots=list(soup.find_all('article')[:20])+list(soup.find_all('main')[:20])
  for e in soup.find_all(True):
   ident=' '.join([str(e.get('id','') or ''),' '.join(e.get('class',[]) or [])])
   if re.search(r'(article[-_ ]?(body|content)|post[-_ ]?content|news[-_ ]?content|detail[-_ ]?(article|content)|content[-_ ]?article)',ident,re.I): roots.append(e)
  seen=set()
  for root in roots:
   if id(root) in seen:continue
   seen.add(id(root)); clone=BeautifulSoup(str(root),'html.parser')
   for e in clone.find_all(['script','style','noscript','svg','header','footer','nav','aside','form','figure','figcaption']):
    try:e.decompose()
    except:pass
   for e in list(clone.find_all(True)):
    ident=' '.join([str(e.get('id','') or ''),' '.join(e.get('class',[]) or [])])
    if re.search(r'(breadcrumb|share|social|related|recommend|sidebar|comment|(^|[-_ ])tags?($|[-_ ])|keywords?)',ident,re.I) and e is not clone:
     try:e.decompose()
     except:pass
   s=segment(safe_text(clone))
   if s:candidates.append(s)
 except:pass
 try:
  s=segment(safe_text(soup))
  if s:candidates.append(s)
 except:pass
 marker=[x for x in candidates if SIFA_RE.search(x) or EDWI_RE.search(x)]
 return max(marker or candidates,key=len) if (marker or candidates) else ''


def extract_author(soup,raw_text):
 vals=[]
 text=raw_text or ''
 # Prioritaskan byline yang tampil di halaman RRI.
 patterns=[
  r'\bOleh\s*[-–—:]\s*([^\n|]{2,100}?)(?=\s*(?:,|\||[-–—])?\s*(?:Editor|RRI\.CO\.ID|Dipublikasikan|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Sep|Okt|Nov|Des))\b)',
  r'\bOleh\s*[-–—:]\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.\s]{1,80})'
 ]
 for pat in patterns:
  for m in re.finditer(pat,text,re.I):
   v=clean(m.group(1)).strip(' -–—,|')
   if v: vals.append(v)
 # Jika byline tidak terbaca, cek metadata author sebagai fallback.
 try:
  for sel,attr in [('meta[name="author"]','content'),('meta[property="article:author"]','content'),('meta[name="byl"]','content')]:
   v=safe_attr(soup.select_one(sel),attr,'')
   if v: vals.append(v)
 except: pass
 # JSON-LD hanya fallback terakhir.
 try:
  for sc in soup.find_all('script',type=re.compile(r'application/ld\+json',re.I)):
   raw=sc.string or sc.get_text(' ',strip=True)
   try:data=json.loads(raw)
   except:continue
   stack=data if isinstance(data,list) else [data]
   while stack:
    o=stack.pop()
    if isinstance(o,dict):
     a=o.get('author'); aa=a if isinstance(a,list) else [a]
     for v in aa:
      if isinstance(v,dict) and isinstance(v.get('name'),str): vals.append(v['name'])
      elif isinstance(v,str): vals.append(v)
     stack.extend(v for v in o.values() if isinstance(v,(dict,list)))
    elif isinstance(o,list): stack.extend(o)
 except: pass
 # Normalisasi nama.
 for v in vals:
  n=clean(re.sub(r'[^A-Za-zÀ-ÿ.\s]',' ',v))
  if re.fullmatch(r'soufi\s+a(?:s)?segaf',n,re.I): return 'Soufi Asegaf'
 for v in vals:
  n=clean(re.sub(r'[^A-Za-zÀ-ÿ.\s]',' ',v))
  if n and n.lower() not in {'rri','rri.co.id','rri surakarta'} and len(n.split())<=8:
   return n
 return ''


def fetch_article(item):
 url=item['url']
 try:
  r=http_get(url,headers={'Referer':LIST_BASE},timeout=REQUEST_TIMEOUT,allow_redirects=True); r.raise_for_status(); html=r.text or ''; soup=BeautifulSoup(html,'html.parser')
  title=safe_text(soup.find('h1') or soup.find('h2')) or item.get('title',''); raw_text=safe_text(soup); author=extract_author(soup,raw_text); published,published_date=parse_date(raw_text)
  meta=soup.find('meta',attrs={'name':'description'}) or soup.find('meta',attrs={'property':'og:description'}); excerpt=clean(safe_attr(meta,'content','')); body=extract_body(soup)
  raw_sifa=int(bool(SIFA_RE.search(html))); body_sifa=int(bool(SIFA_RE.search(body) or SIFA_RE.search(raw_text)))
  raw_edwi=int(bool(EDWI_RE.search(html))); body_edwi=int(bool(EDWI_RE.search(body) or EDWI_RE.search(raw_text)))
  author_clean=clean(re.sub(r'[^A-Za-zÀ-ÿ.\s]',' ',author))
  author_match=int(bool(re.fullmatch(r'soufi\s+a(?:s)?segaf',author_clean,re.I)))
  # Fallback hanya jika byline/metadata gagal diekstrak: cari pola byline Soufi Asegaf pada halaman.
  if not author_match:
   author_match=int(bool(re.search(r'\bOleh\s*[-–—:]\s*Soufi\s+Asegaf\b',raw_text,re.I)))
  return {**item,'title':title,'author':('Soufi Asegaf' if author_match else author),'published':published,'published_date':published_date,'excerpt':excerpt,'content':body,'raw_sifa':raw_sifa,'body_sifa':body_sifa,'raw_edwi':raw_edwi,'body_edwi':body_edwi,'author_match':author_match,'error':''}
 except Exception as e:
  return {**item,'author':'','published':'','published_date':'','excerpt':'','content':'','raw_sifa':0,'body_sifa':0,'raw_edwi':0,'body_edwi':0,'author_match':0,'error':f'{type(e).__name__}: {e}'}


