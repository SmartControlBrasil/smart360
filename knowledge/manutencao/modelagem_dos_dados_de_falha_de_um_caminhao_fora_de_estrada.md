# Modelagem dos dados de falha de um caminhão fora de estrada'

> Fonte original: raw_academico/Manutenção Produtiva Total/Confiabilidade de Sistemas Industriais/Modelagem dos dados de falha de um caminhão fora de estrada'.pdf  
> Categoria: manutencao  
> Material convertido para apoio técnico da LÍVIA Assistant.

## Conteúdo extraído

See discussions, stats, and author profiles for this publication at: https://www.researchgate.net/publication/329765787
Modelagem dos dados de falha de um caminhão fora de estrada
Article  in  ForScience · December 2018
DOI: 10.29069/forscience.2018v6n3.e500
CITATIONS
3
READS
132
2 authors:
Vítor Justus Leal
2 PUBLICATIONS   3 CITATIONS
SEE PROFILE
Paulo César de Resende Andrade
Universidade Federal dos Vales do Jequitinhonha e Mucuri
34 PUBLICATIONS   106 CITATIONS
SEE PROFILE
All content following this page was uploaded by Paulo César de Resende Andrade on 19 August 2019.
The user has requested enhancement of the downloaded file.

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
DOI: 10.29069/forscience.2017v5n1.e500.
Recebido em: 18/07/2018
Aprovado em: 04/09/2018
Publicado em: 19/12/2018
ISSN: 2318-63
ARTIGO

MODELAGEM DOS DADOS DE FALHA DE UM CAMINHÃO FORA DE
ESTRADA1

Vítor Justus Leal2
Paulo César de Resende Andrade3

RESUMO

O mercado cada vez mais competitivo, ocasionado pela globalização, impõe que as empresas
tenham um compromisso ainda maior com a redução dos seus custos. Os clientes necessitam
de equipamentos com alta disponibilidade e confiabilidade. Na mineração, um dos custos
expressivos existentes refere -se a falhas nos caminhões fora de estrada. Baseado na
representatividade dos custos destas falhas, faz -se necessária a aplicação de técnicas de
confiabilidade com a finalidade de aumentar a vida útil e o desempenho destes ativos. O
presente trabalho tem por objetivo modelar o tempo de vida em horas de um caminhão fora de
estrada utilizado na mineração, por meio da análise de confiabilidade paramétrica . O
procedimento de pesquisa utilizado foi o estudo de caso. Foram coletados dados de tempo até
a falha de todos os sistemas do caminhão d urante o período de um ano. Além dos métodos
gráficos, foram utilizados os testes de aderência de Qui -Quadrado e Kolmogorov–Smirnov
para verificar qual distribuição melhor se ajusta ao conjunto amostral. A análise foi feita com
o software ProConf. Os parâm etros das distribuições foram determinados pelo método da
máxima verossimilhança. Utilizou-se o software R para verificar o ajuste por meio do critério
AIC. A distribuição Exponencial foi que melhor se ajustou ao conjunto de dados. A função de
risco teve u m comportamento constante , indicando que o caminhão está na fase de
maturidade, em plena vida útil. A estratégia para esta fase é adotar a manutenção preditiva,
realizando as manutenções e monitoramentos necessários para maximização da sua
performance, com o intuito de evitar o início da fase de desgaste dos seus componentes.

Palavras-chave: Confiabilidade. Tempo de vida. Equipamento de grande porte.

1 INTRODUÇÃO

O ambiente de mudanças nos mais diversos setores da sociedade tem tornado cada vez
mais com plexo o desenvolvimento de equipamentos, produtos e sistemas (SILVA et al .,
2017a), sendo de vital importância que tenham melhores desempenhos e custos competitivos.
Desta forma, pode -se afirmar que o não funcionamento satisfatório de um equipamento

1 Como citar este artigo: LEAL, Vítor Justus; ANDRADE, Paulo César de Resende. Modelagem dos dados de
falha de um caminhão fora de estrada. ForScience: revista científica do IFMG, Formiga, v. 6, n. 3, e00500,
jul./dez. 2018. DOI: 10.29069/forscience.2017v5n1.e500.
2 Autor para correspondência: Paulo César de Resende Andrade: paulo.andrade@ict.ufvjm.edu.br

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 2

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
implica na capacidade de produção de uma empresa, consequentemente, aumentando seus
custos em geral e não garantindo uma boa qualidade ao produto.
Em um contexto no qual ocorrem cada vez mais rápidas mudanças significativas no
mercado, a manutenção dos ativos de produção, antes vista como um mal necessário, passou a
desempenhar papel estratégico e a ser considerada indispensável à produção (SANTOS ;
MOTTA; COLOSIMO, 2007). Tendo em vista o atendimento das necessidades do cliente,
torna-se essencial a criação de estratégias de manutenção e confiabilidade dos equipamentos a
fim de evitar indisponibilidades e desperdícios gerados através de paradas por quebras, falhas
ou produção de produtos defeituosos que acarretam no comprometimento dos resultados
almejados pela organização (GREGOL; ANDRADE, 2014).
É por meio do conhecimento das vulnerabilidades e problemas dos produtos durante
sua etapa de vida útil que se obtém informações de falhas, que quando utilizadas junto a
técnicas estatísticas de forma correta, permitem à engenharia da confiabilidade estimar o
tempo que um produto funcionará de forma continua sem falhas (BRAILE; ANDRADE,
2013). Neste contexto, surge uma intensa procura por equipamentos capazes de manter sua
disponibilidade com mínimas probabilidades de f alhas, resultando em bons investimentos a
um menor custo de manutenção.
Dessa maneira, o estudo da confiabilidade é de suma importância, pois garante a
comercialização de produtos confiáveis, visto que o cliente não espera falhas durante o tempo
de uso d os mesmos. A análise destas falhas é fundamental para compreensão do tipo de
manutenção mais adequada ao comportamento de desempenho dos equipamentos, evitando a
aplicação de atividades desnecessárias ou ineficazes que reduzem a disponibilidade,
confiabilidade e geram custos operacionais (MENDES, 2011).
A alta competitividade entre os produtores de minério no mercado atual leva a
melhorias no processo produtivo, como reduções de custos, aumento da produção, da
qualidade e priorização da segurança.
A mineração constitui uma atividade dispendiosa, além de envolver alto potencial de
riscos, mas, se conduzida de maneira adequada, sua indústria pode gerar ganhos
consideráveis. Estima-se que o setor de transporte, na mineração, pode contribuir em até 40%
dos cu stos totais da produção, dependendo do método de lavra adotado. Sendo assim, a
implantação de uma melhoria neste âmbito implica em significativo impacto no custo final de
produção, bem como nos lucros rendidos.
Neste contexto, uma redução e um controle d o tempo de falha do caminhão,
mantendo-se ou elevando -se a produção, gera não apenas ganhos financeiros para a empresa

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 3

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
(com a redução de custos), mas também ambientais. O foco do trabalho constitui um dos
principais gargalos referentes ao custo produtivo n a atual cadeia de produção mineral.
Especificamente, a abordagem aqui descrita é relativa à frota de transporte de materiais de
lavra de mina, composta por caminhões fora de estrada.
A proposta deste artigo é modelar um estudo de caso aplicado em um cami nhão fora
de estrada de uma mineradora multinacional em uma de suas sedes situada no sudeste do
Pará. Serão analisados os dados de falha levantados no ano de 2016, tendo como critério o
tempo entre as falhas que ocorreram para manutenção corretiva.
O papel do caminhão dentro da empresa é imprescindível para que não prejudique a
produção e há a necessidade de criação e implantação de técnicas de monitoramento e
controle que proporcionem a diminuição de perdas através de uma detecção rápida de
problemas, seguida da tomada de medidas corretivas.

2 REFERENCIAL TEÓRICO

2.1 Confiabilidade

Conforme Fogliatto e Ribeiro (2009), a confiabilidade de um item corresponde à sua
probabilidade de desempenhar adequadamente o seu propósito, por um determinado período
de tempo e sob condições predeterminadas. Já Haviaras (2005) define confiabilidade como a
possibilidade de um componente ou equipamento executar a sua função sob condições de
operação, por um período de tempo pré-determinado, sem apresentar falhas.
As fu nções mais utilizadas para análise da confiabilidade são as funções de
confiabilidade e de risco. A função de confiabilidade R(t) é representada em termos de uma
probabilidade, pois ela nada mais é que a probabilidade de um sistema cumprir uma missão
preestabelecida, com uma duração determinada, sem falhas. A taxa de risco ou taxa de falha
h(t) é considerada como sendo a quantidade de risco relacionada a uma unidade do tempo t,
consequentemente sendo dada em termos de falha por unidade de tempo. O tempo médio até a
falha (Mean Time To Failure – MTTF) define uma média de todos os tempos mensurados até
ocorrer uma falha na unidade observada em questão (LEEMIS, 1995).
A análise possibilita, por meio de estimativa, caracterizar os comportamentos da
confiabilidade, da probabilidade de falha e da taxa de falha em relação ao tempo de um
componente, equipamento ou sistema (SANTOS et al., 2017). Para isso, é necessário fazer a
modelagem de dados históricos de tempos entre falhas em distribuições de probabilidades. A s

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 4

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
distribuições de probabilidade que frequentemente são mais utilizadas para descrever os
tempos até a falha de componentes e sistemas são: Weibull, Lognormal, Gama e Exponencial
(HAVIARAS, 2005).
A distribuição de Weibull é uma das mais importantes distr ibuições em modelos de
confiabilidade devido à flexibilidade e capacidade de representação de amostras de tempos até
a falha com comportamentos distintos (LAFRAIA, 2001; FOGLIATTO; RIBEIRO, 2009;
LEWIS, 1996). A distribuição Exponencial é relevante em estu dos de confiabilidade por ser a
única distribuição contínua em função do risco constante. A Lognormal é uma distribuição
muito utilizada na modelagem de tempos até reparo em unidades reparáveis (FOGLIATTO;
RIBEIRO, 2009).
A modelagem dos tempos até a falh a é, portanto, central em estudos de confiabilidade
(FOGLIATTO; RIBEIRO, 2009). Vários estudos foram desenvolvidos com comprovadas
adequações a várias situações práticas (DUEK, 2005; BRANDÃO; ANDRADE, 2018,
SANTOS et al., 2017; SILVA et al., 2017b, SILVA; ANDRADE, 2018).

2.2 Confiabilidade e manutenção

O comportamento da taxa de falha de um equipamento ao longo do tempo pode ser
analisado pela curva da banheira, que representa genericamente a função de risco h(t) ao
longo do ciclo de vida.
A curva da banheira, representada na FIG. 1, apresenta três períodos característicos de
vida de componentes e equipamentos: mortalidade infantil, fase de maturidade, e mortalidade
senil (LAFRAIA, 2001; SELLITTO, 2005).

Figura 1 - Curva da banheira e o ciclo de vida dos equipamentos
Fonte: Adaptado de Lafraia (2001) e Sellitto (2005).

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 5

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
Sellitto (2005) relaciona cada fase da curva a um comportamento da função de risco
h(t) pelo parâmetro de forma γ da distribuição de Weibull. O autor também associa a cada fase
da curva uma estratégia de manutenção mais adequada sendo que no período inicial, chamado
de mortalidade infantil, a taxa de falhas é alta, porém decrescente.
A estratégia para esta fase é a manutenção corretiva, que identifica e corrige
deficiências de projeto ou de instalação do equipamento. No período seguinte, fase de
maturidade, a taxa de falhas é sensivelmente menor e oscila ao redor de uma média constante.
A estratégia para esta fase é a manutenção preditiva. O último período da curva é chamado de
desgaste por Lafraia (2001) e de mortalidade senil por Sellitto (2005). Segundo os autores, é o
fim da vida útil do equipamento e, neste período, a taxa de falhas é crescente, sendo a
estratégia para esta fase é a manutenção preventiva: a troca antecipa a inevitável quebra.

2.3 Caminhão fora de estrada

Em minas de grandes extensões, a adoção de caminhões fora de estrada é usual devido
à facilidade de realocação ante as diversas frentes de l avra em avanço, sendo ideal para
terrenos adversos - como no caso da mineração - onde seria inviável a utilização de
caminhões caçambas convencionais. Além disso, grandes projetos operam caminhões com
capacidade de até 400 toneladas, otimizando o custo unitário de transporte do material.
Caminhões fora de estrada são utilizados em minas a céu aberto e subterrâneas, para
transporte de material sólido a pequenas e médias distâncias. Além da evidente vantagem da
flexibilidade em sua utilização, eles proporcionam ainda possibilidade de ciclos rápidos e vida
útil de média a longa. Em contrapartida, a desvantagem é a manutenção onerosa, que torna
extremamente importante o investimento mais amplo em um programa de manutenção
preventiva eficiente, de modo a reduzi r o número de paradas corretivas e perdas de
produtividade. Por ser um trabalho que exige o máximo do equipamento, no caso transportar
toneladas de minério em condições de terreno irregular, os números de falhas nestes
caminhões são altos.
Ribeiro e Alme ida (2014) fizeram estudo de confiabilidade de motores diesel de
caminhões fora de estrada e Campos Júnior et al . (2013) desenvolveram uma metodologia
para monitoramento e controle do consumo específico de diesel em caminhões fora de
estrada. Silva et al. (2017b) estudaram os principais modos de falha dos pneus deste tipo de
caminhão, propondo ações de melhorias no intuito de otimizar sua performance e após a

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 6

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
implantação destas ações, observou -se uma melhora significativa nos indicadores de gestão
dos pneus, levando a conclusão dos impactos positivos que o projeto trouxe a mineração.

3 MATERIAL E MÉTODOS

A pesquisa empregada foi o estudo de caso de um caminhão fora de estrada. Os dados
em questão foram de uma das minas da Vale, na região de Carajás, em Pa rauapebas/PA, na
qual a empresa se destaca por ser uma das maiores mineradoras do mundo e a primeira
colocada na produção mundial de minério de ferro, pelotas e níquel. Carajás possui a maior
frota de equipamentos de mina da Vale sendo 147 caminhões fora de estrada. Devido à grande
extração de minério realizada pela empresa, é necessário que tenha uma frota de caminhões de
grande porte para que a produção não pare.
A função do caminhão dentro da mina é fazer o transporte do minério lavrado até a
usina de beneficiamento, onde este será processado conforme expedição do cliente. O
caminhão analisado é do modelo CATERPILLAR 777G, com peso bruto total de 164,6
toneladas, capacidade da caçamba é de 64,3 m³, podendo carregar no máximo 99,8 toneladas,
sendo que sua velocidade máxima carregado é de 67 km/h.
A empresa disponibilizou os dados de falhas de 40 caminhões em operação, todos do
mesmo modelo, fabricante e capacidade de carga. Os sistemas analisados foram transmissão,
elevação, motor, locomoção, ar condici onado, frenagem, elétrico, cabine, direção e
pneumático. Para o estudo estatístico deste artigo foram utilizados os tempos até a falha do
caminhão com maior número de ocorrências na manutenção durante o ano de 2016. Esse
período representa o início e fim d e um período completo de funcionamento até a falha. A
TAB. 1 mostra os tempos até falha coletados.

Tabela 1 - Tempo até a falha de um caminhão fora de estrada
N
Tempo até
a falha
n
Tempo até
a falha
n
Tempo até
a falha
n
Tempo até
a falha

1 224,4 15 325,5 29 23,1 43 22,5
2 42,0 16 209,0 30 24,2 44 61,1
3 112,2 17 145,3 31 180,5 45 167,3
4 3,6 18 258,1 32 89,0 46 208,5
(Continua...)

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 7

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
5 89,0 19 507,3 33 131,3 47 24,5
6 30,1 20 165,3 34 47,3 48 8,4
7 185,0 21 22,0 35 24,0 49 22,0
8 66,0 22 776,0 36 182,2 50 62,5
9 144,0 23 30,1 37 22,3 51 32,4
10 74,0 24 140,4 38 232,5 52 75,2
11 5,3 25 168,0 39 29,0 53 38,0
12 328,0 26 250,1 40 23,4 54 24,3
13 235,5 27 102,7 41 92,3 55 92,1
14 39,3 28 258,5 42 349,5 56 86,5
Fonte: Vale S/A.

Os dados disponibil izados foram trabalhados no ProConf (FRITSCH; RIBEIRO,
1998), um programa computacional projetado para o ajuste de distribuições de tempos de
falha para dados de confiabilidade, por meio de métodos gráficos e métodos analíticos. Os
histogramas de frequênci a das falhas e os papéis de probabilidades foram utilizados como
métodos gráficos para comparar as curvas das distribuições de probabilidade e verificar o
modelo que apresenta melhor aderência aos dados amostrais.
Para a caracterização da distribuição de frequência foram aplicados testes de aderência
às distribuições de probabilidades. Os testes utilizados para verificar o ajuste destas
distribuições candidatas aos dados efluentes foram: Qui -Quadrado ( 2) e Kolmogorov-
Smirnov (K-S). O software informa o n ível de significância e aponta quais distribuições não
podem ser rejeitadas (FRITSCH; RIBEIRO, 1998). A validação é dada se o nível de
significância for maior que 5% em ambos os testes de aderência. Quando o mesmo é maior a
5% em ambos os testes, do Qui -Quadrado e do Kolmogorov-Smirnov, a distribuição não pode
ser rejeitada, o que significa que poderá ser utilizada na modelagem. Caso mais do que uma
distribuição não possa ser rejeitada, cabe ao pesquisador justificar a escolha por uma delas por
fundamentação teórica.
Para verificar a adequação da validação do desempenho dos modelos foi utilizado o
Critério de Informação de Akaike – Akaike’s Information Criterion (AIC). Quanto menor for
o valor de AIC, melhor será o ajuste do modelo (AKAIKE, 1973). Para tal foi utilizado o
software R (R FOUNDATION, 2018).
Em seguida, são fornecidas as estimativas dos parâmetros da distribuição de
probabilidade que melhor modela o conjunto de dados em estudo, utilizando o método de
(Conclusão.)

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 8

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
máxima verossimilhança. Além disso, são apre sentadas as representações das funções de
confiabilidade R(t) e de risco ou taxa de falha h(t).

4 RESULTADOS E DISCUSSÕES

Inicialmente, foram obtidos alguns gráficos relativos ao conjunto de dados. Na FIG. 2
está representado o histograma dos tempos d e falhas apresentados na T AB. 1. O formato do
histograma sugere a aplicação das distribuições, Weibull, Exponencial e Lognormal para
modelar adequadamente o conjunto de dados estudados.

0.000
0.002
0.004
0.006
0 100 200 300 400 500 600 700 800
f(t)
t: tempo

Figura 2 – Gráfico de frequência das falhas
Fonte: ProConf.

A análise dos papéis de probabilidade, mostradas na FIG. 3, indicam que nenhuma das
distribuições apresentam uma linha de tendência, ou seja, apresentam desvios, não se
ajustando perfeitamente em torno da reta. Desta forma, não é possível definir o modelo que
melhor se ajusta ao conjunto amostral.

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 9

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.

Figura 3 – Papel de probabilidade das distribuições Weibull, Exponencial e Lognormal.
Fonte: ProConf.

As significâncias dos testes de aderência Qui-Quadrado (χ2) e de Kolmogorov-Smirnov
(K-S) são apresentadas na Tabela 2. No teste do Qui-Quadrado (χ2) verifica-se que o nível de
significância é maior para a Exponencial se comparado as demais distribuições. No teste de
Kolmogorov-Smirnov (K-S) a maior significância foi obtida para a distribuição Lognormal.
Esses resultados corroboram com a análise anterior, feita nos papéis de probabilidade.

Tabela 2 - Níveis de significância dos testes de aderência
Modelo χ2 K-S Decisão
Weibull 0,5757 0,1204 Não pode ser rejeitada
Exponencial 0,6623 0,1532 Não pode ser rejeitada
Lognormal 0,5010 0,1915 Não pode ser rejeitada
Fonte: Dos autores, 2018.

Apesar de não haver rejeição de nenhuma das três distribuições, deve -se dar maior
importância ao teste de aderência do Qui -Quadrado, pelo fato do tamanho da amostra ser
maior que 30 (FOGLIATTO; RIBEIRO, 2009).
Para validação do desempenho dos modelos foi calculado o AIC, via software R. De
acordo com este critério, quanto menor o valor do AIC melhor será o ajuste do modelo. Desta

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 10

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
forma a hipótese de que a distribuição Exponencial é a mais indicada para se ajustar ao estudo
de caso foi confirmada. Os valores estão apresentados na TAB. 3.

Tabela 3 – Valores do teste AIC
Modelo AIC
Weibull 661,6453
Exponencial 659,6604
Lognormal 662,4557
Fonte: Adaptado do software R.

Dessa forma pode-se afirmar que a distribuição Ex ponencial é a mais apropriada para
o estudo da confiabilidade do caminhão fora de estrada em questão e seus parâmetros
ajustados podem ser utilizados durante os estudos de confiabilidade, pois os resultados dos
papéis de probabilidade e testes de aderência se ajustam melhor a essa distribuição. A T AB. 4
apresenta os parâmetros da distribuição de Exponencial, ajustados pelos dados experimentais
da TAB. 1.

Tabela 4 - Resultados dos ajustes - Exponencial
Parâmetro Resultados
t10 (horas) 13,76
t50 (horas) 90,51
MTTF (horas) 130,58
 0,0077
Fonte: Adaptado do software ProConf.

Pela TAB. 4, o tempo médio até a falha ocorrer (MTTF) no caminhão fora de estrada é
130,58 horas e a metade dos caminhões falhou antes de 91 horas. O t10 e t50 correspondem aos
valores limites dos tempos, nos quais 10% e 50% das falhas ocorreram.
Levando em consideração os resultados dos testes de aderência e do critério AIC, a
distribuição Weibull apresentou resultados bem similares a o da Exponencial, conforme T AB.
5.

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 11

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
Tabela 5 - Resultados dos ajustes - Weibull
Parâmetro Resultado
t10 (horas) 13,31
t50 (horas) 89,63
MTTF (horas) 130,56
γ 1,01
θ 131,29
Fonte: Adaptado do software ProConf.

Isso se deve ao fato de que o valor do parâmetro gama γ estar bem próximo de 1.
Quando γ é igual a 1, a taxa de falha é constante e a Weibull possui o mesmo comportamento
da distribuição Exponencial (LEE; WANG, 2003; LEEMIS, 1995).
Estabelecendo-se uma analogia do comportamento da taxa de falhas constante do
modelo Exponencial, com a fase de maturidade da curva da banheira da distribuição Weibull,
indica-se que a manutenção ideal seria a preditiva (SELLITTO, 2005). Esse tipo de
manutenção é real izado conforme a necessidade, com base no resultado de inspeções
contínuas ou periódicas. As falhas são casuais e decorrentes de fatores menos controláveis,
tais como: mau uso do equipamento, ultrapassagem de resistência ou fenômenos naturais
imprevisíveis. Quando o grau de degradação atinge o limite estabelecido, uma intervenção de
manutenção é executada antes da falha (SELLITTO, 2005).
A função confiabilidade está representada na F IG. 4. Constata-se que a confiabilidade
sempre se dá em uma curva decre scente em função do tempo, já que as probabilidades de
perfeitas condições decaem conforme há a utilização e o desgaste do equipamento.

0.0
0.2
0.4
0.6
0.8
1.0
0 100 200 300 400 500 600 700
R(t)
t: tempo
Figura 4 – Função confiabilidade
Fonte: ProConf

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 12

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
A função de risco está representada na FIG. 5.

0.007
0.008
0 100 200 300 400 500 600 700
h(t)
t: tempo

Figura 5 – Função taxa de falha
Fonte: ProConf.

Nota-se que o equipamento mantém uma taxa de falha relativamente constante na
maioria do tempo decorrido, ou seja, a função de risco do modelo Exponencial é constante.
Como o modelo Exponencial foi adequado na modelagem, sabe-se que o risco de falha
para as unidades que estão em estudo há pouco ou muito tempo, dado que ainda não tenham
falhado, é o mesmo (LEE; WANG, 2003). Essa propriedade é conhecida como a falta de
memória.

5 CONCLUSÕES

Muitos estudos estatísticos de manutenção e confiabilidade utilizam dados s imulados
de horas até a falha ou são realizados submetendo os equipamentos a um regime de estresse
para estimar sua vida útil. Neste estudo foram utilizados dados reais com o equipamento em
regime normal de trabalho, tornando possível verificar, através da análise estatística, que os
dados corroboram para o uso de distribuições já conhecidas.
Os dados de tempo até a falha mostram que a distribuição Exponencial se adequa
melhor aos dados. O valor do parâmetro forma da distribuição Weibull obtido mostra que o
comportamento do caminhão fora de estrada se localiza na segunda fase da curva da banheira,
indicativo de que a manutenção ideal para o equipamento em questão será a preditiva. Desta
forma, os resultados encontrados permitem à empresa conhecer melhor o perfil das falhas dos
caminhões fora de estrada de sua frota.

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 13

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
Por fim conclui-se que a confiabilidade é de suma importância dentro de um processo
industrial, pois o resultado obtido permite que a empresa reduza custos com mão de obra, não
perca tempo de produção com a substituição de equipamentos, possibilitando um melhor
funcionamento da empresa de forma geral. As análises quantitativas dos tempos até as falhas
são relevantes para a determinação de estratégias de manutenção a ser realizadas pelas
empresas, a fim de garantir maior disponibilidade dos produtos.

MODELING THE FAILURE DATA OF AN OFF-ROAD TRUCK

ABSTRACT

The increasingly competitive market, caused by globalization, requires that companies have
an even greater commitment to reduce their costs. The customers need equipment with high
availability and reliability. In mining, one of the significant costs refers to failures in off -road
trucks. Based on the representativeness of the costs of these failures, it is necessary to apply
reliability techniques with the purpose of increasing the useful life and performance of these
assets. The present work aims to model the time of life, in hours, of an off -road truck used in
mining, through parametric reliability analysis. The research procedure used was th e case
study. Time data were collected until failure of all truck systems, resulting in fifty -six failures
during the period of one year. Besides the graphical methods, the adhesion tests of Chi -square
and Kolmogorov-Smirnov were used to verify which distr ibution best fits the sample set. The
analysis was done with ProConf software. The parameters of the distributions were
determined by the maximum likelihood method. The software R was used to verify the
adjustment using the AIC criterion. The Exponential d istribution was the best fit to the data
set. The risk function had a constant behavior, indicating that the truck is in the phase of
maturity, in full working life. The strategy for this phase is to adopt the predictive
maintenance, performing the necessa ry maintenance and monitoring to maximize its
performance, in order to avoid the beginning of the wear phase of its components.

Keywords: Reliability. Lifetime. Large equipment.

REFERÊNCIAS

AKAIKE, Hirotugu. Information Theory and an Extension of the Maximum Likelihood
Principle. In: PARZEN, E.; TANABE, K.; KITAGAWA, G. (ed.). Selected papers of
Hirotugu Akaike. Springer Series in Statistics (Perspectives in Statistics). New York, NY:
Springer, 1998.

BRAILE, Nathalia Ávila; ANDRADE, Jairo José de Oliveira. Estudo de falhas em
equipamentos de costura industriais utilizando o FMEA e a análise de confiabilidade. In:
ENCONTRO NACIONAL DE ENGENHARIA DE PRODUÇÃO, 34, Salvador, 2013.
Anais... Salvador, 2013.

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 14

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
BRANDÃO, Mariane Olivier; ANDRADE, Paulo César de Resende. Modelagem dos dados
de falhas de um pasteurizador de garrafas de cerveja. Revista de Engenharia e Tecnologia,
v. 10, n. 2, p. 172-181, 2018.

CAMPOS JÚNIOR, Carlos Roberto et al. Desenvolvimento de uma metodologia para
redução do consumo específico de diesel em caminhões fora de estrada em uma empresa do
setor de mineração. In: SIMPÓSIO DE EXCELÊNCIA EM GESTÃO E TECNOLOGIA, 10,
Resende, 2013. Anais... Resende, 2013.

DUEK, Carlos. Análise de confiabilidade na manutenção de componente mecânico de
aviação. 2005. 119 f. Dissertação (Mestrado em Engenharia de Produção) – Universidade
Federal de Santa Maria, Santa Maria, 2005.

FOGLIATTO, Flávio Sanson; RIBEIRO, José Luis Duarte. Confiabilidade e manutenção
industrial. Rio de Janeiro: Elsevier, 2009.

FRITSCH, Celso; RIBEIRO, José Luis Duarte. PROCONF: um software orientado para
análises de confiabilidade. In: ENCONTRO NACIONAL DE ENGENHARIA DE
PRODUÇÃO, 18, Niterói, 1998. Anais... Niterói, 1998.

GREGOL, Luciano Bernochi; ANDRADE, Jairo Jose de Oliveira. Análise de falhas como
subsídio para o estabelecimento de procedimentos de manutenção produtiva total (MTP):
estudo de caso de uma máquina gargalo na fabricação de latas de alumínio. In: ENCONTRO
NACIONAL DE ENGENHARIA DE PRODUÇÃO – ENEGEP, 29, Curitiba, 2014.
Anais... Curitiba, 2014.

HAVIARAS, Gilberto. J. Metodologia para análise de confiabilidade de pneus radiais em
frota de caminhões de longa distância. 2009. 124 f. Dissertação (Mestrado em Engenharia
Automotiva) – Escola Politécnica, Universidade de São Paulo, São Paulo, 2005.

LAFRAIA, João Ricardo Barusso. Manual de confiabilidade, mantenabilidade e
disponibilidade. Rio de Janeiro: Qualitymark, 2001.

LEE, Elisa T.; WANG, John Wenyu. Statistical methods for survival data analysis. New
Jersey: Wiley, 2003.

LEEMIS, L. M. Reliability: probabilistic models and statistical methods. New Jersey:
Prentice-Hall, 1995.

LEWIS, E. Introduction to reliability engineering. New York: John Wiley & Sons, 1996.

MENDES Angélica Alebrant. Manutenção centrada em confiabilidade: uma abordagem
quantitativa. 2011. 85 p. Dissertação (Mestrado em Engenharia de Produção) – Escola de
Engenharia, Universidade Federal do Rio Grande do Sul, Porto Alegre, 2011.

LEAL, V. J.; ANDRADE, P. C. de. R. Modelagem dos dados de falha de um caminhão fora de estra da 15

ForSci.: r. cient. IFMG campus Formiga, Formiga, v. 6, n. 3, e00500, jul./dez. 2018.
RIBEIRO, Adriano Gonçalves dos Santos; ALMEIDA, Gean Carlo Feliciano. Estudo de
confiabilidade de motores diesel de caminhões fora de estrada. Revista de Estatística da
UFOP, Ouro Preto, v. 3, p. 460-464, 2014.

SANTOS, Wagner Baracho dos; MOTTA, Sergio Brandão da; COLOSIMO, Enrico Antônio.
Tempo ótimo entre manutenções preventivas para sistemas sujeitos a mais de um tipo de
evento aleatório. Revista Gestão e Produção, São Carlos, v. 14, n. 1, p. 193-202, 2007.

SANTOS, Maicon Mateus de Medeiros et al. Modelagem do tempo de vida de um inversor de
frequência. ForScience: revista científica do IFMG, Formiga, v. 5, n. 3, e00288, 2017.

SELLITTO, M. Formulação estratégica da manutenção industrial com base na confiabilidade
dos equipamentos. Produção, v.15, n.1, p.044-059, 2005.

SILVA, Evaldo da Conceição et al. Análise de Dados de Falha de um Transmissor de Fibra
Óptica. Revista Thema, Pelotas, v. 14, n. 4, p. 259-266, 2017a.

SILVA, Elifas Levi da et al. Análise dos modos de falhas em pneus de caminhões fora de
estrada em uma mineração. In: ABM ANNUAL CONGRESS, 72, São Paulo,
2017. Anais... São Paulo, 2017b.

SILVA, Ellen Maria Neves; ANDRADE, Paulo César de Resende. Análise de confiabilidade
de um inspetor eletrônico de garrafas. Revista da Universidade Vale do Rio Verde, v. 16,
n.2, p. 1-9, 2018.

THE R FOUNDATION. R: a language and environment for statistical computing. R
Foundation for Statistical Computing, Vienna, Áustria, 2018.

DADOS DOS AUTORES

Vítor Justus Leal
E-mail: vitorjustus@gmail.com.
Currículo Lattes: http://lattes.cnpq.br/7816407877526299
Estudante de gradu ação em Ciência e Tecnologia pela Universidade Federal dos Vales do
Jequitinhonha e Mucuri (UFVJM). Tem experiência na área de Ciência e Tecnologia, com
ênfase em Engenharia Mecânica.

Paulo César de Resende Andrade
E-mail: pceandrade@gmail.com.
Currículo Lattes: http://lattes.cnpq.br/0894646446086485
Doutorado em Estatística e Experimentação Agropecuária, mestrado em Ciências (Agronomia
- Estatística e Experimentação Agropecuária) pela Universidade Federal de Lavras (UFLA).
Possui graduação em Engenharia Industrial Elétrica, graduação e especialização em
Matemática. Atualmente é professor Associado II da Universidade Federal dos Vales do
Jequitinhonha e Mucuri (UFVJM), Campus de Diamantina.
View publication stats

## Aplicação para a Smart Control Brasil

Este material deve apoiar respostas técnicas da LÍVIA sobre manutenção, automação, confiabilidade, diagnóstico, TPM, FMEA, falhas ou engenharia, conectando conceitos à aplicação prática da Smart Control Brasil.

A LÍVIA não deve usar este material para prometer preço, prazo, estoque, garantia ou resultado comercial.
