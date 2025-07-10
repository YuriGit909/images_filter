import os
import urllib.request
from abc import ABC, abstractmethod
import uuid
from PIL import Image, ImageOps, ImageFilter
from flask import Flask, flash, render_template, request, redirect, url_for

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Flask app
app = Flask(__name__)
app.secret_key = "secretKey"

# Classe Imagem
class Imagem:
    def __init__(self, caminho):
        self.caminho = caminho
        self.imagem = Image.open(caminho)

    def get_imagem(self):
        return self.imagem

    def salvar(self, nova_imagem, sufixo):
        nome_arquivo = os.path.basename(self.caminho)
        nome, ext = os.path.splitext(nome_arquivo)
        novo_nome = f"{nome}_{sufixo}{ext}"
        caminho_salvo = os.path.join(UPLOAD_FOLDER, novo_nome)
        nova_imagem.save(caminho_salvo)
        print(f"Imagem salva como: {caminho_salvo}")
        return caminho_salvo

# Classe Download
class Download:
    @staticmethod
    def baixar_imagem(url):
        try:
            nome_arquivo = f"{uuid.uuid4()}_" + url.split("/")[-1]
            caminho = os.path.join(UPLOAD_FOLDER, nome_arquivo)
            urllib.request.urlretrieve(url, caminho)
            print(f"Imagem baixada: {caminho}")
            return caminho
        except Exception as e:
            print(f"Erro ao baixar imagem: {e}")
            return None

# Classe base para filtros
class Filtro(ABC):
    @abstractmethod
    def aplicar(self, imagem):
        pass

# Filtros
class EscalaCinza(Filtro):
    def aplicar(self, imagem):
        largura, altura = imagem.size
        nova_imagem = Image.new("RGB", (largura, altura))
        pixels_originais = imagem.load()
        pixels_novos = nova_imagem.load()

        for y in range(altura):
            for x in range(largura):
                r, g, b = pixels_originais[x, y]
                cinza = (r + g + b) // 3
                pixels_novos[x, y] = (cinza, cinza, cinza)
        return nova_imagem

class PretoBranco(Filtro):
    def aplicar(self, imagem):
        imagem = imagem.convert("RGB")
        imagem_cinza = imagem.convert("L")
        largura, altura = imagem.size
        limiar = 128
        imagem_pb = Image.new("RGB", (largura, altura))
        pixels_pb = imagem_pb.load()
        pixels_cinza = imagem_cinza.load()

        for y in range(altura):
            for x in range(largura):
                cor = 255 if pixels_cinza[x, y] >= limiar else 0
                pixels_pb[x, y] = (cor, cor, cor)
        return imagem_pb

class FotoNegativa(Filtro):
    def aplicar(self, imagem):
        return ImageOps.invert(imagem.convert("RGB"))

class Contorno(Filtro):
    def aplicar(self, imagem):
        return imagem.convert("L").filter(ImageFilter.FIND_EDGES)

class Blurred(Filtro):
    def aplicar(self, imagem):
        return imagem.filter(ImageFilter.GaussianBlur(radius=2))

class Cartoon(Filtro):
    def aplicar(self, imagem):
        suavizada = imagem.filter(ImageFilter.MedianFilter(size=5))
        bordas = ImageOps.invert(imagem.convert('L').filter(ImageFilter.FIND_EDGES))
        resultado = suavizada.convert('L').copy()
        resultado.paste(bordas, (0, 0), mask=bordas)
        return resultado.convert('RGB')

# Programa principal
class ProgramaImagemWeb:
    def __init__(self):
        self.imagem_obj = None
        self.filtros = {
            "1": ("Escala de Cinza", EscalaCinza()),
            "2": ("Preto e Branco", PretoBranco()),
            "3": ("Negativo", FotoNegativa()),
            "4": ("Contorno", Contorno()),
            "5": ("Desfoque (Blur)", Blurred()),
            "6": ("Cartoon", Cartoon()),
        }

    def carregar_imagem(self, caminho_ou_url):
        if caminho_ou_url.startswith("http"):
            caminho = Download.baixar_imagem(caminho_ou_url)
            if not caminho:
                raise Exception("Erro ao baixar imagem da URL.")
        else:
            if not os.path.exists(caminho_ou_url):
                raise Exception("Arquivo de imagem local não encontrado.")
            caminho = caminho_ou_url

        self.imagem_obj = Imagem(caminho)

    def aplicar_filtro(self, codigo_filtro):
        if not self.imagem_obj:
            raise Exception("Nenhuma imagem carregada.")
        if codigo_filtro not in self.filtros:
            raise Exception("Filtro inválido.")

        filtro = self.filtros[codigo_filtro][1]
        imagem_filtrada = filtro.aplicar(self.imagem_obj.get_imagem())
        caminho_salvo = self.imagem_obj.salvar(imagem_filtrada, self.filtros[codigo_filtro][0].replace(" ", "_").lower())
        return caminho_salvo

# Instância principal
programa = ProgramaImagemWeb()

# Rota principal
@app.route('/', methods=['GET', 'POST'])
def index():
    imagem_original_url = None
    imagem_filtrada_url = None

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        url_imagem = request.form.get('url_imagem')
        filtro_selecionado = request.form.get('filtro')

        try:
            if arquivo and arquivo.filename:
                nome_arquivo = f"{uuid.uuid4()}_{arquivo.filename}"
                caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_arquivo)
                arquivo.save(caminho_arquivo)
                programa.carregar_imagem(caminho_arquivo)

            elif url_imagem:
                programa.carregar_imagem(url_imagem)

            else:
                flash("Nenhuma imagem foi enviada.")
                return redirect(url_for('index'))

            caminho_filtrado = programa.aplicar_filtro(filtro_selecionado)

            imagem_original_url = os.path.relpath(programa.imagem_obj.caminho, BASE_DIR).replace('\\', '/').replace('static/', '')
            imagem_filtrada_url = os.path.relpath(caminho_filtrado, BASE_DIR).replace('\\', '/').replace('static/', '')

        except Exception as e:
            flash(str(e))
            return redirect(url_for('index'))

    return render_template(
        'index.html',
        filtros=programa.filtros,
        imagem_original=imagem_original_url,
        imagem_filtrada=imagem_filtrada_url
    )

if __name__ == '__main__':
    app.run(debug=True, port=5050)
