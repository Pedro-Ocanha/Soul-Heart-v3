"""
converter_web.py - prepara o Soul Heart pra rodar no navegador (pygbag).

COMO USAR:
  1) Coloque este arquivo na mesma pasta do seu jogo.
  2) python converter_web.py seu_jogo.py
  3) Ele gera  soul_heart/main.py  (pronto pro pygbag) e NAO altera o original.

O que ele faz:
  - troca pygame.font.SysFont(None, N) por pygame.font.Font(None, N)
  - coloca o loop principal dentro de  async def main()
  - adiciona  await asyncio.sleep(0)  depois do pygame.display.flip()
  - troca o final por  asyncio.run(main())
"""
import os
import re
import sys

if len(sys.argv) < 2:
    sys.exit("Uso: python converter_web.py seu_jogo.py")

origem = sys.argv[1]
pasta_saida = "soul_heart"

with open(origem, encoding="utf-8") as f:
    linhas = f.read().split("\n")

# 1) fontes
linhas = [l.replace("pygame.font.SysFont(None,", "pygame.font.Font(None,") for l in linhas]

# 2) acha o loop principal e o final do arquivo
try:
    i_loop = next(i for i, l in enumerate(linhas) if l.startswith("while rodando:"))
    i_fim = next(i for i in range(i_loop, len(linhas)) if linhas[i].startswith("pygame.quit()"))
except StopIteration:
    sys.exit("Nao achei 'while rodando:' ou 'pygame.quit()' no inicio de linha. "
             "Confira se o arquivo e o certo.")

# 3) o que o loop reatribui precisa ser 'global' dentro da funcao
globais = ["tela_jogo", "creditos_y", "tempo_total", "rodando", "opcoes_ignora_eventos"]
corpo = linhas[i_loop:i_fim]
for nome in globais:      # aviso se alguma variavel nao existir no loop
    if not any(re.match(rf"\s*{nome}\s*[-+]?=", l) for l in corpo):
        print(f"[aviso] '{nome}' nao e atribuida no loop (ok, so nao precisava de global)")

novo_corpo = []
for l in corpo:
    novo_corpo.append(("    " + l) if l.strip() else l)
    if l.strip() == "pygame.display.flip()":
        novo_corpo.append("        await asyncio.sleep(0)   # devolve o controle ao navegador")

if not any("await asyncio.sleep(0)" in l for l in novo_corpo):
    sys.exit("Nao achei 'pygame.display.flip()' dentro do loop.")

cabecalho = ["async def main():", f"    global {', '.join(globais)}"]
final = ["    pygame.quit()", "    sys.exit()", "", "", "asyncio.run(main())", ""]

saida = linhas[:i_loop] + cabecalho + novo_corpo + final

os.makedirs(pasta_saida, exist_ok=True)
destino = os.path.join(pasta_saida, "main.py")
with open(destino, "w", encoding="utf-8") as f:
    f.write("\n".join(saida))

# valida a sintaxe
import ast
try:
    ast.parse("\n".join(saida))
except SyntaxError as e:
    sys.exit(f"Gerado, mas com erro de sintaxe na linha {e.lineno}: {e.msg}")

print(f"OK! Gerado: {destino}")
print("Copie sua pasta 'assets' pra dentro de soul_heart/ e rode:  pygbag soul_heart")
