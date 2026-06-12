# ANÁLISE DE FALHAS E DA POSIÇÃO NA CURVA DA BANHEIRA DE MOLDES EMPREGADOS EM EQUIPAMENTOS DE INJEÇÃO

> Fonte original: raw_academico/Manutenção Produtiva Total/Ferramentas da Gestão da Manutenção/ANÁLISE DE FALHAS E DA POSIÇÃO NA CURVA DA BANHEIRA DE MOLDES EMPREGADOS EM EQUIPAMENTOS DE INJEÇÃO.pdf  
> Categoria: manutencao  
> Material convertido para apoio técnico da LÍVIA Assistant.

## Conteúdo extraído

ANÁLISE DE FALHAS E DA POSIÇÃO
NA CURVA DA BANHEIRA DE MOLDES
EMPREGADOS EM EQUIPAMENTOS DE
INJEÇÃO

Luiz Otavio Rosa Reis (PUCRS)
luereis@yahoo.com.br
Jairo José de Oliveira Andrade (PUCRS)
jairo.andrade@pucrs.br

Esse trabalho apresenta uma aplicaçã o da confiabilidade aplicada ao
estudo de falhas em moldes de injeção em uma empresa do setor
elétrico localizada no Estado do Rio Grande do Sul. Durante um
período de um ano foram coletados dados de falhha em moldes de
injeção, cujos mesmos foram inserido s em dois programas estatísticos
para verificar a aderência à distribuição de Weibull. Logo após,
considerações são realizadas a respeito da fase da curva da banheira
na qual os moldes de injeção estão inseridos, correlacionando os
resultados oriundos do m odelo com informações obtidas do dia -a-dia
da operação do equipamento. Verificou -se que os dados obtidos
através da análise de confiabilidade são aderentes com o
comportamento do equipamento na produção, evidenciando pontos que
devem ser objeto de melhoria dentro do processo, a fim de promover
um aumento da produtividade e da confiabilidade do equipamento
estudado.

Palavras-chaves: Confiabilidade, moldes de injeção, análise de falhas,
curva da banheira, distribuição de Weibull
XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUÇÃO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão.
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

2

1. Introdução

No cenário c ompetitivo atual, a criação de controles para monitoramento de processos
produtivos e para atendimento as normas adotadas por empresas de manufatura tornou-se algo
primordial. A partir da coleta destes dados, pouco se tem investido em estudos que
modelassem com precisão as características de falha nos ferramentais utilizados, ficando tal
atividade restrita geralmente às áreas técnicas e não gerenciais. A necessidade destas análises
é evidenciada como carência da alta gerência, com propósitos de estimar pla nos de
investimento anuais que contemplem a condição dos equipamentos.
A importância de qualquer falha específica é determinada parcialmente pelo efeito que tem no
desempenho de toda a produção ou sistema (SLACK, 1999). A partir da detecção,
cadastramento e diagnóstico das ocorrências de falhas há uma maximização da probabilidade
de atuar com precisão nas causas que realmente impactam negativamente nas metas de
produção.
Deve-se ter em mente que o objetivo principal da análise de falhas é evitar a ocorrênc ia de
novas falhas, ou seja, a investigação deve determinar as causas básicas das falhas e as
informaçoes pertinentes devem ser utilizadas para permitir a implantação de ações que
impeçam a reincidência do problema (AFONSO, 200 6). Como exemplo pode -se citar que, a
partir da aplicação dos métodos de análise de falhas, tem-se a possibilidade de prolongar a
fase de desgaste de uma fer ramenta ou equipamento, prorro gando a necessidade de gastos
imprevistos. Como consequência tem -se uma elevação d o nível de excel ência de produção e
redução nos custos inerentes a atividades tidas como de suporte a atividade de manufatura.
As abordagens adotadas para a análise de falhas visam primordialmente modelar o
comportamento de um dado equipamento ao longo da sua vida útil, garantindo uma estimativa
mais concreta no planejamento de novos recursos em planos de investimento e no
estabelecimento de intervalos adequados para as atividades de manutenção preventiva e
preditiva.
Nesse ponto deve-se discutir a respeito da profundidade da análise da falha, pois normalmente
as indústrias não têm uma equipe dedicada exclusivamente para essa atividade. Desta forma,
Afonso (2006) cita que há a necessidade do estabelecimento de um critério de priorização que
ajude a enfocar os problemas principais, a fim de se obter o maior retorno possível em função
dos recursos disponíveis, conforme apresentado sumariamente na Figura 1.

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

3
Tipos de falhas
Não repetitivas
Sem perdas na produção,
riscos de acidentes ou
agressões ambientais
Repetitivas
Ocasionam perdas na
produção, riscos de
acidentes ou agressões
ambientais
Supervisor de manutenção
Grupo multidisciplinar
(operação, manutenção e
engenharia)

Figura 1 – Profundidade da análise em função das características das falhas (Adaptado de AFONSO, 2006)
Desta forma, verifica-se que a aplicação dos conceitos de confiabilidade consiste em uma
ferramenta importante na análise de falhas. A confiabilidade de um item corresponde a sua
probabilidade de desempenhar de forma adequada o propósito pelo qual foi projetado,
considerando um período de tempo sob condições de operação pré -determinadas, isento de
falhas (NBR 5462, 1994). Complementando esse conceito, Lafraia (2001) cita que a
confiabilidade está relacionada com a avaliação probabilística da falha de um dado produto,
equipamento e/ou sistema.
Segundo Filho (2006), a confiabilidade e o gerenciamento de riscos são áreas de pesquisa que
vêm apresentando um crescimento significativo, principalmente devido às exigências
impostas pela sociedade com relação à vários aspectos, podendo -se citar a melhora da
qualidade e eficiência de produtos, aumento da produtividade e competitividade das
organizações, entre ou tros. Nesse contexto, as técnicas de confiabi lidade são um poderoso
instrumento para auxiliar os gestores na tomada de decisão, possibilitando a implementação
de políticas que minimizem os custos de operação, manutenção e inspeção de sistemas
industriais.
Levando-se em consideração a confiabilidade de sistemas, Brostel e Souza (2005) salientam
que existem duas categorias específicas: a confiabilidade de projetos e a confiabilidade
operacional. Na primeira categoria inclui o estudo de itens, como a análise de confiabilidade,
verificação de projetos e análises de testes de confiabilidade. Já a confiabilidade operacional
trata da análise de falhas, registros de operação, ações preventivas/corretivas entre outras.
Desde sistemas simples , e principalmente nos sistemas complexos, as sistemáticas de
manutenção devem ser mais elaboradas. Desta forma, a confiabilidade apresenta-se como uma
ferramenta imprescindível para se conhecer o comportamento de ítens críticos que precisam
ser gerenciados, cujo o aumento da confiabilidade requer o aumento do tempo mé dio entre
falhas (MTBF - Mean Time Between Failures ) de um dado equipamento e/ou sistema. Nesse
sentido, Dias (1996) comenta com propriedade que para se avaliar adequadamente os efeitos
da falha em um sistema devem ser considerados os aspectos tanto técnicos quanto gerenciais.
A análise de confiabilidade tem sido aplicada em várias áreas do conhecimento, como nas
engenharias mecânica e eletrônica, no desenvolvimento de sistemas de software e na
engenharia de manutenção. Martins e Sellitto (2006) realizaram um es tudo de confiabilidade
em alimentadores de energia elétrica, cujos autores determinaram que os dados de falha

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

4
desses elementos seguiam uma distribuição de Weibull, determinando assim a confiabilidade
dos mesmos e o ponto do ciclo de vida no qual o sistema se encontrava no momento. Souza e
Possamai (2000) estudaram a aplicação do conceito de confiabilidade como suporte ao projeto
de desenvolvimento de produtos em uma empresa fabricante de eletrodomésticos do sul do
Brasil, juntamente com outras ferramentas como o QFD, a FTA e o FMEA, mostrando que há
um ganho dentro do processo ao se empregar essas ferramentas de forma integrada . Sellitto
(2007) realizou um a análise da manutenção em uma linha de produção de indústria do ramo
automobilístico composta por seis unidades produtivas, cujos equipamentos podem apresentar
muitos modos de falha diferentes , baseando-se em estudos de confiabilidade sistêmica e de
equipamentos individuais. O autor mostrou, através das análises efetuadas, que havia a
possibilidade da realização de manutenções preventivas e preditivas em determinados grupos
de máquinas, mostrando a aplicabilidade da confiabilidade na determinação de intervalos de
manutenção.
Um trabalho muito interessante foi desenvolvido por Wuttke e Sellitto (2008), cujos autores
apresentaram uma forma de posicionar, na curva da banheira, a condição de uma válvula de
processo com base na técnica da manutenção centrada em confiabilidade ( Reliability centered
maintenance – RCM). Os autores demonstraram que, com base nos dados de falha da válvula,
o ideal seria a realização de atividades de manutenção preventiva.
Desta forma, o presente trabalho visa apresentar uma análise de confiabilidade de moldes
empregados no processo de injeção de plásticos, posicionando na curva da banhe ira a
condição dos mesmos. As análises realizadas, bem como as discussões pertinentes, estão
descritas nos itens a seguir.
2. Estudo de caso
2.1 Apresentação da empresa
A empresa onde o estudo foi realizado é fabricante de interruptores, tomadas, quadros
elétricos, plugues e acessórios domésticos e teve sua fundação no ano de 1964. O trabalho foi
realizado no setor de ferramentaria , onde poucos controles e índices existiam sobre a
utilização e manutenção de ferramentas de injeção. Na ferramentaria são realizados o
desenvolvimento do projeto, execução e manutenção do ferramental. O setor disp õe de quatro
máquinas de eletropenetração, uma de eletropenetração a frio, um torno mecânico, três fresas,
uma furadeira de bancada, mesa para solda T IG, dois moto -esmeris, duas retí ficas (plana e
perfil) e duas fresadoras CNC. Com este suporte são feitas as usinagens de novos
componentes e de reposição . O setor também é responsável pela realização dos testes ( try-
outs) das ferramentas (produzidas dentro e fora da empresa ), que após serem aprovadas são
liberadas a produção. O setor conta atualmente com duzentos moldes de injeção somados a
novos projetos com finalização prevista. Cada molde possui uma concepção única para o qual
foi dimensionado, sempre levando em considera ção principalmente as características gerais
das peças a serem injetadas e o material a ser utilizado. Os mesmos são utilizados em 26
máquinas injetoras, os principais materiais utilizados são os plásticos PP, PS, ABS, PA e PC.
2.2 Procedimento de análise
Para execução de quaisquer atividades relacio nadas ao setor de ferramentaria é necessário
gerar uma ordem de serviço de ferramentaria (OSF), cuja abertura é responsabilidade do
solicitante da área. Todo e qualquer tipo de informação pertinente ao serviço deve ser atrelada

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

5
ao documento. Cada colaborador caracteriza o teor das tarefas a serem executadas em função
dos códigos para classificação (com informações sobre as características de falha), incluindo o
tempo de duração em cada tarefa executada . Após o fechamento do mês as informações são
inseridas em arquivo eletrônico para apresentações e análises estatísticas para discussão,
procurando identificar modos de falha em potencial e orientar medidas preventivas.
Os dados que empregados nesse estudo foram extraídos do controle de OSF dentro do período
de um ano (maio/2008 -maio/2009). No presente trabalho serão apresentados os dados
referentes ao comportamento das falhas do molde do corpo da tomada padrão NBR 14136,
que é um equipamento responsável por uma signi ficativa parcela do faturamento da empresa
atualmente. Na Figura 2 está apresentado um dos moldes que são empregados na produção.

Figura 2 – Molde objeto de estudo
A ferramenta que comporta os moldes teve sua fabricação em agosto de 2004, e é uma peça
de extrema importância para garantia do fa turamento mensal da organização . Dentro do
período de um ano os moldes a presentaram um total de 56 falhas , cuja distribuição nos
diversos modos de falha estão apresentados na Tabela 1.

Modo de falha Ocorrência
Rebarba(s) na(s) peça(s) 34%
Retenção de peça(s) 16%
Bico(s) de injeção entupido(s) 10%
Peça(s) deformada(s) 9%
Vazamento d´água 5%
Outros 26%
Tabela 1 – Grau de incidência dos modos de falha

As principais causas de falha, considerando o modo de falha predominante, estão
apresentadas na
Figura 3.

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

6

Figura 3 – Principais causas de falha relacionadas com a presença de rebarbas em peças injetadas
Em função da importância desse equipamento dentro do processo de produção e da
necessidade da realização de um diagnóstico adequado dos tempos médios entre a ocorrência
de falhas, decidiu-se pela realização de um estudo de confiabilidade operacional dos moldes.
Primeiramente foi realizada uma análise visando determinar o modelo estatístico que tenha
uma melhor aderência aos dados de falha. Para tanto foram usados dois softwares específicos,
empregando-se o estimador da Máxima Verossimilhança para a obtenção dos dados . Os
resultados dos testes de aderência estão apresentados na Tabela 2 e na Tabela 3.

Distribuição Teste 2 5df Teste KS Decisão
Exponencial n.s. = 0,9537 n.s. = 0,3623 Não rejeitar
Weibull n.s. = 0,8811 n.s. = 0,3736 Não rejeitar
Gamma n.s. = 0,8958 n.s. = 0,3658 Não rejeitar
Lognormal n.s. = 0,6273 n.s. = 0,2405 Não rejeitar
Normal n.s. = 0,0000 n.s. = 0,0000 Rejeitar
Tabela 2 – Resultados dos ajustes às distribuições (Fonte: ProConf 98®)

Distribuição Teste 2
P(2
crit < 2)
Teste KS
P(Dcr < D)
Decisão
Exponencial 0,014% 0,027% Não rejeitar
Weibull 0,001% 0,666% Não rejeitar
Gamma - 100% Rejeitar
Lognormal 0,007% 7,39% Não rejeitar
Normal 0,121% 88,81% Rejeitar
Tabela 3 – Resultados dos ajustes às distribuições (Fonte: Weibull ++7®)
Desta forma, decidiu -se adotar a distribuição de Weibull para representar o compo rtamento
das falhas da ferramenta. Essa escolha baseia -se no fato de que essa distribuição expl ica o
comportamento de sistemas complexos cuja falha é oriunda da competição entre diversos
modos de falha, o que ocorre se eles atuarem em série, competindo pel a falha, como em
equipamentos industriais (LEWIS, 1996 citado por SELLITTO, 2007).
Independentemente do software empregado, os parâmetros da distribuição foram exatamente
os mesmos, conforme observado na Tabela 4.
Rebarba(s)
na(s)
peça(s)

Cavidade do
módulo
fora da posição
Deformação
na
cavidade/módulo
Trinca
na
cavidade/módulo

Quebra do pino

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

7

Software   MTBF (horas) t10 (horas) t50 (horas)
ProConf 98® 1,0495 46,9153 46 5,16 32,46
Weibull ++7® 1,0495 46,9153 46 5,16 32,46
Tabela 4 – Valores dos parâmetros para distribuição de Weibull
Pode-se verificar que o parâmetro de forma () está muito próximo de 1, o que significa que a
ferramenta encontra-se na fase de vida útil dentro da chamada curva da banheira. Nesta etapa
pode-se a firmar que as falhas incidentes nos componentes mecânicos estão relacionadas com
eventos aleatórios e/o u erros sistemáticos no processo , conforme mostrado na Figura 4 e
ratificado pela observação do comportamento da taxa de falhas no tempo ( Figura 6). Além
disso, o MTBF calculado está aderente com a situaç ão atual do equipamento de acordo com o
pessoal responsável pela manutenção , evidenciando o curto intervalo de tempo de operação
contínua do mesmo.

Figura 4 – Comportamento de um equipamento em função do parâmetro de forma da distribuição de Weibull
O gráfico de probabilidade para as falhas nos moldes está apresentado na Figura 5.

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

8
ReliaSoft W eibull++ 7 - www.ReliaSoft.com.br
Tempo, (t)
P r o b a b ilid a d e d e F a lh a , F ( t )
0,100 1000,0001,000 10,000 100,000
1,000
5,000
10,000
50,000
90,000
99,000

Figura 5 – Papel de probabilidade de Weibull para os dados apresentados (Fonte: Weibull ++7®)
Na Figura 6 está apresentada a função de risco para os moldes. Pode -se observar que ela
apresenta uma caract erística aproximadamente linear , ratificando a coloca ção de que os
moldes encontram-se na fase de vida útil da curva da banheira.

ReliaSoft W eibull++ 7 - www.ReliaSoft.com.br
Tempo, (t)
T a x a d e F a lh a , f ( t ) / R ( t )
0,000 200,00040,000 80,000 120,000 160,000
0,000
0,030
0,006
0,012
0,018
0,024

Figura 6 – Taxa de falhas dos moldes (Fonte: Weibull ++7®)

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

9
Na Figura 7 está apresentada a curva de confiabililidade dos moldes em estudo ao longo do
tempo.

ReliaSoft W eibull++ 7 - www.ReliaSoft.com.br
Tempo, (t)
C o n f ia b ilid a d e , R ( t ) = 1 - F ( t )
0,000 300,00060,000 120,000 180,000 240,000
0,000
1,000
0,200
0,400
0,600
0,800

Figura 7 – Gráfico de confiabilidade dos moldes (Fonte: Weibull ++7®)

Neste caso específico foi realizada uma análise para se verificar se é mais vantajoso realizar
uma manutenção preventiva nos moldes ou continuar efetuando a manutenção cor retiva,
como é atualmente realizado na empresa. O procedimento efetuado foi baseado no trabalho
apresentado por Sellito et al. (2002) , que analisa a viabilidade da realização de manutenção
corretiva ou preventiva em um equipamento, considerando que os dado s de falha possam ser
modelados pela distribuição de Weibull. Para a realização dessa atividade foi levantado que o
custo da manutenção preventiva na ferramenta era igual a R$ 18,80, excetuando-se os casos
onde ocorra a necessidade da realização de serviços de eletroerosão com fio de cobre, em
função do alto custo da hora -máquina. Já o custo da manutenção corretiva é , em média, igual
a R$ 94,00. Co m base nesses valores e nos parâ metros da distribuição de Weibull , verificou-
se que a implementação da manutenç ão preventiva não se torna viável. Alguns pontos podem
explicar essa afirmação:
a) Como os dados de falha do s moldes encontram-se na região de vida útil do s mesmos as
falhas tentem a ser aleatórias, considerando os principais modos de falha diagnosticados .
A presença de rebarba na peça é considerada responsável pelo maior índice de ocorrências
de manutenção corretiva no equipamento. Dentre os diversos fatores que podem ocasionar
esse problema podem ser destacados a presença de trincas no molde, quebras no pino ,
entre outros. Essas ocorrências são consideradas aleatórias, visto que não há a
possibilidade de identificar algum sintoma de aparecimento desses problemas durante a
operação normal do equipamento.

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

10
b) O baixo valor do MTBF do equipamento (46 horas) indica que, possivelmente, as falhas
sejam de origem sistemá tica, ou seja, atribuídas a um fator externo. No caso em questão
suspeita-se que esteja ocorrendo um desalinhamento da parte fixa com a parte móvel do
equipamento de injeção. Tal fato pode ocorrer em fun ção de algumas causas básicas, tais
como: falta de cuidado dos profissionais responsáveis pela colocação do molde em
máquina, no momento em que ocorrem solicitações para troca do produto a ser f abricado
no processo de injeção bem como o desalinhamento da p rópria máquina injetora, em
função do proce sso repetitivo de funcionamento durante os três turnos , cada um com 8
horas de serviço.

Como o equipamento teoricamente encontra -se na zona de falhas constantes da curva da
banheira (Figura 4), três alternativas podem ser adotadas (isoladamente ou em conjunto). A
primeira diz respeito ao projeto de moldes mais robustos em relação às suas condições de
utilização. A padronização das operações consiste na segunda medida a ser tomada para
melhorar a confiabilidade dos moldes , cujas medidas práticas sugeridas estão detalhadamente
apresentadas nas Conclusões do presente trabalho . Já a terceira alternativa diz respeito à
adoção de técnicas de manutenção preditiva nos moldes, a fim de tentar ident ificar algum
indício de trincas, desalinhamentos, entre outros.

3. Conclusões

O nível de conformidade exigido pela matriz internacional da empresa em qualquer processo
de fabricação corresponde a 97% da produção total. Considerando o alto padrão de exigência,
as constantes paradas de produção em função da constatação de rebarbas (que é con siderado
um item não conforme) tornam -se freqüentes, com perda de tempo para a realização das
atividades de manutenção nos moldes, com conseqüente minimização da dispon ibilidade do
equipamento para a produção.
Com os dados de falha coletados e analisados através da teoria da confiabilidade pôde-se
apresentar à direção da empresa o comportamento do equipamento ao longo do tempo . O
baixo valor do MTBF evidencia que em apro ximadamente 6 turnos ininterruptos de trabalho
ocorre a paralisação da produção por culpa do aparecimento de falhas no molde de injeção.
Desta forma, a fim de maximizar o tempo de operação do equipamento, deve m ser
estabelecidos intervalos pré-programados para a parada do mesmo, em virtude da verificação
das condições dos moldes (limpeza, verificação do alinhamento, avarias na estrutura do
molde, entre outras) , de preferência empregando -se as técnicas de manutenção preditiva . O
MTBF pode ser considerado como parâmetro indicativo desse tempo, já que na atual situação
de operação o molde é revisado somente ao final da produção programada para o mesmo , o
que normalmente ultrapassa o período de 30 dias.
Além disso, os profissionais responsáveis pela s trocas de molde, preparação de máquina
(alimentação de matéria -prima e pré -setagem dos parâmetros de injeção) devem
necessariamente passar por uma qualificação condizente com a complexidade do processo , a
fim de minimizar problemas relacionados ao incorreto posicionamento e manipulação do
molde em situações que não vão de encontro com suas atribuições profissionais,
proporcionando o bom andamento das atividades e conseqüente minimização da ocorrência de
falhas no equipamento. Para isso, a atividade de treinamento inte nsivo relacionado à análise
de falhas para o pessoal operacional é importante, pois a maior parte dos problemas é
diagnosticada pelos operadores e/ou supervisores, que devem reconhecer o modo de falha e
identificar as principais causas das mesmas. Somente com o reconhecimento das limitações

XXIX ENCONTRO NACIONAL DE ENGENHARIA DE PRODUCAO
A Engenharia de Produção e o Desenvolvimento Sustentável: Integrando Tecnologia e Gestão
Salvador, BA, Brasil, 06 a 09 de outubro de 2009

11
sobre a abrangência de cada função no chão de fábrica e com a determinação dos intervalos
de monitoramento, boa parte das medidas corretivas teria uma maior probabilidade de serem
evitadas ou ao menos atenuadas significativamente.

Referências
AFONSO, L. O A. Equipamentos mecânicos: análise de falhas e solução de problemas. Qualitymark.
Rio de Janeiro, 336p. 2006.
ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS . Confiabilidade e mantenabilidade -
terminologia NBR 5462. Rio de Janeiro, 37p. 1994.
BROSTEL, R. C.; SOUZA, M. A. A. Determinação da confiabilidade operacional de estações de
tratamento de esgotos do Distrito Fede ral. 23º Congresso Brasileiro de Engenharia Sanitária e
Ambiental. Campo Grande, 11p. 2005.
DIAS, A. Metodologia para análise da confiabilidade em freios pneumáticos automotivos. Tese (Doutorado
em Engenharia Mecânica) UNICAMP. Campinas, SP. 199p. 1996.
FILHO, S. S . Análise de árvore de falhas considerando incertezas na definição dos eventos básicos . Tese
(Doutorado em Engenharia Civil). COPPE/UFRJ, Rio de Janeiro, 299p. 2006.
LAFRAIA, J. R. B. Manual de confiabilidade, mantenabilidade e disponibilidade. Qualitymark. Rio de Janeiro,
373p. 2001.
MARTINS, J. C.; SELLITTO, M. Análise da estratégia de m anutenção de uma concessionária de energia
elétrica com base em estudos de confiabilidade. XXVI ENEGEP. Fortaleza. ABEPRO, 9p. 2006.
PROCONF 98 . Confiabilidade de Componentes . Software. Copyright©, Maxxi Gestão Empresarial, Porto
Alegre, 1998.
SELLITTO, M. Análise estratégica da m anutenção de uma linha de fabricação metal -mecânica baseada em
cálculos de confiabilidade de equipamentos. Gestão da Produção, Operações e Sistemas. Ano 2, v. 3, p. 97 -108,
mai-jun 2007.
SELLITTO, M.; BORCHADT, M.; ARAÚJO, D. R. C . Manutenção centrada em confiabilidade: aplicando
uma abordagem quantitativa. XXII ENEGEP. Curitiba. ABEPRO, 8p. 2002.
SLACK, N. Administração da Produção. Editora Atlas. São Paulo. 1999.
SOUZA, R. A.; POSSAMAI, O. Confiabilidade e falhas de campo: uma metodologia para su porte ao projeto.
II Congresso Brasileiro de Gestão de Desenvolvimento de Produto. São Carlos, 9p. 2000.
WEIBULL ++7. Software, Copyright©, Reliasoft Corporation, 2008.
WUTTKE, R. A.; SELLITTO, M. Cálculo da disponibilidade e da posição na curva da banheir a de uma
válvula de processo petroquímico. Revista Produção On-line. ABEPRO/UFSC. v. 8, n. 4, 23p., 2008.

## Aplicação para a Smart Control Brasil

Este material deve apoiar respostas técnicas da LÍVIA sobre manutenção, automação, confiabilidade, diagnóstico, TPM, FMEA, falhas ou engenharia, conectando conceitos à aplicação prática da Smart Control Brasil.

A LÍVIA não deve usar este material para prometer preço, prazo, estoque, garantia ou resultado comercial.
