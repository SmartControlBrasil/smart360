# AVALIA¸C˜ AO DA CONFIABILIDADE EM SISTEMAS DE DISTRIBUI¸C˜ AO CONSIDERANDO FALHAS DE GERA¸C˜ AO E TRANSMISS˜ AO

> Fonte original: raw_academico/Manutenção Produtiva Total/Confiabilidade de Sistemas Industriais/AVALIA¸C˜ AO DA CONFIABILIDADE EM SISTEMAS DE DISTRIBUI¸C˜ AO CONSIDERANDO FALHAS DE GERA¸C˜ AO E TRANSMISS˜ AO.pdf  
> Categoria: manutencao  
> Material convertido para apoio técnico da LÍVIA Assistant.

## Conteúdo extraído

AVA L I A ¸C˜AO DA CONFIABILIDADE EM SISTEMAS DE DISTRIBUI ¸ C˜AO
CONSIDERANDO FALHAS DE GERA¸C˜AO E TRANSMISS ˜AO
A.M. Cassula ∗
romeu@eletro.ufrgs.br
A.M. Leite da Silva ∗
teel@ece.ucsb.edu
L.A.F. Manso †
edson@lcmi.ufsc.br
R. Billinton ‡
edson@lcmi.ufsc.br
∗Grupo de Engenharia de Sistemas - GESis, Universidade Federal de Itajub´a - UNIFEI, MG, Brasil
†Departamento de Eletricidade - DEPEL, Universidade Federal de S˜ao Jo˜a od e lR e i-F U N R E I ,M G ,B r a s i l
‡Power System Research Group - University of Saskatchewan - Saskatoon, Canada
ABSTRACT
This paper presents a new methodology to evaluate the
reliability of distribution systems considering the impact
of failures from the generation and transmission (G&T)
systems. Therefore, an integrated adequacy evaluation,
including generation, transmission and distribution, is
performed in order to provide a more detailed infor-
mation about interruptions experienced by consumers.
The G&T systems are represented by a ﬁctitious equiv-
alent network, whose parameters are obtained by Monte
Carlo non-sequential simulation. The equivalent G&T
network is then connected with the distribution network
and analyzed by the minimal cut-set theory. Traditional
distribution indices (e.g. SAIFI, SAIDI, etc.) as well as
the LOLC - Loss of Load Cost - indices are disaggregated
to measure the contribution of G&T and distribution
systems on the overall system indices. The proposed
method is applied to the IEEE-RTS, which represents
the G&T system, connected with the RBTS, which rep-
resents the distribution system. The results and their
potential applications to the new power system compet-
itive environment are discussed.
Artigo submetido em 13/12/2000
1a. Revis˜ao em 19/6/2002; 2a. Revis˜ ao 11/10/2002
Aceito sob recomenda¸c˜ao do Ed. Assoc. Prof. Jos´ e L. R. Pereira
KEYWORDS: Distribution reliability, reliability worth,
generation transmission and distribution reliability, hi-
erarchical level 3.
RESUMO
Este artigo apresenta uma nova metodologia para a an´a-
lise da conﬁabilidade de sistemas de distribui¸c˜ao, onde
se considera os impactos das falhas provenientes dos sis-
temas de gera¸c˜ao e transmiss˜ao. Portanto, ´e viabilizada
uma avalia¸c˜ao integrada, incluindo gera¸c˜ao, transmiss˜ao
(G&T) e distribui-¸c˜ao, de modo a produzir uma infor-
ma¸c˜ao mais detalhada sobre a causa das interrup¸c˜oes
experimentadas pelos consumidores. O sistema G&T ´e
representado por uma rede equivalente ﬁct´ıcia, cujos pa-
rˆametros s˜ao obtidos atrav´es de simula¸c˜ao Monte Carlo
n˜ao-seq¨uencial. Esta rede equivalente G&T ´eco n e ct a d a
ao sistema de distribui¸c˜ao, que ´ee n t ˜ao analisado utili-
zando a teoria dos conjuntos m´ınimos de corte.´Indices
de distribui¸c˜ao tradicionais (e.g. FEC, DEC, etc.) bem
como a LOLC (Loss of Load Cost - Custo Esperado
da Perda de Carga), s˜ao desagregados com o intuito de
quantiﬁcar a contribui¸c˜ao dos sistemas G&T e distribui-
¸c˜ao em rela¸c˜ao ao sistema total. O m´etodo proposto ´e
t e s t a d oe mu ms i s t e m aco n s t i t u ´ıdo pelo sistema de ge-
ra¸c˜ao e transmiss˜ao IEEE-RTS, conectado ao sistema
de distribui¸c˜ao IEEE-RBTS. Os resultados e suas po-
262 Revista Controle & Automa¸ c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003

tenciais aplica¸c˜oes para o novo cen´ario competitivo dos
sistemas el´etricos s˜ao discutidos.
P ALA VRAS-CHA VE: Conﬁabilidade em sistemas de dis-
tribui¸c˜ao, valor da conﬁabilidade, conﬁabilidade na ge-
ra¸c˜ao transmiss˜ao e distribui¸c˜ao, n´ıvel hier´arquico 3.
1 INTRODU ¸ C˜AO
Os sistemas de distribui¸c˜ao (Billinton e Allan, 1994; Bil-
linton, 1988; Allan e da Silva, 1995; Billinton e Satish,
1996; Chowdhury e Koval, 1998; Allanet alii, 1991; Bil-
linton e Jonnavithula, 1996) sempre receberam pouca
aten¸c˜ao em rela¸c˜ao `as t´ecnicas de avalia¸c˜ao de conﬁ-
abilidade quando comparados aos sistemas de gera¸c˜ao
e transmiss˜ao (Leite da Silvaet alii, 1991; Melo et alii,
1993; Goel e Billinton, 1993; Wenyuan e Billinton, 1993;
Mello et alii, 1994; Mello et alii, 1997; Leite da Silvaet
alii, 2000; Manso et alii , 1999). Dois argumentos tˆem
sido utilizados: sistemas G&T necessitam de gastos vul-
tuosos e podem causar conseq¨uˆencias catastr´oﬁcas tanto
para a sociedade quanto para seu pr´oprio ambiente.
An´alises estat´ısticas realizadas pelas concession´arias de
energia sobre falhas nos consumidores, demonstram que
os sistemas de distribui¸c˜ao s˜ao respons´aveis pela maior
parte das contribui¸c˜oes individuais que acarretam in-
disponibilidade de fornecimento para os consumidores
(Billinton e Allan, 1994). Al´em disso, embora um de-
terminado refor¸co ou um novo esquema de prote¸c˜ao em
sistemas de distribui¸c˜ao tenha um custo relativamente
barato, coletivamente os investimentos podem atingir
n´ıveis signiﬁcativos.
Nos ´ultimos anos, os sistemas de distribui¸c˜ao tˆem re-
cebido uma aten¸c˜ao especial, principalmente devido ao
processo de restrutura¸c˜ao e privatiza¸c˜ao do setor el´e-
trico. Neste novo cen´ario, as companhias de distribui-
¸c˜ao ser˜ao respons´aveis pela venda de todo tipo de servi¸co
associado com os sistemas de distribui¸c˜ao e, portanto,
estar˜ao em busca por maior eﬁciˆencia, no sentido de
maximizar seus lucros, mantendo a qualidade de servi¸co
em conformidade com as normas impostas pelas agˆen-
cias reguladoras. Com isso, o valor da conﬁabilidade
dever´a ser corretamente avaliado e inserido nas tarifas
para poss´ıveis indeniza¸c˜oes aos consumidores, no caso
de haver interrup¸c˜oes.
A avalia¸c˜ao integrada da conﬁabilidade de um sistema
el´etrico de potˆencia incluindo gera¸c˜ao, transmiss˜ao e dis-
tribui¸c˜ao (conhecido como N´ıvel Hier´arquico 3, ou sim-
plesmente NH3) ´e uma importante meta para o plane-
jamento e opera¸c˜ao de sistemas de potˆencia (Leite da
Silva et alii , 1991; Melo et alii , 1993). Os n´ıveis hie-
r´arquicos usuais (Billinton e Allan, 1988) est˜ao repre-
Nível Hierárquico 0
NH0
Nível Hierárquico 1
NH1
Nível Hierárquico 2
NH2
Nível Hierárquico 3
NH3
Transmissão
Geração
Sistema
Energético
Distribuição

Figura 1: N´ıveis Hier´arquicos de um Sistema de Potˆen-
cia
sentados na Figura 1. Entretanto, devido `ad i m e n s ˜ao
do problema, estudos de conﬁabilidade em sistemas de
distribui¸c˜ao tˆem sido realizados considerando o sistema
G&T representado por pontos de fornecimento com ca-
pacidade ilimitada e 100% conﬁ´aveis.
Neste trabalho, uma nova metodologia ´ep r o p o s t ap a r a
avaliar o impacto das falhas do NH2 nos sistemas de
distribui¸c˜ao. Isto ser´a obtido por uma simula¸c˜ao Monte
Carlo n˜ao-seq¨uencial e pode envolver diferentes barras
do NH2. Em fun¸c˜ao da pol´ıtica de corte de carga no
n´ıvel de distribui¸c˜ao, uma rede ﬁct´ıcia ´eco n s t r u ´ıda de
modo que a disposi¸c˜ao dos componentes simulem as in-
terrup¸c˜oes oriundas do NH2. Este procedimento genera-
liza os conceitos propostos em (Billinton e Satish, 1996).
O sistema de distribui¸c˜ao juntamente a rede ﬁct´ıcia s˜ao
analisados utilizando os conceitos de minimal cut-set
(Billinton e Allan, 1992). Al´em dos ´ındices usuais de
conﬁabilidade para o sistema e pontos de carga, outro
´ındice, denominado LOLC -Loss of Load Cost (Allan e
da Silva, 1995; Chowdhury e Koval, 1998; Goel e Billin-
ton, 1993; Wenyuan e Billinton, 1993; Melloet alii, 1994;
Mello et alii, 1997; Leite da Silva et alii, 2000; Manso
et alii , 1999; Billinton e Allan, 1988), ser´a avaliado e
desagregado considerando os n´ıveis hier´arquicos. Por-
tanto, a metodologia proposta deﬁne, do ponto de vista
econˆomico, as responsabilidades sobre poss´ıveis preju´ı-
zos causados devido `as interrup¸c˜oes.
Revista Controle & Automa¸c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003 263

2 CONFIABILIDADE DE SISTEMAS DE
DISTRIBUI ¸C˜AO
Um sistema de distribui¸c˜ao pode ser representado por
uma rede cujos componentes podem estar conectados
em s´erie, em paralelo, ou ainda por uma combina¸c˜ao
qualquer dos componentes. Existem v´arios m´etodos dis-
pon´ıveis para a solu¸c˜ao e avalia¸c˜ao destas redes (Billin-
ton e Allan, 1992). Por´em, quando se est´a analisando
continuidade de fornecimento, o m´etodo dos conjuntos
m´ınimos de corte´e o que melhor se aplica, pois indica di-
retamente as falhas predominantes e, portanto, reﬂete o
comportamento distinto dos modos de falha do sistema.
2.1 T´ ecnicas de Avalia¸c˜ao
O processo de Markov e a abordagem de freq¨uˆencia e
dura¸c˜ao formam um excelente m´etodo de modelagem
ea n ´alise para aplica¸c˜oes da conﬁabilidade (Billinton e
Allan, 1992). Para sistemas maiores e mais complexos,
como redes de distribui¸c˜ao, foram desenvolvidas apro-
xima¸c˜oes baseadas nas equa¸c˜oes que derivam deste m´e-
todo. Estas equa¸c˜oes podem ser empregadas conjunta-
mente com a teoria dos conjuntos m´ınimos de corte, pois
fornecem resultados precisos com uma maior rapidez,
para a maioria dos sistemas de distribui¸c˜ao que se en-
contram na pr´atica. Neste caso, a rede de conﬁabilidade
consiste em um n´umero de minimal cut-sets conectados
em s´erie e cada cut-set ´eco n s t i t u ´ıdo por componentes
conectados em paralelo, como mostra a Figura 2. Para o
c´alculo, inicialmente utilizam-se as equa¸c˜oes do sistema
paralelo para cada cut-set,e n t ˜ao combinam-se estes ´ın-
dices atrav´es das equa¸c˜oes do sistema s´erie, para enﬁm
determinar os ´ındices equivalentes.

Figura 2: Rede Equivalente de Conﬁabilidade
2.2 ´Indices de Desempenho
Para as companhias de eletricidade ´e essencial dividir o
sistema de distribui¸c˜ao em n´ıveis de conﬁabilidade, e de-
ﬁnir ´ındices para atender sua fun¸c˜ao b´asica de fornecer
energia conﬁ´avel ao menor custo, para todos os setores
da sociedade. Este procedi-mento´e conhecido como ava-
lia¸c˜ao do desempenho passado, ou hist´orico, da conﬁabi-
lidade, o qual ´e utilizado pela maioria das empresas. A
an´alise de desempenho futuro, ou a avalia¸c˜ao preventiva
da conﬁabilidade, ´e uma outra ﬁlosoﬁa que possibi-lita
determinar refor¸cos os necess´arios ao sistema e compa-
rar alternativas de expans˜ao. Contudo, para quantiﬁcar
o desempe-nho passado ou futuro do fornecimento de
energia nos pontos de carga dos consumidores e para o
sistema total, os´ındices a seguir s˜ao os mais empregados
(Billinton e Allan, 1994):
´Indices para Pontos de Carga:
FIC Freq ¨uˆencia de Interrup¸ c˜ao
Indivi-dual por Unidade
Consumidora
[falhas/ano]
DIC Dura¸ c˜ao de Interrup¸c˜ao Indi-
vidual por Unidade Consumi-
dora
[horas/ano]
rD u r a ¸ c˜ao da Falha [horas]
EENS Energia Esperada N˜ ao Su-
prida
[kWh/ano]
´Indices de Sistema:
FEC Freq ¨uˆencia Equivalente de Interrup¸ c˜ao
por Unidade Consumidora
[Interrup¸c˜oes/consumidor ano]
DEC Dura¸ c˜ao Equivalente de Interrup¸c˜ao por
Unidade Consumidora
[horas/consumidor ano]
No N´ıvel Hier´arquico 2, o emprego da avalia¸c˜ao preven-
tiva ´e bastante difundida para planejar a conﬁabilidade
do sistema. Entretanto, no NH3 esta t´ecnica n˜ao ´et ˜ao
popular quanto ao desempenho passado da conﬁabili-
dade. Com a abertura da competitividade no setor, est´a
aumentando o interesse por metodologias de otimiza¸c˜ao
econˆomica de planejamento e expans˜ao na distribui¸c˜ao.
Em um futuro pr´oximo, ser´a necess´ario que todas com-
panhias de distribui¸c˜ao identiﬁquem quais os pontos no
sistema que devem receber a prioridade nos investimen-
tos. Portanto, o desempenho futuro ser´au m ai n f o r m a -
¸c˜ao valiosa no processo de tomada de decis˜oes para sis-
temas de distribui¸c˜ao.
A conﬁabilidade de qualquer servi¸coe l ´etrico, incluindo
a atividade de distribui¸c˜ao, deve ser baseada no balan¸co
dos custos para a concession´aria e o valor dos benef´ı-
cios oferecidos aos consumidores. Um valor de referˆen-
cia da conﬁabilidade para ser utilizado no planejamento
(Chowdhury e Koval, 1998; Burns e Gross, 1990) deve
considerar uma solu¸c˜ao de m´ınimo custo, onde o custo
total inclui custos de investimento, custos operacionais e
custos de interrup¸c˜ao. Portanto a LOLC, que representa
o custo de interrup¸c˜ao, se tornar´a o mais importante´ın-
dice que representa a conﬁabilidade no planejamento de
264 Revista Controle & Automa¸ c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003

sistemas el´etricos.
Uma compara¸c˜ao de m´etodos alternativos para a avali-
a¸c˜ao do ´ındice LOLC em sistemas de gera¸c˜ao e trans-
miss˜ao est´a descrito em (Billinton e Allan, 1988). Este
´ındice depende basicamente dos custos unit´arios (UC -
Unit Interruption Cost) de interrup¸c˜ao de cada classe
de consumidores, usualmente fornecido em US$/kWh.
Tais custos s˜ao obtidos atrav´es de estudos econˆomicos
espec´ıﬁcos (levantados junto aos consumidores). Estes
estudos apresentam diferentes fatores que inﬂuenciam
na forma¸c˜ao dos UCs, sendo a dura¸c˜ao da interrup¸c˜ao
considerado o fator mais importante (EPRI, 1989). Por-
tanto, o n´ıvel de exatid˜ao estabelecido para determinar
a dura¸c˜ao da interrup¸c˜ao interfere diretamente na qua-
lidade da estimativa do ´ındice LOLC.
3 IMPACTOS DAS FALHAS DE G&T NO
SISTEMA DE DISTRIBUI ¸C˜AO
Existem v´arios benef´ıcios associados com uma avalia¸c˜ao
completa da conﬁabilidade. Os´ındices globais fornecem
uma estimativa da conﬁabilidade at´eon ´ıvel dos consu-
midores, e podem ser usados para estimar a contribui-
¸c˜ao que cada zona funcional exerce em um determinado
ponto de carga e, portanto, otimizar a aloca¸c˜ao de re-
cursos (Billinton e Jonnavithula, 1996).
Oc´alculo dos ´ındices globais pode ser dividido em trˆes
etapas principais. Primeiramente, ´e usado um algoritmo
capaz de avaliar o sistema G&T, com o intuito de ge-
rar um n´umero suﬁciente de amostras que produzem
interrup¸c˜oes na barra (ou barras) de alta tens˜ao do sis-
tema de distribui¸c˜ao. Neste trabalho, a avalia¸c˜ao do
NH2 foi realizada por uma simula¸c˜ao Monte Carlo n˜ao-
seq¨uencial. Na segunda etapa, ser˜ao extra´ıdos parˆame-
tros do processo de simula¸c˜ao anterior para auxiliar na
constru¸c˜ao de uma rede equivalente, que tamb´em de-
pende da pol´ıtica de corte de carga utilizada no sistema
de distribui¸c˜ao. Uma vez deﬁnida a rede G&Tﬁct ´ıcia,
esta ser´aco n e ct a d a`a rede de distribui¸c˜ao, constituindo
assim a terceira e ´ultima etapa da an´alise NH3.
3.1 Parˆ ametros que Caracterizam as Falhas
de G&T
Para se deﬁnir, do ponto de vista da conﬁabilidade,
um componente ﬁct´ıcio que perten¸ca a rede equivalente
G&T, ´e necess´ario apenas conhecer sua taxa de falha
(λ) e sua indisponibilidade (U). Uma metodologia para
determinar tais componentes ﬁct´ıcios ser´ad e s cr i t aas e -
guir, considerando um sistema de distribui¸c˜ao com N
alimentadores (ramais).
Durante a convergˆencia da simula¸c˜ao Monte Carlo, uma
s´erie de eventos que representam os estados de falha
associados com a barra da alta tens˜ao conectada `ar e d e
de distribui¸c˜ao s˜ao armazenados. Cada estado de falha
´e caracterizado pelos seguintes parˆametros: freq¨uˆencia
incremental (finc) e quantidade de carga a ser cortada
devido a falhas no G&T (CCGT). Os cortes de carga s˜ao
agrupados em intervalos de potˆencias que correspondem
ao total de cargas conectadas aos ramais, como ilustra
aT a b e l a1 .
Nesta Tabela, NI ´eoN ´u m e r od oI n t e r v a l oePR1, PR2,
PR3 ... PRk ... PRN s˜ao as potˆencias totais referentes
aos ramais 1, 2, 3 ... k ... N.O n ´umero de intervalos
´et a m b ´em o n´umero de ramais conectados na barra de
alta tens˜ao. Este procedimento pode ser facilmente es-
tendido para sistemas de distribui¸c˜ao que possuem mais
de uma barra como entrada.
A probabilidade ou indisponibilidade (U)eaf r e q¨uˆencia
associada a cada intervalo de potˆencia (que corresponde
ao corte de carga ou evento de falha), podem ser obtidas
pelas Eqs. (1), abaixo. Observa-se que a freq¨uˆencia de
falha ´e aproximadamente a pseudo taxa de falha associ-
ada com os componentes ﬁct´ıcios. Portanto, os compo-
nentes G&T ﬁct´ıcios s˜ao totalmente caracterizados por
λ e U.
U
k = Pk = Nk
NT ; λk ∼= fk =
Nk∑
j=1
fincj
NT ; rk = Uk
λk
(1)
onde,
Pk = Probabilidade do intervalo de potˆencia k.
Uk = Indisponibilidade do intervalo de potˆencia k.
Nk =N ´umero total de estados (de falha)pertencentes
ao intervalo de potˆencia k.
NT =N ´umero total de simula¸c˜oes realizadas.
λk = Taxa de falha do intervalo de potˆencia k.
fk =F r e q¨uˆencia de ocorrˆencia do intervalo de potˆencia
k.
rk =D u r a ¸c˜ao m´edia das falhas relativas ao intervalo de
potˆencia k.
Nk∑
j=1
fincj = Somat´orio da freq¨uˆencia incremental dos es-
tados j pertencentes ao intervalo de potˆencia k.
Normalmente, o parˆametro U ´e fornecido em [ho-
ras/ano], i.e.:
Uk = Pk ×8760 [horas/ano] (2)
Revista Controle & Automa¸c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003 265

Tabela 1: Intervalo de Potˆencia dos Componentes G&T
Ramal
NI
Intervalo de Potˆencia
R1
PR1
1
0 <C C GT ≤ PR1
R2
PR2
2
PR1<C C GT ≤ PR1+PR2
...
...
...
...
Rk
PRk
k
PR1+PR2+... +P(Rk−1)<C C GT ≤ PR1+PR2+... +PRk
...
...
...
...
RN
PRN
N
PR1+PR2+...+P(RN −1)<C C GT ≤ PR1+PR2+...+PRN
3.2 Representa¸ c˜ao das Pol ´ıticas de Corte
de Carga
Cada concession´aria emprega uma pol´ıtica de corte de
carga para seus sistemas de potˆencia. A pol´ıtica ado-
tada obedece a crit´erios que procuram reduzir os efeitos
provocados por falhas no sistema e minimizar os cus-
tos de interrup¸c˜ao de energia. As pol´ıticas de corte de
carga podem ser representadas ou modeladas atrav´es da
disposi¸c˜ao dos componentes G&T ﬁct´ıcios dentro do sis-
tema de distribui¸c˜ao. Para melhor ilustrar, considera-se
um sistema de distribui¸c˜ao com 4 ramais: R1, R2, R3 e
R4. A potˆencia de cada ramal e a pol´ıtica de corte de
carga adotada est˜ao expressas na Tabela 2.
Tabela 2: Pol´ıtica de Corte de Carga
Potˆencia do
Intervalo de
Desconecta o
Ramal [MW]
Potˆencia
Ramal
R1
20
0 <C C GT ≤ 20
R1
R2
15
20 <C C GT ≤ 35
R1+R2
R3
40
35 <C C GT ≤ 75
R1+R2+R3
R4
25
75 <C C GT ≤ 100
R1+R2+R3+R4
Ap o l ´ıtica de corte de carga adotada na Tab. 2, pode ser
representada conectando os componentes G&T ﬁct´ıcios,
conforme a rede equivalente demonstrada na Figura 3.
Neste exemplo, o Ramal 1 ser´a desconectado se o corte
de carga, devido a G&T, estiver entre 0 e 20 MW. Po-
r´em, se a quantidade de carga a ser cortada estiver en-
tre 20 e 35 MW, ambos os ramais R1 e R2 dever˜ao ser
desconectados, e assim por diante. Observe que os pa-
rˆametros λ e U relativos a estes componentes ﬁct´ıcios j´a
foram obtidos nas considera¸c˜oes anteriores.
4A V A L I A ¸C˜AO INTEGRADA DA CONFI-
ABILIDADE
4.1 Sistema B´ asico de Teste
O sistema analisado ´e composto pelo sistema de dis-
tribui¸c˜ao RBTS-Barra2 (Allan et alii, 1991), conectado
`a Barra 6 do RTS (Task Force of the Application of

R1 R2 R4 R3
CGT1
CGT2
CGT4
CGT3
Componente que representa falha no sistema G&T
{ } Indica a carga a ser cortada
{R1}
{R1+R2}
{R1+R2+R3}
{R1+R2+R3+R4}
20 MW 15 MW 40 MW 25 MW
Figura 3: Rede que Representa a Pol´ıtica de C.C. da
Tabela 2
Probability Methods Subcommittee, 1979). Linhas de
transmiss˜ao a´erea foram utilizadas ao inv´es de cabos. A
Barra 2 do RBTS foi aqui renomeada para Barra 25. A
carga m´e d i aed ep i cod e s t ab a r r as ˜ao respectivamente,
12,29 MW e 20 MW. Entretanto, existe a necessidade
de adequar o n´ıvel de tens˜ao, o que ´ef e i t oa t r a v ´es da
inclus˜ao de um transformador de 138/11 kV. A reatˆan-
cia deste transformador ´e igual a 0,12585 pu (50% maior
que os do RTS). A sua taxa de falha foi adotada como
sendo igual a 0,02 [falhas/ano] e seu tempo m´edio de
reparo (MTTR, Mean Time to Repair ou ”r”) de 768
horas. A carga m´edia da Barra 6 ´e igual a 71,8 MW e a
carga de pico de 116,8 MW.
P a r aoc´alculo do ´ındice LOLC, tanto por barra quanto
p a r aos i s t e m a ,´e necess´ario possuir os custos unit´ario de
interrup¸c˜ao. Neste trabalho, foram utilizados os dados
da Ontario Hydro para os setores industrial, comercial
e residencial (Mello et alii , 1994; Mello et alii , 1997;
Leite da Silvaet alii, 2000; Mansoet alii, 1999). Para o
sistema de distribui¸c˜ao RBTS-Barra2, os tipos de con-
266 Revista Controle & Automa¸ c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003

Sistema G&T
IEEE -RTS
Sistema de Distribuição
IEEE-RBTS Barra 2
~
~
~
~ ~
~
~ ~ ~
~
21
3
4
5
7
8
9
11 12
13
14
15
16
17
18
19
20
22
23
21
24
Tie 1Tie 2
SC
10 6
230 kV
138 kV

Figura 4: Sistema El´etrico de Potˆencia Total - NH3
sumidores small user e government/institutions foram
interpretados como industrial e comercial.
Ap o l ´ı t i cad eco r t ed eca r g ap a r aaB a r r a6d os i s t e m a
G&T considera que a prioridade de corte ser´as o b r eo
sistema de distribui¸c˜ao da Barra 25. Para o sistema
de distribui¸c˜ao, primeiramente a an´alise ser´ae f e t u a d a
considerando a pol´ıtica de corte de carga apresentada na
Tabela 2 e mostrada na Figura 3. Por´em, a potˆencia dos
ramais s˜ao aquelas apresentadas para o sistema IEEE-

Figura 5: Sistema El´etrico de Potˆencia Equivalente
RBTS-Barra2 e descritas em (Allan et alii , 1991). O
sistema de potˆencia completo e a rede equivalente para
a avalia¸c˜ao NH3 est˜ao representadas nas Figuras 4 e 5.
4.2 An´ alise NH3 para Carga Pico
Esta an´alise considera apenas a situa¸c˜ao de Carga Pico.
Nesta condi¸c˜ao, os equipamentos G&T operam pr´oxi-
mos `a sua capa-cidade m´axima, estando os consumido-
res mais sujeitos a interrup¸c˜oes.
Tabela 3: Parˆametros dos Componentes G&T - Carga
Pico
Parˆametros
Intervalo de Potˆencia
1
2
3
4
λ [falhas/ano]
9,609
2,939
3,159
4,763
r [horas]
35,646
39,366
46,256
28,360
U [horas/ano]
342,562
115,724
146,153
135,08
A Tabela 3 apresenta os parˆametros obtidos com a simu-
la¸c˜ao Monte Carlo n˜ao-seq¨uencial para os componentes
G&T ﬁct´ıcios; os quais est˜ao expressos em fun¸c˜ao de λ,
re U associados com os intervalos de potˆencia. Estes in-
tervalos s˜ao deﬁnidos de acordo com a pol´ıtica de corte
de carga e da capacidade de potˆencia dos alimentadores
princi-pais do sistema de distribui¸c˜ao, como mostrado
Revista Controle & Automa¸c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003 267

Tabela 5:´Indices para Pontos de Carga em Carga Pico
SISTEMA
FIC
DIC
r
EENS
LOLC
LP-1
G&T
20,4730
739,6046
36,1259
641089,20
128217,80
Distrib.
0,2442
3,5932
14,7114
3114,63
622,93
NH3
20,7172
743,1978
35,8734
644203,90
128840,80
LP-9
G&T
10,8630
397,0081
36,5468
743238,80
2378364,00
Distrib.
0,1448
0,5098
3,5215
954,36
4636,49
NH3
11,0078
397,5178
36,1125
744193,10
2381418,00
LP-12
G&T
7,9230
281,2603
35,4992
205066,90
41013,37
Distrib.
0,2605
3,6625
14,0588
2670,36
534,07
NH3
8,1835
284,9228
34,8167
207737,20
41547,45
LP-21
G&T
4,7630
135,0787
28,3600
123826,60
1077292,00
Distrib.
0,2573
3,5943
13,9703
3294,93
28665,87
NH3
5,0203
138,6730
27,6225
127121,60
1105958,00
na Tabela 4.
Tabela 4: Potˆencia Pico dos ramais e Pol´ıtica de C.C.
Potˆencia do
Corte de Carga
Desconecta
Ramal [MW]
devido a G&T
o Ramal
R1
5,93
0 <C C GT ≤ 5,93
R1
R2
3,50
5,93 <C C GT ≤ 9,43
R1 + R2
R3
5,06
9,43 <C C GT ≤ 14,5
R1+R2+R3
R4
5,51
14,5 <C C GT ≤ 20,0
R1+R2+R3+R4
Observa-se que o intervalo de potˆencia 1 (de 0 a 5,934
MW), que corresponde ao Ramal 1, possui a maior taxa
de falha (λ). Este resultado era de se esperar, pois qual-
quer falha no sistema de alta tens˜ao da Barra 6 do IEEE-
RTS, retira de opera¸c˜ao o Ramal 1. Nota-se tamb´em que
ar e m o ¸c˜ao de todos os 4 ramais (i.e. R1+R2+R3+R4,
que corresponde ao intervalo de potˆencia de 14,491 a
20,0 MW) possui a segunda maior taxa de falha, o que
s i g n i ﬁ caq u eaf r e q¨uˆencia com que ocorrem estes cortes
no sistema G&T da Barra 6 ´e bastante signiﬁcante.
A Tabela 5 exibe os ´ındices de conﬁabilidade para os
pontos de carga LP-1, LP-9, LP-12 e LP-21, que per-
tencem aos ramais 1, 2, 3 e 4, respectivamente. Os
valores apresentados consideram os ´ındices b´asicos FIC
(falhas/ano), DIC (horas/ano), r (horas) mais os ´ındi-
ces EENS (MWh/ano) e LOLC (US$/ano). Todos os
´ındices do NH3 s˜ao fornecidos na situa¸c˜ao de carga pico
e suas contribui¸c˜oes s˜ao desagregadas em G&T e distri-
bui¸c˜ao.
Ao analisar a Tabela 5, pode-se identiﬁcar claramente a
pol´ı t i cap a r aco r t e sd e v i d oa os i s t e m aG & T .O b s e r v a - s e
que, a taxa de falha do Ramal 1 (igual a do LP-1) possui
um valor maior (i.e. 20,473 falhas/ano) que a do Ramal
2 (i.e. 10,863 falhas/ ano) que, por sua vez, ´e maior
que a do Ramal 3 e assim por diante, de acordo com a
pol´ıtica de corte de carga adotada.
Tabela 6:´Indices do Sistema para Carga Pico
SISTEMA
FEC
DEC
EENS
LOLC
G&T
11,1845
390,3521
7943191
36716580,00
Distrib.
0,2532
3,6239
61607
304873,50
NH3
11,4377
393,9759
8004796
37018730,00
Outro ponto que pode ser observado, ´e que a contribui-
¸c˜ao das falhas originadas do sistema G&T ´em u i t om a i s
consider´avel que aquelas oriundas do sistema de distri-
bui¸c˜ao. Deve-se salientar que, neste trabalho, o sistema
G&T ´e analisado por um algoritmo que utiliza ﬂuxo de
carga durante a simula¸c˜ao Monte Carlo, enquanto o de-
sempenho do sistema de distribui¸c˜ao ´e avaliado pelo cri-
t´erio de continuidade.
A Tabela 6 apresenta os resultados obtidos para os ´ın-
dices do sistema, FEC (interrup¸c˜oes/consumidor ano),
DEC (horas/ consumidor ano), EENS (MWh/ano) e
LOLC (US$/ano). Todos os ´ındices NH3 obtidos na si-
tua¸c˜ao de carga pico tamb´em s˜ao desagregados nas con-
tribui¸c˜oes devido aos sistemas G&T e distribui¸c˜ao. Por
exemplo, o´ındice FEC para todo o sistema (i.e. NH3) ´e
igual a 11,4377 interrup-¸c˜oes/consumidor, onde 11,1845
interrup¸c˜oes ´e procedente do sistema G&T e somente
0,2532 interrup¸c˜oes origina-se do sistema de distribui-
¸c˜ao.
Analisando os resultados obtidos nas Tabelas 5 e 6,
pode-se concluir que o sistema de G&T e o sistema de
distribui¸c˜ao se comportam como dois componentes in-
dependentes conectados em s´erie. A independˆencia dos
dois sistemas deve-se ao fato de se ter assumido que
todos os equipamentos do sistema de distribui¸c˜ao (i.e.
linhas, transformadores, etc.) s˜ao capazes de suportar a
energia solicitada. Esta restri¸c˜ao, contudo, ´ed e v i d oa o
crit´erio de continuidade, que ´e amplamente utilizado na
268 Revista Controle & Automa¸ c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003

avalia¸c˜ao de sistemas de distribui¸c˜ao.
4.3 An´ alise NH3 para Carga M´edia
Esta an´alise considera a situa¸c˜ao de carga m´edia. Os
equipamentos G&T est˜ao operando mais aliviados e,
portanto, espera-se um desempenho muito melhor para
o NH2. O procedimento descrito em 4.2 ´e repetido con-
siderando a carga m´edia, e os resultados para os´ındices
do sistema s˜ao mostrados na Tabela 7.
Tabela 7:´Indices do Sistema para Carga M´edia
SISTEMA
FEC
DEC
EENS
LOLC
G&T
0,0200
15,3600
188789,8
876582,90
Distrib.
0,2532
3,6239
37862,0
186782,00
NH3
0,2732
18,9839
226651,7
1061694,00
Com o intuito de combinar os resultados obtidos com a
carga Pico e M´edia, ser´a suposto que a dura¸c˜ao do pico
di´ario de carga ser´a de aproximadamente 1 hora. Por-
tanto, se o conjunto dos ´ındices anteriores forem pon-
derados nesta propor¸c˜ao, i.e. (1/24) para carga pico, e
(23/24) para carga m´edia, que ser´a denominado como
carga fora de pico, ser´ap o s s ´ıvel determinar um con-
junto de ´ındices equivalentes (EQ): e.g. o equivalente
FECG&T = 0,4852 e o equivalente FEC Dist.= 0,2532
interrup-¸c˜oes/consumidor ano. Assim, pode-se dizer que
65,71% das interrup¸c˜oes por consumidor s˜ao originadas
no sistema G&T, enquanto que 34,29% s˜ao oriundas do
sistema de distribui¸c˜ao.
Podemos observar que neste exemplo, o impacto de fa-
lhas G&T foi superior ao das falhas originadas no sis-
tema de distribui¸c˜ao. Obviamente, este ´eu me x e m p l o
hipot´e t i coco mai n t e n ¸c˜ao de demonstrar o potencial da
metodologia proposta, visto que em sistemas reais, como
mencionado na Introdu¸c˜ao, os sistemas de distribui¸c˜ao
s˜ao respons´aveis pela maior parte das contribui¸c˜oes indi-
viduais que acarretam indisponibilidade de fornecimento
para os consumidores.
4.4 Inﬂuˆ e n c i ad aP o l ´ıtica de Corte de Carga
Para avaliar a inﬂuˆencia da pol´ıtica de corte de carga
no n´ıvel de distribui¸c˜ao, a Tabela 8 apresenta uma nova
pol´ıtica, onde o Ramal 3 ´e o primeiro a ser desconectado
, seguido por R4, R1 e ﬁnalmente R2. Deve-se ressaltar
que foi utilizada a mesma pol´ıtica para cortes no sistema
G&T. Portanto, n˜ao existe a necessidade de uma nova
simula¸c˜ao no NH2. A ´unica mudan¸ca´e um remaneja-
mento nos intervalos de potˆencia no sentido de deﬁnir
novos parˆametros ﬁct´ıcios para os componentes G&T. A
estrutura do sistema G&T equivalente ´eam e s m am o s -
t r a d an aF i g u r a5 .
Tabela 8:´Indices do Sistema para Carga M´edia
Potˆencia do
C o r t ed eC a r g a
Desconecta
Ramal[MW]
devido a G&T
o Ramal
R1
5,93
0 <C C GT ≤ 5,06
R3
R2
3,50
5,06 <C C GT ≤ 10,6
R3+R4
R3
5,06
10,6 <C C GT ≤ 16,5
R3+R4+R1
R4
5,51
16,5 <C C GT ≤ 20,0
R3+R4+R1+R2
A Tabela 9 apresenta os resultados para os´ındices do sis-
tema obtidos com esta nova pol´ıtica de corte de carga.
Comparando os resultados das Tabela 6 e 9, pode-se
veriﬁcar que os ´ındices relacionados com o sistema de
distribui¸c˜ao n˜ao sofreram altera¸c˜oes. Isto ocorre por-
que a conﬁabilidade inerente ao sistema de distribui¸c˜ao
depende somente das caracter´ısticas das falhas de seus
pr´oprios componentes. Por outro lado, observa-se uma
altera¸c˜ao nos´ındices referentes ao sistema G&T e, con-
sequentemente dos´ındices NH3. De fato, o sistema com
esta nova pol´ıtica torna-se mais custoso do ponto de
vista das interrup¸c˜oes.
Tabela 9:´Indices do Sistema para Carga Pico
SISTEMA
FEC
DEC
EENS
LOLC
G&T
13,0544
463,3618
7828792
37539720,00
Distrib.
0,2532
3,6239
61607
304873,50
NH3
13,3076
466,9857
7890399
37841880,00
5 CONCLUS ˜OES
O sistema de distribui¸c˜ao realiza uma importante fun¸c˜ao
dentro do fornecimento total de energia, pois providen-
ci aaco n e x ˜ao ﬁnal entre as companhias de transmiss˜ao e
seus consumidores. Em muitos pa´ıses, o processo de pri-
vatiza¸c˜ao iniciou-se pelas companhias de distribui¸c˜ao. O
novo modelo imp˜oe uma mudan¸ca relevante em rela¸c˜ao
ao passado, onde a maioria das empresas de eletricidade
era estatizada. A estrutura legal que se sup˜oe ser a base
p a r aoa m b i e n t eco m p e t i t i v oi d e a l i z a d op a r aos e t o re l ´e-
trico, ainda n˜ao est´a totalmente implementada. Por´em,
as companhias de distribui¸c˜ao j´ae s t ˜ao sendo pressio-
nadas pela opini˜ao p´ublica, e tamb´em pelas comiss˜oes
ea g ˆencias regula-doras, para melhorar a qualidade dos
servi¸cos contratados por seus consumidores. Com esta
nova mentalidade, normas, incentivos, penaliza¸c˜oes, res-
ponsabilidades etc. ir˜ao se tornar pontos fundamentais
na discuss˜ao sobre o funcionamento dos sistemas el´etri-
cos de potˆencia em todo o mundo.
A avalia¸c˜ao integrada da conﬁabilidade, incluindo ge-
ra¸c˜ao, transmiss˜ao e distribui¸c˜ao, ou N´ıvel Hier´arquico
Revista Controle & Automa¸c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003 269

3 (NH3), possui um importante papel no novo cen´a-
rio competitivo, pois providencia uma vis˜ao mais abran-
gente do sistema em termos de desempenho passado ou
futuro. O presente trabalho fornece uma contribui¸c˜ao
na ´area da conﬁabilidade NH3, atrav´es do c´alculo de´ın-
dices, incluindo custos, que avaliam o desempe-nho total
do sistema. A metodologia proposta ´e baseada na com-
bina¸c˜ao da simula¸c˜ao de Monte Carlo com o conceito
tradicional de minimum cut-set . ´Indices tradicionais,
como FEC, DEC, etc. e tamb´em a LOLC, que repre-
senta o custo de interrup¸c˜ao, s˜ao desagregados consi-
derando os n´ıveis hier´arquicos. Por ﬁm, a metodologia
proposta est´a sendo testada em sistemas de distribui¸c˜ao
da CEMIG.
REFERˆENCIAS
Allan, R.N. and Da Silva, M.G. (1995). Evaluation of
Reliability Indices and Outage Costs in Distribu-
tion Systems. IEEE Transactions on Power Sys-
tems, Vol. 10, No. 1, pp. 413-419.
Allan, R.N., Billinton, R., Sjarief, I., Goel, L., So, K.S.
(1991). A Reliability Test System for Educational
Purposes - BasicDistribution System Data and Re-
sults. IEEE Trans. on Power Systems , Vol. 6, No.
2, pp. 813-820.
Billinton, R. (1988). Distribution System Reliability
Performance and Evaluation.Electrical Power and
Energy Systems, Vol. 10, No. 3, pp. 190-200.
Billinton, R. and Alan, R.N. (1994). Reliability Evalu-
ation of Power Systems . Plenum Press, NY, 2nd
edition.
Billinton, R. and Allan, R.N. (1988). Reliability Assess-
ment of Large Electric Power Systems. Kluwer Aca-
demicPub., Boston.
Billinton, R. and Allan, R.N. (1992).Reliability Evalua-
tion of Engineering Systems - Concepts and Tech-
niques. Plenum Press, NY, 2nd edition.
Billinton, R. and Jonnavithula, S. (1996). A Test Sys-
tem for Teaching Overall Power System Reliability
Assessment. IEEE Transactions on Power Systems,
Vol. 11, No. 4, pp. 1670-1676.
Billinton, R. and Satish, J. (1996). Eﬀect of Rotational
Load Shedding on Overall Power System Adequacy
Indices. IEE Proceedings, Part C , Vol. 143, No. 2
pp. 181-187.
Burns, S. and Gross, G. (1990). Value of Service Relia-
bility. IEEE Transactions on Power Systems ,V o l .
5, No.3, pp. 825-834.
Chowdhury, A.A. and Koval, D.O. (1998). Value-based
Distribution System Reliability Planning. IEEE
Transactions on Industry Applications, Vol. 34, No.
1, pp.23-29.
EPRI, Customer Demand for Service Reliability, Report
RP-2801, 1989.
Goel, L. and Billinton, R. (1993). Utilization of Inter-
rupted Energy Assessment Rates to Evaluate Re-
liability Worth in Electrical Power Systems.IEEE
Transactions on Power Systems , Vol. 8, No. 3, pp.
929-936.
Leite da Silva, A.M., Cassula, A.M., Billinton, R.,
Manso, L.A.F. Integrated Reliability Evaluation
of Generation, Transmission and Distribution Sys-
tems. IEE Proceed-ings, Part C , Vol. 149, No. 1,
pp. 1-6.
Leite da Silva, A.M., Manso, L.A.F., Mello, J.C.O.,
Billinton, R. (2000). Pseudo-chronological Simula-
tion for Composite Reliability Analysis with Time
Varying Loads. IEEE Transactions on Power Sys-
tems, Vol. 15, No. 1, pp. 73-80.
Leite da Silva, A.M., Melo, A.C.G. and Cunha, S.H.F.
(1991). Frequency and Duration Method for Relia-
bility Evaluation of Large-scale Hydrothermal Ge-
nerating Systems. IEE Proceedings, Part C ,V o l .
138, No. 1, pp. 94-102.
Manso, L.A.F., Leite da Silva, A. M., Mello, J. C.
O. (1999). Comparison of Alternative Methods for
Evaluating Loss of Load Costs in Generation and
Transmission System. Electric Power Systems Re-
search, Vol. 50, Issue 2, pp. 107-114.
Mello, J. C. O., Leite da Silva, A. M., Pereira, M. V. F.
(1997). Eﬃcient Loss of Load Cost Evaluation by
Combined Pseudo-sequential and State Transition
Simulation. IEE Proceedings, Part C, Vol. 144, No.
2, pp. 147-154.
Mello, J.C.O., Pereira, M.V.F., Leite da Silva, A.M.
(1994). Evaluation of Reliability Worth in Com-
posite Systems Based on Pseudo-sequential Monte
Carlo Simulation.IEEE Transaction on Power Sys-
tems, Vol. 9, No. 3, pp. 1318-1326.
Melo, A.C.G., Pereira, M.V. and Leite da Silva, A.M.
(1993). A Conditional Probability Approach to the
Calculation of Frequency and Duration Indices in
Composite Reliability Evaluations.IEEE Transac-
tions on Power Systems , Vol. 8, No. 3, pp. 1118-
1125
270 Revista Controle & Automa¸ c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003

Task Force of the Application of Probability Methods
Subcommittee. (1979). IEEE Reliability Test Sys-
tem. IEEE Transactions on Power Apparatus Sys-
tems., Vol. PAS-98, No. 6, pp. 2047-2054.
Wenyuan, Li and Billinton, R. (1993). A Minimum Cost
Assessment Method for Composite Generation and
Transmission System Expansion Planning. IEEE
Trans. on Power Systems , Vol. 8, No. 2, pp. 628-
635.
Revista Controle & Automa¸c˜ao/Vol.14 no.3/Julho, Agosto e Setembro 2003 271

## Aplicação para a Smart Control Brasil

Este material deve apoiar respostas técnicas da LÍVIA sobre manutenção, automação, confiabilidade, diagnóstico, TPM, FMEA, falhas ou engenharia, conectando conceitos à aplicação prática da Smart Control Brasil.

A LÍVIA não deve usar este material para prometer preço, prazo, estoque, garantia ou resultado comercial.
