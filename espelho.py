# Espelho: copia o simulador publicado + dados para a pasta do site.
# No GitHub (repositorio do simulador) roda sozinho a cada 30 min; a origem vem do segredo FONTE.
# Localmente, publicar.py --teste usa espelhar_local() para montar um site de teste.
import json, os, sys, urllib.parse, urllib.request

PASTAS = {"tabelas": ["maggi/tabelas", "Maggi/tabelas"], "documentos": ["Maggi/documentos", "maggi/documentos"]}
ARQS = ["tabelas.json", "medias.json", "conhecimento.json"]


def _grava(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(dados)


def _finaliza(destino, conhecimento_bytes, listas):
    c = json.loads(conhecimento_bytes.decode("utf-8"))
    c["documentos_base_url"] = "dados/documentos/"
    _grava(os.path.join(destino, "dados", "conhecimento.json"), json.dumps(c, ensure_ascii=False, indent=1).encode("utf-8"))
    for pasta, nomes in listas.items():
        lista = [{"type": "file", "name": n, "download_url": "dados/" + pasta + "/" + urllib.parse.quote(n)} for n in sorted(nomes)]
        _grava(os.path.join(destino, "dados", "lista_" + pasta + ".json"), json.dumps(lista, ensure_ascii=False).encode("utf-8"))
        d = os.path.join(destino, "dados", pasta)
        for velho in os.listdir(d) if os.path.isdir(d) else []:
            if velho not in nomes:
                os.remove(os.path.join(d, velho))
    _grava(os.path.join(destino, "robots.txt"), b"User-agent: *\nDisallow: /\n")
    _grava(os.path.join(destino, ".nojekyll"), b"")


def espelhar_local(maggi_dir, destino):
    _grava(os.path.join(destino, "index.html"), open(os.path.join(maggi_dir, "publicado", "index.html"), "rb").read())
    for a in ARQS[:2]:
        _grava(os.path.join(destino, "dados", a), open(os.path.join(maggi_dir, a), "rb").read())
    listas = {}
    for pasta in PASTAS:
        origem = os.path.join(maggi_dir, pasta)
        nomes = set(n for n in os.listdir(origem) if os.path.isfile(os.path.join(origem, n)))
        for n in nomes:
            _grava(os.path.join(destino, "dados", pasta, n), open(os.path.join(origem, n), "rb").read())
        listas[pasta] = nomes
    _finaliza(destino, open(os.path.join(maggi_dir, "conhecimento.json"), "rb").read(), listas)


def espelhar_remoto(fonte, destino, token=None):
    def baixa(url, api=False):
        req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%"), headers={"User-Agent": "espelho"})
        if api and token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    raw = "https://raw.githubusercontent.com/" + fonte + "/main/Maggi/"
    for a in ARQS[:2]:
        _grava(os.path.join(destino, "dados", a), baixa(raw + a))
    listas = {}
    for pasta, variantes in PASTAS.items():
        achados = {}
        for v in variantes:
            try:
                itens = json.loads(baixa("https://api.github.com/repos/" + fonte + "/contents/" + v + "?ref=main", api=True))
            except Exception:
                continue
            for it in itens:
                if it.get("type") == "file" and it["name"] not in achados:
                    achados[it["name"]] = it["download_url"]
        if not achados:
            raise SystemExit("lista vazia: " + pasta)  # nao apaga nada se a origem falhar
        for n, url in achados.items():
            _grava(os.path.join(destino, "dados", pasta, n), baixa(url))
        listas[pasta] = set(achados)
    _finaliza(destino, baixa(raw + "conhecimento.json"), listas)


if __name__ == "__main__":
    fonte = os.environ.get("FONTE", "").strip()
    if not fonte:
        sys.exit("defina o segredo FONTE")
    espelhar_remoto(fonte, os.path.dirname(os.path.abspath(__file__)), os.environ.get("GH_TOKEN"))
    print("ok")
