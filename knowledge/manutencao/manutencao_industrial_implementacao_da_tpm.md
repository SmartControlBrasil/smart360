# Manutenção Industrial - Implementacao da TPM

> Fonte original: raw_academico/Manutenção Produtiva Total/Ferramentas da Gestão da Manutenção/Manutenção Industrial - Implementacao da TPM.pdf  
> Categoria: manutencao  
> Material convertido para apoio técnico da LÍVIA Assistant.

## Conteúdo extraído

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/

ISSN: 1984-3151
MANUTENÇÃO INDUSTRIAL: IMPLEMENTAÇÃO DA
M ANUTENÇÃO PRODUTIVA TOTAL (TPM)
INDUSTRIAL MAINTENANCE: I MPLEMENTATION OF TOTAL
PRODUCTIVE M AINTENANCE (TPM)

Cássio Ferreira Nogueira 1; Leonardo Miranda Guimarães 2; Margarete Diniz Braz da
Silva 3 ;

Recebido em: 01/06/2012 - Aprovado em: 30/06/2012 - Disponibilizado em: 30/07/2012

R
ESUMO : O presente trabalho consiste na criação de uma metodologia de análise de falha de um equipamento
destinado à fabricação de componentes empregados na montagem de máquinas de solda de uma indústria da
área de soldagem. Essa metodologia é uma das exigências de um programa de gestão de equipamentos e
processos produtivos, adotado pela empresa, chamado TPM (Total Preventive Maintenance ou Manutenção
Produtiva Total). O TPM tem várias áreas de atuação, destacam-se: o meio ambiente, operação de equipamentos
e manutenção. Cada uma das áreas desse programa de gestão possui uma ferramenta específica chamada de
pilar. O cerne desse trabalho é o pilar de MP (Manutenção Profissional) do TPM. Nesse pilar está incluído o
levantamento de falhas crônicas referentes a um equipamento, o estudo das reais causas dessas falhas, a
identificação de pontos de melhoria no equipamento e a criação de um plano de manutenção otimizado para o
equipamento estudado. Para realizar o desenvolvimento dessa metodologia foram utilizadas técnicas de RCM
(Reliability Centered Maintenance ou Manutenção Centrada na Confiabilidade), estudos de FMEA (Failure Mode
and Effect Analysis ou Modo de Falha e análise do efeito) e ciclos de gestão PDCA (Plan, Do, Check and Act ou
Planejar, Realizar, Verificar e Agir). Com o resultado desse trabalho foi alcançado um plano, onde se tem o menor
custo de realização de manutenção preventiva e a identificação das causas raízes das principais falhas do
equipamento.
P
ALAVRAS CHAVE : TPM. Estudo de falhas. Manutenção Profissional.

A
BSTRACT : The present work is to establish a methodology for failure analysis of an equipment for the manufacture
of components used in assembling welding machines an industry from the welding area. This methodology is one
of the requirements for a management program for equipment and processes, adopted by the company, called
TPM (Total Production Maintenance). The TPM has several areas, stand out the environment, equipment operation
and maintenance. Each one of these areas of program management has a specific tool called the pillar. The core
of this work is the pillar of MP (Professional Maintenance) from TPM. This pillar is included identify chronics failures
related to equipment, the study of the real causes of these failures, the identification of areas for improvement in
equipment and creating a maintenance plan optimized for the equipment studied. To accomplish this development
of this methodology were used techniques RCM (Reliability Centered Maintenance), FMEA studies (Failure Mode
and Effect Analysis) and cycle management PDCA (Plan, Do, Check and Action). As a result of this work has been
achieved an plan, which has the lowest cost of performing preventive maintenance and identify the root causes of
major equipment failures.
K
EYWORDS : TPM. Study faults. Professional Maintenance.
___________________________________________________________________________

1 Engenheiro Eletricista. Centro Universitário de Belo
Horizonte – UniBH. ESAB IND. E COMERCIO LTDA -
Contagem, MG. – cássio.nogueira@esab.com.br
2 Engenheiro Eletricista. Centro Universitário de Belo
Horizonte – UniBH. THELGA Comércio e Serviços LTDA
Belo Horizonte, MG. – leo_mg09@yahoo.com.br
3 Mestre em Administração, Universidade Fumec, 2010 .
Professora do Centro Universitário de Belo Horizonte –
UNIBH, Belo Horizonte, MG – margaretedbs@gmail.com

176
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
1 INTRODUÇÃO
A evolução da manutenção teve seu marco após a
Segunda Guerra Mundial, quando a indústria
necessitou se adequar para atender a demanda do
mercado. Antes deste período as máquinas eram
pouco mecanizadas e muitas vezes
superdimensionadas, prevalecendo a presença da
mão-de-obra industrial.
Após a Segunda Guerra Mundial até a década de 60
houve uma modificação do processo produtivo, devido
pressões do mercado por todos os tipos de produtos,
o que levou a mecanização dos equipamentos e a
instalação de áreas industriais.
Entretanto, a manutenção dos equipamentos era cara,
o que ocasionou em um aumento dos custos
operacionais, mas muitas empresas enxergam, até os
dias atuais, a manutenção de um equipamento
produtivo (Ativo) como uma despesa indesejável.
Quando a manutenção é bem estruturada pode ser
considerada fonte de lucro e um diferencial
competitivo no mercado. Ao se tratar de qualidade e
produtividade, a manutenção exerce um papel vital,
evitando com que o equipamento sofra uma parada
não programada ou que comece a produzir fora de
padrão.
A manutenção do ativo é fundamental no
estabelecimento de uma estrutura, que proporcione o
aumento da confiabilidade e disponibilidade dos
equipamentos para a produção.
Uma empresa na área de soldagem está buscando
um diferencial competitivo frente ao mercado e
investindo na implementação de um sistema de
gestão de equipamentos e processos chamado TPM
(Manutenção de Produção Total). Esse sistema de
gestão abrange diversas áreas de uma indústria e
cada uma dessas áreas de atuação recebe o nome de
“Pilar”.

2 REFERENCIAL TEÓRICO
Segundo Pinto e Xavier (2007) a evolução da
manutenção pode ser dividida em 3 gerações.
A Primeira Geração abrange o período antes da
Segunda Guerra Mundial, quando a indústria era
pouco mecanizada, os equipamentos eram simples e,
na sua grande maioria, superdimensionados.
Aliados a tudo isto, os autores ressaltam que, devido a
conjuntura econômica da época, a questão da
produtividade não era prioritária. Consequentemente,
não era necessária uma manutenção sistemática;
apenas serviços de limpeza, lubrificação e reparo
após a quebra, ou seja, a manutenção era,
fundamentalmente, corretiva.
Para os mesmos autores, a segunda geração inicia na
Segunda Guerra Mundial até os anos 60. As pressões
do período da guerra aumentaram a demanda por
todo tipo de produtos, ao mesmo tempo que o
contingente de mão de obra industrial diminuiu
sensivelmente. Como consequência, neste período
houve forte aumento da mecanização, bem como a
complexidade das instalações industriais.
Começa a evidenciar-se a necessidade de maior
disponibilidade, bem como, maior confiabilidade, tudo
isto na busca do aumento da produtividade. A
indústria estava bastante dependente do bom
funcionamento das máquinas. Isto levou à ideia de
que falhas dos equipamentos poderiam e deveriam
ser evitadas, o que resultou no conceito de
manutenção preventiva. (PINTO; XAVIER, 2007)
Os autores ainda ressaltam que na década de 60 esta
manutenção consistia de intervenções nos
equipamentos, feitas a intervalo fixo e que o custo da
manutenção também começou a se elevar muito em
comparação com outros custos operacionais. Esse
fato fez aumentar os sistemas de planejamento e
controle de manutenção que, hoje, são partes
integrantes da manutenção moderna.

177

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Finalmente, a quantidade de capital investido em itens
físicos, justamente com o nítido aumento do custo
deste capital, levaram as
indústrias a começarem a
buscar meios para aumentar a vida útil dos itens
físicos.(PINTO; XAVIER, 2007)
Ainda para os mesmos autores a terceira geração
iniciou-se a partir da década de 70, acelerando o
processo de mudança nas indústrias. A paralisação da
produção, que sempre diminui a capacidade produtiva,
aumentou os custos e afetou a qualidade dos produtos
e era uma preocupação generalizada. Na manufatura,
os efeitos dos períodos de paralisação foram se
agravando pela tendência mundial de utilizar sistemas
Just-in-time , onde estoques reduzidos para a
produção em andamento significavam que pequenas
pausas na produção, naquele momento, poderiam
paralisar a fábrica.
O crescimento da automação e da mecanização
passou a indicar que a confiabilidade e a
disponibilidade tornaram-se pontos–chave em setores
tão distintos quanto saúde, processamento de dados,
telecomunicações e gerenciamento de edificações.
Segundo Pinto e Xavier (2007), na terceira geração
reforçou-se o conceito de uma manutenção preditiva.
A manutenção preditiva é aquela que indica as
condições reais de funcionamento das máquinas com
base em dados que informam o seu desgaste ou
processo de degradação. Trata-se de um processo
que prediz o tempo de vida útil dos componentes das
máquinas e equipamentos e as condições para que
esse tempo de vida seja bem aproveitado. A interação
entre as fases de implantação de um sistema (projeto,
fabricação, instalação e manutenção) e a
disponibilidade e a confiabilidade tornam-se mais
evidentes.

2.1
TIPOS DE MANUTENÇÃO
Segundo Viana (2002), os tipos de manutenção são
as formas de encaminhar as intervenções nos
instrumentos de produção, ou seja, nos equipamentos
que compõem uma determinada planta. Neste sentido
observa-se que existe um consenso, salvo algumas
variações irrelevantes, quanto aos tipos de
manutenção.
Os principais tipos de manutenção são descritos nas
seções subsequentes.

2.2
M ANUTENÇÃO C ORRETIVA
A manutenção corretiva ocorre em duas situações
específicas: quando o equipamento apresenta um
desempenho abaixo do esperado, apontado pelo
monitoramento, ou quando ocorre a falha do
equipamento.
Dessa forma, pode-se verificar que a principal função
da manutenção corretiva é restaurar ou corrigir as
condições de funcionamento de um determinado
equipamento ou sistema. E baseado nisto, a
manutenção corretiva se divide em: Planejada ou Não
Planejada.

2.2.1 M ANUTENÇÃO CORRETIVA NÃO PLANEJADA
Este tipo de manutenção acontece após a falha ou
perda de desempenho de um equipamento sem que
haja tempo para a preparação dos serviços, trazendo
prejuízos enormes para as empresas, pois implica em
altos custos, causados pela interrupção da produção,
a realização de manutenção inesperada e,
dependendo da atividade da empresa, perda da
qualidade do produto.
Um dos grandes desafios dos setores responsáveis é
conseguir evitar esse tipo de manutenção, que apesar
de todos os transtornos, ainda é muito praticada nos
dias de hoje.

178
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
2.2.2 M ANUTENÇÃO CORRETIVA PLANEJADA
É a correção do desempenho menor do que o
esperado ou da falha, por decisão gerencial, isto é,
pela atuação em função de acompanhamento
preditivo ou pela decisão de operar até a quebra.
(PINTO e XAVIER, 2007, p. 34).

Este tipo de manutenção depende da qualidade da
informação fornecida pelo acompanhamento preditivo
e possibilita um planejamento para a execução das
tarefas, de forma que os custos podem ser
minimizados, uma vez que é esperada a falha ou a
perda de rendimento do equipamento.

2.3
M ANUTENÇÃO PREVENTIVA
A manutenção preventiva, ao contrário da corretiva,
visa evitar a falha do equipamento. Este tipo de
manutenção é realizado em equipamentos que não
estejam em falha, ou seja, estejam operando em
perfeitas condições. Desta forma, podem-se ter duas
situações bastante diferentes: a primeira é quando
desativa o equipamento bem antes do necessário para
fazer a manutenção do mesmo; a segunda situação é
a falha do equipamento, por estimar o período de
reparo do mesmo de maneira incorreta.
Baseando-se nestas duas situações é importante
ressaltar que, a definição do período de parada dos
equipamentos seja efetuada por pessoas experientes,
que conheçam bem o equipamento a ser manutenido,
seguindo as informações do fabricante e,
principalmente, dependendo das condições climáticas
em que estes se encontram, pois um mesmo
equipamento pode se comportar de maneira bem
distinta, conforme as condições climáticas que estiver
submetido.
A manutenção preventiva tem um lado negativo, pois
pode introduzir defeitos não existentes no
equipamento devido a:
• falhas humanas,
• falhas nos componentes sobressalentes,
• contaminações em sistemas de óleo dos
equipamentos,
• falhas ocasionadas durante partidas e
paradas dos equipamentos, e
• falhas nos procedimentos de manutenção.

2.4 M ANUTENÇÃO PREDITIVA
Este tipo de manutenção, nada mais é do que uma
manutenção preventiva baseada na condição do
equipamento. É interessante, pois permite o
acompanhamento do equipamento através de
medições realizadas quando ele estiver em pleno
funcionamento, o que possibilita uma maior
disponibilidade, já que este vai sofrer intervenção,
somente quando estiver próximo de um limite
estabelecido previamente pela equipe de manutenção.
Pode-se dizer que a manutenção preditiva prediz a
falha do equipamento e quando se resolve fazer a
intervenção para o reparo do mesmo, o que acontece,
é na verdade uma manutenção corretiva programada.
As condições básicas para que seja estabelecido este
tipo de manutenção, são as seguintes:
a) o equipamento, sistema ou instalação deve permitir
algum tipo de monitoramento.
b) o equipamento, sistema ou instalação deve ter a
escolha por este tipo de manutenção justificada pelos
custos envolvidos.
c) as falhas devem ser originadas de causas que
possam ser monitoradas e ter sua progressão
acompanhada.

179

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
2.5 TPM (M ANUTENÇÃO PRODUTIVA TOTAL )
Para Wyrebski (1997), a TPM, antes de tudo, deve ser
encarada como uma filosofia de gestão empresarial
centrada na disponibilidade total do equipamento para
a produção. Tal filosofia deve ser seguida por todos os
segmentos da empresa, desde a alta gerência até o
operador do equipamento. A Manutenção Produtiva
Total surgiu no Japão no período pós Segunda Guerra
Mundial. As empresas Japonesas, até então famosas
pela fabricação de produtos de baixa qualidade e
arrasadas pela destruição causada pela guerra,
buscaram, na excelência da qualidade, uma
alternativa para reverter o quadro na qual se
encontravam. Com isso, os primeiros registros de
implementação da TPM pertencem à empresa Nippon
Denso, do grupo Toyota. No Brasil, essa filosofia
começou a ser praticada em 1986.
O autor ressalta que a TPM é baseada em alguns
aspectos chamados de pilares. Já Pinto e Xavier
(2007) apresentam diferenciações nesses conceitos
no que diz respeito à classificação ou à nomenclatura,
entretanto não divergem nos princípios e metas que a
TPM apresenta. Os pilares da TPM são apresentados
na Figura 1.

Figura 1: Os pilares da TPM
Fonte: PINTO; XAVIER, 2007, p.185

2.6.1 C ONCEITOS E CARACTERÍSTICAS DA TPM
Segundo Tavares (1999), o conceito básico da TPM é
a reformulação e a melhoria da estrutura empresarial
a partir da reestruturação e melhoria das pessoas e
dos equipamentos, com envolvimento de todos os
níveis hierárquicos e a mudança da postura
organizacional.
Em relação aos equipamentos, o autor ressalta que
significa promover a revolução junto à linha de
produção, através da incorporação da "Quebra Zero",
"Defeito Zero" e "Acidente Zero".

180
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Para Nakajima (1989), significa montar uma estrutura
onde haja a participação de todos os escalões, desde
a alta direção até os postos operacionais de todos os
departamentos, ou seja, uma sistemática PM
(Prevenção da Manutenção), com envolvimento de
todos. Trata-se da efetivação de um " Equipment
Management ", isto é, a administração das máquinas
por toda a organização.
Conforme Banker (1995), a TPM cria um auto-
gerenciamento no local de trabalho, uma vez que os
operadores "assumem" a propriedade de seu
equipamento e, cuidam dele, eles próprios.
Eliminando-se as paradas e defeitos, cria-se
confiança. A TPM respeita a inteligência e o potencial
de conhecimento de todos os empregados da
empresa.
Tahashi e Osada (1993) reforçam o significado da
TPM como:
Uma manutenção preventiva mais ampla, baseada na
aplicabilidade econômica vitalícia de equipamentos,
matrizes e gabaritos que desempenham os papéis
mais importantes na produção. (TAHASHI; OSADA,
1993).
A definição da TPM, proposta em 1971 pela JIPM
(Japan Institute of Plant Maintenance), foi revista em
1989, estabelecendo-se uma nova exposição, que se
constitui dos cinco itens seguintes:
1 - tendo como o objetivo a constituição de uma
estrutura empresarial que busca a máxima eficiência
do sistema de produção (eficiência global);
2 - construindo, no próprio local de trabalho,
mecanismos para prevenir as diversas perdas,
atingindo "zero de acidente, zero de defeito e zero de
quebra/falha", tendo como objetivo o ciclo total de vida
útil do sistema de produção;
3 - envolvendo todos os departamentos, começando
pelo departamento de produção, e se estendendo aos
setores de desenvolvimento, vendas, administração
etc;
4 - contando com a participação de todos, desde a alta
cúpula até os operários de primeira linha;
5 - atingindo a perda zero por meio de atividades
sobrepostas de pequenos grupos.

Tahashi e Osada (1993), ainda ressaltam que em
harmonia com a definição do TPM, cada uma das
letras possui um significado próprio como segue:
- a letra "T" significa "TOTAL". Total no sentido de
eficiência global, de ciclo total de vida útil do sistema
de produção e de envolvimento de todos os
departamentos que compõem a empresa;
- a letra "P" significa "PRODUCTIVE". A busca do
sistema de produção até o limite máximo da eficiência,
atingindo "zero acidente, zero defeito e quebra/falha
zero", ou seja, a eliminação de todos os tipos de perda
ate chegar ao nível zero;
- a letra "M" significa "MAINTENANCE". Manutenção
no sentido amplo, que tem como objeto o ciclo total de
vida útil do sistema de produção e designa a
manutenção que tem como objeto o sistema de
produção de processo único, a fábrica e o sistema de
vendas.
A partir da definição, pode-se delinear algumas
características peculiares ao TPM, que o diferenciam
dos movimentos tradicionais, como o da manutenção
do sistema de produção.
1 - A busca da Economicidade - A manutenção
produzida deve proporcionar lucros.
2 - Um sistema integrado (total system).
3 - Manutenção espontânea, executada pelo próprio
operador - atividade de pequenos grupos.
Verifica-se, portanto, que "a manutenção produtiva
total é o envolvimento dos operários nos trabalhos de

181

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
prevenção e correção dos defeitos em seus
equipamentos".(JIPM,2011)

2.6.2 OBJETIVO DA TPM
Para Tahashi e Osada (1993), o TPM é um conceito
gerencial que começa pela liberação da criatividade
normalmente escondida e inexplorada em qualquer
grupo de trabalhadores. Estes trabalhadores,
frequentemente atarefados em tarefas aparentemente
repetitivas, têm muito a contribuir se, pelo menos, isto
lhes for permitido. Seu objetivo é promover uma
cultura na qual os operadores sintam que eles
"possuem" suas máquinas, aprendem muito mais
sobre elas, e no processo se liberam de sua ocupação
prática para se concentrarem no diagnóstico do
problema e do projeto de aperfeiçoamento do
equipamento. Desta forma, há um ganho direto.
Os mesmos autores ainda dizem que o objetivo do
TPM é a "melhoria da estrutura empresarial mediante
a melhoria da qualidade de pessoal e de
equipamento". Melhoria da qualidade de pessoal
significa a formação de pessoal adaptado à era da
Automação Fabril. Em outras palavras, cada pessoa
deve adquirir novas capacidades. Mediante a melhoria
da qualidade do pessoal realiza-se a melhoria da
qualidade do equipamento, que incluem-se os dois
pontos seguintes:
- atingir a eficiência global mediante melhoria da
qualidade dos equipamentos utilizados atualmente;
- elaborar o projeto LCC (Life Cycle Cost ) de novos
equipamentos e entrada imediata em produção.
Para atingir a eficiência global do equipamento, a TPM
visa a eliminação das perdas, que a prejudicam.
Tradicionalmente a identificação das perdas era
realizada ao se analisar estatisticamente os resultados
dos usos dos equipamentos, objetivando a
determinação de um problema, só então eram
investigadas as causas. O método adotado pela TPM
examina a produção de inputs como causa direta. Ele
é mais pró-ativo do que reativo, uma vez que corrige
as deficiências do equipamento, do operador e o
conhecimento do administrador em relação ao
equipamento. Deficiências de input (homem, máquina,
materiais e métodos) são consideradas perdas, e o
objetivo da TPM é a eliminação de todas as perdas.
Segundo Tahashi e Osada (1993), as seis grandes
perdas são:
1. por parada devido à quebra/falha;
2. por mudança de linha e regulagens;
3. por operação em vazio e pequenas paradas;
4. por queda de velocidade;
5. por defeitos gerados no processo de
produção;
6. no início da operação e por queda de
rendimento.

2.7
PDCA
Tahashi e Osada (1993), definem que o ciclo PDCA,
também conhecido como ciclo de Deming, é um ciclo
de desenvolvimento que tem cerne na melhoria
contínua de um processo produtivo, de um projeto ou
de um equipamento.
Ainda os autores completam que o PDCA foi
introduzido no Japão após a guerra, idealizado por
Shewhart e divulgado por Deming, quem efetivamente
o aplicou. Inicialmente deu-se o uso para estatística e
métodos de amostragem. O ciclo de Deming tem por
princípio tornar mais claros e ágeis os processos
envolvidos na execução da gestão, como, por
exemplo, na gestão da qualidade, dividindo-a em
quatro principais passos. (TAHASHI; OSADA, 1993).
Os passos desse ciclo podem ser resumidos, também,
da seguinte maneira:

182
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
P (Plan = Planejar): Definir o objetivo, planejar o que
será feito, estabelecer metas e definir os métodos que
permitirão atingir as metas propostas.
D (Do = Executar): Tomar iniciativa, treinar,
implementar, executar o planejado conforme as metas
e métodos definidos.
C (Check = Verificar): Verificar os resultados que se
está obtendo, verificar de maneira continua os
trabalhos para ver se estão sendo executados
conforme planejados.
A (Action = Agir): Fazer correções de rotas se for
necessário, tomar ações corretivas ou de melhoria.

2.8
M ÉTODOS DE ANÁLISE DE FALHA - FMEA
Conforme Pinto e Xavier (2007), a metodologia FMEA
(do inglês Failure Mode and Effect Analysis ), é uma
ferramenta que busca, em princípio, evitar, por meio
da análise das falhas potenciais e propostas de ações
de melhoria, que ocorram falhas no projeto do produto
ou do processo. O objetivo básico dessa ferramenta é
detectar as falhas e as causas raízes das mesmas
podendo-se intervir no processo ou no equipamento.
Pode-se dizer que, com sua utilização, está
diminuindo as chances do produto ou processo
falharem, ou seja, busca-se aumentar sua
confiabilidade, produtividade e disponibilidade.
Os mesmos autores ainda esclarecem que essa
metodologia pode ser aplicada tanto para produto
como para processos e equipamentos, as etapas e a
maneira de realização da análise são as mesmas,
ambas
diferenciando-se somente quanto ao objetivo.
As literaturas usam classificar as FMEA´s em dois
tipos:
FMEA DE PRODUTO: na qual são consideradas as
falhas que poderão ocorrer com o produto dentro das
especificações do projeto. O objetivo desta análise é
evitar
falhas no produto ou nos processos decorrentes
do projeto. É comumente denominada também de
FMEA de projeto.
FMEA DE PROCESSO: são consideradas as falhas
no planejamento e execução do processo, ou seja, o
objetivo desta análise é evitar falhas do processo,
tendo como base as não conformidades do produto
com as especificações do projeto.

2.8.1 A
PLICAÇÃO DA FMEA
Segundo Capaldo; Guerrero e Rozenfeld (1999), por
se tratar de uma metodologia bastante utilizada,
alguns casos de aplicação já se tornaram bastante
característicos como:
• “para diminuir a probabilidade da ocorrência
de falhas em projetos de novos produtos ou
processos;
• para diminuir a probabilidade de falhas
potenciais (ou seja, que ainda não tenham
ocorrido) em produtos/processos já em
operação;
• para aumentar a confiabilidade de produtos ou
processos já em operação por meio da análise
das falhas que já ocorreram;
• para diminuir os riscos de erros e aumentar a
qualidade em procedimentos administrativos.”

2.8.2
FUNCIONAMENTO BÁSICO
Para Capaldo, Guerrero e Rozenfeld (1999), para
realizar essa análise de fallhas, forma-se um grupo de
especialistas ou pessoas diretamente envolvidas no
processo, que identificam para o produto/processo em
questão suas funções, os tipos de falhas que podem
ocorrer, os efeitos e as possíveis causas desta falha.
Durante a análise, ferramentas tais como 4M, 5W1H e
5 Por quês são utilizadas para se obter a maior
quantidade de informações sobre o produto, processo
ou equipamento em questão. Depois de identificados

183

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
os pontos de melhoria, o grupo é incumbido de traçar
um plano de melhoria para sanar essa deficiência.
Para aplicar-se a análise FMEA em um
determinado produto/processo, portanto, forma-se
um grupo de trabalho que irá definir a função ou
característica daquele produto/processo, irá
relacionar todos os tipos de falhas que possam
ocorrer, descrever, para cada tipo de falha suas
possíveis causas e efeitos, relacionar as medidas
de detecção e prevenção de falhas que estão
sendo, ou já foram tomadas, e, para cada causa de
falha, atribuir índices para avaliar os riscos e, por
meio destes riscos, discutir medidas de melhoria.
(...) o Diagrama de Ishikawa ”, também conhecido
como "Diagrama de Causa e Efeito", "Diagrama
Espinha-de-peixe" ou "Diagrama 4M", é uma
ferramenta gráfica utilizada na Administração para
o gerenciamento e o Controle da Qualidade (CQ)
em processos diversos de manipulação das
fórmulas. Originalmente proposto pelo engenheiro
químico Kaoru Ishikawa em 1943 e aperfeiçoado
nos anos seguintes. (...)O sistema permite
estruturar hierarquicamente as causas potenciais
de determinado problema ou oportunidade de
melhoria, bem como seus efeitos sobre a qualidade
dos produtos. Permite, também, estruturar qualquer
sistema que necessite de resposta de forma gráfica
e sintética, isto é, com melhor visualização. (...) A
ferramenta 5W1H é um roteiro de perguntas a
serem feitas de maneira estratégica que visam
descrever de uma maneira mais detalhada o que
está acontecendo, qual é a falha, etc. (...) As
perguntas devem começar com : Quem (Who), O
que (What), Quando (When), Onde (Where), Por
que (Why) e Como (How). (...) O brainstorming
(literalmente: "tempestade cerebral" em inglês) ou
tempestade de ideias, mais que uma técnica de
dinâmica de grupo, é uma atividade desenvolvida
para explorar a potencialidade criativa de um
indivíduo ou de um grupo - criatividade em equipe -
colocando-a a serviço de objetivos pré-
determinados. O método dos 5 Por quês? consiste
em perguntas encadeadas sobre os efeitos,
motivos e causas dos problemas nos levam às
causas fundamentais que devem ser atacadas,
evitando que se fique, como muitas vezes é usual,
agindo apenas sobre os sintomas dos problemas e
não em sua solução e bloqueio. (CAPALDO;
GUERRERO; ROZENFELD, 1999).

3 M ETODOLOGIA
A pesquisa experimental do tipo estudo de caso
consiste em um estudo profundo e exaustivo de um
ou poucos objetos, de maneira que permite seu
amplo e detalhado conhecimento de tarefas
praticamente impossíveis mediante outros
delineamentos já considerados. Além disso, contém
as características de explorar situações da vida
real, cujos limites não estão claramente definidos,
preserva o caráter unitário do objeto estudado,
descreve a situação do contexto em que está
sendo feita determinada investigação, formula
hipóteses e desenvolve teorias e explica as
variáveis causais de determinado fenômeno em
situações muito complexas que não possibilitam a
utilização de levantamentos e experimentos. Foram
levantadas informações para subsidiar a
demonstração da proposta de implementação de
um modelo de manutenção. (GIL, 2010, p.184)
Essa metodologia pode ser descrita por meio dos
seguintes itens:

3.1 E
NTENDIMENTO DO SISTEMA DE PRODUÇÃO
VIGENTE
Para que houvesse uma familiaridade, uma visita ao
processo produtivo se fez essencial. Com essa visita
buscou-se entender as necessidades e características
do processo produtivo do setor, bem como o fluxo de
materiais, operações realizadas.

3.2 ENTENDIMENTO DO SISTEMA DE
MANUTENÇÃO VIGENTE
Uma vez conhecido o sistema de produção, a
manutenção se torna o próximo passo. Na
manutenção foram levantados dados técnicos e
estatísticos sobre o equipamento que foram vitais para
a realização do trabalho. No setor de manutenção
também foi verificado o processo de geração de
ordem de serviço e toda a documentação de serviços
de manutenção preventiva e corretiva, assim como o
fluxo de informação e gestão de mão-de-obra do
setor.

3.3 VERIFICAÇÃO E ENTENDIMENTO DOS DADOS
Nesse item da metodologia buscou-se analisar os
documentos que foram disponibilizados, formando um
banco de dados que deu suporte às atividades que
foram desenvolvidas. Nessa etapa verificou-se se as
informações foram suficientes e se foram bem
compreendidas.

184
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
3.4 C ONHECIMENTO DO SISTEMA SAP
Devido ao volume de informações que permeiam uma
indústria, normalmente são adotados softwares de
controle da informação. O software utilizado foi o SAP.
No SAP foram encontradas todas as informações de
serviços de manutenção ou a maior parte delas. Para
que se pudesse ganhar fluência entre essas
informações foi preciso entender como os dados se
organizavam, como eram apontados no sistema e
quais eram suas limitações.

3.5
REVISÃO DO HISTÓRICO DE FALHAS
Essa etapa consistiu na avaliação de todo o registro
disponível sobre as falhas do equipamento ao longo
do tempo. Essa informação foi conhecida como
histórico de falhas. O histórico de falhas pode ser
conseguido por meio de um sistema de gerenciamento
de informações, utilizando os documentos que
registraram as atividades de manutenção em campo
ou por meio de entrevistas com operadores e
profissionais da manutenção. Essa última fonte é
pouco confiável devido à subjetividade da informação
e sua imprecisão, restringindo sua utilização apenas
para completar uma informação que estivesse
faltando. Após o levantamento das informações de
falha, começou-se o trabalho de relacionar todas as
informações disponíveis do equipamento, como carga
produtiva, operação, visando uma correlação com o
registro de falhas.

3.6 TRIAGEM DOS DADOS
Uma vez que as informações de falha do equipamento
foram levantadas, iniciou-se um trabalho de triagem
de dados buscando encontrar subgrupos que
formassem a base de cada análise realizada. Os
subgrupos desejados foram os de trabalho
preventivo, falhas que envolvem paradas do
equipamento, falhas cotidianas, falhas eventuais e
falhas crônicas .
O primeiro subgrupo, trabalho preventivo visou
extrair a efetividade da manutenção preventiva
realizada até o momento, correlacionando o número
de falhas de cada mês e o número de falhas
observadas no mesmo Com essa contraposição,
observaram-se os intervalos entre uma falha e uma
atividade preventiva o que possibilitou estudos de
efetividade e descarte de possíveis causas de falha.
As Falhas que envolvem paradas do equipamento
representaram aquelas falhas que promovem a perda
de produtividade direta.
As Falhas cotidianas são aquelas que não param o
equipamento, mas geram custo de manutenção e
compõem o quadro de falhas do equipamento. Esse
subgrupo permitiu estudar o ganho indireto de capital,
uma vez que a falha não gera impacto na
produtividade do equipamento. Esse custo indireto era
composto pelos custos de manutenção do
equipamento (mão-de-obra e material).
As Falhas eventuais são aquelas que acontecem de
repente e se gasta um tempo muito maior que o
normal para se reparar. Esse subgrupo permitiu
entender quais foram as limitações da equipe de
manutenção na execução do reparo e quais dessas
falhas estavam relacionadas com pequenas falhas ou
falta de uma atividade preventiva.
E por último, as Falhas Crônicas. Essas falhas são
periódicas e frequentes no equipamento. Esse
subgrupo permitiu a realização de melhorias no
equipamento e no sistema produtivo, além de servir
como indicador de melhoria para o novo plano de
manutenção que foi implementado.

185

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
3.7 APLICAÇÃO DE PARETO
O Princípio de Pareto propõe a teoria de que 80% das
falhas estão sendo geradas por 20% das causas, ou
seja, 20% das falhas estão gerando 80% das
ocorrências.
Com essa informação foram levantadas prioridades de
intervenção e pontos que o novo plano de
manutenção deveria contemplar, assim como
direcionar as melhorias a serem feitas para
proporcionar uma maximização dos resultados de
maneira mais rápida.

4 RESULTADOS E D ISCUSSÃO
4.1 TRIAGEM DOS D ADOS
O objeto de estudo desta pesquisa foi uma máquina
responsável pelo corte de chapas de aço silício,
empregadas na construção do núcleo do
transformador, que é um dos componentes
empregados na montagem de máquinas de solda.
Essa máquina foi chamada de equipamento piloto, por
ser a primeira a receber a implantação do programa
TPM nessa indústria.
O histórico das falhas do equipamento piloto é
composto por uma planilha que resume todas as
intervenções realizadas pela equipe de manutenção
desde junho de 2011 até abril de 2012. Desta forma
obtêm-se os registros de falha mais estratificados,
específicos e que dizem respeito a pequenos
conjuntos que influem em um grande equipamento. As
figuras 4, 5, 6, 7 e 8 mostram uma visão do
equipamento em questão.

Visão geral do equipamento

Figura 4: Localização esquemática dos subconjuntos do equipamento piloto.

186
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Detalhamento do equipamento:
Alimentador

Figura 5: ALI - Alimentador de fita de aço silício.

Prensa

Figura 6: PRE – Prensa de corte das laminas.

187

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Desbobinador

Figura 7: DES - Desbobinador de fita de aço silício.

Mesa de solda

Figura 8: MES – Mesa de solda das laminas.

188
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
4.2 APLICAÇÃO DO PRINCÍPIO DE PARETO ANTES
DA TPM
Ao se efetuar a segmentação dos dados, tornou-se
mais fácil realizar uma análise de falha, pois, por se
tratar de um mesmo conjunto, as falhas tendem a ser
repetidas e suas origens são as mesmas.
À primeira vista, o volume de dados reduzidos
impulsiona a realizar uma análise em todos os
subconjuntos listados. Entretanto, ao se aplicar esta
análise a uma instalação fabril inteira ou a um grupo
de empresas com dezenas de equipamentos
diversificados, o volume de informações a ser
trabalhado se torna grande, o que inviabiliza a
realização desta análise.
Segundo o teorema de Pareto não é necessário
realizar uma análise de todos os conjuntos para se
obter um resultado satisfatório. Seguindo esta teoria,
foi realizado um estudo de frequência de ocorrências
de paradas e o tempo das mesmas e organizado de
forma acumulativa, como se pode observar no Gráfico
1, Gráfico 2, Tabela 1 e Tabela 2.

Gráfico 1: Gráfico de Pareto mostrando a quantidade de paradas.

189

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Tabela 1: Priorização dos dados de paradas.

Aplicando esse teorema é possível analisar e atacar
20% das causas e obter 80% dos resultados. O
resultado da aplicação do princípio de Pareto pode ser
contemplado, como observado na Tabela 1 em:
• Corretiva Mecânica, com 40,16% de
relevância;
• Corretiva Elétrica, com 33,33% de relevância;
• Setup, com 16,87% de relevância;
• Qualidade, com 9,64% de relevância;

Gráfico 2: Gráfico de Pareto mostrando o tempo das paradas.

190
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Tabela 2: Priorização dos tempos de paradas.

4.3
ORGANOGRAMA DE IMPLANTAÇÃO DOS TRÊS
PRIMEIROS PASSOS DO PILAR DE M ANUTENÇÃO
AUTÔNOMA
O organograma da Figura 9 mostra os procedimentos
que foram realizados para a implantação do pilar de
manutenção autônoma.

Figura 9: Organograma de implantação dos três primeiros passos do pilar de manutenção autônoma

191

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Declaração da alta administração da implantação
do TPM
A alta administração, através de uma reunião anual
entre os gerentes, apresentou o programa de TPM.
Através de uma pequena palestra, demonstrando os
índices, melhorias e desenvolvimento profissional
obtidos pelas empresas que iniciaram a implantação
do programa TPM.
Após esta reunião ficou determinado que os gerentes
e lideres da empresa divulgariam o programa de TPM
a todos os funcionários. Foram apresentados o
conceito existente sobre o programa, suas metas e
objetivos.
Capacitação introdutória
Nesse treinamento inicial foram abordados todos os
temas necessários para o gerenciamento da
implantação e manutenção do programa. O
treinamento também é chamado de facilitador TPM, a
partir do qual um colaborador fica capacitado a treinar
os outros com relação ao programa.
Definição do equipamento piloto
Foi escolhido como equipamento piloto uma Prensa
de chapa de aço silício, devido sua expressiva
produção, cerca de 105t/mês o que representa
R$ 577.443,00/mês de faturamento em média, o que
justifica a escolha por se tratar de um equipamento
que proporciona um alto volume de produto e é um
gargalo na produção de núcleos de transformadores.
Conquistas e metas
O objetivo da implantação do TPM será reduzir o
máximo possível a quantidade de paradas,
aumentando assim a produtividade do equipamento.
Plano mestre
O programa TPM necessita de um plano de trabalho,
ou seja, um cronograma de implantação. Este
cronograma contém o desenvolvimento dos pilares ao
longo do tempo.
Início formal do TPM
O marco inicial do programa foi uma reunião realizada
na empresa com a participação de todos os
colaboradores, onde foram apresentados os princípios
e fundamentos do mesmo. Após essa reunião foram
realizados os primeiros procedimentos na máquina.
Estabelecimento dos pilares básicos
Nesse programa estão sendo abordados os três
primeiros passos do pilar de Manutenção Autônoma.
São observadas grandes mudanças, pois,
originalmente, os equipamentos eram sujos e, os
processos, desorganizados. Assim, qualquer ação de
melhoria é facilmente observada.
1° Passo: Limpeza e inspeção inicial
2° Passo: Eliminação das fontes de contaminação e
de locais de difícil acesso
3° Passo: Definição de padrões de atividade
1.° Passo: Limpar e inspecionar
O início das atividades de manutenção autônoma deu-
se através da parada total do equipamento. Na
parada, que durou 5 dias, onde as equipes de
produção e manutenção realizaram a limpeza inicial. A
limpeza ficou caracterizada pela desmontagem de
todas as partes móveis do equipamento para retirada
de sujeira, pó e contaminações. Durante a limpeza o
operador e seus ajudantes realizaram inspeções
mecânicas buscando e restaurando defeitos em
potencial.
Durante as inspeções houve problemas que não foram
resolvidos. Neste ponto, o operador registrou a
anomalia na ficha TPM. As fichas são de duas cores:
azul, para anomalias que o operador deve resolver, e
vermelha, para anomalias que são de
responsabilidade da manutenção. Tais fichas são
preenchidas em duas vias; uma cópia deve ficar fixada
no local onde foi identificada a falha e a outra serve
como ordem de serviço.

192
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Após o registro de todas as anomalias encontradas,
as cópias das fichas azuis e vermelhas são
registradas em uma tabela de resumo das fichas TPM.
Esse resumo é orientativo e serve como guia dos
gestores para priorizar atividades a serem executadas
na manutenção planejada.
Para que os líderes de manutenção e produção
possam monitorar a abertura e resolução das
anomalias registradas nas fichas TPM, um controle
das fichas foi elaborado. Este controle consiste em um
gráfico de acompanhamento do número de fichas
abertas e executadas. Tal informação também fica
disponível no painel TPM do equipamento.
Segundo o Coordenador de Produção da Empresa, o
controle das fichas TPM foi fundamental para o
desenvolvimento do programa. Ele observou que
nesta etapa é fundamental que todos trabalhem em
prol da restauração das condições originais do
equipamento.
Outro item desenvolvido durante o passo 1 foi o aperto
de parafusos. Durante a operação do equipamento
verificou-se que ele apresentava vibrações que, na
maioria das vezes, poderiam gradativamente ir
soltando seus parafusos. Isto poderia ocasionar falhas
e/ou acidentes graves durante a operação. Esta
atividade foi desenvolvida dividindo o equipamento em
9 partes.
Cada uma das partes teve o trabalho realizado pelos
operadores com supervisão dos técnicos de
manutenção.
Como última atividade desenvolvida, a equipe iniciou
os trabalhos de 5S. Para realizar este trabalho a
equipe dividiu o local de trabalho em setores. O
objetivo desta divisão em setores, segundo o
operador, é de otimizar a implantação dos 5S. Ele
relata que em tentativas anteriores de implantar o 5S
em toda a área, resultou em trabalho desordenado,
concluindo-se que as atividades não passaram de
limpeza e organização.
A equipe desenvolveu inicialmente as atividades de
5S no painel de ferramentas. Atualmente a equipe
piloto já desenvolveu mais de 24 atividades distintas
de 5S.
2.° passo: Eliminação das fontes de contaminação
e de locais de difícil acesso.
O passo 2 da manutenção autônoma inicia com um
desafio à equipe piloto. O coordenador de produção
ressalta que este equipamento possui muitos
problemas de vazamentos devido ao longo período de
tempo em que as manutenções não foram realizadas
de forma adequada.
Como atividade inicial, a equipe piloto realizou uma
parada de 2 dias de trabalho para levantamento das
áreas de vazamento e áreas de difícil acesso. Quanto
aos vazamentos, a equipe iniciou uma verificação de
todo o equipamento, eliminando os vazamentos
possíveis e registrando nas fichas TPM os
vazamentos de difícil solução. Essas atividades
tiveram a supervisão de mecânicos.
Para facilitar a visualização dos locais em que os
vazamentos persistiram, a equipe desenvolveu um
desenho do equipamento indicando as áreas de
vazamentos.
Com relação às áreas de difícil acesso, a equipe
buscou identificar áreas onde é difícil limpar, lubrificar
e inspecionar. Estas áreas devem ser eliminadas,
segundo o operador, para facilitar as atividades diárias
de manutenção autônoma. Inicialmente a equipe
detectou 23 áreas de difícil acesso, sendo: (i) 7 áreas
de inspeção; (ii) 7 áreas de lubrificação; e (iii) 9 áreas
de limpeza.

3.° Passo: Definição de padrões de atividade.
No terceiro passo, o trabalho em conjunto entre a
produção e a manutenção desenvolveu os padrões de
limpeza, lubrificação e inspeção. Estes padrões
possuem a meta de oferecer ao equipamento as
condições básicas para prevenir a deterioração,

193

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
estando também disponíveis no painel TPM. Os
mesmos são revisados a cada ano com o objetivo de
reavaliar se estão desempenhando o papel para o
qual foram criados.
Os padrões trazem a imagem ou foto do local onde
serão realizadas as inspeções, lubrificação e limpeza.
Trata-se de um controle visual utilizado pelo programa
que tem o objetivo de facilitar a localização do local
onde será executada a manutenção autônoma. Além
das imagens, os padrões indicam o método de
execução, o tempo e o responsável pela realização
das atividades.

4.4
PRINCIPAIS RESULTADOS
Os resultados de implantação do TPM na empresa
são detalhados através de resultados objetivos e
subjetivos. Entretanto, devido ao programa estar em
sua fase inicial de implantação, os resultados serão
relativos apenas à equipe piloto. Também é
necessário relatar que mesmo a equipe piloto
encontra-se em fase de implantação.

4.4.1 RESULTADOS SUBJETIVOS
Os resultados subjetivos são aqueles não
mensuráveis quantitativamente. A Tabela 6 apresenta
os resultados subjetivos obtidos pela equipe piloto.
Estes resultados foram coletados e tabulados através
de pesquisa interna. Pode-se observar que as
atividades de manutenção autônoma estão sendo
realizadas no equipamento. Através de treinamento, a
equipe piloto ficou capacitada a realizar pequenos
reparos. Atividades de operação e manutenção são
realizadas de forma sistemática pelos operadores,
diminuindo a probabilidade de erros na execução. Os
operadores iniciaram um trabalho de desenvolvimento
no qual pode-se observar maior compromisso com as
condições básicas dos equipamentos.

Tabela 6: Resultados subjetivos obtidos com o equipamento piloto.
Melhoria Início 2011 2012
Atividade de manutenção autônoma Não Sim Sim
Conquista da auto-gestão plena Não Não Não
Satisfação dos funcionários Não Sim Sim
Satisfação dos clientes visitantes do equipamento piloto Não Não Sim
Autoconfiança na obtenção de Zero perdas mediante ao “posso fazê-lo” Não Não Sim
Organização do local de trabalho Não Sim Sim
Melhoria da relação entre operadores e técnicos de manutenção Não Não Não

As atividades de manutenção autônoma
proporcionaram uma melhoria no local de trabalho.
Pode-se observar melhor organização e limpeza do
equipamento. Os operadores passaram a ter maior
reconhecimento por suas atividades desenvolvidas.
As atividades de melhoria individual proporcionaram a
autoconfiança nos operadores em desenvolver
atividades para a obtenção de Zero-Perdas.
Sistematicamente, as perdas do equipamento são
eliminadas, seja somente pelas atividades de melhoria
individual ou em conjunto com o 5S.
A manutenção autônoma melhorou a satisfação dos
funcionários, pois a divisão das atividades definiu,
claramente, as responsabilidades da operação e da

194
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
manutenção do equipamento. Os operadores e
técnicos de manutenção trabalham em conjunto,
dividindo atividades e metas. Entretanto, ainda não se
pode observar uma melhoria na relação entre os
mesmos.
O programa TPM proporciona aos técnicos da
manutenção e aos operadores uma forma sistemática
de desenvolver suas atividades. Atualmente, os dois
setores possuem metas em conjunto, fazendo com
que trabalhem em grupo. Outra ferramenta disponível
aos envolvidos com o programa é a possibilidade de
demonstrar as melhorias através do painel TPM. Este
painel representa de forma concisa as atividades
executadas, bem como os ganhos obtidos com os
trabalhos desde o início da implantação.
4.4.2 RESULTADOS OBJETIVOS APÓS A
IMPLANTAÇÃO DO PROGRAMA TPM
Os resultados objetivos são de natureza quantitativa,
sendo divididos em frequência de ocorrências de
paradas e o tempo das mesmas e organizados de
forma acumulativa, como se pode observar no Gráfico
3, Gráfico 4, Tabela 7 e Tabela 8. Segundo o
coordenador de produção, a equipe piloto conquistou
bons resultados, reduzindo consideravelmente as
paradas após a implantação do programa. Ele ressalta
que a determinação e trabalho do grupo viabilizaram a
obtenção dos resultados.

Gráfico 3: Gráfico de Pareto mostrando a quantidade de paradas.

195

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Tabela 7: Priorização da quantidade de paradas.

Gráfico 4: Gráfico de Pareto mostrando os tempos de paradas.

Tabela 8: Priorização dos tempos de paradas.

196
e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
Os bons resultados obtidos na produtividade líquida e
na eficiência global de produção tiveram relação direta
com a implantação do programa TPM.
O TPM foi responsável pela diminuição das queixas e
reclamações dos clientes. Padrões de qualidade foram
implantados e seguidos pelas equipes de trabalho. Os
operadores se conscientizaram que a produtividade
somente seria alcançada se os produtos possuíssem
qualidade.
A melhoria de índices de número de acidentes, clima
organizacional e sugestões é um indicativo direto de
que os funcionários estão mais comprometidos e
satisfeitos com o trabalho. O programa TPM
proporcionou aos funcionários expressarem suas
opiniões sobre melhorias do local de trabalho e do
equipamento. Ações de eliminação de situações de
risco de acidentes no equipamento foram
desenvolvidas e um melhor reconhecimento do
operador como técnico do equipamento foi observado.

5
C ONCLUSÃO
O estudo de caso na empresa analisada mostrou a
efetividade do programa TPM para atingir os objetivos
propostos. O programa demonstrou que através da
organização dos processos, elevação do nível de
habilidades dos operadores e organização da
manutenção do equipamento piloto, pode-se
conquistar bons resultados no quesito produtividade
do equipamento.
O sucesso na implantação de um programa que
necessite da formação de grupos de trabalho, como a
sistemática proposta para o TPM, depende do
envolvimento da alta gerência. Técnicas para solução
de problemas foram aplicadas para a obtenção de
sucesso na implantação de uma sistemática do
programa TPM.
Através da utilização dos três principais pilares:
manutenção autônoma, melhorias individuais e
manutenção planejada, descritos no estudo de caso,
foi possível comprovar o quanto ações simples,
porém, sincronizadas, podem contribuir para a
redução de perdas dentro da linha de produção.
Também se observou a possibilidade da realização de
desdobramentos do presente trabalho em trabalhos
futuros.

__________________________________________________________________________
REFERÊNCIAS
BANKER, Shailen. The Performance Advantage -
Revitalizing the Workplace . ago/95. Disponível em
<http://www.eps.ufsc.br/disserta98/jerzy/biblio.htm l>
Acesso em: 10 out. 2011.

CAPALDO, D.; GUERRERO, V. e ROZENFELD, H.
1999. FMEA (Failure Model and Effect
Analysis) .Disponível em
<
http://www.numa.org.br/conhecimentos/conheciment
os_port/pag_conhec/FMEAv2.html > Acesso em: 10
out. 2011.

GIL, Antonio Carlos. Como Elaborar Projetos de
Pesquisa. São Paulo: Atlas, 2010. p.184.

JIPM. História do TPM e JIPM . Disponível em
http://www.jipm.or.jp. Acesso em:10 out. 2011.

NAKAJIMA, Seiichi. Introdução ao TPM - Total
Productive Maintenance . São Paulo: IMC Internacional
Sistemas Educativos Ltda., 1989.Disponível em
<http://www.eps.ufsc.br/disserta98/jerzy/biblio.html>.
Acesso em 10 out. 2011.

PINTO, Alan Kardec e XAVIER, Júlio Nascif.
Manutenção: função estratégica . Rio de Janeiro:
Qualitymark. Ed. 2007.

TAHASHI, Yoshikazu; OSADA, Takashi. TPM/MPT:
Manutenção Produtiva Total . São Paulo: Instituto
IMAM, 1993.

197

e-xacta , Belo Horizonte, v. 5, n. 1, p. 175-197. (2012). Editora UniBH.
Disponível em: www.unibh.br/revistas/exacta/
TAVARES, Lourival. Administração Moderna da
Manutenção . Rio de Janeiro: Novo Pólo Publicações,
1999.

VIANA, Herbert Ricardo Garcia. PCM, Planejamento e
controle da manutenção. Rio de Janeiro: Qualitymark.
Ed. 2002.

WYREBSKI, Jerzy. Manutenção produtiva total - um
modelo adaptado. 1997. Dissertação (M.sc) - UFSC,
Florianópolis, 1997. Disponível em
http://www.eps.ufsc.br/disserta98/jerzy/. Acesso em:
10 out. 2011.

## Aplicação para a Smart Control Brasil

Este material deve apoiar respostas técnicas da LÍVIA sobre manutenção, automação, confiabilidade, diagnóstico, TPM, FMEA, falhas ou engenharia, conectando conceitos à aplicação prática da Smart Control Brasil.

A LÍVIA não deve usar este material para prometer preço, prazo, estoque, garantia ou resultado comercial.
