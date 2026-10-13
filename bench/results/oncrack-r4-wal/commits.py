import sys, struct, sqlite3, shutil, os, tempfile, collections
src=sys.argv[1]; n0=int(sys.argv[2]); n1=int(sys.argv[3])
work=tempfile.mkdtemp()
for f in ("production.sqlite3","production.sqlite3-wal"): shutil.copy(os.path.join(src,f),os.path.join(work,f))
wal=open(work+"/production.sqlite3-wal","rb").read()
magic,ver,ps,seq,s1,s2,c1,c2=struct.unpack(">IIIIIIII",wal[:32])
db=sqlite3.connect(work+"/production.sqlite3")
owner={p:n for n,p in db.execute("select name,pageno from dbstat")}
off=32; cur=[]; k=0
while off+24+ps<=len(wal):
    pg,dbs,a,b=struct.unpack(">IIII",wal[off:off+16])
    if (a,b)!=(s1,s2): break
    cur.append(pg)
    if dbs:
        if n0<=k<n1: print(k, len(cur), [(p,owner.get(p,'?')[:24]) for p in cur])
        k+=1; cur=[]
    off+=24+ps
