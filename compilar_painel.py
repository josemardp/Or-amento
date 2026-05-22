import re
import os

def compile_dashboard():
    print("Iniciando compilação do painel autônomo...")
    
    # 1. Ler index.html
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    # 2. Ler estilos.css
    with open("estilos.css", "r", encoding="utf-8") as f:
        css = f.read()
        
    # 3. Ler dados.js
    with open("dados.js", "r", encoding="utf-8") as f:
        dados = f.read()
        
    # 4. Ler app.js
    with open("app.js", "r", encoding="utf-8") as f:
        app = f.read()
        
    # 5. Substituir link css por <style>
    css_pattern = re.compile(r'<link\s+rel="stylesheet"\s+href="estilos\.css"[^>]*>')
    html = css_pattern.sub(f"<style>\n{css}\n</style>", html)
    
    # 6. Substituir script dados.js por <script>
    dados_pattern = re.compile(r'<script\s+src="dados\.js"[^>]*></script>')
    html = dados_pattern.sub(f"<script>\n{dados}\n</script>", html)
    
    # 7. Substituir script app.js por <script>
    app_pattern = re.compile(r'<script\s+src="app\.js"[^>]*></script>')
    html = app_pattern.sub(f"<script>\n{app}\n</script>", html)
    
    # 8. Escrever no Painel_Orcamento_SSP_SAP.html
    with open("Painel_Orcamento_SSP_SAP.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Compilação concluída com sucesso! Painel salvo em 'Painel_Orcamento_SSP_SAP.html'.")

if __name__ == "__main__":
    compile_dashboard()
