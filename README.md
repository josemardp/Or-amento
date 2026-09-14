# Painel de Orçamentos - Segurança Pública (SSP) e Sistema Prisional (SAP)

Comparação do gasto executado em segurança pública e sistema prisional pelos **27 estados
brasileiros, de 2015 a 2026**, a partir dos dados que os próprios estados publicam no
SICONFI/Tesouro Nacional.

**No ar, sem login:** https://josemardp.github.io/Or-amento/

## O problema

Comparar orçamento de segurança entre estados parece simples e não é. Três armadilhas
derrubam qualquer comparação ingênua, e as três estão tratadas aqui:

1. **Cada estado organiza a pasta de um jeito.** Em uns, o sistema prisional é secretaria
   própria (SAP); em outros, está dentro da Secretaria de Segurança. Somar "o orçamento da
   SSP" de um estado com o do outro compara coisas diferentes. O painel identifica o modelo
   de cada UF (*SAP separada* ou *SSP integrada*) e deixa escolher qual visão usar.
2. **A previdência militar entra em uns orçamentos e em outros não.** Onde os inativos da
   PM estão dentro da Função 06, o orçamento parece muito maior sem que nada tenha sido
   gasto a mais em policiamento. O painel marca cada UF como modelo previdenciário
   *Integrado* ou *Separado* e oferece o modo "exceto previdência".
3. **Órgãos que não são polícia moram na mesma função orçamentária.** DETRAN e Casa Militar
   aparecem em vários estados sob Segurança. O modo *equiparado* ajusta esses itens para
   que a comparação entre UFs fique honesta.

Sem esses três ajustes, a diferença entre o primeiro e o último colocado de um ranking de
gasto é, em boa parte, diferença de contabilidade — não de política pública.

## Como é feito

```
coletar_dados.py / coletar_anexo4.py   → baixam o RREO da API do SICONFI (27 UFs × 12 anos),
                                          com cache em disco para não repetir requisição
processar_dados_all.py                  → normaliza contas, funções e subfunções
classify_all_states.py                  → classifica cada UF por modelo de gestão e por
                                          modelo previdenciário, usando a distribuição real
                                          das subfunções, não uma lista escrita à mão
validar_resultado.py / validar_equiparacao.py
                                        → refazem, em Python, o mesmo cálculo que o
                                          JavaScript do painel faz no navegador, e comparam
compilar_painel.py                      → embute CSS, dados e JS num HTML único e autônomo
```

O painel em si é **um arquivo HTML sem build e sem dependência de runtime**: Chart.js vem de
CDN, o resto é JavaScript puro. Abrir o `index.html` no navegador basta.

**Stack:** Python (requests, pandas) para o pipeline de dados; HTML, CSS e JavaScript puro
com Chart.js para a visualização; GitHub Pages para publicação.

## Rodar na sua máquina

```bash
pip install requests pandas openpyxl

python coletar_dados.py       # baixa do SICONFI (respeita o cache local)
python processar_dados_all.py # gera os CSVs consolidados
python validar_resultado.py   # confere a matemática do painel contra o Python
python compilar_painel.py     # gera o HTML autônomo

# ou, só para ver o painel pronto:
start index.html              # Windows
```

`validar_resultado.py` é o teste que importa: ele reimplementa em Python o
`calculateRowValues` do `app.js` e compara registro a registro. Se o JavaScript do painel e o
Python discordarem em qualquer UF, ano ou modo, ele falha. Saída esperada:

```
Sucesso! Todos os testes de validação matemática passaram sem erros.
```

## Decisões e limitações

- **Fonte única e pública.** Tudo vem da API do Tesouro
  (`apidatalake.tesouro.gov.br/ords/siconfi`). Não há dado pessoal, dado institucional
  interno nem número que não esteja publicado.
- **2026 é ano parcial.** Os valores de 2026 são acumulados até abril e estão rotulados assim
  no painel. Comparar 2026 com um ano fechado subestima o ano corrente.
- **Campo sem dado fica vazio.** Quando um estado não publicou o desdobramento de um ano, a
  célula aparece vazia. Não há interpolação nem média do grupo: dado plausível sem fonte é
  pior que lacuna, porque ninguém sabe que precisa conferir.
- **A classificação de modelo é heurística, e está no código.** `classify_all_states.py`
  decide pelo peso de "Demais Subfunções" na série de cada UF. É reproduzível e discutível:
  os dois arquivos `inspect_*.py` que sustentam cada decisão ficaram versionados de
  propósito, porque a conclusão sem a apuração não vale muito.
- **Os scripts `inspect_*.py` e `debug_*.py` são o caderno de apuração**, não biblioteca.
  Foram mantidos para mostrar como cada caso estranho (MG 2015, RS 2020, AC 2016) foi
  investigado antes de virar regra.

## Escopo

Trabalha só com dado orçamentário público. **Não tem relação com o `financeiroje`**, que é
app de finanças pessoais: são domínios diferentes que só se parecem pelo nome.
