## LER Sandbox

# Kode i projektet skal i Git Repositoriet LER-U_redesign i LER Devops projektet.

Som det første skal du lave en PAT (Personal Access Token) i Devops.

* Klik på dit billede på startsiden i DevOps, vælg Security

* Vælg Personal Access Tokens til venste.  New Token

* Kald den LER, med udløb fx 1/1 2026, Full Access til Code. Create

* Kopier til klippebord. Gem et sikkert sted i en fil, fx på h-drevet.

Udviklerne i LER projektet (som defineret via LER’s DevOps projekt) kan logge på srvpython16.

Analyseprogrammer, MobaXterm.

# Ny session.

* Åbn MobaXterm på din computer
* Log på med din tretegnsident og dit almindelige Windows-password.

Du lander ved en prompt.

Du skal en gang for alle køre scriptet
* /opt/dst/dst-spark/scripts/init_sandbox.sh

Du bliver promptet for at indtaste MinIO brugernavn og password.
* Tast din ident (med små bogstaver) og tast Passw0rd1234

* Du bliver promptet for MinIO hostname. Tryk enter for at vælge localhost.

Kommandoen sætter nogle indledene ting op, heunder at initiere anaconda

* Den ender med at logge dig af. Tryk R for at logge på igen

Nu skal du køre scriptet
* /opt/dst/dst-spark/scripts/run_sandbox.sh

Det skal du køre hver gang du starter en arbejdssession. Den opretter en sandbox arbejdsmappe i dit home-directory og  starter jupyter derfra. Marker linjen der starter med http://srvpython16. Markeringen er kopieret til klippebordet (bare ved at markere det).

* Gå til din pc, start en browser, fx Google Chrome, paste linjen ind. Frem kommer Jupyter. Klik på Git ikonen til venstre og vælg Clone A Repository.

# Clone DevOps repos.
I URI feltet skal du paste følgende lange streng,hvor PAT er din konkrete PAT fra tidligere:
* http://PAT@srvdevops1.dst.local/Danmarksstatistik/LER%20%28L%C3%A6rer-Elev%20registreret%29/_git/LER-U_redesign

Det kommer til at se ud cirka sådan her,

* http://vn2zxczczxczxcrkkskkeiivjjxkskskkemtynphjhdoa@srvdevops1.dst.local/Danmarksstatistik/LER%20%28L%C3%A6rer-Elev%20registreret%29/_git/LER-U_redesign

Derefter vil filbrowseren vise et Gitr repo i din mappe:

# Udløbet PAT.

Hvis/når din Personal Access Token i DevOps udløber, skal du forny den 

* Klik på dit billede på startsiden i DevOps, vælg Security

* Vælg din eksisterende PAT og klik på Regenerate

* Kopier din PAT til et sted, hvor du kan finde den igen.


I MobaXterm skal du nu:

* Overskrive variablen GIT_AUTH_TOKEN med din nye PAT (minPATtoken): 

    (miniconda3) {user}@srvpython16:~$ export GIT_AUTH_TOKEN=minPATtoken

* Vær obs på, at den er sat korrekt. Værdien af variablen kan tjekkes med: 

    (miniconda3) {user}@srvpython16:~$ echo $GIT_AUTH_TOKEN


Herefter skal du køre init-scriptet igen. Hvis det fejler, så log ud af MobaXterm og ind igen. 
* /opt/dst/dst-spark/scripts/init_sandbox.sh


# Storage på MinIO
Systemet bruger MinIO som storage. 
MinIO er en open-source, S3-kompatibel objektlagringsserver, der gemmer filer som objekter i “buckets” og kan køre on-prem.
Den bruges til hurtig, skalerbar lagring til apps, der taler Amazons S3-API.

MinIO på srvpython16 kan tilgås på på 
* http://srvpython16:9001

Her logger vi ind med username (små bogstaver) og Passw0rd1234, som dannet i init-scriptet

Her kan vi bl.a. se de buckets og fx delta-filer, vi kreerer.

# Spark Master at spark://58bb5d79d236:7077
Vi kan se hvilke clustre der kører på 
* http://srvpython16:8080/


# Det opsatte miljø.

Miljøet er foreløbigt defineret således:

name: sandbox_env

//#conda env update -f env.yml --prefix /opt/miniconda3/envs/sandbox_env

dependencies:
- python=3.12
- pip
- pip:
- pandas
- polars
- jupyter
- jupyterlab-git
- pyspark

Ændringer til miljøet kan udføres af njn.
