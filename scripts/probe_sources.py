from urllib.request import Request, urlopen
from urllib.parse import quote
from bs4 import BeautifulSoup
import re
TARGETS = [
    "https://ai.zju.edu.cn/zstz/list1.htm",
    "https://www.cs.zju.edu.cn/",
    "https://www.cst.zju.edu.cn/36207/list.htm",
    "https://www.cst.zju.edu.cn/36267/list.htm",
    "https://s2.zju.edu.cn/search/info.do?words=" + quote("计算机科学与技术学院"),
    "https://s2.zju.edu.cn/search/info.do?words=" + quote("软件学院"),
    "https://s2.zju.edu.cn/search/info.do?words=" + quote("奖学金"),
    "https://mse.zju.edu.cn/51031/list.htm",
    "https://ic.zju.edu.cn/tzgg/",
    "https://grs.zju.edu.cn/",
]
for url in TARGETS:
    try:
        with urlopen(Request(url, headers={"User-Agent":"CampusAgentPublicNotices/0.1 (public pages only)","Accept":"text/html"}), timeout=15) as resp:
            raw=resp.read(900000)
            soup=BeautifulSoup(raw,"html.parser")
            entries=[(a.get_text(" ",strip=True) or a.get("title",""),a.get("href","")) for a in soup.select("a[href]") if re.search(r"/\d{4}/\d{4}/c\d+a\d+/(?:page|pagem)\.htm",a.get("href",""))]
            print("OK",url,"status",resp.status,"final",resp.url,"bytes",len(raw),"title",str(soup.title.get_text(" ",strip=True) if soup.title else "")[:80],"articles",len(entries),"samples",[(s[:55],u[:110]) for s,u in entries[:3]],flush=True)
            if "s2.zju.edu.cn" in url:
                a = next((a for a in soup.select("a[href]") if re.search(r"/\\d{4}/\\d{4}/c\\d+a\\d+/", a.get("href",""))),None)
                if a:
                    p = a
                    for i in range(3):
                        p = p.parent
                        print("PARENT",i+1,p.name,p.get("class"),repr(p.get_text(" ",strip=True)[:250]),flush=True)
    except Exception as exc:
        print("FAIL",url,type(exc).__name__,str(exc)[:120],flush=True)
