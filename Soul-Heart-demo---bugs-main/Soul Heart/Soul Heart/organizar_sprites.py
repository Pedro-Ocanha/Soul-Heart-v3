import os, pygame
pygame.init()
pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "jogador")
arqs = [a for a in sorted(os.listdir(pasta)) if a.lower().endswith(".png")]
imgs = [pygame.image.load(os.path.join(pasta, a)) for a in arqs]
esc = 0.5
w = int(max(i.get_width() for i in imgs) * esc) + 10
h = int(max(i.get_height() for i in imgs) * esc) + 30
cols = 6
linhas = (len(imgs) + cols - 1) // cols
folha = pygame.Surface((cols * w, linhas * h)); folha.fill((60, 60, 70))
fonte = pygame.font.Font(None, 18)
for k, (a, im) in enumerate(zip(arqs, imgs)):
    x, y = (k % cols) * w, (k // cols) * h
    im = pygame.transform.scale(im, (int(im.get_width() * esc), int(im.get_height() * esc)))
    folha.blit(im, (x + 5, y + 5))
    folha.blit(fonte.render(a, True, (255, 255, 0)), (x + 5, y + h - 20))
pygame.image.save(folha, os.path.join(pasta, "_folha.png"))
print("salvo em assets/jogador/_folha.png")